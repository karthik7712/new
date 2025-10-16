import re
import phonenumbers
from email_validator import validate_email, EmailNotValidError


class Validators:
    """Validation utilities for the credit card management system"""

    # Regex patterns
    PAN_PATTERN = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    AADHAAR_PATTERN = r'^[2-9]{1}[0-9]{3}[0-9]{4}[0-9]{4}$'
    STRONG_PASSWORD_PATTERN = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    USERNAME_PATTERN = r'^[a-zA-Z0-9_]{3,20}$'

    @staticmethod
    def validate_email(email):
        """Validate email format"""
        try:
            validate_email(email)
            return True, None
        except EmailNotValidError as e:
            return False, str(e)

    @staticmethod
    def validate_phone_number(phone_number, country_code='IN'):
        """Validate phone number format"""
        try:
            parsed_number = phonenumbers.parse(phone_number, country_code)
            return phonenumbers.is_valid_number(parsed_number), None
        except phonenumbers.NumberParseException as e:
            return False, str(e)

    @staticmethod
    def validate_pan(pan):
        """Validate PAN format"""
        if not pan or not isinstance(pan, str):
            return False, "PAN is required"

        pan = pan.upper().strip()
        if not re.match(Validators.PAN_PATTERN, pan):
            return False, "Invalid PAN format. Expected format: ABCDE1234F"

        return True, None

    @staticmethod
    def validate_aadhaar(aadhaar):
        """Validate Aadhaar format"""
        if not aadhaar or not isinstance(aadhaar, str):
            return False, "Aadhaar is required"

        aadhaar = aadhaar.strip()
        if not re.match(Validators.AADHAAR_PATTERN, aadhaar):
            return False, "Invalid Aadhaar format. Expected 12 digits starting with 2-9"

        return True, None

    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password or not isinstance(password, str):
            return False, "Password is required"

        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.match(Validators.STRONG_PASSWORD_PATTERN, password):
            return False, "Password must contain at least one lowercase letter, one uppercase letter, one digit, and one special character"

        return True, None

    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not username or not isinstance(username, str):
            return False, "Username is required"

        if not re.match(Validators.USERNAME_PATTERN, username):
            return False, "Username must be 3-20 characters long and contain only letters, numbers, and underscores"

        return True, None

    @staticmethod
    def validate_required_fields(data, required_fields):
        """Validate required fields"""
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)

        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        return True, None

    @staticmethod
    def validate_numeric_range(value, min_val=None, max_val=None, field_name="Value"):
        """Validate numeric range"""
        try:
            num_value = float(value)
            if min_val is not None and num_value < min_val:
                return False, f"{field_name} must be at least {min_val}"
            if max_val is not None and num_value > max_val:
                return False, f"{field_name} must be at most {max_val}"
            return True, None
        except (ValueError, TypeError):
            return False, f"{field_name} must be a valid number"

    @staticmethod
    def validate_age(age):
        """Validate age"""
        return Validators.validate_numeric_range(
            age, min_val=18, max_val=100, field_name="Age"
        )

    @staticmethod
    def validate_annual_income(income):
        """Validate annual income"""
        return Validators.validate_numeric_range(
            income, min_val=0, field_name="Annual income"
        )

    @staticmethod
    def validate_years_of_experience(yoe):
        """Validate years of experience"""
        return Validators.validate_numeric_range(
            yoe, min_val=0, max_val=50, field_name="Years of experience"
        )

    @staticmethod
    def validate_credit_limit(limit):
        """Validate credit limit"""
        return Validators.validate_numeric_range(
            limit, min_val=10000, max_val=1000000, field_name="Credit limit"
        )

    @staticmethod
    def validate_transaction_amount(amount):
        """Validate transaction amount"""
        return Validators.validate_numeric_range(
            amount, min_val=1, max_val=100000, field_name="Transaction amount"
        )

    @staticmethod
    def validate_pin(pin):
        """Validate 4-digit PIN"""
        if not pin or not isinstance(pin, str):
            return False, "PIN is required"

        if not re.match(r'^\d{4}$', pin):
            return False, "PIN must be exactly 4 digits"

        return True, None

    @staticmethod
    def validate_bank_key(bank_key):
        """Validate bank key format"""
        if not bank_key or not isinstance(bank_key, str):
            return False, "Bank key is required"

        if len(bank_key) < 8:
            return False, "Bank key must be at least 8 characters long"

        return True, None

    @staticmethod
    def sanitize_input(data):
        """Sanitize input data"""
        if isinstance(data, dict):
            return {key: Validators.sanitize_input(value) for key, value in data.items()}
        elif isinstance(data, str):
            return data.strip()
        else:
            return data

    @staticmethod
    def validate_file_upload(file):
        """Validate uploaded file"""
        if not file:
            return False, "No file uploaded"

        # Check file size (16MB max)
        max_size = 16 * 1024 * 1024
        if file.content_length and file.content_length > max_size:
            return False, "File size exceeds 16MB limit"

        # Check file extension
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
        if file.filename:
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            if file_extension not in allowed_extensions:
                return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"

        return True, None