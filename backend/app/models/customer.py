from datetime import datetime
from bson import ObjectId
from app import mongo


class Customer:
    def __init__(self, data):
        self.id = data.get('_id')
        self.first_name = data.get('first_name')
        self.last_name = data.get('last_name')
        self.username = data.get('username')
        self.email = data.get('email')
        self.password_hash = data.get('password_hash')
        self.age = data.get('age')
        self.gender = data.get('gender')
        self.nationality = data.get('nationality')
        self.address = data.get('address')
        self.phone_number = data.get('phone_number')
        self.pan = data.get('pan')
        self.aadhaar = data.get('aadhaar')
        self.salary_slips = data.get('salary_slips', [])
        self.employment_type = data.get('employment_type')  # salaried, unemployed, self_employed
        self.company = data.get('company')
        self.years_of_experience = data.get('years_of_experience')
        self.annual_income = data.get('annual_income')
        self.bank_account_details = data.get('bank_account_details')
        self.existing_loan_amount = data.get('existing_loan_amount', 0)
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())
        self.is_active = data.get('is_active', True)
        self.cibil_score = data.get('cibil_score', 0)

    @classmethod
    def create(cls, customer_data):
        """Create a new customer"""
        customer_data['created_at'] = datetime.utcnow()
        customer_data['updated_at'] = datetime.utcnow()
        customer_data['is_active'] = True
        customer_data['cibil_score'] = 0

        result = mongo.db.customers.insert_one(customer_data)
        customer_data['_id'] = result.inserted_id
        return cls(customer_data)

    @classmethod
    def find_by_id(cls, customer_id):
        """Find customer by ID"""
        customer = mongo.db.customers.find_one({'_id': ObjectId(customer_id)})
        return cls(customer) if customer else None

    @classmethod
    def find_by_email(cls, email):
        """Find customer by email"""
        customer = mongo.db.customers.find_one({'email': email})
        return cls(customer) if customer else None

    @classmethod
    def find_by_username(cls, username):
        """Find customer by username"""
        customer = mongo.db.customers.find_one({'username': username})
        return cls(customer) if customer else None

    @classmethod
    def find_by_pan(cls, pan):
        """Find customer by PAN"""
        customer = mongo.db.customers.find_one({'pan': pan})
        return cls(customer) if customer else None

    @classmethod
    def find_by_aadhaar(cls, aadhaar):
        """Find customer by Aadhaar"""
        customer = mongo.db.customers.find_one({'aadhaar': aadhaar})
        return cls(customer) if customer else None

    def update(self, update_data):
        """Update customer data"""
        update_data['updated_at'] = datetime.utcnow()
        result = mongo.db.customers.update_one(
            {'_id': self.id},
            {'$set': update_data}
        )
        if result.modified_count > 0:
            for key, value in update_data.items():
                setattr(self, key, value)
        return result.modified_count > 0

    def delete(self):
        """Soft delete customer"""
        return self.update({'is_active': False})

    def to_dict(self):
        """Convert customer to dictionary"""
        return {
            'id': str(self.id),
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
            'email': self.email,
            'age': self.age,
            'gender': self.gender,
            'nationality': self.nationality,
            'address': self.address,
            'phone_number': self.phone_number,
            'employment_type': self.employment_type,
            'company': self.company,
            'years_of_experience': self.years_of_experience,
            'annual_income': self.annual_income,
            'existing_loan_amount': self.existing_loan_amount,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'cibil_score': self.cibil_score
        }

    @staticmethod
    def calculate_cibil_score(customer_data):
        """Calculate CIBIL score based on customer data"""
        score = 300  # Base score

        # Income factor
        annual_income = customer_data.get('annual_income', 0)
        if annual_income >= 1000000:
            score += 200
        elif annual_income >= 500000:
            score += 150
        elif annual_income >= 300000:
            score += 100

        # Experience factor
        years_of_experience = customer_data.get('years_of_experience', 0)
        if years_of_experience >= 5:
            score += 100
        elif years_of_experience >= 2:
            score += 50

        # Employment type factor
        employment_type = customer_data.get('employment_type', '')
        if employment_type == 'salaried':
            score += 100
        elif employment_type == 'self_employed':
            score += 50

        # Age factor
        age = customer_data.get('age', 0)
        if 25 <= age <= 35:
            score += 50
        elif 36 <= age <= 45:
            score += 75

        # Existing loan factor (negative)
        existing_loan = customer_data.get('existing_loan_amount', 0)
        if existing_loan > 0:
            score -= min(existing_loan / 10000, 100)  # Max deduction of 100 points

        return min(max(score, 300), 900)  # CIBIL score range: 300-900