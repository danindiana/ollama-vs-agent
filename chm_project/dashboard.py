import sqlite3
from prettytable import PrettyTable
import os

def get_last_5_scans(conn):
    # Summing LOC and Duplicate count per unique scan timestamp
    query = """
    SELECT scan_timestamp, COUNT(file_path), SUM(loc), SUM(duplicate_count) 
    FROM scan_results 
    GROUP BY scan_timestamp 
    ORDER BY scan_timestamp DESC 
    LIMIT 5
    """
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def get_top_5_duplicated_files(conn):
    query = """
    SELECT file_path, duplicate_count 
    FROM scan_results 
    WHERE duplicate_count > 0
    ORDER BY duplicate_count DESC 
    LIMIT 5
    """
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def main():
    db_path = 'chm_health.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found. Run analyzer.py first.")
        return

    conn = sqlite3.connect(db_path)
    
    try:
        last_5_scans = get_last_5_scans(conn)
        top_duplicated_files = get_top_5_duplicated_files(conn)

        print("\n=== CHM Codebase Health Dashboard ===")
        
        # ASCII Table for Scan History
        scan_table = PrettyTable()
        scan_table.field_names = ["Timestamp", "Files", "Total LOC", "Total Dups"]
        for scan in last_5_scans:
            scan_table.add_row(scan)
        
        print("\nScan History (Last 5):")
        print(scan_table)

        # ASCII Table for Problematic Files
        if top_duplicated_files:
            file_table = PrettyTable()
            file_table.field_names = ["Problematic File Path", "Dups Found"]
            for file in top_duplicated_files:
                file_table.add_row(file)
            
            print("\nTop 5 Duplicated Files:")
            print(file_table)
        else:
            print("\nNo duplicates detected in recent scans.")

    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
