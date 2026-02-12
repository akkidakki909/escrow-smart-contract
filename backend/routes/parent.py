"""
Parent Routes — Fund Student & View Aggregated Spending

THIS IS THE PRIVACY-CRITICAL ROUTE FILE.
The /spending endpoint returns ONLY aggregated data — no individual
transactions, merchant names, or timestamps.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db
from services.algorand_service import fund_student_direct, get_token_balance

parent_bp = Blueprint("parent", __name__, url_prefix="/api/parent")


@parent_bp.route("/fund", methods=["POST"])
@jwt_required()
def fund():
    """
    Fund a student's wallet (simulated UPI → mint tokens).
    Body: { student_id, amount }
    """
    claims = get_jwt()
    if claims.get("role") != "parent":
        return jsonify({"error": "Parent access only"}), 403

    parent_id = get_jwt_identity()
    data = request.get_json()
    student_id = data.get("student_id")
    amount = data.get("amount", 0)

    if not student_id or amount <= 0:
        return jsonify({"error": "Invalid funding details"}), 400

    db = get_db()

    # Verify parent-student relationship
    relation = db.execute(
        "SELECT 1 FROM parent_student WHERE parent_id = ? AND student_id = ?",
        (parent_id, student_id),
    ).fetchone()
    if not relation:
        db.close()
        return jsonify({"error": "Student not linked to this parent"}), 403

    # Get student's algo address
    student = db.execute(
        "SELECT algo_address FROM users WHERE id = ? AND role = 'student'",
        (student_id,),
    ).fetchone()
    if not student or not student["algo_address"]:
        db.close()
        return jsonify({"error": "Student wallet not found"}), 404

    try:
        # Simulate UPI payment success, then mint tokens
        tx_id = fund_student_direct(student["algo_address"], amount)

        # Log the funding
        db.execute(
            "INSERT INTO funding_log (parent_id, student_id, amount, txn_id) VALUES (?, ?, ?, ?)",
            (parent_id, student_id, amount, tx_id),
        )
        db.commit()
        db.close()

        return jsonify({
            "message": f"Successfully funded ₹{amount}",
            "tokens_sent": amount,
            "txn_id": tx_id,
        })
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 500


@parent_bp.route("/spending", methods=["GET"])
@jwt_required()
def spending():
    """
    Get aggregated spending for the parent's linked student(s).

    Query params: student_id, month (YYYY-MM)

    PRIVACY: Returns ONLY totals and per-category breakdowns.
    Does NOT return individual transactions, vendor names, or timestamps.
    """
    claims = get_jwt()
    if claims.get("role") != "parent":
        return jsonify({"error": "Parent access only"}), 403

    parent_id = get_jwt_identity()
    student_id = request.args.get("student_id")
    month = request.args.get("month")  # e.g. "2026-02"

    db = get_db()

    # Verify relationship
    relation = db.execute(
        "SELECT 1 FROM parent_student WHERE parent_id = ? AND student_id = ?",
        (parent_id, student_id),
    ).fetchone()
    if not relation:
        db.close()
        return jsonify({"error": "Student not linked to this parent"}), 403

    # Get student info
    student = db.execute(
        "SELECT username, algo_address FROM users WHERE id = ?", (student_id,)
    ).fetchone()
    if not student:
        db.close()
        return jsonify({"error": "Student not found"}), 404

    # Get aggregated spending
    rows = db.execute(
        "SELECT category, amount FROM category_spending WHERE student_id = ? AND month = ?",
        (student_id, month),
    ).fetchall()

    # Get total funded this month
    funded = db.execute(
        """SELECT COALESCE(SUM(amount), 0) as total FROM funding_log
           WHERE student_id = ? AND strftime('%Y-%m', created_at) = ?""",
        (student_id, month),
    ).fetchone()
    db.close()

    breakdown = {}
    total_spent = 0
    for row in rows:
        breakdown[row["category"]] = row["amount"]
        total_spent += row["amount"]

    # Get current balance from blockchain
    balance = get_token_balance(student["algo_address"]) if student["algo_address"] else 0

    return jsonify({
        "student_name": student["username"],
        "month": month,
        "total_funded": funded["total"] if funded else 0,
        "total_spent": total_spent,
        "balance": balance,
        "breakdown": breakdown,
        # NOTE: No transaction list, no vendor names, no timestamps
    })
