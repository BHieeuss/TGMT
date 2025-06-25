#!/usr/bin/env python3
"""
Script to run the Face Recognition Attendance System
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import flask
        import cv2
        import face_recognition
        import pandas
        import openpyxl
        print("✅ All required packages are installed!")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("📦 Installing required packages...")
        
        # Install requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True

def init_database():
    """Initialize the database"""
    print("🗄️ Initializing database...")
    from models.database import init_database
    init_database()
    print("✅ Database initialized successfully!")

def run_app():
    """Run the Flask application"""
    print("🚀 Starting Face Recognition Attendance System...")
    print("📱 Access the application at: http://localhost:5000")
    print("👤 Login credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n🎯 Features available:")
    print("   • Manage classes and students")
    print("   • Create attendance sessions")
    print("   • Face recognition attendance")
    print("   • Generate Excel reports")
    print("\n⚡ Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Import and run the Flask app
    from app import app
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    print("🎯 Face Recognition Attendance System")
    print("=" * 50)
    
    # Check requirements
    if check_requirements():
        # Initialize database
        init_database()
        
        # Run the application
        run_app()
    else:
        print("❌ Failed to install requirements. Please check your Python environment.")
        sys.exit(1)
