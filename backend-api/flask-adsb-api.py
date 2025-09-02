from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
import os
from functools import wraps
from dotenv import load_dotenv
from firebase_utils import verify_firebase_token
from loguru import logger
import sys
from validators.parameter_validators import ParameterValidator, ValidationError

# Load environment variables
load_dotenv()

# Configure loguru
log_file = os.environ.get('LOG_FILE', 'adsb_api.log')
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO")  # Add stderr handler
logger.add(log_file, rotation="10 MB", retention="1 week", level="DEBUG")  # Add file handler

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database connection parameters - these should be set as environment variables in production
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'adsb')
DB_USER = os.environ.get('DB_USER', 'dbuser')
DB_PASS = os.environ.get('DB_PASS', 'dbpassword')
DB_PORT = os.environ.get('DB_PORT', '5432')

# DB SCHEMA
'''
                                                      Table "public.adsb"
    Column    |           Type           | Collation | Nullable | Default | Storage  | Compression | Stats target | Description
--------------+--------------------------+-----------+----------+---------+----------+-------------+--------------+-------------
 t            | timestamp with time zone |           |          |         | plain    |             |              |
 hex          | text                     |           |          |         | extended |             |              |
 flight       | text                     |           |          |         | extended |             |              |
 alt          | bigint                   |           |          |         | plain    |             |              |
 gs           | double precision         |           |          |         | plain    |             |              |
 geom         | geometry                 |           |          |         | main     |             |              |
 bearing      | double precision         |           |          |         | plain    |             |              |
 registration | text                     |           |          |         | extended |             |              |
 typecode     | text                     |           |          |         | extended |             |              |
 category     | text                     |           |          |         | extended |             |              |
 military     | boolean                  |           |          |         | plain    |             |              |
'''

