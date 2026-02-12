"""
CampusChain Backend — Spending Indexer Service

Polls Algorand Indexer for new ASA transfers involving student addresses.
Parses the note field to extract category, then aggregates spending into
the category_spending table.

THIS IS THE PRIVACY LAYER — it aggregates and discards raw txn details
from the parent-facing data model.
"""

import json
import time
import threading
from datetime import datetime

from algosdk.v2client import indexer

from config import INDEXER_ADDRESS, INDEXER_TOKEN, ASA_ID
from models import get_db


def get_indexer_client():
    return indexer.IndexerClient(INDEXER_TOKEN, INDEXER_ADDRESS)


def parse_note(note_b64):
    """
    Parse the base64-encoded note field from an Algorand transaction.
    Expected format: {"cat": "food"}
    Returns the category string or None.
    """
    try:
        import base64
        note_bytes = base64.b64decode(note_b64)
        data = json.loads(note_bytes.decode("utf-8"))
        cat = data.get("cat", "").lower()
        if cat in ("food", "events", "stationery"):
            return cat
        return None
    except Exception:
        return None


def get_student_addresses():
    """Get all student algo addresses from the database."""
    db = get_db()
    rows = db.execute(
        "SELECT id, algo_address FROM users WHERE role = 'student' AND algo_address IS NOT NULL"
    ).fetchall()
    db.close()
    return [(row["id"], row["algo_address"]) for row in rows]


def get_vendor_category_map():
    """Build a map of vendor_address → category from the database."""
    db = get_db()
    rows = db.execute("SELECT algo_address, category FROM vendors").fetchall()
    db.close()
    return {row["algo_address"]: row["category"] for row in rows}


def index_student_spending(student_id, student_addr, vendor_map):
    """
    Fetch recent ASA transfers FROM a student address and aggregate spending.
    """
    idx_client = get_indexer_client()
    db = get_db()

    try:
        # Search for asset transfers sent by this student
        response = idx_client.search_transactions(
            address=student_addr,
            asset_id=ASA_ID,
            txn_type="axfer",
            address_role="sender",
        )

        transactions = response.get("transactions", [])

        for txn in transactions:
            txn_id = txn["id"]

            # Check if already processed
            existing = db.execute(
                "SELECT 1 FROM processed_txns WHERE txn_id = ?", (txn_id,)
            ).fetchone()
            if existing:
                continue

            # Extract amount
            asset_transfer = txn.get("asset-transfer-transaction", {})
            amount = asset_transfer.get("amount", 0)
            receiver = asset_transfer.get("receiver", "")

            if amount == 0:
                continue  # Skip opt-in txns

            # Determine category: note field first, vendor lookup fallback
            category = None
            note = txn.get("note", "")
            if note:
                category = parse_note(note)

            if not category and receiver in vendor_map:
                category = vendor_map[receiver]

            if not category:
                category = "stationery"  # Default fallback

            # Determine month from round-time
            round_time = txn.get("round-time", 0)
            if round_time:
                dt = datetime.utcfromtimestamp(round_time)
                month = dt.strftime("%Y-%m")
            else:
                month = datetime.utcnow().strftime("%Y-%m")

            # AGGREGATE — upsert into category_spending
            db.execute("""
                INSERT INTO category_spending (student_id, category, month, amount)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(student_id, category, month)
                DO UPDATE SET amount = amount + ?
            """, (student_id, category, month, amount, amount))

            # Mark as processed
            db.execute(
                "INSERT INTO processed_txns (txn_id) VALUES (?)", (txn_id,)
            )

        db.commit()

    except Exception as e:
        print(f"Indexer error for student {student_id}: {e}")
    finally:
        db.close()


def run_indexer_cycle():
    """Run one full indexer cycle across all students."""
    students = get_student_addresses()
    vendor_map = get_vendor_category_map()

    for student_id, student_addr in students:
        index_student_spending(student_id, student_addr, vendor_map)

    print(f"Indexer cycle complete. Processed {len(students)} students.")


def start_indexer_thread(interval=30):
    """Start the indexer as a background thread, running every `interval` seconds."""

    def loop():
        while True:
            try:
                run_indexer_cycle()
            except Exception as e:
                print(f"Indexer thread error: {e}")
            time.sleep(interval)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    print(f"Indexer thread started (every {interval}s)")
