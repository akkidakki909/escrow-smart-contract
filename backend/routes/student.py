"""
Student Routes — Balance & Pay
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db
from services.algorand_service import get_token_balance, pay_vendor

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
    return jsonify({"balance": bal, "address": user["algo_address"]})


@student_bp.route("/pay", methods=["POST"])
@jwt_required()
def pay():
    """
    Pay a vendor.
    Body: { vendor_address, amount, category: 'food'|'events'|'stationery' }

    NOTE: In a real app, the student's private key would be managed
    by a wallet (e.g. Pera Wallet). For MVP, we accept mnemonic in
    the request header.
    """
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "Student access only"}), 403

    data = request.get_json()
    vendor_address = data.get("vendor_address")
    amount = data.get("amount", 0)
    category = data.get("category", "")

    if not vendor_address or amount <= 0:
        return jsonify({"error": "Invalid payment details"}), 400

    if category not in ("food", "events", "stationery"):
        return jsonify({"error": "Invalid category"}), 400

    # For MVP: mnemonic passed in header (NOT safe for production)
    from algosdk import mnemonic as mn, account as acc
    student_mnemonic = request.headers.get("X-Student-Mnemonic", "")
    if not student_mnemonic:
        return jsonify({"error": "Student mnemonic required (MVP mode)"}), 400

    try:
        student_sk = mn.to_private_key(student_mnemonic)
        student_addr = acc.address_from_private_key(student_sk)
    except Exception:
        return jsonify({"error": "Invalid mnemonic"}), 400

    try:
        tx_id = pay_vendor(student_sk, student_addr, vendor_address, amount, category)
        return jsonify({
            "message": "Payment successful",
            "txn_id": tx_id,
            "amount": amount,
            "category": category,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
