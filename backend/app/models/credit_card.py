from datetime import datetime, timedelta
from bson import ObjectId
from app import mongo


class CreditCard:
    def __init__(self, data):
        self.id = data.get('_id')
        self.card_number = data.get('card_number')
        self.card_holder_name = data.get('card_holder_name')
        self.expiry_date = data.get('expiry_date')
        self.cvv = data.get('cvv')
        self.pin = data.get('pin')
        self.customer_id = data.get('customer_id')
        self.bank_name = data.get('bank_name')
        self.card_type = data.get('card_type')
        self.credit_limit = data.get('credit_limit')
        self.current_balance = data.get('current_balance', 0)
        self.available_credit = data.get('available_credit')
        self.interest_rate = data.get('interest_rate')
        self.apr = data.get('apr')
        self.rewards_program = data.get('rewards_program')
        self.fees_and_charges = data.get('fees_and_charges')
        self.policies = data.get('policies')
        self.is_active = data.get('is_active', True)
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())

    @classmethod
    def create(cls, card_data):
        """Create a new credit card"""
        # Generate card number (simplified for demo)
        card_data['card_number'] = cls._generate_card_number()
        card_data['expiry_date'] = (datetime.utcnow() + timedelta(days=365 * 5)).strftime('%m/%y')
        card_data['cvv'] = cls._generate_cvv()
        card_data['available_credit'] = card_data.get('credit_limit', 0) - card_data.get('current_balance', 0)
        card_data['created_at'] = datetime.utcnow()
        card_data['updated_at'] = datetime.utcnow()
        card_data['is_active'] = True

        result = mongo.db.credit_cards.insert_one(card_data)
        card_data['_id'] = result.inserted_id
        return cls(card_data)

    @classmethod
    def find_by_id(cls, card_id):
        """Find credit card by ID"""
        card = mongo.db.credit_cards.find_one({'_id': ObjectId(card_id)})
        return cls(card) if card else None

    @classmethod
    def find_by_customer_id(cls, customer_id):
        """Find all credit cards for a customer"""
        cards = mongo.db.credit_cards.find({'customer_id': ObjectId(customer_id), 'is_active': True})
        return [cls(card) for card in cards]

    @classmethod
    def find_by_card_number(cls, card_number):
        """Find credit card by card number"""
        card = mongo.db.credit_cards.find_one({'card_number': card_number})
        return cls(card) if card else None

    @classmethod
    def get_available_cards(cls):
        """Get all available credit card offers"""
        return [
            {
                'bank_name': 'HDFC Bank',
                'cards': [
                    {
                        'name': 'HDFC Millennia Credit Card',
                        'type': 'Rewards',
                        'credit_limit': 100000,
                        'interest_rate': '2.5%',
                        'apr': '30%',
                        'rewards_program': '5X rewards on online spends',
                        'fees': '₹1000 annual fee, waived off on spends above ₹1 lakh',
                        'policies': 'Zero liability protection, 24/7 customer support'
                    },
                    {
                        'name': 'HDFC Regalia Credit Card',
                        'type': 'Premium',
                        'credit_limit': 200000,
                        'interest_rate': '2.5%',
                        'apr': '28%',
                        'rewards_program': '4X rewards on dining, 2X on travel',
                        'fees': '₹2500 annual fee',
                        'policies': 'Airport lounge access, travel insurance'
                    },
                    {
                        'name': 'HDFC Freedom Credit Card',
                        'type': 'Cashback',
                        'credit_limit': 75000,
                        'interest_rate': '3%',
                        'apr': '32%',
                        'rewards_program': '5% cashback on online shopping',
                        'fees': '₹500 annual fee',
                        'policies': 'Fuel surcharge waiver, EMI options'
                    },
                    {
                        'name': 'HDFC Diners Club Credit Card',
                        'type': 'Travel',
                        'credit_limit': 150000,
                        'interest_rate': '2.5%',
                        'apr': '30%',
                        'rewards_program': '6X rewards on travel bookings',
                        'fees': '₹2000 annual fee',
                        'policies': 'Global acceptance, travel concierge'
                    }
                ]
            },
            {
                'bank_name': 'ICICI Bank',
                'cards': [
                    {
                        'name': 'ICICI Amazon Pay Credit Card',
                        'type': 'Cashback',
                        'credit_limit': 80000,
                        'interest_rate': '3%',
                        'apr': '31%',
                        'rewards_program': '5% cashback on Amazon, 2% on other online',
                        'fees': 'No annual fee',
                        'policies': 'Instant approval, digital payments'
                    },
                    {
                        'name': 'ICICI Platinum Credit Card',
                        'type': 'Standard',
                        'credit_limit': 120000,
                        'interest_rate': '2.5%',
                        'apr': '29%',
                        'rewards_program': '2X rewards on all spends',
                        'fees': '₹750 annual fee',
                        'policies': 'Balance transfer facility, EMI options'
                    },
                    {
                        'name': 'ICICI Coral Credit Card',
                        'type': 'Lifestyle',
                        'credit_limit': 100000,
                        'interest_rate': '2.5%',
                        'apr': '30%',
                        'rewards_program': '3X rewards on dining and entertainment',
                        'fees': '₹1000 annual fee',
                        'policies': 'Movie ticket discounts, dining offers'
                    },
                    {
                        'name': 'ICICI Bank Instant Platinum Credit Card',
                        'type': 'Premium',
                        'credit_limit': 250000,
                        'interest_rate': '2.5%',
                        'apr': '28%',
                        'rewards_program': '4X rewards on international spends',
                        'fees': '₹3000 annual fee',
                        'policies': 'Airport lounge access, concierge services'
                    }
                ]
            },
            {
                'bank_name': 'SBI Card',
                'cards': [
                    {
                        'name': 'SBI SimplyCLICK Credit Card',
                        'type': 'Online Shopping',
                        'credit_limit': 60000,
                        'interest_rate': '3.5%',
                        'apr': '33%',
                        'rewards_program': '5X rewards on online shopping',
                        'fees': '₹499 annual fee',
                        'policies': 'Fuel surcharge waiver, EMI options'
                    },
                    {
                        'name': 'SBI Card PRIME Credit Card',
                        'type': 'Premium',
                        'credit_limit': 180000,
                        'interest_rate': '2.5%',
                        'apr': '29%',
                        'rewards_program': '3X rewards on dining and movies',
                        'fees': '₹2999 annual fee',
                        'policies': 'Airport lounge access, travel benefits'
                    },
                    {
                        'name': 'SBI Card ELITE Credit Card',
                        'type': 'Super Premium',
                        'credit_limit': 300000,
                        'interest_rate': '2.5%',
                        'apr': '27%',
                        'rewards_program': '5X rewards on travel and dining',
                        'fees': '₹4999 annual fee',
                        'policies': 'Unlimited airport lounge access, concierge'
                    },
                    {
                        'name': 'SBI Card Unnati Credit Card',
                        'type': 'Entry Level',
                        'credit_limit': 40000,
                        'interest_rate': '3.5%',
                        'apr': '35%',
                        'rewards_program': '2X rewards on all spends',
                        'fees': 'No annual fee for first year',
                        'policies': 'Easy approval, basic benefits'
                    }
                ]
            }
        ]

    def update(self, update_data):
        """Update credit card data"""
        update_data['updated_at'] = datetime.utcnow()
        result = mongo.db.credit_cards.update_one(
            {'_id': self.id},
            {'$set': update_data}
        )
        if result.modified_count > 0:
            for key, value in update_data.items():
                setattr(self, key, value)
        return result.modified_count > 0

    def update_balance(self, amount, transaction_type='debit'):
        """Update card balance"""
        if transaction_type == 'debit':
            self.current_balance += amount
        else:  # credit/payment
            self.current_balance = max(0, self.current_balance - amount)

        self.available_credit = self.credit_limit - self.current_balance
        return self.update({
            'current_balance': self.current_balance,
            'available_credit': self.available_credit
        })

    def set_pin(self, pin):
        """Set card PIN"""
        return self.update({'pin': pin})

    def delete(self):
        """Soft delete credit card"""
        return self.update({'is_active': False})

    def to_dict(self, mask_sensitive=True):
        """Convert credit card to dictionary"""
        data = {
            'id': str(self.id),
            'card_holder_name': self.card_holder_name,
            'expiry_date': self.expiry_date,
            'bank_name': self.bank_name,
            'card_type': self.card_type,
            'credit_limit': self.credit_limit,
            'current_balance': self.current_balance,
            'available_credit': self.available_credit,
            'interest_rate': self.interest_rate,
            'apr': self.apr,
            'rewards_program': self.rewards_program,
            'fees_and_charges': self.fees_and_charges,
            'policies': self.policies,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if mask_sensitive:
            data['card_number'] = self._mask_card_number()
            data['cvv'] = '***'
            data['pin'] = '****' if self.pin else None
        else:
            data['card_number'] = self.card_number
            data['cvv'] = self.cvv
            data['pin'] = self.pin

        return data

    def _mask_card_number(self):
        """Mask card number for display"""
        if not self.card_number:
            return None
        return f"{self.card_number[:4]} **** **** {self.card_number[-4:]}"

    @staticmethod
    def _generate_card_number():
        """Generate a random card number (simplified for demo)"""
        import random
        # Generate a 16-digit card number
        return ''.join([str(random.randint(0, 9)) for _ in range(16)])

    @staticmethod
    def _generate_cvv():
        """Generate a random CVV (simplified for demo)"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(3)])