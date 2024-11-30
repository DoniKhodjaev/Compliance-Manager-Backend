from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Initialize Flask application
app = Flask(__name__)
CORS(app)

# Import blueprints and initialization functions
from app.routes.swift_routes import swift_blueprint
from app.routes.sdn_routes import sdn_blueprint
from app.routes.auth_routes import auth_blueprint
from app.services.swift_service import initialize_db  # Example import
from app.services.auth_service import AuthService

# Initialize database
initialize_db()
AuthService.initialize_db()

# Register blueprints
app.register_blueprint(swift_blueprint, url_prefix="/api/swift")
app.register_blueprint(sdn_blueprint, url_prefix="/api/sdn")
app.register_blueprint(auth_blueprint, url_prefix='/api/auth')


# Add other endpoints
@app.route("/")
def home():
    return jsonify(
        {
            "message": "Welcome to the API",
            "version": "1.0",
            "endpoints": {
                "swift": {
                    "base": "/api/swift",
                    "routes": [
                        "/process-swift",
                        "/parsed-swift-files",
                        "/search-orginfo",
                        "/search-egrul",
                        "/search-swift",
                    ],
                },
                "sdn": {"base": "/api/sdn", "routes": ["/list", "/update"]},
                "auth": {"base": "/api/auth", "routes": ["/login", "/register", "/verify-token", "/protected"]},
            },
        }
    )


@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


@app.route("/api/status")
def api_status():
    return jsonify(
        {"status": "operational", "database": "connected", "version": "1.0.0"}
    )


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
   return (
       jsonify(
           {
               "error": "Not Found",
               "message": "The requested URL was not found on the server.",
           }
      ),
       404,
   )


@app.errorhandler(500)
def internal_error(error):
    return (
        jsonify(
            {
                "error": "Internal Server Error",
                "message": "An internal server error occurred.",
            }
        ),
        500,
    )


if __name__ == "__main__":
    try:
        debug_mode = os.getenv("DEBUG_MODE", "True").lower() == "true"
        port = int(os.getenv("PORT", 5000))
        app.run(host="127.0.0.1", port=port, debug=debug_mode)
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
