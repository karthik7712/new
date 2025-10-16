from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.models.customer import Customer
from app.utils.security import require_customer_auth
from app.utils.validators import Validators
from app.utils.helpers import APIResponse, ErrorHandler, AuditLogger
import google.generativeai as genai
from app import mongo
import os

customer_bp = Blueprint('customer', __name__)

# Configure Google AI
if os.environ.get('GOOGLE_API_KEY'):
    genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))


@customer_bp.route('/profile', methods=['GET'])
@require_customer_auth
def get_profile(customer):
    """Get customer profile"""
    try:
        return APIResponse.success(
            data=customer.to_dict(),
            message="Profile retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@customer_bp.route('/profile', methods=['PUT'])
@require_customer_auth
def update_profile(customer):
    """Update customer profile"""
    try:
        data = request.get_json()

        # Define editable fields
        editable_fields = [
            'first_name', 'last_name', 'phone_number',
            'annual_income', 'years_of_experience'
        ]

        # Validate fields if provided
        update_data = {}

        if 'first_name' in data:
            if not data['first_name'] or len(data['first_name'].strip()) < 2:
                return APIResponse.validation_error("First name must be at least 2 characters")
            update_data['first_name'] = data['first_name'].strip()

        if 'last_name' in data:
            if not data['last_name'] or len(data['last_name'].strip()) < 2:
                return APIResponse.validation_error("Last name must be at least 2 characters")
            update_data['last_name'] = data['last_name'].strip()

        if 'phone_number' in data:
            is_valid, error = Validators.validate_phone_number(data['phone_number'])
            if not is_valid:
                return APIResponse.validation_error(error)
            update_data['phone_number'] = data['phone_number']

        if 'annual_income' in data:
            is_valid, error = Validators.validate_annual_income(data['annual_income'])
            if not is_valid:
                return APIResponse.validation_error(error)
            update_data['annual_income'] = float(data['annual_income'])

        if 'years_of_experience' in data:
            is_valid, error = Validators.validate_years_of_experience(data['years_of_experience'])
            if not is_valid:
                return APIResponse.validation_error(error)
            update_data['years_of_experience'] = int(data['years_of_experience'])

        if not update_data:
            return APIResponse.validation_error("No valid fields to update")

        # Update customer
        success = customer.update(update_data)

        if success:
            # Recalculate CIBIL score
            customer_data = customer.to_dict()
            customer_data.update(update_data)
            new_cibil_score = Customer.calculate_cibil_score(customer_data)
            customer.update({'cibil_score': new_cibil_score})

            AuditLogger.log_user_action(
                str(customer.id), 'customer', 'profile_update',
                {'updated_fields': list(update_data.keys())}
            )

            return APIResponse.success(
                data=customer.to_dict(),
                message="Profile updated successfully"
            )
        else:
            return APIResponse.server_error("Failed to update profile")

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@customer_bp.route('/cibil-score', methods=['GET'])
@require_customer_auth
def get_cibil_score(customer):
    """Get customer's CIBIL score"""
    try:
        # Recalculate CIBIL score
        customer_data = customer.to_dict()
        current_score = Customer.calculate_cibil_score(customer_data)

        # Update score in database
        customer.update({'cibil_score': current_score})

        return APIResponse.success(
            data={'cibil_score': current_score},
            message="CIBIL score retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@customer_bp.route('/insights/<card_id>', methods=['GET'])
@require_customer_auth
def get_spending_insights(customer, card_id):
    """Get AI-powered spending insights for a card"""
    try:
        from app.models.credit_card import CreditCard
        from app.models.transaction import Transaction

        # Verify card ownership
        card = CreditCard.find_by_id(card_id)
        if not card or str(card.customer_id) != str(customer.id):
            return APIResponse.forbidden("Access denied")

        # Get spending summary
        spending_summary = Transaction.get_spending_summary(str(customer.id))

        # Get monthly trend
        monthly_trend = Transaction.get_monthly_spending_trend(str(customer.id))

        # Prepare data for AI analysis
        analysis_data = {
            'customer_profile': {
                'age': customer.age,
                'annual_income': customer.annual_income,
                'employment_type': customer.employment_type,
                'years_of_experience': customer.years_of_experience
            },
            'card_details': {
                'credit_limit': card.credit_limit,
                'current_balance': card.current_balance,
                'available_credit': card.available_credit
            },
            'spending_patterns': spending_summary,
            'monthly_trend': monthly_trend
        }

        # Generate AI insights using Gemini
        insights = generate_ai_insights(analysis_data)

        return APIResponse.success(
            data={
                'insights': insights,
                'spending_summary': spending_summary,
                'monthly_trend': monthly_trend
            },
            message="Insights generated successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@customer_bp.route('/applications', methods=['GET'])
@require_customer_auth
def get_applications(customer):
    """Get customer's card applications"""
    try:
        from app.models.card_application import CardApplication

        applications = CardApplication.find_by_customer_id(str(customer.id))
        applications_data = [app.to_dict() for app in applications]

        return APIResponse.success(
            data=applications_data,
            message="Applications retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@customer_bp.route('/notifications', methods=['GET'])
@require_customer_auth
def get_notifications(customer):
    """Get customer notifications"""
    try:
        from app.utils.helpers import NotificationService

        notifications = NotificationService.get_user_notifications(
            str(customer.id), 'customer', limit=20
        )

        return APIResponse.success(
            data=notifications,
            message="Notifications retrieved successfully"
        )

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


@customer_bp.route('/notifications/<notification_id>/read', methods=['PUT'])
@require_customer_auth
def mark_notification_read(customer, notification_id):
    """Mark notification as read"""
    try:
        from app.utils.helpers import NotificationService

        success = NotificationService.mark_notification_read(notification_id)

        if success:
            return APIResponse.success(message="Notification marked as read")
        else:
            return APIResponse.server_error("Failed to mark notification as read")

    except Exception as e:
        return ErrorHandler.handle_general_error(e)


def generate_ai_insights(data):
    """Generate AI insights using Gemini"""
    try:
        if not os.environ.get('GOOGLE_API_KEY'):
            return get_default_insights(data)

        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = f"""
        Analyze the following credit card usage data and provide personalized financial insights:

        Customer Profile:
        - Age: {data['customer_profile']['age']}
        - Annual Income: ₹{data['customer_profile']['annual_income']:,.2f}
        - Employment: {data['customer_profile']['employment_type']}
        - Experience: {data['customer_profile']['years_of_experience']} years

        Card Details:
        - Credit Limit: ₹{data['card_details']['credit_limit']:,.2f}
        - Current Balance: ₹{data['card_details']['current_balance']:,.2f}
        - Available Credit: ₹{data['card_details']['available_credit']:,.2f}

        Spending Patterns: {data['spending_patterns']}
        Monthly Trend: {data['monthly_trend']}

        Please provide:
        1. Spending analysis and recommendations
        2. Credit utilization advice
        3. Budget suggestions
        4. Financial health tips
        5. Risk assessment

        Keep the response concise, actionable, and personalized.
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"AI insight generation failed: {str(e)}")
        return get_default_insights(data)


def get_default_insights(data):
    """Provide default insights when AI is not available"""
    credit_utilization = (data['card_details']['current_balance'] / data['card_details']['credit_limit']) * 100

    insights = []

    if credit_utilization > 80:
        insights.append(
            "⚠️ High credit utilization detected. Consider paying down your balance to improve your credit score.")
    elif credit_utilization > 50:
        insights.append(
            "💡 Moderate credit utilization. You're doing well, but consider reducing your balance for optimal credit health.")
    else:
        insights.append("✅ Excellent credit utilization! Keep up the good work.")

    if data['card_details']['available_credit'] < 10000:
        insights.append("💳 Low available credit. Monitor your spending to avoid over-limit fees.")

    if data['customer_profile']['annual_income'] > 500000:
        insights.append("💰 Consider upgrading to a premium card with better rewards and benefits.")

    insights.append("📊 Regular monitoring of your spending patterns can help optimize your financial health.")
    insights.append("🎯 Set up automatic payments to avoid late fees and maintain good credit history.")

    return "\n".join(insights)