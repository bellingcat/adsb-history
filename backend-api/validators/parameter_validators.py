"""
Parameter validation functions for ADS-B API endpoints.

This module provides reusable validation functions that can be used
across different endpoints to ensure consistent parameter validation.
"""

from datetime import datetime
from typing import Optional, Tuple, List
from flask import jsonify


class ValidationError(Exception):
    """Custom exception for validation errors with HTTP status code."""
    
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def validate_bounding_box(bbox_str: str) -> Tuple[float, float, float, float]:
    """
    Validate and parse bounding box coordinates.
    
    Args:
        bbox_str: Bounding box string in format "min_lon,min_lat,max_lon,max_lat"
        
    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat)
        
    Raises:
        ValidationError: If bbox format is invalid
    """
    try:
        coords = [float(x) for x in bbox_str.split(',')]
        if len(coords) != 4:
            raise ValidationError("Bounding box must be in format: min_lon,min_lat,max_lon,max_lat")
        
        min_lon, min_lat, max_lon, max_lat = coords
        
        # Validate coordinate ranges
        if not -180 <= min_lon <= 180 or not -180 <= max_lon <= 180:
            raise ValidationError("Longitude must be between -180 and 180 degrees")
        if not -90 <= min_lat <= 90 or not -90 <= max_lat <= 90:
            raise ValidationError("Latitude must be between -90 and 90 degrees")
        
        return min_lon, min_lat, max_lon, max_lat
    except ValueError:
        raise ValidationError("Invalid bounding box coordinates")


def validate_hex_code(hex_code: str) -> str:
    """
    Validate aircraft hex code format.
    
    Args:
        hex_code: Aircraft hex identifier
        
    Returns:
        The validated hex code
        
    Raises:
        ValidationError: If hex code format is invalid
    """
    if not all(c in '~0123456789ABCDEFabcdef' for c in hex_code):
        raise ValidationError("Invalid hex code format. Must contain only hexadecimal characters")
    return hex_code


def validate_flight_code(flight_code: str) -> str:
    """
    Validate flight code format.
    
    Args:
        flight_code: Flight number/call sign
        
    Returns:
        The validated flight code
        
    Raises:
        ValidationError: If flight code format is invalid
    """
    if not all(c.isalnum() or c in '-_' for c in flight_code):
        raise ValidationError("Invalid flight code format")
    return flight_code


def validate_iso_datetime(datetime_str: str) -> datetime:
    """
    Validate and parse ISO 8601 datetime string.
    
    Args:
        datetime_str: ISO 8601 timestamp string
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValidationError: If datetime format is invalid
    """
    try:
        return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    except ValueError:
        raise ValidationError("Invalid datetime format. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)")


def validate_altitude(altitude_str: str) -> int:
    """
    Validate altitude parameter.
    
    Args:
        altitude_str: Altitude string
        
    Returns:
        Validated altitude as integer
        
    Raises:
        ValidationError: If altitude format is invalid
    """
    if not altitude_str.isdigit():
        raise ValidationError("Altitude must be a positive integer")
    return int(altitude_str)


def _validate_numeric_range(value_str: str, min_val: float, max_val: float, param_name: str) -> float:
    """
    Helper function to validate numeric parameters within a range.
    
    Args:
        value_str: String value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        param_name: Name of parameter for error messages
        
    Returns:
        Validated numeric value
        
    Raises:
        ValidationError: If format or range is invalid
    """
    try:
        numeric_val = float(value_str)
        if numeric_val < min_val or numeric_val > max_val:
            raise ValidationError(f"{param_name} must be between {min_val} and {max_val}")
        return numeric_val
    except ValueError:
        raise ValidationError(f"{param_name} must be a number")


def validate_bearing(bearing_str: str) -> float:
    """
    Validate bearing parameter (0-360 degrees).
    
    Args:
        bearing_str: Bearing string
        
    Returns:
        Validated bearing as float
        
    Raises:
        ValidationError: If bearing format or range is invalid
    """
    return _validate_numeric_range(bearing_str, 0, 360, "Bearing")


def validate_speed(speed_str: str) -> float:
    """
    Validate speed parameter (positive number).
    
    Args:
        speed_str: Speed string
        
    Returns:
        Validated speed as float
        
    Raises:
        ValidationError: If speed format or range is invalid
    """
    return _validate_numeric_range(speed_str, 0, float('inf'), "Speed")





