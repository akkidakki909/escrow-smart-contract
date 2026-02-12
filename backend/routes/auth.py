"""
Auth Routes — Register & Login
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from algosdk import account, mnemonic

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    Body: { username, password, role: 'student'|'parent'|'vendor' }
    """
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "student")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if role not in ("student", "parent", "vendor"):
        return jsonify({"error": "Invalid role"}), 400

    # Generate an Algorand address for the user
    sk, addr = account.generate_account()
    user_mnemonic = mnemonic.from_private_key(sk)

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash, role, algo_address) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), role, addr),
        )
        db.commit()
    except Exception as e:
        db.close()
        return jsonify({"error": "Username already taken"}), 409

    user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    db.close()

    return jsonify({
        "message": "Registered successfully",
        "user_id": user["id"],
        "algo_address": addr,
        "mnemonic": user_mnemonic,  # In production, store securely — shown for MVP demo
        "role": role,
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login and receive JWT.
    Body: { username, password }
    """
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    db.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(
        identity=str(user["id"]),
        additional_claims={"role": user["role"], "username": user["username"]},
    )

    return jsonify({
        "token": token,
        "user_id": user["id"],
        "role": user["role"],
        "algo_address": user["algo_address"],
    })
