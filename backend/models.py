"""
CampusChain Backend — Database Models (SQLite)
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "campuschain.db")


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'parent', 'vendor', 'admin')),
            algo_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS parent_student (
            parent_id INTEGER NOT NULL REFERENCES users(id),
            student_id INTEGER NOT NULL REFERENCES users(id),
            PRIMARY KEY (parent_id, student_id)
        );

        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('food', 'events', 'stationery')),
            algo_address TEXT NOT NULL
        );

        -- AGGREGATED spending — no individual txn details for parent view
        CREATE TABLE IF NOT EXISTS category_spending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES users(id),
            category TEXT NOT NULL CHECK(category IN ('food', 'events', 'stationery')),
            month TEXT NOT NULL,  -- format: YYYY-MM
            amount INTEGER NOT NULL DEFAULT 0,
            UNIQUE(student_id, category, month)
        );

        CREATE TABLE IF NOT EXISTS funding_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER NOT NULL REFERENCES users(id),
            student_id INTEGER NOT NULL REFERENCES users(id),
            amount INTEGER NOT NULL,
            txn_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Track processed blockchain txns to avoid double-counting
        CREATE TABLE IF NOT EXISTS processed_txns (
            txn_id TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    print("Database initialized.")


if __name__ == "__main__":
    init_db()
