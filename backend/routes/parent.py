"""
Parent Routes — Fund Student & View Aggregated Spending (Custodial)

PRIVACY: Parents NEVER see individual transactions, vendor names, or timestamps.
CUSTODIAL: Parents don't need any wallet or crypto. They click "Fund" and the
           backend signs everything.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db
from services.algorand_service import fund_student, get_token_balance

parent_bp = Blueprint("parent", __name__, url_prefix="/api/parent")


@parent_bp.route("/fund", methods=["POST"])
@jwt_required()
def fund():
    """
    Fund a student's wallet (simulated UPI → backend mints tokens).
    Body: { student_id, amount }

    The parent clicks a button. The backend:
    1. Simulates UPI success
    2. Signs an ASA transfer from admin → student using admin mnemonic
    3. Logs the funding
    NO wallet connection required from the parent.
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

    student = db.execute(
        "SELECT algo_address FROM users WHERE id = ? AND role = 'student'",
        (student_id,),
    ).fetchone()
    if not student or not student["algo_address"]:
        db.close()
        return jsonify({"error": "Student wallet not found"}), 404

    try:
        tx_id = fund_student(student["algo_address"], amount)

        db.execute(
            "INSERT INTO funding_log (parent_id, student_id, amount, txn_id) VALUES (?, ?, ?, ?)",
            (parent_id, student_id, amount, tx_id),
        )
        db.commit()
        db.close()

        return jsonify({
            "message": f"Successfully funded ₹{amount}",
            "tokens_sent": amount,
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
    Does NOT return: individual transactions, vendor names, timestamps.
    """
    claims = get_jwt()
    if claims.get("role") != "parent":
        return jsonify({"error": "Parent access only"}), 403

    parent_id = get_jwt_identity()
    student_id = request.args.get("student_id")
    month = request.args.get("month", datetime.utcnow().strftime("%Y-%m"))

    db = get_db()

    relation = db.execute(
        "SELECT 1 FROM parent_student WHERE parent_id = ? AND student_id = ?",
        (parent_id, student_id),
    ).fetchone()
    if not relation:
        db.close()
        return jsonify({"error": "Student not linked to this parent"}), 403

    student = db.execute(
        "SELECT username, algo_address FROM users WHERE id = ?", (student_id,)
    ).fetchone()
    if not student:
        db.close()
        return jsonify({"error": "Student not found"}), 404

    # Aggregated spending from DB (written at payment time)
    rows = db.execute(
        "SELECT category, amount FROM category_spending WHERE student_id = ? AND month = ?",
        (student_id, month),
    ).fetchall()

    funded = db.execute(
        """SELECT COALESCE(SUM(amount), 0) as total FROM funding_log
           WHERE student_id = ? AND strftime('%Y-%m', created_at) = ?""",
        (student_id, month),
    ).fetchone()
    db.close()

    breakdown = {"food": 0, "events": 0, "stationery": 0}
    total_spent = 0
    for row in rows:
        breakdown[row["category"]] = row["amount"]
        total_spent += row["amount"]

    balance = get_token_balance(student["algo_address"]) if student["algo_address"] else 0

    return jsonify({
        "student_name": student["username"],
        "month": month,
        "total_funded": funded["total"] if funded else 0,
        "total_spent": total_spent,
        "balance": balance,
        "breakdown": breakdown,
        # INTENTIONALLY NO: transaction list, vendor names, timestamps
    })


@parent_bp.route("/students", methods=["GET"])
@jwt_required()
def get_students():
    """Get list of linked students for this parent."""
    claims = get_jwt()
    if claims.get("role") != "parent":
        return jsonify({"error": "Parent access only"}), 403

    parent_id = get_jwt_identity()
    db = get_db()
    rows = db.execute(
        """SELECT u.id, u.username FROM users u
           JOIN parent_student ps ON u.id = ps.student_id
           WHERE ps.parent_id = ?""",
        (parent_id,),
    ).fetchall()
    db.close()

    return jsonify({
        "students": [{"id": r["id"], "name": r["username"]} for r in rows]
    })
