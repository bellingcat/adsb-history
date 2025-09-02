#!/usr/bin/env python3
"""
ADS-B Data Processor

This script processes downloaded tar1090 heatmap binary files from a specified directory
and inserts the parsed data into a PostgreSQL database.
"""

import argparse
import csv
import datetime
import glob
import os
import time
from io import StringIO
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from loguru import logger


def setup_logging(log_file='process_adsb_data.log'):
    """Setup logging configuration."""
    logger.add(log_file, rotation='1 MB', retention='7 days', level='DEBUG')


def get_database_engine(connection_string=None):
    """Create and return database engine."""
    if connection_string is None:
        connection_string = 'postgresql://root:postgresql@/adsb?host=/var/run/postgresql'
    return create_engine(connection_string)


def psql_insert_copy(table, conn, keys, data_iter):
    """
    Execute SQL statement inserting data using COPY for better performance.
    
    Parameters
    ----------
    table : pandas.io.sql.SQLTable
    conn : sqlalchemy.engine.Engine or sqlalchemy.engine.Connection
    keys : list of str
        Column names
    data_iter : Iterable that iterates the values to be inserted
    """
    # gets a DBAPI connection that can provide a cursor
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)

        columns = ', '.join('"{}"'.format(k) for k in keys)
        if table.schema:
            table_name = '{}.{}'.format(table.schema, table.name)
        else:
            table_name = table.name

        sql = 'COPY {} ({}) FROM STDIN WITH CSV'.format(
            table_name, columns)
        cur.copy_expert(sql=sql, file=s_buf)


