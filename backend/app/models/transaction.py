from datetime import datetime
from bson import ObjectId
from app import mongo


class Transaction:
    TRANSACTION_TYPES = {
        'purchase': 'purchase',
        'payment': 'payment',
        'refund': 'refund',
        'cash_advance': 'cash_advance',
        'fee': 'fee',
        'interest': 'interest'
    }

    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'

    def __init__(self, data):
        self.id = data.get('_id')
        self.card_id = data.get('card_id')
        self.customer_id = data.get('customer_id')
        self.transaction_type = data.get('transaction_type')
        self.amount = data.get('amount')
        self.currency = data.get('currency', 'INR')
        self.merchant_name = data.get('merchant_name')
        self.merchant_category = data.get('merchant_category')
        self.description = data.get('description')
        self.status = data.get('status', self.STATUS_PENDING)
        self.transaction_date = data.get('transaction_date', datetime.utcnow())
        self.settlement_date = data.get('settlement_date')
        self.reference_number = data.get('reference_number')
        self.location = data.get('location')
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())

    @classmethod
    def create(cls, transaction_data):
        """Create a new transaction"""
        transaction_data['created_at'] = datetime.utcnow()
        transaction_data['updated_at'] = datetime.utcnow()
        transaction_data['status'] = cls.STATUS_PENDING
        transaction_data['reference_number'] = cls._generate_reference_number()

        result = mongo.db.transactions.insert_one(transaction_data)
        transaction_data['_id'] = result.inserted_id
        return cls(transaction_data)

    @classmethod
    def find_by_id(cls, transaction_id):
        """Find transaction by ID"""
        transaction = mongo.db.transactions.find_one({'_id': ObjectId(transaction_id)})
        return cls(transaction) if transaction else None

    @classmethod
    def find_by_card_id(cls, card_id, limit=10, skip=0):
        """Find transactions for a specific card"""
        transactions = mongo.db.transactions.find(
            {'card_id': ObjectId(card_id)}
        ).sort('transaction_date', -1).skip(skip).limit(limit)
        return [cls(txn) for txn in transactions]

    @classmethod
    def find_by_customer_id(cls, customer_id, limit=10, skip=0):
        """Find transactions for a specific customer"""
        transactions = mongo.db.transactions.find(
            {'customer_id': ObjectId(customer_id)}
        ).sort('transaction_date', -1).skip(skip).limit(limit)
        return [cls(txn) for txn in transactions]

    @classmethod
    def get_spending_summary(cls, customer_id, start_date=None, end_date=None):
        """Get spending summary for a customer"""
        match_conditions = {'customer_id': ObjectId(customer_id)}

        if start_date and end_date:
            match_conditions['transaction_date'] = {
                '$gte': start_date,
                '$lte': end_date
            }

        pipeline = [
            {'$match': match_conditions},
            {'$group': {
                '_id': '$merchant_category',
                'total_amount': {'$sum': '$amount'},
                'transaction_count': {'$sum': 1},
                'avg_amount': {'$avg': '$amount'}
            }},
            {'$sort': {'total_amount': -1}}
        ]

        return list(mongo.db.transactions.aggregate(pipeline))

    @classmethod
    def get_monthly_spending_trend(cls, customer_id, months=6):
        """Get monthly spending trend for a customer"""
        from datetime import datetime, timedelta

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)

        pipeline = [
            {'$match': {
                'customer_id': ObjectId(customer_id),
                'transaction_date': {'$gte': start_date, '$lte': end_date}
            }},
            {'$group': {
                '_id': {
                    'year': {'$year': '$transaction_date'},
                    'month': {'$month': '$transaction_date'}
                },
                'total_amount': {'$sum': '$amount'},
                'transaction_count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]

        return list(mongo.db.transactions.aggregate(pipeline))

    def update_status(self, status, settlement_date=None):
        """Update transaction status"""
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow()
        }

        if settlement_date:
            update_data['settlement_date'] = settlement_date
        elif status == self.STATUS_COMPLETED:
            update_data['settlement_date'] = datetime.utcnow()

        result = mongo.db.transactions.update_one(
            {'_id': self.id},
            {'$set': update_data}
        )

        if result.modified_count > 0:
            self.status = status
            self.updated_at = update_data['updated_at']
            if settlement_date:
                self.settlement_date = settlement_date

        return result.modified_count > 0

    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            'id': str(self.id),
            'card_id': str(self.card_id) if self.card_id else None,
            'customer_id': str(self.customer_id) if self.customer_id else None,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'currency': self.currency,
            'merchant_name': self.merchant_name,
            'merchant_category': self.merchant_category,
            'description': self.description,
            'status': self.status,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'settlement_date': self.settlement_date.isoformat() if self.settlement_date else None,
            'reference_number': self.reference_number,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def _generate_reference_number():
        """Generate a unique reference number"""
        import random
        import string
        return 'TXN' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    @classmethod
    def create_sample_transactions(cls, card_id, customer_id):
        """Create sample transactions for demo purposes"""
        sample_transactions = [
            {
                'card_id': ObjectId(card_id),
                'customer_id': ObjectId(customer_id),
                'transaction_type': 'purchase',
                'amount': 2500,
                'merchant_name': 'Amazon India',
                'merchant_category': 'Online Shopping',
                'description': 'Electronics purchase',
                'status': 'completed'
            },
            {
                'card_id': ObjectId(card_id),
                'customer_id': ObjectId(customer_id),
                'transaction_type': 'purchase',
                'amount': 800,
                'merchant_name': 'Swiggy',
                'merchant_category': 'Food & Dining',
                'description': 'Food delivery',
                'status': 'completed'
            },
            {
                'card_id': ObjectId(card_id),
                'customer_id': ObjectId(customer_id),
                'transaction_type': 'purchase',
                'amount': 1200,
                'merchant_name': 'Uber',
                'merchant_category': 'Transportation',
                'description': 'Ride payment',
                'status': 'completed'
            },
            {
                'card_id': ObjectId(card_id),
                'customer_id': ObjectId(customer_id),
                'transaction_type': 'purchase',
                'amount': 4500,
                'merchant_name': 'BigBazaar',
                'merchant_category': 'Groceries',
                'description': 'Grocery shopping',
                'status': 'completed'
            },
            {
                'card_id': ObjectId(card_id),
                'customer_id': ObjectId(customer_id),
                'transaction_type': 'payment',
                'amount': 5000,
                'merchant_name': 'Credit Card Payment',
                'merchant_category': 'Payment',
                'description': 'Monthly bill payment',
                'status': 'completed'
            }
        ]

        created_transactions = []
        for txn_data in sample_transactions:
            txn_data['transaction_date'] = datetime.utcnow()
            txn_data['settlement_date'] = datetime.utcnow()
            result = mongo.db.transactions.insert_one(txn_data)
            txn_data['_id'] = result.inserted_id
            created_transactions.append(cls(txn_data))

        return created_transactions