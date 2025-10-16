from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.models.transaction import Transaction
from app.models.credit_card import CreditCard
from app.utils.security import require_customer_auth
from app.utils.helpers import APIResponse, ErrorHandler, AuditLogger
from bson import ObjectId

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/card/<card_id>', methods=['GET'])
@require_customer_auth
def get_card_transactions(customer, card_id):
    """Get transactions for a specific card"""
    try:
        # Verify card ownership
        card = CreditCard.find_by_id(card_id)
        if not card or str(card.customer_id) != str(customer.id):
            return APIResponse.forbidden("Access denied")

        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        # Get transactions
        skip = (page - 1) * per_page
        transactions = Transaction.find_by_card_id(card_id, limit=per_page, skip=skip)

        # Get total count
        from app import mongo
        total = mongo.db.transactions.count_documents({'card_id': ObjectId(card_id)})

        transactions_data = [txn.to_dict() for txn in transactions]

        return APIResponse.success(
            data={
                'transactions': transactions_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            },
            message="Transactions retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@transactions_bp.route('/customer', methods=['GET'])
@require_customer_auth
def get_customer_transactions(customer):
    """Get all transactions for a customer"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        # Get transactions
        skip = (page - 1) * per_page
        transactions = Transaction.find_by_customer_id(str(customer.id), limit=per_page, skip=skip)

        # Get total count
        from app import mongo
        total = mongo.db.transactions.count_documents({'customer_id': ObjectId(str(customer.id))})

        transactions_data = [txn.to_dict() for txn in transactions]

        return APIResponse.success(
            data={
                'transactions': transactions_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            },
            message="Transactions retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@transactions_bp.route('/spending-summary', methods=['GET'])
@require_customer_auth
def get_spending_summary(customer):
    """Get spending summary for customer"""
    try:
        # Get date range parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Convert to datetime if provided
        if start_date:
            from datetime import datetime
            start_date = datetime.fromisoformat(start_date)

        if end_date:
            from datetime import datetime
            end_date = datetime.fromisoformat(end_date)

        # Get spending summary
        spending_summary = Transaction.get_spending_summary(
            str(customer.id), start_date, end_date
        )

        return APIResponse.success(
            data=spending_summary,
            message="Spending summary retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@transactions_bp.route('/monthly-trend', methods=['GET'])
@require_customer_auth
def get_monthly_trend(customer):
    """Get monthly spending trend"""
    try:
        # Get months parameter
        months = int(request.args.get('months', 6))

        # Get monthly trend
        monthly_trend = Transaction.get_monthly_spending_trend(str(customer.id), months)

        return APIResponse.success(
            data=monthly_trend,
            message="Monthly trend retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@transactions_bp.route('/<transaction_id>', methods=['GET'])
@require_customer_auth
def get_transaction_details(customer, transaction_id):
    """Get specific transaction details"""
    try:
        transaction = Transaction.find_by_id(transaction_id)

        if not transaction:
            return APIResponse.not_found("Transaction not found")

        if str(transaction.customer_id) != str(customer.id):
            return APIResponse.forbidden("Access denied")

        return APIResponse.success(
            data=transaction.to_dict(),
            message="Transaction details retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@transactions_bp.route('/create', methods=['POST'])
@require_customer_auth
def create_transaction(customer):
    """Create a new transaction (for testing purposes)"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['card_id', 'amount', 'merchant_name', 'description']
        from app.utils.validators import Validators
        is_valid, error = Validators.validate_required_fields(data, required_fields)
        if not is_valid:
            return APIResponse.validation_error(error)

        # Validate amount
        is_valid, error = Validators.validate_transaction_amount(data['amount'])
        if not is_valid:
            return APIResponse.validation_error(error)

        # Verify card ownership
        card = CreditCard.find_by_id(data['card_id'])
        if not card or str(card.customer_id) != str(customer.id):
            return APIResponse.forbidden("Access denied")

        # Check if transaction would exceed credit limit
        transaction_amount = float(data['amount'])
        if card.current_balance + transaction_amount > card.credit_limit:
            return APIResponse.validation_error("Transaction would exceed credit limit")

        # Create transaction
        transaction_data = {
            'card_id': ObjectId(data['card_id']),
            'customer_id': ObjectId(str(customer.id)),
            'transaction_type': data.get('transaction_type', 'purchase'),
            'amount': transaction_amount,
            'merchant_name': data['merchant_name'],
            'merchant_category': data.get('merchant_category', 'Other'),
            'description': data['description'],
            'location': data.get('location'),
            'status': 'completed'
        }

        transaction = Transaction.create(transaction_data)

        # Update card balance
        card.update_balance(transaction_amount, 'debit')

        # Log transaction creation
        AuditLogger.log_user_action(
            str(customer.id), 'customer', 'transaction_created',
            {
                'transaction_id': str(transaction.id),
                'card_id': data['card_id'],
                'amount': transaction_amount,
                'merchant': data['merchant_name']
            }
        )

        return APIResponse.success(
            data={
                'transaction': transaction.to_dict(),
                'new_balance': card.current_balance,
                'available_credit': card.available_credit
            },
            message="Transaction created successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)