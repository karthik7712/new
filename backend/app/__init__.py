from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from app.config.config import config

mongo = PyMongo()
bcrypt = Bcrypt()
jwt = JWTManager()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    mongo.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.cards import cards_bp
    from app.routes.customer import customer_bp
    from app.routes.manager import manager_bp
    from app.routes.transactions import transactions_bp
    from app.routes.health import health_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(cards_bp, url_prefix='/api/cards')
    app.register_blueprint(customer_bp, url_prefix='/api/customer')
    app.register_blueprint(manager_bp, url_prefix='/api/manager')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(health_bp, url_prefix='/api/health')

    # Error handlers
    from app.utils.helpers import register_error_handlers
    register_error_handlers(app)

    return app