"""
CampusChain Backend — Flask Application Entry Point (Custodial)

No indexer thread needed — spending is aggregated at payment time
in the /vendor/pay route, not by polling the blockchain.
"""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import SECRET_KEY, JWT_SECRET_KEY
from models import init_db
from routes.auth import auth_bp
from routes.student import student_bp
from routes.parent import parent_bp
from routes.vendor import vendor_bp
from routes.admin import admin_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY

    CORS(app)
    JWTManager(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(vendor_bp)
    app.register_blueprint(admin_bp)

    # Initialize database
    init_db()

    @app.route("/")
    def health():
        return {"status": "ok", "service": "CampusChain API (Custodial)"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
