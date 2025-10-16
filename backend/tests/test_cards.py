import pytest
import json
from app import create_app
from app.models.customer import Customer
from app.models.credit_card import CreditCard
from app.models.card_application import CardApplication


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


@pytest.fixture
def authenticated_customer(client, customer_data):
    """Create and authenticate a customer"""
    # Register customer
    client.post('/api/auth/register/customer',
                data=json.dumps(customer_data),
                content_type='application/json')

    # Login customer
    login_data = {
        'username': customer_data['username'],
        'password': customer_data['password']
    }

    response = client.post('/api/auth/login/customer',
                           data=json.dumps(login_data),
                           content_type='application/json')

    login_response = json.loads(response.data)
    access_token = login_response['data']['access_token']

    return {
        'customer_data': customer_data,
        'access_token': access_token,
        'headers': {'Authorization': f'Bearer {access_token}'}
    }


@pytest.fixture
def authenticated_manager(client, manager_data):
    """Create and authenticate a manager"""
    # Register manager
    client.post('/api/auth/register/manager',
                data=json.dumps(manager_data),
                content_type='application/json')

    # Login manager
    login_data = {
        'username': manager_data['email'],
        'password': manager_data['password'],
        'bank_key': manager_data['bank_key']
    }

    response = client.post('/api/auth/login/manager',
                           data=json.dumps(login_data),
                           content_type='application/json')

    login_response = json.loads(response.data)
    access_token = login_response['data']['access_token']

    return {
        'manager_data': manager_data,
        'access_token': access_token,
        'headers': {'Authorization': f'Bearer {access_token}'}
    }


class TestAvailableCards:
    """Test available credit cards functionality"""

    def test_get_available_cards(self, client, authenticated_customer):
        """Test getting available credit cards"""
        response = client.get('/api/cards/available',
                              headers=authenticated_customer['headers'])

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert len(data['data']) == 3  # 3 banks
        assert all('bank_name' in bank for bank in data['data'])
        assert all('cards' in bank for bank in data['data'])


class TestCardApplication:
    """Test card application functionality"""

    def test_successful_card_application(self, client, authenticated_customer):
        """Test successful card application"""
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 100000
        }

        response = client.post('/api/cards/apply',
                               data=json.dumps(application_data),
                               content_type='application/json',
                               headers=authenticated_customer['headers'])

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'application_id' in data['data']

    def test_card_application_missing_fields(self, client, authenticated_customer):
        """Test card application with missing fields"""
        incomplete_data = {
            'card_name': 'HDFC Millennia Credit Card'
        }

        response = client.post('/api/cards/apply',
                               data=json.dumps(incomplete_data),
                               content_type='application/json',
                               headers=authenticated_customer['headers'])

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_card_application_invalid_credit_limit(self, client, authenticated_customer):
        """Test card application with invalid credit limit"""
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 5000  # Too low
        }

        response = client.post('/api/cards/apply',
                               data=json.dumps(application_data),
                               content_type='application/json',
                               headers=authenticated_customer['headers'])

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_duplicate_card_application(self, client, authenticated_customer):
        """Test duplicate card application from same bank"""
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 100000
        }

        # First application
        client.post('/api/cards/apply',
                    data=json.dumps(application_data),
                    content_type='application/json',
                    headers=authenticated_customer['headers'])

        # Second application from same bank
        application_data['card_name'] = 'HDFC Regalia Credit Card'
        response = client.post('/api/cards/apply',
                               data=json.dumps(application_data),
                               content_type='application/json',
                               headers=authenticated_customer['headers'])

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] is False


class TestMyCards:
    """Test my cards functionality"""

    def test_get_my_cards_empty(self, client, authenticated_customer):
        """Test getting cards when customer has no cards"""
        response = client.get('/api/cards/my-cards',
                              headers=authenticated_customer['headers'])

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data'] == []

    def test_get_my_cards_with_cards(self, client, authenticated_customer, authenticated_manager):
        """Test getting cards when customer has cards"""
        # Create a card application and approve it
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 100000
        }

        # Apply for card
        apply_response = client.post('/api/cards/apply',
                                     data=json.dumps(application_data),
                                     content_type='application/json',
                                     headers=authenticated_customer['headers'])

        apply_data = json.loads(apply_response.data)
        application_id = apply_data['data']['application_id']

        # Manager approves application
        approval_data = {
            'approved_credit_limit': 100000
        }

        client.post(f'/api/manager/applications/{application_id}/approve',
                    data=json.dumps(approval_data),
                    content_type='application/json',
                    headers=authenticated_manager['headers'])

        # Get customer's cards
        response = client.get('/api/cards/my-cards',
                              headers=authenticated_customer['headers'])

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 1
        assert data['data'][0]['bank_name'] == 'HDFC Bank'


class TestCardDetails:
    """Test card details functionality"""

    def test_get_card_details_not_found(self, client, authenticated_customer):
        """Test getting details for non-existent card"""
        fake_card_id = '507f1f77bcf86cd799439011'  # Valid ObjectId format
        response = client.get(f'/api/cards/{fake_card_id}',
                              headers=authenticated_customer['headers'])

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False

    def test_get_card_details_success(self, client, authenticated_customer, authenticated_manager):
        """Test getting card details successfully"""
        # Create a card application and approve it
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 100000
        }

        # Apply for card
        apply_response = client.post('/api/cards/apply',
                                     data=json.dumps(application_data),
                                     content_type='application/json',
                                     headers=authenticated_customer['headers'])

        apply_data = json.loads(apply_response.data)
        application_id = apply_data['data']['application_id']

        # Manager approves application
        approval_data = {
            'approved_credit_limit': 100000
        }

        client.post(f'/api/manager/applications/{application_id}/approve',
                    data=json.dumps(approval_data),
                    content_type='application/json',
                    headers=authenticated_manager['headers'])

        # Get customer's cards to get card ID
        cards_response = client.get('/api/cards/my-cards',
                                    headers=authenticated_customer['headers'])
        cards_data = json.loads(cards_response.data)
        card_id = cards_data['data'][0]['id']

        # Get card details
        response = client.get(f'/api/cards/{card_id}',
                              headers=authenticated_customer['headers'])

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'recent_transactions' in data['data']


