import pytest
import json
from app import create_app
from app.models.customer import Customer
from app.models.manager import Manager
from app.utils.security import SecurityUtils


@pytest.fixture
def app():
    """Create test app"""
    app = create_app('testing')
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def customer_data():
    """Sample customer data for testing"""
    return {
        'first_name': 'John',
        'last_name': 'Doe',
        'username': 'johndoe',
        'email': 'john.doe@example.com',
        'password': 'SecurePass123!',
        'age': 25,
        'gender': 'Male',
        'nationality': 'Indian',
        'address': '123 Main St, Mumbai, India',
        'phone_number': '+919876543210',
        'pan': 'ABCDE1234F',
        'aadhaar': '234567890123',
        'employment_type': 'salaried',
        'company': 'Tech Corp',
        'years_of_experience': 3,
        'annual_income': 600000
    }


@pytest.fixture
def manager_data():
    """Sample manager data for testing"""
    return {
        'first_name': 'Jane',
        'last_name': 'Smith',
        'email': 'jane.smith@bank.com',
        'password': 'ManagerPass123!',
        'bank_key': 'BANKKEY123456'
    }


class TestCustomerRegistration:
    """Test customer registration functionality"""

    def test_successful_customer_registration(self, client, customer_data):
        """Test successful customer registration"""
        response = client.post('/api/auth/register/customer',
                               data=json.dumps(customer_data),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'customer_id' in data['data']
        assert 'cibil_score' in data['data']

    def test_customer_registration_missing_fields(self, client):
        """Test customer registration with missing fields"""
        incomplete_data = {
            'first_name': 'John',
            'email': 'john@example.com'
        }

        response = client.post('/api/auth/register/customer',
                               data=json.dumps(incomplete_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_customer_registration_duplicate_email(self, client, customer_data):
        """Test customer registration with duplicate email"""
        # Register first customer
        client.post('/api/auth/register/customer',
                    data=json.dumps(customer_data),
                    content_type='application/json')

        # Try to register with same email
        customer_data['username'] = 'johndoe2'
        response = client.post('/api/auth/register/customer',
                               data=json.dumps(customer_data),
                               content_type='application/json')

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] is False

    def test_customer_registration_invalid_email(self, client, customer_data):
        """Test customer registration with invalid email"""
        customer_data['email'] = 'invalid-email'

        response = client.post('/api/auth/register/customer',
                               data=json.dumps(customer_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_customer_registration_weak_password(self, client, customer_data):
        """Test customer registration with weak password"""
        customer_data['password'] = 'weak'

        response = client.post('/api/auth/register/customer',
                               data=json.dumps(customer_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestManagerRegistration:
    """Test manager registration functionality"""

    def test_successful_manager_registration(self, client, manager_data):
        """Test successful manager registration"""
        response = client.post('/api/auth/register/manager',
                               data=json.dumps(manager_data),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'manager_id' in data['data']

    def test_manager_registration_duplicate_email(self, client, manager_data):
        """Test manager registration with duplicate email"""
        # Register first manager
        client.post('/api/auth/register/manager',
                    data=json.dumps(manager_data),
                    content_type='application/json')

        # Try to register with same email
        manager_data['bank_key'] = 'DIFFERENT123456'
        response = client.post('/api/auth/register/manager',
                               data=json.dumps(manager_data),
                               content_type='application/json')

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] is False


class TestCustomerLogin:
    """Test customer login functionality"""

    def test_successful_customer_login(self, client, customer_data):
        """Test successful customer login"""
        # Register customer first
        client.post('/api/auth/register/customer',
                    data=json.dumps(customer_data),
                    content_type='application/json')

        # Login
        login_data = {
            'username': customer_data['username'],
            'password': customer_data['password']
        }

        response = client.post('/api/auth/login/customer',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert 'user' in data['data']

    def test_customer_login_invalid_credentials(self, client, customer_data):
        """Test customer login with invalid credentials"""
        # Register customer first
        client.post('/api/auth/register/customer',
                    data=json.dumps(customer_data),
                    content_type='application/json')

        # Login with wrong password
        login_data = {
            'username': customer_data['username'],
            'password': 'wrongpassword'
        }

        response = client.post('/api/auth/login/customer',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False

    def test_customer_login_with_email(self, client, customer_data):
        """Test customer login using email instead of username"""
        # Register customer first
        client.post('/api/auth/register/customer',
                    data=json.dumps(customer_data),
                    content_type='application/json')

        # Login with email
        login_data = {
            'username': customer_data['email'],
            'password': customer_data['password']
        }

        response = client.post('/api/auth/login/customer',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestManagerLogin:
    """Test manager login functionality"""

    def test_successful_manager_login(self, client, manager_data):
        """Test successful manager login"""
        # Register manager first
        client.post('/api/auth/register/manager',
                    data=json.dumps(manager_data),
                    content_type='application/json')

        # Login
        login_data = {
            'username': manager_data['email'],
            'password': manager_data['password'],
            'bank_key': manager_data['bank_key']
        }

        response = client.post('/api/auth/login/manager',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert 'user' in data['data']

    def test_manager_login_invalid_bank_key(self, client, manager_data):
        """Test manager login with invalid bank key"""
        # Register manager first
        client.post('/api/auth/register/manager',
                    data=json.dumps(manager_data),
                    content_type='application/json')

        # Login with wrong bank key
        login_data = {
            'username': manager_data['email'],
            'password': manager_data['password'],
            'bank_key': 'WRONGKEY123456'
        }

        response = client.post('/api/auth/login/manager',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False


class TestTokenVerification:
    """Test token verification functionality"""

    def test_verify_valid_token(self, client, customer_data):
        """Test verification of valid token"""
        # Register and login customer
        client.post('/api/auth/register/customer',
                    data=json.dumps(customer_data),
                    content_type='application/json')

        login_data = {
            'username': customer_data['username'],
            'password': customer_data['password']
        }

        login_response = client.post('/api/auth/login/customer',
                                     data=json.dumps(login_data),
                                     content_type='application/json')

        login_data = json.loads(login_response.data)
        access_token = login_data['data']['access_token']

        # Verify token
        headers = {'Authorization': f'Bearer {access_token}'}
        response = client.get('/api/auth/verify-token', headers=headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'user' in data['data']

    def test_verify_invalid_token(self, client):
        """Test verification of invalid token"""
        headers = {'Authorization': 'Bearer invalid_token'}
        response = client.get('/api/auth/verify-token', headers=headers)

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False