from flask import Blueprint
from app.utils.helpers import APIResponse

health_bp = Blueprint('health', __name__)

@health_bp.route('/check', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return APIResponse.success(
        data={'status': 'healthy', 'service': 'Credit Card Management System'},
        message="Service is running"
    )