"""
CampusChain Backend — Database Models (SQLite)

CUSTODIAL MODEL: The backend stores wallet mnemonics and signs all
transactions on behalf of users. No user ever needs crypto or wallet software.
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
            algo_mnemonic TEXT,
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

        -- Individual transactions stored for student view, never exposed to parents
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES users(id),
            vendor_id INTEGER REFERENCES vendors(id),
            amount INTEGER NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('food', 'events', 'stationery')),
            txn_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Canteen menu items (pre-seeded)
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('food', 'beverages', 'snacks')),
            emoji TEXT NOT NULL DEFAULT '🍽️',
            available INTEGER NOT NULL DEFAULT 1
        );

        -- Student orders
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES users(id),
            vendor_id INTEGER REFERENCES vendors(id),
            total_amount INTEGER NOT NULL,
            txn_id TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Line items per order
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
            quantity INTEGER NOT NULL DEFAULT 1,
            price INTEGER NOT NULL
        );
    """)

    # Seed canteen menu items (only if table is empty)
    existing = conn.execute("SELECT COUNT(*) as c FROM menu_items").fetchone()
    if existing["c"] == 0:
        menu_items = [
            ("Samosa", 15, "snacks", "🥟"),
            ("Vada Pav", 20, "snacks", "🍔"),
            ("Masala Dosa", 45, "food", "🥞"),
            ("Paneer Roll", 50, "food", "🌯"),
            ("Chicken Biryani", 90, "food", "🍛"),
            ("Veg Thali", 70, "food", "🍱"),
            ("Chai", 10, "beverages", "☕"),
            ("Cold Coffee", 40, "beverages", "🧋"),
            ("Fresh Lime Soda", 25, "beverages", "🍋"),
            ("Maggi", 30, "snacks", "🍜"),
            ("French Fries", 35, "snacks", "🍟"),
            ("Sandwich", 40, "food", "🥪"),
        ]
        conn.executemany(
            "INSERT INTO menu_items (name, price, category, emoji) VALUES (?, ?, ?, ?)",
            menu_items,
        )

    conn.commit()
    conn.close()
    print("Database initialized.")


if __name__ == "__main__":
    init_db()
