#!/usr/bin/env python3
"""
Setup and Fix Dependencies for Face Recognition Attendance System
"""

import subprocess
import sys
import os

def run_command(command):
    """Run command and handle errors"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def fix_numpy_opencv_compatibility():
    """Fix NumPy and OpenCV compatibility issues"""
    print("🔧 Fixing NumPy and OpenCV compatibility...")
    
    # Uninstall problematic packages
    print("📤 Uninstalling conflicting packages...")
    commands = [
        "pip uninstall -y numpy",
        "pip uninstall -y opencv-python", 
        "pip uninstall -y face-recognition",
        "pip uninstall -y dlib"
    ]
    
    for cmd in commands:
        print(f"   Running: {cmd}")
        run_command(cmd)
    
    # Install compatible versions
    print("📥 Installing compatible versions...")
    compatible_packages = [
        "numpy==1.24.3",
        "opencv-python==4.10.0.84",
        "cmake",
        "dlib==19.24.2", 
        "face-recognition==1.3.0"
    ]
    
    for package in compatible_packages:
        print(f"   Installing: {package}")
        success, output = run_command(f"pip install {package}")
        if not success:
            print(f"   ⚠️  Warning: Failed to install {package}")
            print(f"   Error: {output}")
    
    # Install remaining requirements
    print("📦 Installing remaining requirements...")
    success, output = run_command("pip install -r requirements.txt")
    if not success:
        print(f"⚠️  Warning: Some packages may have failed to install")
        print(f"Error: {output}")
    
    print("✅ Dependency fix completed!")

def test_imports():
    """Test if critical imports work"""
    print("🧪 Testing critical imports...")
    
    try:
        import numpy
        print(f"✅ NumPy {numpy.__version__} - OK")
    except ImportError as e:
        print(f"❌ NumPy import failed: {e}")
        return False
    
    try:
        import cv2
        print(f"✅ OpenCV {cv2.__version__} - OK")
    except ImportError as e:
        print(f"❌ OpenCV import failed: {e}")
        return False
    
    try:
        import face_recognition
        print("✅ face_recognition - OK")
    except ImportError as e:
        print(f"❌ face_recognition import failed: {e}")
        print("💡 Tip: You may need to install Visual Studio Build Tools")
        return False
    
    try:
        import flask
        print("✅ Flask - OK")
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
        return False
    
    return True

def init_database():
    """Initialize the database"""
    print("🗄️ Initializing database...")
    try:
        from models.database import init_database
        init_database()
        print("✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def create_directories():
    """Create required directories"""
    print("📁 Creating required directories...")
    directories = ['uploads', 'exports', 'static/img']
    
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"   ✅ {dir_path}")

def run_app():
    """Run the Flask application"""
    print("\n🚀 Starting Face Recognition Attendance System...")
    print("=" * 60)
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
    print("=" * 60)
    
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

def main():
    """Main function"""
    print("🎯 Face Recognition Attendance System - Setup & Run")
    print("=" * 60)
    
    # Fix dependencies
    fix_numpy_opencv_compatibility()
    
    # Test imports
    if not test_imports():
        print("\n❌ Critical imports failed. Please check the error messages above.")
        print("💡 Try running this script as administrator or install Visual Studio Build Tools")
        input("Press Enter to exit...")
        return
    
    # Create directories
    create_directories()
    
    # Initialize database
    if not init_database():
        print("❌ Database initialization failed")
        input("Press Enter to exit...")
        return
    
    # Run the application
    run_app()

if __name__ == "__main__":
    main()
