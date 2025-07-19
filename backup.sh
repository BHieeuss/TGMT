#!/bin/bash

# TGMT Face Attendance System Backup Script
# This script creates backups of database and important files

# Configuration
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_NAME="tgmt-face-attendance"
RETENTION_DAYS=30

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[BACKUP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
mkdir -p $BACKUP_DIR

print_status "Starting backup process for $PROJECT_NAME..."

# Backup database
if [ -f "attendance_system.db" ]; then
    print_status "Backing up database..."
    cp attendance_system.db "$BACKUP_DIR/attendance_system_$DATE.db"
    
    # Create SQL dump as well
    if command -v sqlite3 &> /dev/null; then
        sqlite3 attendance_system.db .dump > "$BACKUP_DIR/attendance_system_$DATE.sql"
        print_status "Database SQL dump created"
    fi
else
    print_warning "Database file not found"
fi

# Backup uploads directory (student photos)
if [ -d "uploads" ]; then
    print_status "Backing up uploads directory..."
    tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" uploads/
else
    print_warning "Uploads directory not found"
fi

# Backup exports directory (reports)
if [ -d "exports" ]; then
    print_status "Backing up exports directory..."
    tar -czf "$BACKUP_DIR/exports_$DATE.tar.gz" exports/
else
    print_warning "Exports directory not found"
fi

# Backup configuration files
print_status "Backing up configuration files..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='backups' \
    --exclude='uploads' \
    --exclude='exports' \
    --exclude='attendance_system.db' \
    .

# Create full backup
print_status "Creating full backup archive..."
tar -czf "$BACKUP_DIR/full_backup_$DATE.tar.gz" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='backups' \
    .

# Clean old backups (keep only last 30 days)
print_status "Cleaning old backups (keeping last $RETENTION_DAYS days)..."
find $BACKUP_DIR -name "*.db" -type f -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.sql" -type f -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete

# Display backup info
print_status "Backup completed successfully!"
echo ""
echo "Backup files created:"
ls -la $BACKUP_DIR/*$DATE*
echo ""
echo "Backup location: $(pwd)/$BACKUP_DIR"
echo "Backup date: $DATE"

# Calculate total backup size
TOTAL_SIZE=$(du -sh $BACKUP_DIR | cut -f1)
echo "Total backup size: $TOTAL_SIZE"
