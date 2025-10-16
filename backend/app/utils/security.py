import jwt
import secrets
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import bcrypt, mongo
from app.models.customer import Customer
from app.models.manager import Manager


class SecurityUtils:
    """Security utilities for authentication and authorization"""

    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt"""
        return bcrypt.generate_password_hash(password).decode('utf-8')

    @staticmethod
    def verify_password(password, hashed_password):
        """Verify password against hash"""
        return bcrypt.check_password_hash(hashed_password, password)

    @staticmethod
    def generate_secure_token(length=32):
        """Generate secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def generate_bank_key():
        """Generate secure bank key for managers"""
        return SecurityUtils.generate_secure_token(16)

    @staticmethod
    def mask_sensitive_data(data, fields_to_mask):
        """Mask sensitive data for logging"""
        masked_data = data.copy()
        for field in fields_to_mask:
            if field in masked_data:
                value = masked_data[field]
                if isinstance(value, str) and len(value) > 4:
                    masked_data[field] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    masked_data[field] = '***'
        return masked_data

    @staticmethod
    def validate_jwt_token(token):
        """Validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, "Token has expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"

    @staticmethod
    def get_user_from_token():
        """Get user information from JWT token"""
        try:
            user_id = get_jwt_identity()
            user_type = get_jwt().get('user_type')

            if user_type == 'customer':
                return Customer.find_by_id(user_id), 'customer'
            elif user_type == 'manager':
                return Manager.find_by_id(user_id), 'manager'
            else:
                return None, None
        except Exception:
            return None, None

    @staticmethod
    def check_permissions(user, required_permissions):
        """Check if user has required permissions"""
        if not user:
            return False

        user_permissions = getattr(user, 'permissions', [])
        return any(perm in user_permissions for perm in required_permissions)


def require_auth(f):
    """Decorator to require authentication"""

    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user, user_type = SecurityUtils.get_user_from_token()
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        return f(user, user_type, *args, **kwargs)

    return decorated_function


def require_customer_auth(f):
    """Decorator to require customer authentication"""

    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user, user_type = SecurityUtils.get_user_from_token()
        if not user or user_type != 'customer':
            return jsonify({'error': 'Customer authentication required'}), 403
        return f(user, *args, **kwargs)

    return decorated_function


def require_manager_auth(f):
    """Decorator to require manager authentication"""

    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user, user_type = SecurityUtils.get_user_from_token()
        if not user or user_type != 'manager':
            return jsonify({'error': 'Manager authentication required'}), 403
        return f(user, *args, **kwargs)

    return decorated_function


def validate_request_data(schema):
    """Decorator to validate request data"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No JSON data provided'}), 400

                # Validate data against schema
                errors = schema.validate(data)
                if errors:
                    return jsonify({'error': 'Validation failed', 'details': errors}), 400

                return f(data, *args, **kwargs)
            except Exception as e:
                return jsonify({'error': 'Invalid request data'}), 400

        return decorated_function

    return decorator


def rate_limit(max_requests=100, window=3600):
    """Rate limiting decorator"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = datetime.utcnow()

            # Check rate limit
            key = f"rate_limit:{client_ip}"
            requests = mongo.db.rate_limits.find_one({'key': key})

            if requests:
                if current_time - requests['window_start'] > timedelta(seconds=window):
                    # Reset window
                    mongo.db.rate_limits.update_one(
                        {'key': key},
                        {'$set': {'count': 1, 'window_start': current_time}}
                    )
                elif requests['count'] >= max_requests:
                    return jsonify({'error': 'Rate limit exceeded'}), 429
                else:
                    # Increment count
                    mongo.db.rate_limits.update_one(
                        {'key': key},
                        {'$inc': {'count': 1}}
                    )
            else:
                # Create new rate limit entry
                mongo.db.rate_limits.insert_one({
                    'key': key,
                    'count': 1,
                    'window_start': current_time
                })

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def log_activity(activity_type):
    """Decorator to log user activity"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                user, user_type = SecurityUtils.get_user_from_token()
                if user:
                    # Log activity
                    activity_log = {
                        'user_id': str(user.id),
                        'user_type': user_type,
                        'activity_type': activity_type,
                        'ip_address': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent'),
                        'timestamp': datetime.utcnow(),
                        'endpoint': request.endpoint,
                        'method': request.method
                    }

                    mongo.db.activity_logs.insert_one(activity_log)

                return f(*args, **kwargs)
            except Exception:
                # Don't fail the request if logging fails
                return f(*args, **kwargs)

        return decorated_function

    return decorator


class CSRFProtection:
    """CSRF protection utilities"""

    @staticmethod
    def generate_csrf_token():
        """Generate CSRF token"""
        return SecurityUtils.generate_secure_token()

    @staticmethod
    def validate_csrf_token(token):
        """Validate CSRF token"""
        # In a real implementation, you would store and validate CSRF tokens
        # For this demo, we'll use a simple validation
        return len(token) >= 16 and token.isalnum()


def require_csrf_token(f):
    """Decorator to require CSRF token"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            csrf_token = request.headers.get('X-CSRF-Token')
            if not csrf_token or not CSRFProtection.validate_csrf_token(csrf_token):
                return jsonify({'error': 'Invalid CSRF token'}), 403
        return f(*args, **kwargs)

    return decorated_function