def parse_binary_file(file_path):
    """
    Parse a single ADS-B binary file and return aircraft data.
    
    Args:
        file_path: Path to the binary file
        
    Returns:
        list: List of aircraft data dictionaries
    """
    logger.info(f"Processing file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return []
    
    try:
        # Load binary file into int32 array
        points = np.fromfile(file_path, dtype=np.int32)
        
        if len(points) == 0:
            logger.warning(f"Empty file: {file_path}")
            return []
        
        # Convert to uint32 array
        pointsU = points.view(np.uint32)
        
        # convert to uint8 array
        pointsU8 = points.view(np.uint8)
        
        assert len(pointsU8) == len(pointsU) * 4
        
        slices = []
        found = 0
        
        for i in range(0, len(points), 4):
            if points[i] == 243235997:
                found = 1
                slices.append(i)
        
        if found == 0:
            logger.warning(f"No valid data markers found in file: {file_path}")
            return []
        
        last_seen = {}
        data = []
        
        for index in range(len(slices)):
            acinfo = {}
            
            i = slices[index]
            
            now = pointsU[i + 2] / 1e3 + 4294967.296 * pointsU[i + 1]
            
            i += 4
            
            while i < len(points) and 243235997 != points[i]:
                lat = points[i+1]
                lon = points[i+2]
                
                hex = f"{points[i] & 16777215:06x}"
                hex = "~" + hex if points[i] & (1 << 24) else hex
                
                if lat > 1073741824:
                    flight = None
                    
                    if pointsU8[4* (i + 2)]:
                        flight = ""
                        for j in range(0, 8):
                            flight += chr(pointsU8[4 * (i + 2) + j])
                    
                    squawk = f"{lat & 65535:04d}"
                    acinfo[hex] = (flight, squawk)
                else:
                    flight = acinfo.get(hex, (None, None))[0]
                    squawk = acinfo.get(hex, (None, None))[1]
                
                lat /= 1e6
                lon /= 1e6
                
                if lat > -90 and lat < 90 and lon > -180 and lon < 180:
                    type_dict = {
                        0: "adsb_icao",
                        1: "adsb_icao_nt",
                        2: "adsr_icao",
                        3: "tisb_icao",
                        4: "adsc",
                        5: "mlat",
                        6: "other",
                        7: "mode_s",
                        8: "adsb_other",
                        9: "adsr_other",
                        10: "tisb_trackfile",
                        11: "tisb_other",
                        12: "mode_ac"
                    }
                    
                    type_num = (pointsU[i] >> 27) & 31
                    # store the type as a number for more efficient postgres
                    type = type_num
                    
                    # Get altitude
                    alt = points[i + 3] & 65535
                    
                    # Sign extend if bit 15 is set (converting 2's complement)
                    if alt & 32768:
                        alt |= -65536
                    
                    # Convert altitude to "ground" or multiply by 25
                    # keep alt a number for more efficient postgres
                    alt = -123 if alt == -123 else alt * 25
                    
                    # Get ground speed
                    gs = points[i + 3] >> 16
                    
                    # Convert ground speed to None or divide by 10
                    gs = None if gs == -1 else gs / 10
                    
                    # keep one position every minute
                    if (hex in last_seen and now - last_seen[hex] >= 60) or not hex in last_seen:
                        ac = {
                            "t": now,
                            "hex": hex,
                            "flight": flight,
                            "squawk": squawk,
                            "lat": lat,
                            "lon": lon,
                            "alt": alt,
                            "gs": gs,
                            "type": type
                        }
                        
                        last_seen[hex] = now
                        data.append(ac)
                
                i += 4
        
        logger.info(f'Parsed {len(data)} aircraft records from {file_path}')
        return data
        
    except Exception as e:
        logger.error(f"Error parsing file {file_path}: {e}")
        return []


def process_directory(directory_path, engine, cleanup_files=False):
    """
    Process all binary files in a directory and insert data into database.
    
    Args:
        directory_path: Path to directory containing binary files
        engine: SQLAlchemy database engine
        cleanup_files: Whether to delete files after processing
        
    Returns:
        int: Number of records processed
    """
    if not os.path.exists(directory_path):
        logger.error(f"Directory does not exist: {directory_path}")
        return 0
    
    # Find all date directories
    date_dirs = []
    if os.path.isdir(directory_path):
        # Look for date pattern directories (YYYY-MM-DD)
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            if os.path.isdir(item_path) and len(item) == 10 and item.count('-') == 2:
                try:
                    datetime.datetime.strptime(item, '%Y-%m-%d')
                    date_dirs.append(item_path)
                except ValueError:
                    continue
        
        # If no date directories found, assume the directory itself contains files
        if not date_dirs:
            date_dirs = [directory_path]
    else:
        logger.error(f"Path is not a directory: {directory_path}")
        return 0
    
    total_records = 0
    files_to_cleanup = []
    
    for date_dir in sorted(date_dirs):
        logger.info(f"Processing directory: {date_dir}")
        
        # Find all numeric files (0-47 for half-hour intervals)
        files_pattern = os.path.join(date_dir, "*")
        files = glob.glob(files_pattern)
        
        # Filter to numeric files only
        numeric_files = []
        for file_path in files:
            filename = os.path.basename(file_path)
            if filename.isdigit() and 0 <= int(filename) <= 47:
                numeric_files.append(file_path)
        
        if not numeric_files:
            logger.warning(f"No valid data files found in {date_dir}")
            continue
        
        # Sort files by numeric value
        numeric_files.sort(key=lambda x: int(os.path.basename(x)))
        
        for file_path in numeric_files:
            data = parse_binary_file(file_path)
            
            if data:
                # Convert to DataFrame and insert
                df = pd.DataFrame(data)
                
                start_time = time.time()
                df.to_sql(
                    name="adsb_temp",
                    con=engine,
                    if_exists="append",
                    index=False,
                    method=psql_insert_copy
                )
                end_time = time.time()
                
                logger.info(f"Inserted {len(df)} records in {end_time - start_time:.2f} seconds")
                total_records += len(df)
            
            if cleanup_files:
                files_to_cleanup.append(file_path)
    
    # Cleanup files if requested
    if cleanup_files and files_to_cleanup:
        logger.info(f"Cleaning up {len(files_to_cleanup)} processed files")
        for file_path in files_to_cleanup:
            try:
                os.remove(file_path)
                logger.debug(f"Deleted {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")
    
    return total_records


def create_indexes_and_finalize(engine):
    """
    Create indexes on temporary table and move data to main table.
    
    Args:
        engine: SQLAlchemy database engine
    """
    logger.info("Creating indexes and finalizing data")
    
    with engine.connect() as con:
        try:
            # Create indices on temporary table
            logger.info("Creating index on timestamp column")
            con.execute(text('CREATE INDEX IF NOT EXISTS adsb_temp_t_idx ON adsb_temp (t)'))
            
            logger.info("Creating index on hex column")
            con.execute(text('CREATE INDEX IF NOT EXISTS adsb_temp_hex_idx ON adsb_temp (hex)'))
            
            # Insert data into main table with geospatial and bearing calculations
            logger.info("Inserting data into main adsb table")
            con.execute(text('''
                INSERT INTO adsb SELECT
                    to_timestamp(a.t) as t,
                    a.hex, a.flight, a.alt, a.gs,
                    ST_SetSRID(ST_MakePoint(a.lon, a.lat), 4326) AS geom,
                    ST_Azimuth(
                        ST_SetSRID(ST_MakePoint(
                            LAG(a.lon) OVER (PARTITION BY a.hex ORDER BY t),
                            LAG(a.lat) OVER (PARTITION BY a.hex ORDER BY t)
                        ), 4326),
                        ST_SetSRID(ST_MakePoint(a.lon, a.lat), 4326)
                    ) as bearing,
                    m.registration,
                    m.typecode,
                    m.category,
                    m.military
                FROM adsb_temp a
                LEFT JOIN modes m ON a.hex = m.hex;'''))
            
            con.commit()
            logger.info("Data insertion completed successfully")
            
        except Exception as e:
            logger.error(f"Error during index creation or data insertion: {e}")
            con.rollback()
            raise


def cleanup_temp_table(engine):
    """
    Drop the temporary table after processing.
    
    Args:
        engine: SQLAlchemy database engine
    """
    logger.info("Dropping temporary table")
    
    with engine.connect() as con:
        try:
            con.execute(text('DROP TABLE IF EXISTS adsb_temp'))
            con.commit()
            logger.info("Temporary table dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping temporary table: {e}")
            raise


def main():
    """Main function to run the processing."""
    parser = argparse.ArgumentParser(description='Process ADS-B binary data files')
    parser.add_argument('directory', 
                       help='Directory containing ADS-B binary files to process')
    parser.add_argument('--connection-string', '-c',
                       help='Database connection string')
    parser.add_argument('--cleanup-files', action='store_true',
                       help='Delete processed files after successful insertion')
    parser.add_argument('--skip-finalize', action='store_true',
                       help='Skip the finalization step (useful for batch processing)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logging()
    if args.verbose:
        logger.remove()  # Remove default handler
        logger.add(lambda msg: print(msg, end=''), level='DEBUG')
    
    logger.info("Starting ADS-B data processing")
    logger.info(f"Processing directory: {args.directory}")
    
    try:
        # Create database engine
        engine = get_database_engine(args.connection_string)
        
        # Process the directory
        total_records = process_directory(args.directory, engine, args.cleanup_files)
        
        if total_records == 0:
            logger.warning("No records were processed")
            return
        
        logger.info(f"Processed {total_records} total records")
        
        # Finalize data (create indexes and move to main table)
        if not args.skip_finalize:
            create_indexes_and_finalize(engine)
            cleanup_temp_table(engine)
        else:
            logger.info("Skipping finalization step as requested")
        
        logger.info("Processing completed successfully")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise


if __name__ == "__main__":
    main()
