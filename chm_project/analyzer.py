import os
import sqlite3
import hashlib
import argparse
from collections import defaultdict
from datetime import datetime

def init_db(db_path):
    if not os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            with open(schema_path, "r") as f:
                conn.executescript(f.read())

def calculate_loc(file_path):
    try:
        # Skip macOS metadata files
        if os.path.basename(file_path).startswith('._'):
            return 0
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = [line for line in file if line.strip()]
        return len(lines)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def find_duplicate_code_blocks(directory, verbose=False):
    files = []
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            # Skip hidden and macOS metadata files
            if f.startswith('.') or f.startswith('._'):
                continue
            if f.endswith('.py'):
                files.append(os.path.join(root, f))
                
    code_blocks = defaultdict(list)
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            # Simplified logic: split by double newlines to find potential duplicate functional blocks
            blocks = content.split('\n\n')
            for block in blocks:
                clean_block = block.strip()
                if len(clean_block) > 50:  # Only track blocks of significant size
                    code_blocks[clean_block].append(file_path)
        except Exception as e:
            if verbose:
                print(f"Failed extracting blocks from {file_path}: {e}")
            continue
    
    duplicates = {block: paths for block, paths in code_blocks.items() if len(paths) > 1}
    return duplicates

def save_to_db(file_stats, duplicates, db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Invert duplicates for easier lookup
        file_to_dup_count = defaultdict(int)
        for block, paths in duplicates.items():
            for path in paths:
                file_to_dup_count[path] += 1
        
        for file_path, loc in file_stats.items():
            cursor.execute("""
                INSERT INTO scan_results (scan_timestamp, file_path, loc, duplicate_count)
                VALUES (?, ?, ?, ?)
            """, (now, file_path, loc, file_to_dup_count[file_path]))
            
        # Optional: Save duplicate block locations
        scan_id = cursor.lastrowid
        for block, paths in duplicates.items():
            block_hash = hashlib.md5(block.encode('utf-8', errors='ignore')).hexdigest()
            for path in paths:
                cursor.execute("""
                    INSERT INTO duplicate_blocks (scan_id, block_hash, file_path)
                    VALUES (?, ?, ?)
                """, (scan_id, block_hash, path))
        conn.commit()

def analyze_directory(directory, db_path, verbose=False):
    total_loc = 0
    file_count = 0
    file_stats = {}
    
    for root, _, files in os.walk(directory):
        for file in files:
            # Skip hidden and macOS metadata files
            if file.startswith('.') or file.startswith('._'):
                continue
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                loc = calculate_loc(file_path)
                file_stats[file_path] = loc
                total_loc += loc
                file_count += 1
    
    duplicates = find_duplicate_code_blocks(directory, verbose)
    save_to_db(file_stats, duplicates, db_path)
    return total_loc, file_count, duplicates

def main():
    parser = argparse.ArgumentParser(
        description="Codebase Health Monitor (CHM) - Scanner",
        epilog="Analyzes Python codebases for LOC and duplicated blocks, saving to SQLite."
    )
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan (default: current directory)")
    parser.add_argument("--db", dest="db_path", default="chm_health.db", help="Path to SQLite database")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    search_dir = args.path
    db_path = args.db_path
    
    if args.verbose:
        print(f"--- Configuration ---")
        print(f"Target Directory: {os.path.abspath(search_dir)}")
        print(f"Database Path:    {os.path.abspath(db_path)}\n")
        
    print(f"--- Analyzing: {os.path.abspath(search_dir)} ---")
    
    init_db(db_path)
    loc, count, dups = analyze_directory(search_dir, db_path, args.verbose)
    
    print(f"Total Files: {count}")
    print(f"Total Lines of Code (LOC): {loc}")
    print(f"Duplicate Blocks Found: {len(dups)}")
    print(f"Database Updated: {db_path}")
    
    if dups:
        print("\n--- Duplicate Examples ---")
        for i, (block, paths) in enumerate(list(dups.items())[:3]):
            print(f"Duplicate {i+1} in: {paths}")

if __name__ == "__main__":
    main()
