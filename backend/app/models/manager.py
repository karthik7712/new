from datetime import datetime
from bson import ObjectId
from app import mongo


class Manager:
    def __init__(self, data):
        self.id = data.get('_id')
        self.first_name = data.get('first_name')
        self.last_name = data.get('last_name')
        self.email = data.get('email')
        self.password_hash = data.get('password_hash')
        self.bank_key = data.get('bank_key')
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())
        self.is_active = data.get('is_active', True)

    @classmethod
    def create(cls, manager_data):
        """Create a new manager"""
        manager_data['created_at'] = datetime.utcnow()
        manager_data['updated_at'] = datetime.utcnow()
        manager_data['is_active'] = True

        result = mongo.db.managers.insert_one(manager_data)
        manager_data['_id'] = result.inserted_id
        return cls(manager_data)

    @classmethod
    def find_by_id(cls, manager_id):
        """Find manager by ID"""
        manager = mongo.db.managers.find_one({'_id': ObjectId(manager_id)})
        return cls(manager) if manager else None

    @classmethod
    def find_by_email(cls, email):
        """Find manager by email"""
        manager = mongo.db.managers.find_one({'email': email})
        return cls(manager) if manager else None

    @classmethod
    def find_by_bank_key(cls, bank_key):
        """Find manager by bank key"""
        manager = mongo.db.managers.find_one({'bank_key': bank_key})
        return cls(manager) if manager else None

    def update(self, update_data):
        """Update manager data"""
        update_data['updated_at'] = datetime.utcnow()
        result = mongo.db.managers.update_one(
            {'_id': self.id},
            {'$set': update_data}
        )
        if result.modified_count > 0:
            for key, value in update_data.items():
                setattr(self, key, value)
        return result.modified_count > 0

    def delete(self):
        """Soft delete manager"""
        return self.update({'is_active': False})

    def to_dict(self):
        """Convert manager to dictionary"""
        return {
            'id': str(self.id),
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }