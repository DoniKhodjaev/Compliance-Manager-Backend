from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
import jwt
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Add your user verification logic here
    if username == "admin" and password == "password":
        token = jwt.encode({
            'user': username,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, 'your-secret-key')
        
        return jsonify({'token': token})
    
    return jsonify({'error': 'Invalid credentials'}), 401 