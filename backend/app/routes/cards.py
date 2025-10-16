from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.credit_card import CreditCard
from app.models.customer import Customer
from app.utils.security import require_customer_auth, require_manager_auth
from app.utils.validators import Validators
from app.utils.helpers import APIResponse, ErrorHandler, AuditLogger
from bson import ObjectId

cards_bp = Blueprint('cards', __name__)


@cards_bp.route('/available', methods=['GET'])
@jwt_required()
def get_available_cards():
    """Get available credit card offers"""
    try:
        available_cards = CreditCard.get_available_cards()

        return APIResponse.success(
            data=available_cards,
            message="Available credit cards retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@cards_bp.route('/apply', methods=['POST'])
@require_customer_auth
def apply_for_card(customer):
    """Apply for a credit card"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['card_name', 'bank_name', 'requested_credit_limit']
        is_valid, error = Validators.validate_required_fields(data, required_fields)
        if not is_valid:
            return APIResponse.validation_error(error)

        # Validate credit limit
        is_valid, error = Validators.validate_credit_limit(data['requested_credit_limit'])
        if not is_valid:
            return APIResponse.validation_error(error)

        # Check if customer already has a card from the same bank
        from app.models.credit_card import CreditCard
        existing_cards = CreditCard.find_by_customer_id(str(customer.id))

        for card in existing_cards:
            if card.bank_name == data['bank_name']:
                return APIResponse.conflict("You already have a card from this bank")

        # Create card application
        from app.models.card_application import CardApplication

        application_data = {
            'customer_id': ObjectId(str(customer.id)),
            'card_name': data['card_name'],
            'bank_name': data['bank_name'],
            'card_type': data.get('card_type', 'Standard'),
            'requested_credit_limit': float(data['requested_credit_limit'])
        }

        application = CardApplication.create(application_data)

        # Log application
        AuditLogger.log_user_action(
            str(customer.id), 'customer', 'card_application',
            {'card_name': data['card_name'], 'bank_name': data['bank_name']}
        )

        return APIResponse.success(
            data={'application_id': str(application.id)},
            message="Card application submitted successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@cards_bp.route('/my-cards', methods=['GET'])
@require_customer_auth
def get_my_cards(customer):
    """Get customer's credit cards"""
    try:
        cards = CreditCard.find_by_customer_id(str(customer.id))
        cards_data = [card.to_dict() for card in cards]

        return APIResponse.success(
            data=cards_data,
            message="Cards retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@cards_bp.route('/<card_id>', methods=['GET'])
@require_customer_auth
def get_card_details(customer, card_id):
    """Get specific card details"""
    try:
        card = CreditCard.find_by_id(card_id)

        if not card:
            return APIResponse.not_found("Card not found")

        if str(card.customer_id) != str(customer.id):
            return APIResponse.forbidden("Access denied")

        # Get recent transactions
        from app.models.transaction import Transaction
        recent_transactions = Transaction.find_by_card_id(card_id, limit=5)

        card_data = card.to_dict(mask_sensitive=False)
        card_data['recent_transactions'] = [txn.to_dict() for txn in recent_transactions]

        return APIResponse.success(
            data=card_data,
            message="Card details retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@cards_bp.route('/<card_id>/pin', methods=['POST'])
@require_customer_auth
def set_card_pin(customer, card_id):
    """Set or update card PIN"""
    try:
        data = request.get_json()

        # Validate PIN
        is_valid, error = Validators.validate_pin(data.get('pin'))
        if not is_valid:
            return APIResponse.validation_error(error)

        card = CreditCard.find_by_id(card_id)

        if not card:
            return APIResponse.not_found("Card not found")

        if str(card.customer_id) != str(customer.id):
            return APIResponse.forbidden("Access denied")

        # Set PIN
        success = card.set_pin(data['pin'])

        if success:
            AuditLogger.log_user_action(
                str(customer.id), 'customer', 'pin_set',
                {'card_id': card_id}
            )

            return APIResponse.success(message="PIN set successfully")
        else:
            return APIResponse.server_error("Failed to set PIN")

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@cards_bp.route('/<card_id>/remove', methods=['DELETE'])
@require_customer_auth
def remove_card(customer, card_id):
    """Remove card from customer's account"""
    try:
        card = CreditCard.find_by_id(card_id)

        if not card:
            return APIResponse.not_found("Card not found")

        if str(card.customer_id) != str(customer.id):
            return APIResponse.forbidden("Access denied")

        # Soft delete card
        success = card.delete()

        if success:
            AuditLogger.log_user_action(
                str(customer.id), 'customer', 'card_removed',
                {'card_id': card_id}
            )

            return APIResponse.success(message="Card removed successfully")
        else:
            return APIResponse.server_error("Failed to remove card")

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@cards_bp.route('/<card_id>/pay-bill', methods=['POST'])
@require_customer_auth
def pay_bill(customer, card_id):
    """Pay credit card bill"""
    try:
        data = request.get_json()

        # Validate payment amount
        is_valid, error = Validators.validate_transaction_amount(data.get('amount'))
        if not is_valid:
            return APIResponse.validation_error(error)

        card = CreditCard.find_by_id(card_id)

        if not card:
            return APIResponse.not_found("Card not found")

        if str(card.customer_id) != str(customer.id):
            return APIResponse.forbidden("Access denied")

        payment_amount = float(data['amount'])

        # Check if payment amount is valid
        if payment_amount > card.current_balance:
            return APIResponse.validation_error("Payment amount cannot exceed current balance")

        # Update card balance
        success = card.update_balance(payment_amount, 'credit')

        if success:
            # Create payment transaction
            from app.models.transaction import Transaction

            transaction_data = {
                'card_id': ObjectId(card_id),
                'customer_id': ObjectId(str(customer.id)),
                'transaction_type': 'payment',
                'amount': payment_amount,
                'merchant_name': 'Credit Card Payment',
                'merchant_category': 'Payment',
                'description': 'Bill payment',
                'status': 'completed'
            }

            Transaction.create(transaction_data)

            AuditLogger.log_user_action(
                str(customer.id), 'customer', 'bill_payment',
                {'card_id': card_id, 'amount': payment_amount}
            )

            return APIResponse.success(
                data={
                    'new_balance': card.current_balance,
                    'available_credit': card.available_credit
                },
                message="Bill payment successful"
            )
        else:
            return APIResponse.server_error("Failed to process payment")

    except Exception as e:
        return ErrorHandler.handle_general_error(e)