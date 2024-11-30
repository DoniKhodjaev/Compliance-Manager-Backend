import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Optional
import os
from app.utils import get_db_connection

# Constants
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')  # In production, use environment variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )

    @staticmethod
    def create_token(user_data: Dict) -> str:
        """Create a JWT token for a user."""
        expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        payload = {
            **user_data,
            "exp": expiration
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """Verify a JWT token and return the payload if valid."""
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def initialize_db():
        """Initialize the users table in the database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    @staticmethod
    def create_user(username: str, password: str, email: str = None, role: str = 'user') -> bool:
        """Create a new user in the database."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            hashed_password = AuthService.hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)',
                (username, hashed_password, email, role)
            )
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict]:
        """Authenticate a user and return user data if successful."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            if user and AuthService.verify_password(password, user['password']):
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role']
                }
            return None
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
        finally:
            conn.close() 