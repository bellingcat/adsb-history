import argparse
import datetime
import glob
import os
import shutil
import subprocess
import sys
import tarfile
import requests
from tqdm import tqdm
from sqlalchemy import text
from process_adsb_data import get_database_engine

def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total_size = int(r.headers.get('content-length', 0))
        with open(local_filename, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=local_filename) as pbar:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

def purge_db(connection_string):
    engine = get_database_engine(connection_string)
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE adsb"))
        conn.commit()
    print("Database purged.")

def main():
    parser = argparse.ArgumentParser(description="Download and process ADSB data or purge the database.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--start-date', type=str, help="Start date (YYYY-MM-DD)")
    group.add_argument('--purge-db', action='store_true', help="Purge all data from the database")
    
    parser.add_argument('--end-date', type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument('--connection-string', type=str, default="postgresql://root:postgresql@localhost:5432/adsb")
    
    args = parser.parse_args()

    if args.purge_db:
        purge_db(args.connection_string)
        return

    start_date = datetime.datetime.fromisoformat(args.start_date)
    end_date = datetime.datetime.fromisoformat(args.end_date) if args.end_date else start_date
    date = start_date

    while date <= end_date:
        str_date = date.strftime("%Y.%m.%d")
        url = f"https://github.com/adsblol/globe_history_{date.year}/releases/download/v{str_date}-planes-readsb-prod-0/v{str_date}-planes-readsb-prod-0.tar"
        
        try:
            download_file(url + ".aa", "data.tar.aa")
            download_file(url + ".ab", "data.tar.ab")
            
            with open('data.tar', 'wb') as destination:
                for filename in ['data.tar.aa', 'data.tar.ab']:
                    with open(filename, 'rb') as source:
                        shutil.copyfileobj(source, destination)
            
            with tarfile.open("data.tar", "r:*") as tar:
                members = [m for m in tar.getmembers() if m.name.startswith("./heatmap")]
                tar.extractall(members=members)

            subprocess.run([
                sys.executable,
                "process_adsb_data.py",
                "heatmap",
                "--connection-string",
                args.connection_string,
                "--verbose",
            ], check=True)
            
        finally:
            for file in glob.glob("data.tar*"):
                if os.path.exists(file):
                    os.remove(file)
            if os.path.exists("heatmap"):
                shutil.rmtree("heatmap")

        date += datetime.timedelta(days=1)

if __name__ == "__main__":
    main()
