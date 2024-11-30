from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from functools import wraps

auth_blueprint = Blueprint('auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        user_data = AuthService.verify_token(token)
        if not user_data:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated

@auth_blueprint.route('/login', methods=['POST'])
def login():
    """Handle user login."""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Missing username or password'}), 400
    
    user = AuthService.authenticate_user(data['username'], data['password'])
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401
    
    token = AuthService.create_token(user)
    return jsonify({
        'token': token,
        'user': user
    })

@auth_blueprint.route('/register', methods=['POST'])
def register():
    """Handle user registration."""
    data = request.get_json()
    
    required_fields = ['username', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Missing required fields'}), 400
    
    if AuthService.create_user(
        username=data['username'],
        password=data['password'],
        email=data.get('email'),
        role=data.get('role', 'user')
    ):
        return jsonify({'message': 'User created successfully'}), 201
    else:
        return jsonify({'message': 'Username already exists'}), 409

@auth_blueprint.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify a JWT token."""
    data = request.get_json()
    
    if not data or 'token' not in data:
        return jsonify({'message': 'Token is missing'}), 400
    
    user_data = AuthService.verify_token(data['token'])
    if user_data:
        return jsonify({'valid': True, 'user': user_data})
    return jsonify({'valid': False}), 401

@auth_blueprint.route('/protected', methods=['GET'])
@token_required
def protected():
    """Example protected route."""
    return jsonify({'message': 'This is a protected route'}) 