class TestCardPIN:
    """Test card PIN functionality"""

    def test_set_card_pin_success(self, client, authenticated_customer, authenticated_manager):
        """Test setting card PIN successfully"""
        # Create a card first
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 100000
        }

        apply_response = client.post('/api/cards/apply',
                                     data=json.dumps(application_data),
                                     content_type='application/json',
                                     headers=authenticated_customer['headers'])

        apply_data = json.loads(apply_response.data)
        application_id = apply_data['data']['application_id']

        approval_data = {'approved_credit_limit': 100000}
        client.post(f'/api/manager/applications/{application_id}/approve',
                    data=json.dumps(approval_data),
                    content_type='application/json',
                    headers=authenticated_manager['headers'])

        # Get card ID
        cards_response = client.get('/api/cards/my-cards',
                                    headers=authenticated_customer['headers'])
        cards_data = json.loads(cards_response.data)
        card_id = cards_data['data'][0]['id']

        # Set PIN
        pin_data = {'pin': '1234'}
        response = client.post(f'/api/cards/{card_id}/pin',
                               data=json.dumps(pin_data),
                               content_type='application/json',
                               headers=authenticated_customer['headers'])

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_set_card_pin_invalid_format(self, client, authenticated_customer, authenticated_manager):
        """Test setting card PIN with invalid format"""
        # Create a card first (similar to above)
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 100000
        }

        apply_response = client.post('/api/cards/apply',
                                     data=json.dumps(application_data),
                                     content_type='application/json',
                                     headers=authenticated_customer['headers'])

        apply_data = json.loads(apply_response.data)
        application_id = apply_data['data']['application_id']

        approval_data = {'approved_credit_limit': 100000}
        client.post(f'/api/manager/applications/{application_id}/approve',
                    data=json.dumps(approval_data),
                    content_type='application/json',
                    headers=authenticated_manager['headers'])

        # Get card ID
        cards_response = client.get('/api/cards/my-cards',
                                    headers=authenticated_customer['headers'])
        cards_data = json.loads(cards_response.data)
        card_id = cards_data['data'][0]['id']

        # Set invalid PIN
        pin_data = {'pin': '12'}  # Too short
        response = client.post(f'/api/cards/{card_id}/pin',
                               data=json.dumps(pin_data),
                               content_type='application/json',
                               headers=authenticated_customer['headers'])

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestBillPayment:
    """Test bill payment functionality"""

    def test_pay_bill_success(self, client, authenticated_customer, authenticated_manager):
        """Test successful bill payment"""
        # Create a card with some balance first
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 100000
        }

        apply_response = client.post('/api/cards/apply',
                                     data=json.dumps(application_data),
                                     content_type='application/json',
                                     headers=authenticated_customer['headers'])

        apply_data = json.loads(apply_response.data)
        application_id = apply_data['data']['application_id']

        approval_data = {'approved_credit_limit': 100000}
        client.post(f'/api/manager/applications/{application_id}/approve',
                    data=json.dumps(approval_data),
                    content_type='application/json',
                    headers=authenticated_manager['headers'])

        # Get card ID
        cards_response = client.get('/api/cards/my-cards',
                                    headers=authenticated_customer['headers'])
        cards_data = json.loads(cards_response.data)
        card_id = cards_data['data'][0]['id']

        # Pay bill
        payment_data = {'amount': 5000}
        response = client.post(f'/api/cards/{card_id}/pay-bill',
                               data=json.dumps(payment_data),
                               content_type='application/json',
                               headers=authenticated_customer['headers'])

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'new_balance' in data['data']
        assert 'available_credit' in data['data']

    def test_pay_bill_exceed_balance(self, client, authenticated_customer, authenticated_manager):
        """Test bill payment exceeding current balance"""
        # Create a card first
        application_data = {
            'card_name': 'HDFC Millennia Credit Card',
            'bank_name': 'HDFC Bank',
            'requested_credit_limit': 100000
        }

        apply_response = client.post('/api/cards/apply',
                                     data=json.dumps(application_data),
                                     content_type='application/json',
                                     headers=authenticated_customer['headers'])

        apply_data = json.loads(apply_response.data)
        application_id = apply_data['data']['application_id']

        approval_data = {'approved_credit_limit': 100000}
        client.post(f'/api/manager/applications/{application_id}/approve',
                    data=json.dumps(approval_data),
                    content_type='application/json',
                    headers=authenticated_manager['headers'])

        # Get card ID
        cards_response = client.get('/api/cards/my-cards',
                                    headers=authenticated_customer['headers'])
        cards_data = json.loads(cards_response.data)
        card_id = cards_data['data'][0]['id']

        # Try to pay more than current balance
        payment_data = {'amount': 50000}  # More than current balance (which is 0)
        response = client.post(f'/api/cards/{card_id}/pay-bill',
                               data=json.dumps(payment_data),
                               content_type='application/json',
                               headers=authenticated_customer['headers'])

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False