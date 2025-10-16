#!/bin/bash

# SafeC Credit Card Management System Setup Script
# This script sets up the development environment for the SafeC application

set -e

echo "🚀 Setting up SafeC Credit Card Management System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_status "Checking system requirements..."

    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+ and try again."
        exit 1
    fi

    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm and try again."
        exit 1
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.11+ and try again."
        exit 1
    fi

    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install pip3 and try again."
        exit 1
    fi

    # Check MongoDB
    if ! command -v mongod &> /dev/null; then
        print_warning "MongoDB is not installed. You'll need to install MongoDB or use Docker."
    fi

    print_success "System requirements check completed!"
}

# Setup backend
setup_backend() {
    print_status "Setting up backend..."

    cd backend

    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install Python dependencies
    print_status "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating .env file..."
        cp .env.example .env
        print_warning "Please edit backend/.env with your configuration!"
    fi

    cd ..
    print_success "Backend setup completed!"
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."

    cd frontend

    # Install Node.js dependencies
    print_status "Installing Node.js dependencies..."
    npm install

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating frontend .env file..."
        echo "REACT_APP_API_URL=http://localhost:5000/api" > .env
    fi

    cd ..
    print_success "Frontend setup completed!"
}

# Setup Docker (optional)
setup_docker() {
    print_status "Setting up Docker configuration..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_warning "Docker is not installed. Skipping Docker setup."
        return
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose is not installed. Skipping Docker setup."
        return
    fi

    # Create .env file for Docker if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating Docker .env file..."
        cat > .env << EOF
# Database
MONGODB_URI=mongodb://admin:password123@mongodb:27017/creditcard_db?authSource=admin

# Security
SECRET_KEY=your-super-secret-key-here-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production

# Google AI (optional)
GOOGLE_API_KEY=your-google-api-key-here

# Environment
FLASK_ENV=development
NODE_ENV=development
EOF
        print_warning "Please edit .env with your configuration!"
    fi

    print_success "Docker setup completed!"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."

    mkdir -p uploads
    mkdir -p logs
    mkdir -p ssl

    print_success "Directories created!"
}

# Run tests
run_tests() {
    print_status "Running tests..."

    # Backend tests
    cd backend
    source venv/bin/activate
    python -m pytest tests/ -v --tb=short
    cd ..

    # Frontend tests
    cd frontend
    npm test -- --coverage --watchAll=false
    cd ..

    print_success "Tests completed!"
}

# Main setup function
main() {
    echo "=========================================="
    echo "  SafeC Setup Script"
    echo "=========================================="
    echo

    check_requirements
    create_directories
    setup_backend
    setup_frontend
    setup_docker

    echo
    echo "=========================================="
    print_success "Setup completed successfully!"
    echo "=========================================="
    echo
    echo "Next steps:"
    echo "1. Edit configuration files:"
    echo "   - backend/.env"
    echo "   - frontend/.env"
    echo "   - .env (for Docker)"
    echo
    echo "2. Start MongoDB (if not using Docker):"
    echo "   sudo systemctl start mongod"
    echo
    echo "3. Start the backend:"
    echo "   cd backend && source venv/bin/activate && python app.py"
    echo
    echo "4. Start the frontend (in another terminal):"
    echo "   cd frontend && npm start"
    echo
    echo "5. Or use Docker Compose:"
    echo "   docker-compose up -d"
    echo
    echo "The application will be available at:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:5000"
    echo "  API Docs: http://localhost:5000/api/docs"
    echo
    print_success "Happy coding! 🎉"
}

# Handle script arguments
case "${1:-}" in
    --test)
        run_tests
        ;;
    --docker-only)
        setup_docker
        ;;
    --help)
        echo "SafeC Setup Script"
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --test        Run tests after setup"
        echo "  --docker-only Setup Docker configuration only"
        echo "  --help        Show this help message"
        ;;
    *)
        main
        ;;
esac