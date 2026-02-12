"""
Canteen Routes — Menu, Order, and Soft Bill (Custodial)

Students browse a menu, add items to a cart, and place an order.
The backend signs the ASA transfer (student → canteen vendor) and
generates a soft bill/receipt.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db
from services.algorand_service import transfer_student_to_vendor, get_token_balance

canteen_bp = Blueprint("canteen", __name__, url_prefix="/api/canteen")


# ---------- helpers ----------

def _get_or_create_canteen_vendor(db):
    """
    Get (or auto-create) the built-in 'Campus Canteen' vendor.
    This vendor receives all canteen order payments.
    """
    vendor = db.execute(
        "SELECT id, algo_address FROM vendors WHERE name = 'Campus Canteen' LIMIT 1"
    ).fetchone()

    if vendor:
        return vendor["id"], vendor["algo_address"]

    # If no canteen vendor exists, use the first registered food vendor
    vendor = db.execute(
        "SELECT id, algo_address FROM vendors WHERE category = 'food' LIMIT 1"
    ).fetchone()

    if vendor:
        return vendor["id"], vendor["algo_address"]

    return None, None


# ---------- routes ----------

@canteen_bp.route("/menu", methods=["GET"])
@jwt_required()
def get_menu():
    """Get all available canteen menu items."""
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "Student access only"}), 403

    db = get_db()
    items = db.execute(
        "SELECT id, name, price, category, emoji FROM menu_items WHERE available = 1 ORDER BY category, name"
    ).fetchall()
    db.close()

    return jsonify({
        "items": [
            {
                "id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "category": item["category"],
                "emoji": item["emoji"],
            }
            for item in items
        ]
    })


@canteen_bp.route("/order", methods=["POST"])
@jwt_required()
def place_order():
    """
    Place a canteen order (Custodial).
    Body: { items: [{ id: number, qty: number }, ...] }

    The backend:
    1. Validates items and computes total
    2. Checks student balance
    3. Signs ASA transfer (student → canteen vendor)
    4. Creates order + order_items records
    5. Updates aggregated category_spending
    6. Returns the order with a soft bill
    """
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "Student access only"}), 403

    student_id = get_jwt_identity()
    data = request.get_json()
    cart_items = data.get("items", [])

    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400

    db = get_db()

    # Validate items and compute total
    order_lines = []
    total = 0
    for ci in cart_items:
        item_id = ci.get("id")
        qty = ci.get("qty", 1)

        if not item_id or qty < 1:
            db.close()
            return jsonify({"error": "Invalid item in cart"}), 400

        menu_item = db.execute(
            "SELECT id, name, price, emoji FROM menu_items WHERE id = ? AND available = 1",
            (item_id,),
        ).fetchone()

        if not menu_item:
            db.close()
            return jsonify({"error": f"Menu item {item_id} not found or unavailable"}), 404

        line_total = menu_item["price"] * qty
        total += line_total
        order_lines.append({
            "menu_item_id": menu_item["id"],
            "name": menu_item["name"],
            "emoji": menu_item["emoji"],
            "price": menu_item["price"],
            "qty": qty,
            "line_total": line_total,
        })

    # Get student wallet
    student = db.execute(
        "SELECT algo_address, algo_mnemonic FROM users WHERE id = ? AND role = 'student'",
        (student_id,),
    ).fetchone()

    if not student or not student["algo_mnemonic"]:
        db.close()
        return jsonify({"error": "Student wallet not set up"}), 404

    # Check balance
    balance = get_token_balance(student["algo_address"])
    if balance < total:
        db.close()
        return jsonify({
            "error": f"Insufficient balance. Have ₹{balance}, need ₹{total}"
        }), 400

    # Get canteen vendor
    vendor_id, vendor_addr = _get_or_create_canteen_vendor(db)
    if not vendor_addr:
        db.close()
        return jsonify({
            "error": "No canteen vendor registered. An admin must register a food vendor first."
        }), 404

    try:
        # Sign and submit the ASA transfer on Algorand
        tx_id = transfer_student_to_vendor(
            student["algo_mnemonic"],
            vendor_addr,
            total,
            "food",  # canteen orders are always food category
        )

        now = datetime.utcnow()
        month = now.strftime("%Y-%m")

        # Create the order
        cursor = db.execute(
            "INSERT INTO orders (student_id, vendor_id, total_amount, txn_id) VALUES (?, ?, ?, ?)",
            (student_id, vendor_id, total, tx_id),
        )
        order_id = cursor.lastrowid

        # Create order line items
        for line in order_lines:
            db.execute(
                "INSERT INTO order_items (order_id, menu_item_id, quantity, price) VALUES (?, ?, ?, ?)",
                (order_id, line["menu_item_id"], line["qty"], line["price"]),
            )

        # Record in transactions table (visible to student)
        db.execute(
            "INSERT INTO transactions (student_id, vendor_id, amount, category, txn_id) VALUES (?, ?, ?, ?, ?)",
            (student_id, vendor_id, total, "food", tx_id),
        )

        # Update aggregated spending (visible to parent)
        db.execute("""
            INSERT INTO category_spending (student_id, category, month, amount)
            VALUES (?, 'food', ?, ?)
            ON CONFLICT(student_id, category, month)
            DO UPDATE SET amount = amount + ?
        """, (student_id, month, total, total))

        db.commit()

        # Build the bill
        bill = _build_bill(order_id, student_id, order_lines, total, tx_id, now)

        db.close()
        return jsonify({
            "message": "Order placed successfully!",
            "order_id": order_id,
            "txn_id": tx_id,
            "bill": bill,
        }), 201

    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 500


@canteen_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    """Get past canteen orders for the logged-in student."""
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "Student access only"}), 403

    student_id = get_jwt_identity()
    db = get_db()

    orders = db.execute(
        """SELECT id, total_amount, txn_id, status, created_at
           FROM orders WHERE student_id = ?
           ORDER BY created_at DESC LIMIT 20""",
        (student_id,),
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
            "total": o["total_amount"],
            "txn_id": o["txn_id"],
            "status": o["status"],
            "time": o["created_at"],
            "items": [
                {
                    "name": i["name"],
                    "emoji": i["emoji"],
                    "qty": i["quantity"],
                    "price": i["price"],
                }
                for i in items
            ],
        })

    db.close()
    return jsonify({"orders": result})


@canteen_bp.route("/orders/<int:order_id>/bill", methods=["GET"])
@jwt_required()
def get_bill(order_id):
    """Get the soft bill for a specific order."""
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "Student access only"}), 403

    student_id = get_jwt_identity()
    db = get_db()

    order = db.execute(
        "SELECT id, total_amount, txn_id, status, created_at FROM orders WHERE id = ? AND student_id = ?",
        (order_id, student_id),
    ).fetchone()

    if not order:
        db.close()
        return jsonify({"error": "Order not found"}), 404

    items = db.execute(
        """SELECT oi.quantity, oi.price, mi.name, mi.emoji
           FROM order_items oi
           JOIN menu_items mi ON oi.menu_item_id = mi.id
           WHERE oi.order_id = ?""",
        (order_id,),
    ).fetchall()

    db.close()

    lines = [
        {
            "name": i["name"],
            "emoji": i["emoji"],
            "qty": i["quantity"],
            "price": i["price"],
            "line_total": i["quantity"] * i["price"],
        }
        for i in items
    ]

    bill = _build_bill(
        order["id"], student_id, lines,
        order["total_amount"], order["txn_id"], order["created_at"],
    )

    return jsonify({"bill": bill})


# ---------- bill builder ----------

def _build_bill(order_id, student_id, lines, total, txn_id, timestamp):
    """Build a structured soft bill / receipt object."""
    return {
        "order_id": order_id,
        "student_id": int(student_id),
        "vendor": "Campus Canteen",
        "items": [
            {
                "name": l.get("name", ""),
                "emoji": l.get("emoji", "🍽️"),
                "qty": l.get("qty", l.get("quantity", 1)),
                "unit_price": l.get("price", 0),
                "line_total": l.get("line_total", l.get("price", 0) * l.get("qty", l.get("quantity", 1))),
            }
            for l in lines
        ],
        "total": total,
        "txn_id": txn_id,
        "timestamp": str(timestamp),
        "payment_method": "CampusToken (Algorand ASA)",
    }
