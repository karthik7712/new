from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.models.manager import Manager
from app.models.card_application import CardApplication
from app.models.credit_card import CreditCard
from app.utils.security import require_manager_auth
from app.utils.validators import Validators
from app.utils.helpers import APIResponse, ErrorHandler, AuditLogger, NotificationService
from bson import ObjectId

manager_bp = Blueprint('manager', __name__)


@manager_bp.route('/profile', methods=['GET'])
@require_manager_auth
def get_profile(manager):
    """Get manager profile"""
    try:
        return APIResponse.success(
            data=manager.to_dict(),
            message="Profile retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@manager_bp.route('/applications/pending', methods=['GET'])
@require_manager_auth
def get_pending_applications(manager):
    """Get pending card applications"""
    try:
        applications = CardApplication.find_pending_applications()

        # Get detailed application data with customer information
        detailed_applications = []
        for app in applications:
            app_data = app.to_dict()

            # Get customer details
            from app.models.customer import Customer
            customer = Customer.find_by_id(app.customer_id)
            if customer:
                app_data['customer_details'] = {
                    'id': str(customer.id),
                    'name': f"{customer.first_name} {customer.last_name}",
                    'email': customer.email,
                    'annual_income': customer.annual_income,
                    'years_of_experience': customer.years_of_experience,
                    'employment_type': customer.employment_type,
                    'cibil_score': customer.cibil_score
                }

            detailed_applications.append(app_data)

        return APIResponse.success(
            data=detailed_applications,
            message="Pending applications retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@manager_bp.route('/applications/<application_id>/approve', methods=['POST'])
@require_manager_auth
def approve_application(manager, application_id):
    """Approve a card application"""
    try:
        data = request.get_json()

        # Get application
        application = CardApplication.find_by_id(application_id)
        if not application:
            return APIResponse.not_found("Application not found")

        if application.status != CardApplication.STATUS_PENDING:
            return APIResponse.conflict("Application is not pending")

        # Get approved credit limit
        approved_limit = data.get('approved_credit_limit', application.requested_credit_limit)

        # Validate approved limit
        is_valid, error = Validators.validate_credit_limit(approved_limit)
        if not is_valid:
            return APIResponse.validation_error(error)

        # Approve application
        success = application.approve(str(manager.id), approved_limit)

        if success:
            # Create credit card for customer
            from app.models.customer import Customer
            customer = Customer.find_by_id(application.customer_id)

            if customer:
                card_data = {
                    'customer_id': application.customer_id,
                    'card_holder_name': f"{customer.first_name} {customer.last_name}",
                    'bank_name': application.bank_name,
                    'card_type': application.card_type,
                    'credit_limit': approved_limit,
                    'current_balance': 0,
                    'interest_rate': '3.0%',  # Default interest rate
                    'apr': '36%',  # Default APR
                    'rewards_program': '2X rewards on all spends',
                    'fees_and_charges': 'No annual fee for first year',
                    'policies': 'Standard terms and conditions apply'
                }

                # Create the credit card
                credit_card = CreditCard.create(card_data)

                # Create sample transactions for demo
                from app.models.transaction import Transaction
                Transaction.create_sample_transactions(str(credit_card.id), str(customer.id))

                # Send notification to customer
                NotificationService.create_notification(
                    str(customer.id), 'customer', 'application_approved',
                    f"Your {application.card_name} application has been approved! Credit limit: ₹{approved_limit:,.2f}",
                    {'card_id': str(credit_card.id), 'application_id': application_id}
                )

                # Log approval
                AuditLogger.log_user_action(
                    str(manager.id), 'manager', 'application_approved',
                    {
                        'application_id': application_id,
                        'customer_id': str(customer.id),
                        'approved_limit': approved_limit
                    }
                )

                return APIResponse.success(
                    data={
                        'application_id': application_id,
                        'card_id': str(credit_card.id),
                        'approved_limit': approved_limit
                    },
                    message="Application approved successfully"
                )
            else:
                return APIResponse.server_error("Customer not found")
        else:
            return APIResponse.server_error("Failed to approve application")

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@manager_bp.route('/applications/<application_id>/reject', methods=['POST'])
@require_manager_auth
def reject_application(manager, application_id):
    """Reject a card application"""
    try:
        data = request.get_json()

        # Validate rejection reason
        rejection_reason = data.get('rejection_reason', 'Application does not meet our criteria')
        if not rejection_reason or len(rejection_reason.strip()) < 10:
            return APIResponse.validation_error("Rejection reason must be at least 10 characters")

        # Get application
        application = CardApplication.find_by_id(application_id)
        if not application:
            return APIResponse.not_found("Application not found")

        if application.status != CardApplication.STATUS_PENDING:
            return APIResponse.conflict("Application is not pending")

        # Reject application
        success = application.reject(str(manager.id), rejection_reason)

        if success:
            # Send notification to customer
            from app.models.customer import Customer
            customer = Customer.find_by_id(application.customer_id)

            if customer:
                NotificationService.create_notification(
                    str(customer.id), 'customer', 'application_rejected',
                    f"Your {application.card_name} application has been rejected. Reason: {rejection_reason}",
                    {'application_id': application_id, 'rejection_reason': rejection_reason}
                )

            # Log rejection
            AuditLogger.log_user_action(
                str(manager.id), 'manager', 'application_rejected',
                {
                    'application_id': application_id,
                    'customer_id': str(application.customer_id),
                    'rejection_reason': rejection_reason
                }
            )

            return APIResponse.success(
                data={'application_id': application_id},
                message="Application rejected successfully"
            )
        else:
            return APIResponse.server_error("Failed to reject application")

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@manager_bp.route('/applications/<application_id>', methods=['GET'])
@require_manager_auth
def get_application_details(manager, application_id):
    """Get detailed application information"""
    try:
        # Get application with customer details
        applications = CardApplication.get_application_with_customer_details(application_id)

        if not applications:
            return APIResponse.not_found("Application not found")

        application = applications[0]  # Should return one result

        return APIResponse.success(
            data=application,
            message="Application details retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@manager_bp.route('/statistics', methods=['GET'])
@require_manager_auth
def get_statistics(manager):
    """Get manager dashboard statistics"""
    try:
        from app import mongo

        # Get statistics
        total_applications = mongo.db.card_applications.count_documents({})
        pending_applications = mongo.db.card_applications.count_documents({'status': 'pending'})
        approved_applications = mongo.db.card_applications.count_documents({'status': 'approved'})
        rejected_applications = mongo.db.card_applications.count_documents({'status': 'rejected'})

        total_customers = mongo.db.customers.count_documents({'is_active': True})
        total_cards = mongo.db.credit_cards.count_documents({'is_active': True})

        # Get recent applications
        recent_applications = list(mongo.db.card_applications.find().sort('applied_at', -1).limit(5))

        statistics = {
            'total_applications': total_applications,
            'pending_applications': pending_applications,
            'approved_applications': approved_applications,
            'rejected_applications': rejected_applications,
            'total_customers': total_customers,
            'total_cards': total_cards,
            'recent_applications': recent_applications
        }

        return APIResponse.success(
            data=statistics,
            message="Statistics retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@manager_bp.route('/customers', methods=['GET'])
@require_manager_auth
def get_customers(manager):
    """Get all customers (for manager view)"""
    try:
        from app.models.customer import Customer
        from app import mongo

        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        # Get customers with pagination
        query = mongo.db.customers.find({'is_active': True})
        customers = []

        skip = (page - 1) * per_page
        for customer_doc in query.skip(skip).limit(per_page):
            customer = Customer(customer_doc)
            # Sanitize customer data for manager view
            customer_data = customer.to_dict()
            customers.append(customer_data)

        total = mongo.db.customers.count_documents({'is_active': True})

        return APIResponse.success(
            data={
                'customers': customers,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            },
            message="Customers retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)