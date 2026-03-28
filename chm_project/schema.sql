CREATE TABLE IF NOT EXISTS scan_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_timestamp DATETIME DEFAULT (DATETIME('now', 'localtime')),
    file_path TEXT NOT NULL,
    loc INTEGER DEFAULT 0,
    duplicate_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS duplicate_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER,
    block_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scan_results(id)
);