def validate_pagination(limit_str: str = "1000", offset_str: str = "0", max_limit: int = 10000) -> Tuple[int, int]:
    """
    Validate pagination parameters.
    
    Args:
        limit_str: Limit string (default: "1000")
        offset_str: Offset string (default: "0")
        max_limit: Maximum allowed limit (default: 10000)
        
    Returns:
        Tuple of (limit, offset)
        
    Raises:
        ValidationError: If pagination parameters are invalid
    """
    try:
        limit = min(int(limit_str), max_limit)
        offset = max(int(offset_str), 0)
        return limit, offset
    except ValueError:
        raise ValidationError("Invalid limit or offset parameters")


def validate_boolean_param(param_str: str) -> bool:
    """
    Validate boolean parameter from string.
    
    Args:
        param_str: Boolean parameter as string ("true"/"false")
        
    Returns:
        Boolean value
        
    Raises:
        ValidationError: If boolean format is invalid
    """
    if param_str.lower() == 'true':
        return True
    elif param_str.lower() == 'false':
        return False
    else:
        raise ValidationError("Boolean parameter must be 'true' or 'false'")


class ParameterValidator:
    """
    Parameter validation helper class for request parameters.
    
    This class provides a convenient interface for validating multiple
    parameters and collecting validation errors.
    """
    
    def __init__(self, request_args: dict):
        self.args = request_args
        self.errors = []
    
    def _validate_optional_param(self, param_name: str, validation_func, default=None):
        """
        Generic method to validate an optional parameter.
        
        Args:
            param_name: Name of the parameter to validate
            validation_func: Function to use for validation
            default: Default value to return if parameter is missing
            
        Returns:
            Validated value or default if parameter is missing
        """
        param_value = self.args.get(param_name)
        if param_value:
            try:
                return validation_func(param_value)
            except ValidationError as e:
                self.errors.append(e.message)
        return default
    
    def _validate_range_params(self, min_param: str, max_param: str, validation_func):
        """
        Generic method to validate min/max range parameters.
        
        Args:
            min_param: Name of the minimum parameter
            max_param: Name of the maximum parameter
            validation_func: Function to use for validation
            
        Returns:
            Tuple of (min_value, max_value) where either can be None
        """
        min_val = self._validate_optional_param(min_param, validation_func)
        max_val = self._validate_optional_param(max_param, validation_func)
        return min_val, max_val
    
    # Simplified validation methods using the generic approach
    def validate_optional_bbox(self, param_name: str = 'bbox'):
        """Validate optional bounding box parameter."""
        return self._validate_optional_param(param_name, validate_bounding_box)
    
    def validate_optional_hex(self, param_name: str = 'hex'):
        """Validate optional hex code parameter."""
        return self._validate_optional_param(param_name, validate_hex_code)
    
    def validate_optional_flight(self, param_name: str = 'flight'):
        """Validate optional flight code parameter."""
        return self._validate_optional_param(param_name, validate_flight_code)
    
    def validate_optional_datetime(self, param_name: str):
        """Validate optional datetime parameter."""
        return self._validate_optional_param(param_name, validate_iso_datetime)
    
    def validate_optional_altitude_range(self):
        """Validate optional altitude range parameters."""
        return self._validate_range_params('min_alt', 'max_alt', validate_altitude)
    
    def validate_optional_bearing_range(self):
        """Validate optional bearing range parameters."""
        return self._validate_range_params('min_bearing', 'max_bearing', validate_bearing)
    
    def validate_optional_speed_range(self):
        """Validate optional speed range parameters."""
        return self._validate_range_params('min_speed', 'max_speed', validate_speed)
    
    def validate_optional_military(self):
        """Validate optional military parameter."""
        return self._validate_optional_param('military', validate_boolean_param)
    
    def validate_pagination(self, max_limit: int = 10000):
        """Validate pagination parameters."""
        limit_str = self.args.get('limit', '1000')
        offset_str = self.args.get('offset', '0')
        
        try:
            return validate_pagination(limit_str, offset_str, max_limit)
        except ValidationError as e:
            self.errors.append(e.message)
            return 1000, 0  # Return defaults on error
    
    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return len(self.errors) > 0
    
    def get_error_response(self):
        """Get Flask JSON error response for validation errors."""
        if self.errors:
            return jsonify({"error": "; ".join(self.errors)}), 400
        return None
