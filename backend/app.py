"""
CampusChain Backend — Flask Application Entry Point
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
from services.indexer_service import start_indexer_thread


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

    # Initialize database
    init_db()

    # Start the spending indexer background thread
    start_indexer_thread(interval=30)

    @app.route("/")
    def health():
        return {"status": "ok", "service": "CampusChain API"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
