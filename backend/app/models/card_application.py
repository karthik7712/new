from datetime import datetime
from bson import ObjectId
from app import mongo


class CardApplication:
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    def __init__(self, data):
        self.id = data.get('_id')
        self.customer_id = data.get('customer_id')
        self.card_name = data.get('card_name')
        self.bank_name = data.get('bank_name')
        self.card_type = data.get('card_type')
        self.requested_credit_limit = data.get('requested_credit_limit')
        self.status = data.get('status', self.STATUS_PENDING)
        self.approved_credit_limit = data.get('approved_credit_limit')
        self.approved_by = data.get('approved_by')  # Manager ID
        self.rejection_reason = data.get('rejection_reason')
        self.applied_at = data.get('applied_at', datetime.utcnow())
        self.processed_at = data.get('processed_at')
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())

    @classmethod
    def create(cls, application_data):
        """Create a new card application"""
        application_data['applied_at'] = datetime.utcnow()
        application_data['created_at'] = datetime.utcnow()
        application_data['updated_at'] = datetime.utcnow()
        application_data['status'] = cls.STATUS_PENDING

        result = mongo.db.card_applications.insert_one(application_data)
        application_data['_id'] = result.inserted_id
        return cls(application_data)

    @classmethod
    def find_by_id(cls, application_id):
        """Find card application by ID"""
        application = mongo.db.card_applications.find_one({'_id': ObjectId(application_id)})
        return cls(application) if application else None

    @classmethod
    def find_by_customer_id(cls, customer_id):
        """Find all card applications for a customer"""
        applications = mongo.db.card_applications.find({'customer_id': ObjectId(customer_id)})
        return [cls(app) for app in applications]

    @classmethod
    def find_pending_applications(cls):
        """Find all pending card applications"""
        applications = mongo.db.card_applications.find({'status': cls.STATUS_PENDING})
        return [cls(app) for app in applications]

    @classmethod
    def get_application_with_customer_details(cls, application_id):
        """Get application with customer details for manager review"""
        pipeline = [
            {'$match': {'_id': ObjectId(application_id)}},
            {'$lookup': {
                'from': 'customers',
                'localField': 'customer_id',
                'foreignField': '_id',
                'as': 'customer'
            }},
            {'$unwind': '$customer'},
            {'$project': {
                'card_name': 1,
                'bank_name': 1,
                'card_type': 1,
                'requested_credit_limit': 1,
                'status': 1,
                'applied_at': 1,
                'customer.first_name': 1,
                'customer.last_name': 1,
                'customer.email': 1,
                'customer.annual_income': 1,
                'customer.years_of_experience': 1,
                'customer.cibil_score': 1,
                'customer.employment_type': 1
            }}
        ]

        result = mongo.db.card_applications.aggregate(pipeline)
        return list(result)

    def approve(self, manager_id, approved_credit_limit=None):
        """Approve the card application"""
        approved_limit = approved_credit_limit or self.requested_credit_limit

        update_data = {
            'status': self.STATUS_APPROVED,
            'approved_by': ObjectId(manager_id),
            'approved_credit_limit': approved_limit,
            'processed_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = mongo.db.card_applications.update_one(
            {'_id': self.id},
            {'$set': update_data}
        )

        if result.modified_count > 0:
            for key, value in update_data.items():
                setattr(self, key, value)

        return result.modified_count > 0

    def reject(self, manager_id, rejection_reason):
        """Reject the card application"""
        update_data = {
            'status': self.STATUS_REJECTED,
            'approved_by': ObjectId(manager_id),
            'rejection_reason': rejection_reason,
            'processed_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = mongo.db.card_applications.update_one(
            {'_id': self.id},
            {'$set': update_data}
        )

        if result.modified_count > 0:
            for key, value in update_data.items():
                setattr(self, key, value)

        return result.modified_count > 0

    def to_dict(self):
        """Convert card application to dictionary"""
        return {
            'id': str(self.id),
            'customer_id': str(self.customer_id) if self.customer_id else None,
            'card_name': self.card_name,
            'bank_name': self.bank_name,
            'card_type': self.card_type,
            'requested_credit_limit': self.requested_credit_limit,
            'status': self.status,
            'approved_credit_limit': self.approved_credit_limit,
            'approved_by': str(self.approved_by) if self.approved_by else None,
            'rejection_reason': self.rejection_reason,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }