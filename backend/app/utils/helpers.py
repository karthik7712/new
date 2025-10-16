import logging
import traceback
from datetime import datetime
from flask import jsonify, request
from app import mongo
from app.utils.security import SecurityUtils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIResponse:
    """Standardized API response helper"""

    @staticmethod
    def success(data=None, message="Success", status_code=200):
        """Create success response"""
        response = {
            'success': True,
            'message': message,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        return jsonify(response), status_code

    @staticmethod
    def error(message="Error", status_code=400, details=None):
        """Create error response"""
        response = {
            'success': False,
            'message': message,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        return jsonify(response), status_code

    @staticmethod
    def validation_error(errors, message="Validation failed"):
        """Create validation error response"""
        return APIResponse.error(
            message=message,
            status_code=400,
            details={'validation_errors': errors}
        )

    @staticmethod
    def unauthorized(message="Unauthorized"):
        """Create unauthorized response"""
        return APIResponse.error(message=message, status_code=401)

    @staticmethod
    def forbidden(message="Forbidden"):
        """Create forbidden response"""
        return APIResponse.error(message=message, status_code=403)

    @staticmethod
    def not_found(message="Resource not found"):
        """Create not found response"""
        return APIResponse.error(message=message, status_code=404)

    @staticmethod
    def conflict(message="Resource conflict"):
        """Create conflict response"""
        return APIResponse.error(message=message, status_code=409)

    @staticmethod
    def server_error(message="Internal server error"):
        """Create server error response"""
        return APIResponse.error(message=message, status_code=500)


class ErrorHandler:
    """Centralized error handling"""

    @staticmethod
    def handle_validation_error(error):
        """Handle validation errors"""
        logger.warning(f"Validation error: {str(error)}")
        return APIResponse.validation_error(str(error))

    @staticmethod
    def handle_authentication_error(error):
        """Handle authentication errors"""
        logger.warning(f"Authentication error: {str(error)}")
        return APIResponse.unauthorized("Invalid credentials")

    @staticmethod
    def handle_authorization_error(error):
        """Handle authorization errors"""
        logger.warning(f"Authorization error: {str(error)}")
        return APIResponse.forbidden("Insufficient permissions")

    @staticmethod
    def handle_not_found_error(error):
        """Handle not found errors"""
        logger.warning(f"Not found error: {str(error)}")
        return APIResponse.not_found("Resource not found")

    @staticmethod
    def handle_database_error(error):
        """Handle database errors"""
        logger.error(f"Database error: {str(error)}")
        return APIResponse.server_error("Database operation failed")

    @staticmethod
    def handle_general_error(error):
        """Handle general errors"""
        logger.error(f"General error: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return APIResponse.server_error("An unexpected error occurred")


def register_error_handlers(app):
    """Register error handlers with Flask app"""

    @app.errorhandler(400)
    def bad_request(error):
        return APIResponse.error("Bad request", 400)

    @app.errorhandler(401)
    def unauthorized(error):
        return APIResponse.unauthorized()

    @app.errorhandler(403)
    def forbidden(error):
        return APIResponse.forbidden()

    @app.errorhandler(404)
    def not_found(error):
        return APIResponse.not_found()

    @app.errorhandler(409)
    def conflict(error):
        return APIResponse.conflict()

    @app.errorhandler(422)
    def unprocessable_entity(error):
        return APIResponse.validation_error("Unprocessable entity")

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return APIResponse.error("Rate limit exceeded", 429)

    @app.errorhandler(500)
    def internal_server_error(error):
        return APIResponse.server_error()

    @app.errorhandler(Exception)
    def handle_exception(error):
        return ErrorHandler.handle_general_error(error)


class DataProcessor:
    """Data processing utilities"""

    @staticmethod
    def paginate_query(query, page=1, per_page=10):
        """Paginate MongoDB query results"""
        skip = (page - 1) * per_page
        total = query.count()
        items = list(query.skip(skip).limit(per_page))

        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'has_next': page * per_page < total,
            'has_prev': page > 1
        }

    @staticmethod
    def sanitize_user_data(user_data):
        """Sanitize user data by removing sensitive fields"""
        sensitive_fields = ['password', 'password_hash', 'bank_key', 'pan', 'aadhaar']
        sanitized = user_data.copy()

        for field in sensitive_fields:
            sanitized.pop(field, None)

        return sanitized

    @staticmethod
    def format_currency(amount, currency='INR'):
        """Format currency amount"""
        if currency == 'INR':
            return f"₹{amount:,.2f}"
        else:
            return f"{currency} {amount:,.2f}"

    @staticmethod
    def calculate_age(birth_date):
        """Calculate age from birth date"""
        today = datetime.utcnow().date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


class NotificationService:
    """Notification service for sending alerts"""

    @staticmethod
    def create_notification(user_id, user_type, notification_type, message, data=None):
        """Create a notification"""
        notification = {
            'user_id': user_id,
            'user_type': user_type,
            'notification_type': notification_type,
            'message': message,
            'data': data or {},
            'is_read': False,
            'created_at': datetime.utcnow()
        }

        try:
            mongo.db.notifications.insert_one(notification)
            logger.info(f"Notification created for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            return False

    @staticmethod
    def get_user_notifications(user_id, user_type, limit=10):
        """Get user notifications"""
        try:
            notifications = mongo.db.notifications.find({
                'user_id': user_id,
                'user_type': user_type
            }).sort('created_at', -1).limit(limit)

            return list(notifications)
        except Exception as e:
            logger.error(f"Failed to get notifications: {str(e)}")
            return []

    @staticmethod
    def mark_notification_read(notification_id):
        """Mark notification as read"""
        try:
            mongo.db.notifications.update_one(
                {'_id': notification_id},
                {'$set': {'is_read': True, 'read_at': datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {str(e)}")
            return False


class AuditLogger:
    """Audit logging for security and compliance"""

    @staticmethod
    def log_user_action(user_id, user_type, action, details=None):
        """Log user action for audit trail"""
        audit_entry = {
            'user_id': user_id,
            'user_type': user_type,
            'action': action,
            'details': details or {},
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'timestamp': datetime.utcnow()
        }

        try:
            mongo.db.audit_logs.insert_one(audit_entry)
            logger.info(f"Audit log: {action} by {user_type} {user_id}")
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")

    @staticmethod
    def log_security_event(event_type, details=None):
        """Log security-related events"""
        security_entry = {
            'event_type': event_type,
            'details': details or {},
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'timestamp': datetime.utcnow()
        }

        try:
            mongo.db.security_logs.insert_one(security_entry)
            logger.warning(f"Security event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to create security log: {str(e)}")


class PerformanceMonitor:
    """Performance monitoring utilities"""

    @staticmethod
    def measure_execution_time(func):
        """Decorator to measure function execution time"""
        import time

        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            execution_time = end_time - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")

            return result

        return wrapper

    @staticmethod
    def log_slow_queries(query_time, query_details):
        """Log slow database queries"""
        if query_time > 1.0:  # Log queries taking more than 1 second
            logger.warning(f"Slow query detected: {query_time:.4f}s - {query_details}")


# Utility functions for common operations
def generate_unique_id():
    """Generate unique ID"""
    import uuid
    return str(uuid.uuid4())


def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr


def is_valid_object_id(id_string):
    """Check if string is valid MongoDB ObjectId"""
    from bson import ObjectId
    try:
        ObjectId(id_string)
        return True
    except:
        return False