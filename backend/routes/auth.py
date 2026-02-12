"""
Auth Routes — Register & Login (Custodial)

Wallets are created server-side and mnemonics stored in DB.
No user ever needs to know about Algorand or wallets.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import get_db
from services.algorand_service import create_wallet, opt_in_asa, fund_account_with_algo

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    Body: { username, password, role: 'student'|'parent'|'vendor' }

    For students and vendors: a custodial Algorand wallet is created,
    funded with ALGO, and opted into CampusToken — all silently.
    Parents do NOT get wallets.
    """
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "student")
    linked_student = data.get("linked_student_id")  # For parent registration

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if role not in ("student", "parent", "vendor"):
        return jsonify({"error": "Invalid role"}), 400

    algo_address = None
    algo_mnemonic = None

    # Only students and vendors get custodial wallets
    if role in ("student", "vendor"):
        algo_address, algo_mnemonic = create_wallet()
        try:
            # Seed with ALGO for minimum balance + ASA opt-in fees
            fund_account_with_algo(algo_address)
            # Auto opt-in to CampusToken ASA
            opt_in_asa(algo_mnemonic)
        except Exception as e:
            # Non-fatal for MVP — can retry later
            print(f"Warning: wallet setup incomplete for {username}: {e}")

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash, role, algo_address, algo_mnemonic) VALUES (?, ?, ?, ?, ?)",
            (username, generate_password_hash(password), role, algo_address, algo_mnemonic),
        )
        db.commit()

        user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()

        # Auto-link parent to student if provided
        if role == "parent" and linked_student:
            db.execute(
                "INSERT OR IGNORE INTO parent_student (parent_id, student_id) VALUES (?, ?)",
                (user["id"], linked_student),
            )
            db.commit()

        db.close()

        response = {
            "message": "Registered successfully",
            "user_id": user["id"],
            "role": role,
        }
        # Only show address for students/vendors (never mnemonic to user)
        if algo_address:
            response["algo_address"] = algo_address

        return jsonify(response), 201

    except Exception:
        db.close()
        return jsonify({"error": "Username already taken"}), 409


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
    })


@auth_bp.route("/link-student", methods=["POST"])
def link_student():
    """
    Link a parent to a student.
    Body: { parent_id, student_id }
    """
    data = request.get_json()
    parent_id = data.get("parent_id")
    student_id = data.get("student_id")

    db = get_db()
    parent = db.execute("SELECT role FROM users WHERE id = ?", (parent_id,)).fetchone()
    student = db.execute("SELECT role FROM users WHERE id = ?", (student_id,)).fetchone()

    if not parent or parent["role"] != "parent":
        db.close()
        return jsonify({"error": "Invalid parent"}), 400
    if not student or student["role"] != "student":
        db.close()
        return jsonify({"error": "Invalid student"}), 400

    db.execute(
        "INSERT OR IGNORE INTO parent_student (parent_id, student_id) VALUES (?, ?)",
        (parent_id, student_id),
    )
    db.commit()
    db.close()

    return jsonify({"message": "Linked successfully"})
