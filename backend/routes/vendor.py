"""
Vendor Routes — Register, QR, and Accept Payment (Custodial)

POST /vendor/pay: The key custodial endpoint. The vendor submits
{ student_id, amount, category } and the backend signs the ASA
transfer from the student's custodial wallet to the vendor's wallet.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
import json

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db
from services.algorand_service import transfer_student_to_vendor, get_token_balance

vendor_bp = Blueprint("vendor", __name__, url_prefix="/api/vendor")


@vendor_bp.route("/register", methods=["POST"])
@jwt_required()
def register_vendor():
    """
    Register a vendor with a category.
    Body: { name, category: 'food'|'events'|'stationery' }
    """
    claims = get_jwt()
    if claims.get("role") != "vendor":
        return jsonify({"error": "Vendor access only"}), 403

    user_id = get_jwt_identity()
    data = request.get_json()
    name = data.get("name", "").strip()
    category = data.get("category", "")

    if not name or category not in ("food", "events", "stationery"):
        return jsonify({"error": "Name and valid category required"}), 400

    db = get_db()
    user = db.execute("SELECT algo_address FROM users WHERE id = ?", (user_id,)).fetchone()

    if not user or not user["algo_address"]:
        db.close()
        return jsonify({"error": "No wallet found"}), 404

    db.execute(
        "INSERT INTO vendors (user_id, name, category, algo_address) VALUES (?, ?, ?, ?)",
        (user_id, name, category, user["algo_address"]),
    )
    db.commit()
    db.close()

    return jsonify({
        "message": "Vendor registered",
        "name": name,
        "category": category,
    }), 201


@vendor_bp.route("/pay", methods=["POST"])
@jwt_required()
def pay():
    """
    Accept payment from a student (Custodial).
    Body: { student_id, amount, category }

    The backend:
    1. Looks up student's custodial mnemonic from DB
    2. Looks up vendor's Algorand address from DB
    3. Signs and submits the ASA transfer
    4. Records the transaction in DB
    5. Updates aggregated category_spending

    Neither the student nor the vendor touches any crypto.
    """
    claims = get_jwt()
    if claims.get("role") != "vendor":
        return jsonify({"error": "Vendor access only"}), 403

    vendor_user_id = get_jwt_identity()
    data = request.get_json()
    student_id = data.get("student_id")
    amount = data.get("amount", 0)
    category = data.get("category", "")

    if not student_id or amount <= 0:
        return jsonify({"error": "Invalid payment details"}), 400

    if category not in ("food", "events", "stationery"):
        return jsonify({"error": "Invalid category. Must be: food, events, stationery"}), 400

    db = get_db()

    # Get student's custodial mnemonic
    student = db.execute(
        "SELECT algo_address, algo_mnemonic FROM users WHERE id = ? AND role = 'student'",
        (student_id,),
    ).fetchone()
    if not student or not student["algo_mnemonic"]:
        db.close()
        return jsonify({"error": "Student not found or wallet not set up"}), 404

    # Get vendor info
    vendor = db.execute(
        "SELECT id, algo_address FROM vendors WHERE user_id = ?",
        (vendor_user_id,),
    ).fetchone()
    if not vendor:
        db.close()
        return jsonify({"error": "Vendor not registered. Call /vendor/register first."}), 404

    # Check student balance
    balance = get_token_balance(student["algo_address"])
    if balance < amount:
        db.close()
        return jsonify({"error": f"Insufficient balance. Has {balance}, needs {amount}"}), 400

    try:
        # Backend signs the transaction using student's custodial mnemonic
        tx_id = transfer_student_to_vendor(
            student["algo_mnemonic"],
            vendor["algo_address"],
            amount,
            category,
        )

        month = datetime.utcnow().strftime("%Y-%m")

        # Record individual transaction (visible to student, NOT to parent)
        db.execute(
            "INSERT INTO transactions (student_id, vendor_id, amount, category, txn_id) VALUES (?, ?, ?, ?, ?)",
            (student_id, vendor["id"], amount, category, tx_id),
        )

        # Update aggregated spending (THIS is what the parent sees)
        db.execute("""
            INSERT INTO category_spending (student_id, category, month, amount)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id, category, month)
            DO UPDATE SET amount = amount + ?
        """, (student_id, category, month, amount, amount))

        db.commit()
        db.close()

        return jsonify({
            "message": "Payment successful",
            "amount": amount,
            "category": category,
        })
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 500


@vendor_bp.route("/qr", methods=["GET"])
@jwt_required()
def get_qr_data():
    """Generate QR code data for vendor payment."""
    claims = get_jwt()
    user_id = get_jwt_identity()

    db = get_db()
    vendor = db.execute(
        "SELECT name, category FROM vendors WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    db.close()

    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    qr_data = {
        "type": "campuschain_payment",
        "vendor_id": user_id,
        "category": vendor["category"],
        "vendor_name": vendor["name"],
    }

    return jsonify({
        "qr_data": json.dumps(qr_data),
        "display": {
            "vendor": vendor["name"],
            "category": vendor["category"],
        },
    })


@vendor_bp.route("/balance", methods=["GET"])
@jwt_required()
def vendor_balance():
    """Get the vendor's CampusToken balance."""
    claims = get_jwt()
    if claims.get("role") != "vendor":
        return jsonify({"error": "Vendor access only"}), 403

    user_id = get_jwt_identity()
    db = get_db()
    user = db.execute("SELECT algo_address FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()

    if not user or not user["algo_address"]:
        return jsonify({"error": "No wallet found"}), 404

    bal = get_token_balance(user["algo_address"])
    return jsonify({"balance": bal})


@vendor_bp.route("/orders", methods=["GET"])
@jwt_required()
def vendor_orders():
    """
    Get incoming orders for this vendor (canteen feed).
    Vendors see WHO ordered WHAT so they can prepare the food.
    No acceptance needed — orders are auto-processed.
    """
    claims = get_jwt()
    if claims.get("role") != "vendor":
        return jsonify({"error": "Vendor access only"}), 403

    user_id = get_jwt_identity()
    db = get_db()

    vendor = db.execute(
        "SELECT id FROM vendors WHERE user_id = ?", (user_id,)
    ).fetchone()
    if not vendor:
        db.close()
        return jsonify({"error": "Vendor not registered"}), 404

    orders = db.execute(
        """SELECT o.id, o.total_amount, o.txn_id, o.status, o.created_at,
                  u.username as student_name
           FROM orders o
           JOIN users u ON o.student_id = u.id
           WHERE o.vendor_id = ?
           ORDER BY o.created_at DESC LIMIT 50""",
        (vendor["id"],),
    ).fetchall()

    result = []
    for o in orders:
        items = db.execute(
            """SELECT oi.quantity, oi.price, mi.name, mi.emoji
               FROM order_items oi
               JOIN menu_items mi ON oi.menu_item_id = mi.id
               WHERE oi.order_id = ?""",
            (o["id"],),
        ).fetchall()

        result.append({
            "id": o["id"],
            "student": o["student_name"],
            "total": o["total_amount"],
            "txn_id": o["txn_id"],
            "status": o["status"],
            "time": o["created_at"],
            "items": [
                {"name": i["name"], "emoji": i["emoji"], "qty": i["quantity"], "price": i["price"]}
                for i in items
            ],
        })

    db.close()
    return jsonify({"orders": result})
