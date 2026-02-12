"""
Student Routes — Balance & Summary (Custodial)

GET /student/balance  → current CampusToken balance
GET /student/summary  → aggregated monthly spending (privacy-preserving)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db
from services.algorand_service import get_token_balance

student_bp = Blueprint("student", __name__, url_prefix="/api/student")


@student_bp.route("/balance", methods=["GET"])
@jwt_required()
def balance():
    """Get the student's CampusToken balance."""
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "Student access only"}), 403

    user_id = get_jwt_identity()
    db = get_db()
    user = db.execute("SELECT algo_address FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()

    if not user or not user["algo_address"]:
        return jsonify({"error": "No wallet found"}), 404

    bal = get_token_balance(user["algo_address"])
    return jsonify({"balance": bal})


@student_bp.route("/summary", methods=["GET"])
@jwt_required()
def summary():
    """
    Get student's own spending summary.
    Query params: month (YYYY-MM, optional — defaults to current)

    Returns:
      - total monthly spending
      - spending by category
      - current balance
    Does NOT return raw transaction hashes or vendor addresses.
    """
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "Student access only"}), 403

    user_id = get_jwt_identity()
    month = request.args.get("month", datetime.utcnow().strftime("%Y-%m"))

    db = get_db()
    user = db.execute("SELECT username, algo_address FROM users WHERE id = ?", (user_id,)).fetchone()

    if not user:
        db.close()
        return jsonify({"error": "User not found"}), 404

    # Aggregated spending
    rows = db.execute(
        "SELECT category, amount FROM category_spending WHERE student_id = ? AND month = ?",
        (user_id, month),
    ).fetchall()

    # Recent transactions (student can see their own)
    recent = db.execute(
        """SELECT t.amount, t.category, t.created_at, v.name as vendor_name
           FROM transactions t
           LEFT JOIN vendors v ON t.vendor_id = v.id
           WHERE t.student_id = ? AND strftime('%Y-%m', t.created_at) = ?
           ORDER BY t.created_at DESC LIMIT 20""",
        (user_id, month),
    ).fetchall()

    db.close()

    breakdown = {"food": 0, "events": 0, "stationery": 0}
    total_spent = 0
    for row in rows:
        breakdown[row["category"]] = row["amount"]
        total_spent += row["amount"]

    balance = get_token_balance(user["algo_address"]) if user["algo_address"] else 0

    return jsonify({
        "user_id": int(user_id),
        "username": user["username"],
        "month": month,
        "total_spent": total_spent,
        "balance": balance,
        "breakdown": breakdown,
        "recent_transactions": [
            {
                "amount": r["amount"],
                "category": r["category"],
                "vendor": r["vendor_name"] or "Unknown",
                "time": r["created_at"],
            }
            for r in recent
        ],
    })
