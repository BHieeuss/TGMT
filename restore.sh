#!/bin/bash

# TGMT Face Attendance System Restore Script
# This script restores backups of database and files

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[RESTORE]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to list available backups
list_backups() {
    echo ""
    print_info "Available backups:"
    echo ""
    
    if [ -d "backups" ] && [ "$(ls -A backups/)" ]; then
        # Database backups
        echo "Database backups:"
        ls -la backups/*.db 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}'
        
        echo ""
        echo "Full backups:"
        ls -la backups/full_backup_*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}'
        
        echo ""
        echo "Upload backups:"
        ls -la backups/uploads_*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}'
        
        echo ""
        echo "Export backups:"
        ls -la backups/exports_*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}'
    else
        print_warning "No backups found in backups/ directory"
    fi
}

# Function to restore database
restore_database() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi
    
    print_warning "This will overwrite the current database!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup current database first
        if [ -f "attendance_system.db" ]; then
            print_status "Backing up current database..."
            cp attendance_system.db "attendance_system.db.backup.$(date +%Y%m%d_%H%M%S)"
        fi
        
        # Restore database
        print_status "Restoring database from $backup_file..."
        cp "$backup_file" "attendance_system.db"
        print_status "Database restored successfully!"
    else
        print_info "Database restore cancelled."
    fi
}

# Function to restore uploads
restore_uploads() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi
    
    print_warning "This will overwrite the current uploads directory!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup current uploads first
        if [ -d "uploads" ]; then
            print_status "Backing up current uploads..."
            mv uploads "uploads.backup.$(date +%Y%m%d_%H%M%S)"
        fi
        
        # Restore uploads
        print_status "Restoring uploads from $backup_file..."
        tar -xzf "$backup_file"
        print_status "Uploads restored successfully!"
    else
        print_info "Uploads restore cancelled."
    fi
}

# Function to restore exports
restore_exports() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi
    
    print_warning "This will overwrite the current exports directory!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup current exports first
        if [ -d "exports" ]; then
            print_status "Backing up current exports..."
            mv exports "exports.backup.$(date +%Y%m%d_%H%M%S)"
        fi
        
        # Restore exports
        print_status "Restoring exports from $backup_file..."
        tar -xzf "$backup_file"
        print_status "Exports restored successfully!"
    else
        print_info "Exports restore cancelled."
    fi
}

# Function to restore full backup
restore_full() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi
    
    print_warning "This will overwrite ALL current files (except backups)!"
    print_warning "Make sure to stop the application first!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Create safety backup
        print_status "Creating safety backup of current state..."
        ./backup.sh
        
        # Restore full backup
        print_status "Restoring full backup from $backup_file..."
        tar -xzf "$backup_file"
        print_status "Full backup restored successfully!"
        
        print_info "Please restart the application."
    else
        print_info "Full restore cancelled."
    fi
}

# Main script
echo "TGMT Face Attendance System - Restore Tool"
echo "=========================================="

# Check if backups directory exists
if [ ! -d "backups" ]; then
    print_error "Backups directory not found!"
    exit 1
fi

while true; do
    echo ""
    echo "What would you like to restore?"
    echo "1. List available backups"
    echo "2. Restore database"
    echo "3. Restore uploads (student photos)"
    echo "4. Restore exports (reports)"
    echo "5. Restore full backup"
    echo "6. Exit"
    echo ""
    read -p "Choose an option (1-6): " choice
    
    case $choice in
        1)
            list_backups
            ;;
        2)
            list_backups
            echo ""
            read -p "Enter database backup filename: " db_file
            restore_database "backups/$db_file"
            ;;
        3)
            list_backups
            echo ""
            read -p "Enter uploads backup filename: " uploads_file
            restore_uploads "backups/$uploads_file"
            ;;
        4)
            list_backups
            echo ""
            read -p "Enter exports backup filename: " exports_file
            restore_exports "backups/$exports_file"
            ;;
        5)
            list_backups
            echo ""
            read -p "Enter full backup filename: " full_file
            restore_full "backups/$full_file"
            ;;
        6)
            print_info "Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid option. Please choose 1-6."
            ;;
    esac
done
