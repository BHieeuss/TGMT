#!/bin/bash

# TGMT Face Attendance System Deployment Script
echo "🚀 Starting TGMT Face Attendance System Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down

# Build and start containers
print_status "Building and starting containers..."
docker-compose up --build -d

# Wait for containers to be ready
print_status "Waiting for containers to be ready..."
sleep 10

# Check container status
if docker-compose ps | grep -q "Up"; then
    print_status "✅ Deployment successful!"
    echo ""
    echo "🌐 Application is running at:"
    echo "   - http://localhost:5000 (Direct Flask)"
    echo "   - http://localhost (Through Nginx - if enabled)"
    echo ""
    echo "👤 Default login credentials:"
    echo "   - Username: admin"
    echo "   - Password: admin123"
    echo ""
    echo "📊 To view logs:"
    echo "   - docker-compose logs -f face-attendance"
    echo ""
    echo "🛑 To stop the application:"
    echo "   - docker-compose down"
else
    print_error "❌ Deployment failed. Check logs with: docker-compose logs"
    exit 1
fi
