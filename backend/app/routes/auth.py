from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app.models.customer import Customer
from app.models.manager import Manager
from app.utils.security import SecurityUtils
from app.utils.validators import Validators
from app.utils.helpers import APIResponse, ErrorHandler, AuditLogger
from app import mongo

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register/customer', methods=['POST'])
def register_customer():
    """Register a new customer"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            'first_name', 'last_name', 'username', 'email', 'password',
            'age', 'gender', 'nationality', 'address', 'phone_number',
            'pan', 'aadhaar', 'employment_type', 'annual_income'
        ]

        is_valid, error = Validators.validate_required_fields(data, required_fields)
        if not is_valid:
            return APIResponse.validation_error(error)

        # Validate individual fields
        validations = [
            Validators.validate_email(data['email']),
            Validators.validate_username(data['username']),
            Validators.validate_password(data['password']),
            Validators.validate_phone_number(data['phone_number']),
            Validators.validate_pan(data['pan']),
            Validators.validate_aadhaar(data['aadhaar']),
            Validators.validate_age(data['age']),
            Validators.validate_annual_income(data['annual_income'])
        ]

        for is_valid, error in validations:
            if not is_valid:
                return APIResponse.validation_error(error)

        # Check for existing users
        if Customer.find_by_email(data['email']):
            return APIResponse.conflict("Email already registered")

        if Customer.find_by_username(data['username']):
            return APIResponse.conflict("Username already taken")

        if Customer.find_by_pan(data['pan']):
            return APIResponse.conflict("PAN already registered")

        if Customer.find_by_aadhaar(data['aadhaar']):
            return APIResponse.conflict("Aadhaar already registered")

        # Calculate CIBIL score
        cibil_score = Customer.calculate_cibil_score(data)

        # Prepare customer data
        customer_data = {
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'username': data['username'],
            'email': data['email'],
            'password_hash': SecurityUtils.hash_password(data['password']),
            'age': int(data['age']),
            'gender': data['gender'],
            'nationality': data['nationality'],
            'address': data['address'],
            'phone_number': data['phone_number'],
            'pan': data['pan'].upper(),
            'aadhaar': data['aadhaar'],
            'salary_slips': data.get('salary_slips', []),
            'employment_type': data['employment_type'],
            'company': data.get('company'),
            'years_of_experience': int(data.get('years_of_experience', 0)),
            'annual_income': float(data['annual_income']),
            'bank_account_details': data.get('bank_account_details'),
            'existing_loan_amount': float(data.get('existing_loan_amount', 0)),
            'cibil_score': cibil_score
        }

        # Create customer
        customer = Customer.create(customer_data)

        # Log registration
        AuditLogger.log_user_action(
            str(customer.id), 'customer', 'registration',
            {'email': data['email'], 'username': data['username']}
        )

        return APIResponse.success(
            data={'customer_id': str(customer.id), 'cibil_score': cibil_score},
            message="Customer registered successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@auth_bp.route('/register/manager', methods=['POST'])
def register_manager():
    """Register a new manager"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'password', 'bank_key']
        is_valid, error = Validators.validate_required_fields(data, required_fields)
        if not is_valid:
            return APIResponse.validation_error(error)

        # Validate individual fields
        validations = [
            Validators.validate_email(data['email']),
            Validators.validate_password(data['password']),
            Validators.validate_bank_key(data['bank_key'])
        ]

        for is_valid, error in validations:
            if not is_valid:
                return APIResponse.validation_error(error)

        # Check for existing manager
        if Manager.find_by_email(data['email']):
            return APIResponse.conflict("Email already registered")

        if Manager.find_by_bank_key(data['bank_key']):
            return APIResponse.conflict("Bank key already in use")

        # Prepare manager data
        manager_data = {
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'password_hash': SecurityUtils.hash_password(data['password']),
            'bank_key': data['bank_key']
        }

        # Create manager
        manager = Manager.create(manager_data)

        # Log registration
        AuditLogger.log_user_action(
            str(manager.id), 'manager', 'registration',
            {'email': data['email']}
        )

        return APIResponse.success(
            data={'manager_id': str(manager.id)},
            message="Manager registered successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@auth_bp.route('/login/customer', methods=['POST'])
def login_customer():
    """Customer login"""
    try:
        data = request.get_json()

        # Validate required fields
        is_valid, error = Validators.validate_required_fields(data, ['username', 'password'])
        if not is_valid:
            return APIResponse.validation_error(error)

        # Find customer by username or email
        customer = Customer.find_by_username(data['username'])
        if not customer:
            customer = Customer.find_by_email(data['username'])

        if not customer or not SecurityUtils.verify_password(data['password'], customer.password_hash):
            AuditLogger.log_security_event('failed_login_attempt', {
                'username': data['username'],
                'user_type': 'customer'
            })
            return APIResponse.unauthorized("Invalid credentials")

        if not customer.is_active:
            return APIResponse.forbidden("Account is deactivated")

        # Create tokens
        access_token = create_access_token(
            identity=str(customer.id),
            additional_claims={'user_type': 'customer'}
        )
        refresh_token = create_refresh_token(
            identity=str(customer.id),
            additional_claims={'user_type': 'customer'}
        )

        # Log successful login
        AuditLogger.log_user_action(
            str(customer.id), 'customer', 'login',
            {'ip_address': request.remote_addr}
        )

        return APIResponse.success(
            data={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': customer.to_dict()
            },
            message="Login successful"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@auth_bp.route('/login/manager', methods=['POST'])
def login_manager():
    """Manager login"""
    try:
        data = request.get_json()

        # Validate required fields
        is_valid, error = Validators.validate_required_fields(data, ['username', 'password', 'bank_key'])
        if not is_valid:
            return APIResponse.validation_error(error)

        # Find manager by username or email
        manager = Manager.find_by_email(data['username'])

        if not manager or not SecurityUtils.verify_password(data['password'], manager.password_hash):
            AuditLogger.log_security_event('failed_login_attempt', {
                'username': data['username'],
                'user_type': 'manager'
            })
            return APIResponse.unauthorized("Invalid credentials")

        if manager.bank_key != data['bank_key']:
            AuditLogger.log_security_event('invalid_bank_key', {
                'username': data['username'],
                'user_type': 'manager'
            })
            return APIResponse.unauthorized("Invalid bank key")

        if not manager.is_active:
            return APIResponse.forbidden("Account is deactivated")

        # Create tokens
        access_token = create_access_token(
            identity=str(manager.id),
            additional_claims={'user_type': 'manager'}
        )
        refresh_token = create_refresh_token(
            identity=str(manager.id),
            additional_claims={'user_type': 'manager'}
        )

        # Log successful login
        AuditLogger.log_user_action(
            str(manager.id), 'manager', 'login',
            {'ip_address': request.remote_addr}
        )

        return APIResponse.success(
            data={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': manager.to_dict()
            },
            message="Login successful"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        user_type = get_jwt().get('user_type')

        # Verify user still exists and is active
        if user_type == 'customer':
            user = Customer.find_by_id(current_user_id)
        elif user_type == 'manager':
            user = Manager.find_by_id(current_user_id)
        else:
            return APIResponse.unauthorized("Invalid user type")

        if not user or not user.is_active:
            return APIResponse.unauthorized("User not found or inactive")

        # Create new access token
        new_access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'user_type': user_type}
        )

        return APIResponse.success(
            data={'access_token': new_access_token},
            message="Token refreshed successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user"""
    try:
        current_user_id = get_jwt_identity()
        user_type = get_jwt().get('user_type')

        # Log logout
        AuditLogger.log_user_action(
            current_user_id, user_type, 'logout',
            {'ip_address': request.remote_addr}
        )

        return APIResponse.success(message="Logout successful")

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@auth_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if token is valid"""
    try:
        current_user_id = get_jwt_identity()
        user_type = get_jwt().get('user_type')

        # Get user details
        if user_type == 'customer':
            user = Customer.find_by_id(current_user_id)
        elif user_type == 'manager':
            user = Manager.find_by_id(current_user_id)
        else:
            return APIResponse.unauthorized("Invalid user type")

        if not user or not user.is_active:
            return APIResponse.unauthorized("User not found or inactive")

        return APIResponse.success(
            data={'user': user.to_dict()},
            message="Token is valid"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)