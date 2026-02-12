"""
Admin Routes — System overview
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    """Get system-wide statistics."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access only"}), 403

    db = get_db()

    total_students = db.execute("SELECT COUNT(*) as c FROM users WHERE role = 'student'").fetchone()["c"]
    total_parents = db.execute("SELECT COUNT(*) as c FROM users WHERE role = 'parent'").fetchone()["c"]
    total_vendors = db.execute("SELECT COUNT(*) as c FROM vendors").fetchone()["c"]
    total_funded = db.execute("SELECT COALESCE(SUM(amount), 0) as t FROM funding_log").fetchone()["t"]
    total_spent = db.execute("SELECT COALESCE(SUM(amount), 0) as t FROM category_spending").fetchone()["t"]
    total_txns = db.execute("SELECT COUNT(*) as c FROM transactions").fetchone()["c"]

    # Spending by category (all-time)
    rows = db.execute(
        "SELECT category, SUM(amount) as total FROM category_spending GROUP BY category"
    ).fetchall()
    db.close()

    by_category = {r["category"]: r["total"] for r in rows}

    return jsonify({
        "users": {
            "students": total_students,
            "parents": total_parents,
            "vendors": total_vendors,
        },
        "financials": {
            "total_funded": total_funded,
            "total_spent": total_spent,
            "total_transactions": total_txns,
        },
        "spending_by_category": by_category,
    })
