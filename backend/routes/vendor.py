"""
Vendor Routes — Register & QR generation
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
import json

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db

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
        "algo_address": user["algo_address"],
    }), 201


@vendor_bp.route("/qr", methods=["GET"])
@jwt_required()
def get_qr_data():
    """
    Generate QR code data for vendor payment.
    The QR encodes the vendor address and category.

    For the MVP, we return JSON that a student wallet would scan.
    """
    claims = get_jwt()
    user_id = get_jwt_identity()

    db = get_db()
    vendor = db.execute(
        "SELECT name, category, algo_address FROM vendors WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    db.close()

    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404

    qr_data = {
        "type": "campuschain_payment",
        "vendor_address": vendor["algo_address"],
        "category": vendor["category"],
        "vendor_name": vendor["name"],  # Visible to student, NOT to parent
    }

    return jsonify({
        "qr_data": json.dumps(qr_data),
        "display": {
            "vendor": vendor["name"],
            "category": vendor["category"],
        },
    })