def get_db_connection():
    """Create and return a database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )


def require_firebase_auth(f):
    """Decorator to require a valid Firebase token for each request"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning("Unauthorized request: No Authorization header")
            return jsonify({"error": "Authorization header is required"}), 401
        
        # Check if the header is in the format "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != 'Bearer':
            logger.warning("Unauthorized request: Invalid Authorization header format")
            return jsonify({"error": "Invalid Authorization header format"}), 401
        
        token = parts[1]
        
        # Verify the Firebase token
        decoded_token = verify_firebase_token(token)
        
        if not decoded_token:
            logger.warning("Unauthorized request: Invalid or expired token")
            return jsonify({"error": "Invalid or expired token"}), 403
        
        # Add the user info to the request context
        request.user = decoded_token
        
        # Log the authenticated request with email
        email = decoded_token.get('email', 'unknown')
        logger.info(f"Authenticated request from {email} to {request.endpoint}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def log_performance_warning(email, category, has_constraints=True):
    """Log performance warnings for potentially expensive queries"""
    if category and category.lower() in ['uav', 'general aviation', 'airliner']:
        if not has_constraints:
            logger.warning(f"Large category filter '{category}' requested by {email} without time/geographic constraints. This may be slow.")
        else:
            logger.info(f"Large category filter '{category}' requested by {email} with constraints.")

def validate_params(f):
    """Decorator to validate request parameters using the validation module"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            validator = ParameterValidator(request.args)
            
            if request.endpoint == 'get_by_bbox':
                # Validate bbox endpoint parameters
                validator.validate_optional_bbox()
                validator.validate_optional_hex()
                validator.validate_optional_flight()
                validator.validate_optional_datetime('start_time')
                validator.validate_optional_datetime('end_time')
                validator.validate_optional_altitude_range()
                validator.validate_optional_bearing_range()
                validator.validate_optional_speed_range()
                validator.validate_optional_military()
                validator.validate_pagination(max_limit=1000000)  # Cap at 1,000,000 records
                

            elif request.endpoint == 'get_intersecting_bboxes':
                # Validate intersect bboxes endpoint parameters
                validator.validate_optional_bbox('bbox1')
                validator.validate_optional_bbox('bbox2')
                validator.validate_optional_hex()
                validator.validate_optional_flight()
                validator.validate_optional_datetime('start_time')
                validator.validate_optional_datetime('end_time')
                validator.validate_optional_altitude_range()
                validator.validate_optional_speed_range()
                validator.validate_optional_military()
                validator.validate_pagination(max_limit=1000000)
                
                # Check required bbox parameters for intersect endpoint
                if not all([request.args.get('bbox1'), request.args.get('bbox2')]):
                    validator.errors.append("bbox1 and bbox2 are required")
            
            # Return error response if validation failed
            if validator.has_errors():
                return validator.get_error_response()
            
            return f(*args, **kwargs)
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return decorated_function

@app.route('/api/adsb/bbox', methods=['GET'])
@require_firebase_auth
@validate_params
def get_by_bbox():
    """
    Get ADS-B data points within a geographic bounding box with optional filters
    
    Query Parameters:
    - bbox (optional): Bounding box in format "min_lon,min_lat,max_lon,max_lat"
    - hex (optional): Aircraft hex identifier
    - flight (optional): Flight number/call sign
    - start_time (optional): ISO 8601 timestamp (YYYY-MM-DDTHH:MM:SSZ)
    - end_time (optional): ISO 8601 timestamp (YYYY-MM-DDTHH:MM:SSZ)
    - min_alt (optional): Minimum altitude in feet
    - max_alt (optional): Maximum altitude in feet
    - min_bearing (optional): Minimum bearing in degrees (0-360)
    - max_bearing (optional): Maximum bearing in degrees (0-360)
    - min_speed (optional): Minimum speed in knots
    - max_speed (optional): Maximum speed in knots
    - military (optional): Filter for military aircraft (true/false)
    - category (optional): Filter by aircraft category
    - limit (optional): Maximum number of records to return (default: 1000)
    - offset (optional): Number of records to skip (default: 0)
    
    Returns:
    - Standard ADS-B fields: t, hex, flight, alt, gs, type, bearing, geom
    """
    try:
        # Log request parameters with user email
        email = request.user.get('email', 'unknown')
        logger.info(f"API Request from {email}: /api/adsb/bbox - Parameters: {dict(request.args)}")
        
        # Get parameters
        bbox = request.args.get('bbox')
        hex_code = request.args.get('hex')
        flight_code = request.args.get('flight')
        
        base_query = """
            SELECT 
                t, 
                adsb.hex, 
                adsb.flight,
                adsb.alt, 
                adsb.gs, 
                ST_X(geom) AS lon,
                ST_Y(geom) AS lat,
                adsb.bearing,
                adsb.registration,
                adsb.typecode,
                adsb.category,
                adsb.military,
                modes.owner,
                modes.aircraft
            FROM adsb
            LEFT JOIN modes ON adsb.hex = modes.hex
            WHERE 1=1
        """
        
        params = []
        conditions = []
        
        # Add bbox condition if provided
        if bbox:
            try:
                min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(','))
                base_query += " AND ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                params.extend([min_lon, min_lat, max_lon, max_lat])
            except ValueError:
                logger.error(f"Invalid bbox format from {email}: {bbox}")
                return jsonify({"error": "Invalid bbox format. Expected format: min_lon,min_lat,max_lon,max_lat"}), 400
        
        # Add hex condition if provided
        if hex_code:
            base_query += " AND adsb.hex = %s"
            params.append(hex_code)
        
        # Add flight condition if provided
        if flight_code:
            base_query += " AND TRIM(flight) = %s"
            params.append(flight_code)
        
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        min_alt = request.args.get('min_alt')
        max_alt = request.args.get('max_alt')
        min_bearing = request.args.get('min_bearing')
        max_bearing = request.args.get('max_bearing')
        min_speed = request.args.get('min_speed')
        max_speed = request.args.get('max_speed')
        military = request.args.get('military')
        category = request.args.get('category')
        typecode = request.args.get('typecode')
        
        # Pagination parameters
        limit = request.args.get('limit', '1000')
        offset = request.args.get('offset', '0')
        
        try:
            limit = min(int(limit), 1000000)  # Cap at 1,000,000 records
            offset = max(int(offset), 0)
        except ValueError:
            logger.error(f"Invalid limit/offset from {email}: limit={limit}, offset={offset}")
            return jsonify({"error": "Invalid limit or offset parameters"}), 400
        
        # Add optional time constraints
        if start_time:
            conditions.append("t >= %s")
            params.append(datetime.fromisoformat(start_time.replace('Z', '+00:00')))
        
        if end_time:
            conditions.append("t <= %s")
            params.append(datetime.fromisoformat(end_time.replace('Z', '+00:00')))
        
        # Add optional altitude constraints
        if min_alt:
            conditions.append("alt >= %s")
            params.append(int(min_alt))
        
        if max_alt:
            conditions.append("alt <= %s")
            params.append(int(max_alt))
        
        # Add optional bearing constraints
        if min_bearing and max_bearing:
            # Handle cases where bearing range crosses 0/360 boundary
            min_b = float(min_bearing)
            max_b = float(max_bearing)
            
            if min_b <= max_b:
                conditions.append("bearing BETWEEN %s AND %s")
                params.extend([min_b, max_b])
            else:
                # Range crosses the 0/360 boundary
                conditions.append("(bearing >= %s OR bearing <= %s)")
                params.extend([min_b, max_b])
        elif min_bearing:
            conditions.append("bearing >= %s")
            params.append(float(min_bearing))
        elif max_bearing:
            conditions.append("bearing <= %s")
            params.append(float(max_bearing))

        # Add optional speed constraints
        if min_speed:
            conditions.append("gs >= %s")
            params.append(float(min_speed))
        if max_speed:
            conditions.append("gs <= %s")
            params.append(float(max_speed))
        
        # Add military filter if provided
        if military is not None:
            if military.lower() == 'true':
                conditions.append("adsb.military = true")
            elif military.lower() == 'false':
                conditions.append("adsb.military = false")
        
        # Add category filter if provided
        if category:
            conditions.append("adsb.category = %s")
            params.append(category)
        
        # Add typecode filter if provided
        if typecode:
            conditions.append("adsb.typecode = %s")
            params.append(typecode)
        
        # Log performance warning for large categories
        has_constraints = bool(bbox or start_time or end_time or min_alt or max_alt or min_bearing or max_bearing or min_speed or max_speed)
        log_performance_warning(email, category, has_constraints)
        
        # Append all conditions to query
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Add order, limit and offset
        base_query += " ORDER BY t DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Log the final query with parameters
        logger.debug(f"SQL Query from {email}: {base_query}")
        logger.debug(f"Query Parameters from {email}: {params}")
        
        # Log the final query with parameters substituted
        try:
            # Create a copy of the query for logging
            debug_query = base_query
            # Replace each %s with the corresponding parameter
            for param in params:
                if isinstance(param, str):
                    # Escape single quotes in strings
                    param = param.replace("'", "''")
                    debug_query = debug_query.replace("%s", f"'{param}'", 1)
                elif isinstance(param, (int, float)):
                    debug_query = debug_query.replace("%s", str(param), 1)
                elif isinstance(param, datetime):
                    debug_query = debug_query.replace("%s", f"'{param.isoformat()}'", 1)
                else:
                    debug_query = debug_query.replace("%s", str(param), 1)
            logger.debug(f"Final SQL Query with parameters from {email}: {debug_query}")
        except Exception as e:
            logger.warning(f"Failed to log final query with parameters from {email}: {str(e)}")
        
        # Execute query
        conn = get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(base_query, params)
                results = cur.fetchall()
                
                # Log the number of results
                logger.info(f"Query from {email} returned {len(results)} results")
                
                # Convert results to list of dictionaries and fix timestamp format
                formatted_results = []
                for row in results:
                    # Convert datetime to ISO format string
                    row['t'] = row['t'].isoformat()
                    formatted_results.append(dict(row))
        
        # Return results
        response = {
            "count": len(formatted_results),
            "results": formatted_results
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in /api/adsb/bbox from {email}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/adsb/metadata', methods=['GET'])
def get_metadata():
    """
    Get metadata about the ADS-B database including date range and record count
    """
    try:
        # Log request with user email if authenticated
        email = getattr(request, 'user', {}).get('email', 'unauthenticated')
        logger.info(f"API Request from {email}: /api/adsb/metadata")
        
        conn = get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Get date range and count
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_records,
                        MIN(t) as earliest_record,
                        MAX(t) as latest_record,
                        COUNT(DISTINCT hex) as unique_aircraft
                    FROM adsb
                """)
                stats = cur.fetchone()
                
                # Log the results
                logger.info(f"Metadata query from {email} returned: {stats}")
                
                # Convert datetime objects to strings
                stats['earliest_record'] = stats['earliest_record'].isoformat() if stats['earliest_record'] else None
                stats['latest_record'] = stats['latest_record'].isoformat() if stats['latest_record'] else None
                
                return jsonify(stats)
    
    except Exception as e:
        logger.error(f"Error in /api/adsb/metadata from {email}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/adsb/intersect_bboxes', methods=['GET'])
@require_firebase_auth
@validate_params
def get_intersecting_bboxes():
    """
    Find aircraft that were present in two different bounding boxes within a time interval
    
    Query Parameters:
    - bbox1 (required): First bounding box in format "min_lon,min_lat,max_lon,max_lat"
    - bbox2 (required): Second bounding box in format "min_lon,min_lat,max_lon,max_lat"
    - hex (optional): Aircraft hex identifier
    - flight (optional): Flight number/call sign
    - start_time (optional): ISO 8601 timestamp (YYYY-MM-DDTHH:MM:SSZ)
    - end_time (optional): ISO 8601 timestamp (YYYY-MM-DDTHH:MM:SSZ)
    - min_alt (optional): Minimum altitude in feet (for both bounding boxes)
    - max_alt (optional): Maximum altitude in feet (for both bounding boxes)
    - min_time_diff (optional): Minimum time difference between bbox1 and bbox2 in seconds
    - max_time_diff (optional): Maximum time difference between bbox1 and bbox2 in seconds
    - military (optional): Filter for military aircraft (true/false)
    - category (optional): Filter by aircraft category
    - limit (optional): Maximum number of records to return (default: 1000)
    - offset (optional): Number of records to skip (default: 0)
    
    Returns:
    - Standard ADS-B fields: t, hex, flight, lat, lon, squawk, alt, gs, type, bearing, geom
    - Aircraft metadata (from modes table): registration, manufacturer, typecode, aircraft_type, owner, operator, aircraft, category, military
    """
    try:
        # Log request parameters with user email
        email = request.user.get('email', 'unknown')
        logger.info(f"API Request from {email}: /api/adsb/intersect_bboxes - Parameters: {dict(request.args)}")
        
        # Get and validate parameters
        bbox1 = request.args.get('bbox1')
        bbox2 = request.args.get('bbox2')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        min_time_diff = request.args.get('min_time_diff')
        max_time_diff = request.args.get('max_time_diff')
        min_alt = request.args.get('min_alt')
        max_alt = request.args.get('max_alt')
        min_speed = request.args.get('min_speed')
        max_speed = request.args.get('max_speed')
        military = request.args.get('military')
        category = request.args.get('category')
        typecode = request.args.get('typecode')
        hex_code = request.args.get('hex')
        flight_code = request.args.get('flight')
        # Pagination parameters
        limit = request.args.get('limit', '1000')
        offset = request.args.get('offset', '0')

        try:
            limit = min(int(limit), 1000000)  # Cap at 1,000,000 records
            offset = max(int(offset), 0)
        except ValueError:
            logger.error(f"Invalid limit/offset from {email}: limit={limit}, offset={offset}")
            return jsonify({"error": "Invalid limit or offset parameters"}), 400

        if not all([bbox1, bbox2]):
            logger.error(f"Missing required bbox parameters from {email}: bbox1={bbox1}, bbox2={bbox2}")
            return jsonify({"error": "bbox1 and bbox2 are required"}), 400

        try:
            min_lon1, min_lat1, max_lon1, max_lat1 = map(float, bbox1.split(','))
            min_lon2, min_lat2, max_lon2, max_lat2 = map(float, bbox2.split(','))
            
            # Parse time parameters if provided
            start_dt = None
            end_dt = None
            if start_time:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

            # Validate altitude parameters
            if min_alt and not min_alt.isdigit():
                logger.error(f"Invalid min_alt from {email}: {min_alt}")
                return jsonify({"error": "min_alt must be a positive integer"}), 400
            if max_alt and not max_alt.isdigit():
                logger.error(f"Invalid max_alt from {email}: {max_alt}")
                return jsonify({"error": "max_alt must be a positive integer"}), 400
        except ValueError as e:
            logger.error(f"Invalid parameter format from {email}: {str(e)}")
            return jsonify({"error": "Invalid parameter format: {}".format(str(e))}), 400

        # Build optimized query: filter first, join at the end for better performance
        # Start with modes filter if category or military is specified
        modes_filter_parts = []
        if category:
            modes_filter_parts.append("category = %s")
        if typecode:
            modes_filter_parts.append("typecode = %s")
        if military is not None:
            if military.lower() == 'true':
                modes_filter_parts.append("military = true")
            elif military.lower() == 'false':
                modes_filter_parts.append("military = false")
        
        if modes_filter_parts:
            query = f"""
                WITH bbox1_points AS (
                    SELECT hex, t as t1
                    FROM adsb
                    WHERE ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))
                    AND {' AND '.join(modes_filter_parts)}
            """
        else:
            query = """
                WITH bbox1_points AS (
                    SELECT hex, t as t1
                    FROM adsb
                    WHERE ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))
            """
        
        # Set up parameters - bbox1 params first, then modes filter params
        params = [min_lon1, min_lat1, max_lon1, max_lat1]
        if modes_filter_parts:
            if category:
                params.append(category)
            if typecode:
                params.append(typecode)
            # military filter is added as literal true/false, no parameter needed
        
        # Add time constraints if provided
        if start_dt:
            query += " AND t >= %s"
            params.append(start_dt)
        if end_dt:
            query += " AND t <= %s"
            params.append(end_dt)
            
        # Add altitude constraints if provided
        if min_alt:
            query += " AND alt >= %s"
            params.append(int(min_alt))
        if max_alt:
            query += " AND alt <= %s"
            params.append(int(max_alt))
        
        # Add speed constraints if provided
        if min_speed:
            query += " AND gs >= %s"
            params.append(float(min_speed))
        if max_speed:
            query += " AND gs <= %s"
            params.append(float(max_speed))

        # Add hex condition if provided
        if hex_code:
            query += " AND adsb.hex = %s"
            params.append(hex_code)
            
        # Add flight condition if provided
        if flight_code:
            query += " AND TRIM(flight) = %s"
            params.append(flight_code)
            
        if modes_filter_parts:
            query += """
                ),
                bbox2_points AS (
                    SELECT hex, t as t2
                    FROM adsb
                    WHERE ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))
                    AND """ + ' AND '.join(modes_filter_parts) + """
            """
        else:
            query += """
                ),
                bbox2_points AS (
                    SELECT hex, t as t2
                    FROM adsb
                    WHERE ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))
            """
        
        params.extend([min_lon2, min_lat2, max_lon2, max_lat2])
        
        # Add modes filter params for bbox2 if provided
        if modes_filter_parts:
            if category:
                params.append(category)
            if typecode:
                params.append(typecode)
        
        # Add time constraints for bbox2 if provided
        if start_dt:
            query += " AND t >= %s"
            params.append(start_dt)
        if end_dt:
            query += " AND t <= %s"
            params.append(end_dt)
            
        # Add altitude constraints for bbox2 if provided
        if min_alt:
            query += " AND alt >= %s"
            params.append(int(min_alt))
        if max_alt:
            query += " AND alt <= %s"
            params.append(int(max_alt))

        # Add speed constraints for bbox2 if provided
        if min_speed:
            query += " AND gs >= %s"
            params.append(float(min_speed))
        if max_speed:
            query += " AND gs <= %s"
            params.append(float(max_speed))

        # Add hex condition for bbox2 if provided
        if hex_code:
            query += " AND adsb.hex = %s"
            params.append(hex_code)
            
        # Add flight condition for bbox2 if provided
        if flight_code:
            query += " AND TRIM(flight) = %s"
            params.append(flight_code)
            
        query += """
            ),
            matching_pairs AS (
                SELECT b1.hex, b1.t1, b2.t2
                FROM bbox1_points b1
                JOIN bbox2_points b2 ON b1.hex = b2.hex
        """

        # Add time difference constraints if provided
        if min_time_diff:
            query += " AND ABS(EXTRACT(EPOCH FROM (b2.t2 - b1.t1))) >= %s"
            params.append(float(min_time_diff))
        
        if max_time_diff:
            query += " AND ABS(EXTRACT(EPOCH FROM (b2.t2 - b1.t1))) <= %s"
            params.append(float(max_time_diff))

        query += """
            )
            SELECT 
                af1.hex,
                af1.t as t,
                ST_Y(af1.geom) as lat,
                ST_X(af1.geom) as lon,
                af1.flight,
                af1.alt,
                af1.gs,
                af1.bearing,
                af1.registration,
                af1.typecode,
                af1.category,
                af1.military,
                modes.owner,
                modes.aircraft
            FROM adsb af1
            LEFT JOIN modes ON af1.hex = modes.hex
            WHERE EXISTS (
                SELECT 1 FROM matching_pairs mp 
                WHERE mp.hex = af1.hex AND mp.t1 = af1.t
            )
            UNION ALL
            SELECT 
                af2.hex,
                af2.t as t,
                ST_Y(af2.geom) as lat,
                ST_X(af2.geom) as lon,
                af2.flight,
                af2.alt,
                af2.gs,
                af2.bearing,
                af2.registration,
                af2.typecode,
                af2.category,
                af2.military,
                modes.owner,
                modes.aircraft
            FROM adsb af2
            LEFT JOIN modes ON af2.hex = modes.hex
            WHERE EXISTS (
                SELECT 1 FROM matching_pairs mp 
                WHERE mp.hex = af2.hex AND mp.t2 = af2.t
            )
            ORDER BY t DESC
            LIMIT %s OFFSET %s
        """

        params.extend([limit, offset])

        # Log the final query with parameters
        logger.debug(f"Query Parameters from {email}: {params}")

        # Log the final query with parameters substituted
        try:
            # Create a copy of the query for logging
            debug_query = query
            # Replace each %s with the corresponding parameter
            for param in params:
                if isinstance(param, str):
                    # Escape single quotes in strings
                    param = param.replace("'", "''")
                    debug_query = debug_query.replace("%s", f"'{param}'", 1)
                elif isinstance(param, (int, float)):
                    debug_query = debug_query.replace("%s", str(param), 1)
                elif isinstance(param, datetime):
                    debug_query = debug_query.replace("%s", f"'{param.isoformat()}'", 1)
                else:
                    debug_query = debug_query.replace("%s", str(param), 1)
            logger.debug(f"Final SQL Query with parameters from {email}: {debug_query}")
        except Exception as e:
            logger.warning(f"Failed to log final query with parameters from {email}: {str(e)}")
        
        # Execute query
        conn = get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Log the number of results
                logger.info(f"Query from {email} returned {len(results)} results")
                
                # Format results to match bbox endpoint format
                formatted_results = []
                for row in results:
                    # Convert datetime to ISO format string
                    row['t'] = row['t'].isoformat()
                    formatted_results.append(dict(row))

        return jsonify({
            'count': len(formatted_results),
            'results': formatted_results
        })

    except Exception as e:
        import traceback
        logger.error(f"Error in /api/adsb/intersect_bboxes from {email}: {str(e)}", exc_info=True)
        # log stack trace using loguru
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
