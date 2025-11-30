import sys
import os
from import_utils import import_file_to_db

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <file_path> [farm_id]")
        sys.exit(1)
    file_path = sys.argv[1]
    farm_id = sys.argv[2] if len(sys.argv) > 2 else None
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
    try:
        inserted = import_file_to_db(file_path, farm_id)
        print(f"Successfully inserted {inserted} rows from {file_path} into the database.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
