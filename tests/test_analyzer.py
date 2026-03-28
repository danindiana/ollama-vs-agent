import os
import sqlite3
import pytest
import sys
from pathlib import Path

# Add the chm_project directory to the path so we can import analyzer
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../chm_project')))
from analyzer import init_db, calculate_loc, find_duplicate_code_blocks, analyze_directory

@pytest.fixture
def temp_workspace(tmp_path):
    """Creates a temporary workspace with some mock Python files."""
    # File 1: Normal file
    file1 = tmp_path / "normal.py"
    file1.write_text("def hello():\n    print('world')\n")
    
    # File 2 & 3: Files with a large duplicated block (>50 chars required by logic)
    dup_content = "def highly_duplicated_function():\n" + "    print('This is a test line to pad length')\n" * 5
    
    file2 = tmp_path / "dup1.py"
    file2.write_text(dup_content)
    
    file3 = tmp_path / "dup2.py"
    file3.write_text(dup_content)
    
    # File 4: macOS metadata mock
    file4 = tmp_path / "._metadata.py"
    file4.write_text("Binary garb\x00age")
    
    # Database path
    db_path = tmp_path / "test_health.db"
    
    return tmp_path, db_path

def test_calculate_loc(temp_workspace):
    tmp_path, _ = temp_workspace
    
    assert calculate_loc(str(tmp_path / "normal.py")) == 2
    
    # macOS metadata should return 0
    assert calculate_loc(str(tmp_path / "._metadata.py")) == 0

def test_find_duplicate_blocks(temp_workspace):
    tmp_path, _ = temp_workspace
    
    duplicates = find_duplicate_code_blocks(str(tmp_path))
    
    # Should find 1 duplicated block present in 2 files
    assert len(duplicates) == 1
    paths = list(duplicates.values())[0]
    assert len(paths) == 2
    assert any("dup1.py" in p for p in paths)
    assert any("dup2.py" in p for p in paths)

def test_database_initialization(temp_workspace):
    _, db_path = temp_workspace
    init_db(str(db_path))
    
    assert os.path.exists(str(db_path))
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall()]
        assert "scan_results" in tables
        assert "duplicate_blocks" in tables

def test_analyze_directory_integration(temp_workspace):
    tmp_path, db_path = temp_workspace
    init_db(str(db_path))
    
    total_loc, file_count, dups = analyze_directory(str(tmp_path), str(db_path))
    
    # normal.py (2 loc) + dup1.py (6 loc) + dup2.py (6 loc) = 14 LOC
    assert file_count == 3  # Ignores ._metadata.py
    assert total_loc == 14
    assert len(dups) == 1
    
    # Verify DB persistence
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path, loc, duplicate_count FROM scan_results;")
        results = cursor.fetchall()
        
        assert len(results) == 3
        # Check that duplicate_count populated correctly
        for row in results:
            if "dup" in row[0]:
                assert row[2] == 1  # 1 duplicate occurrence marked
