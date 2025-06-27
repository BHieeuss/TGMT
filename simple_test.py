#!/usr/bin/env python3

"""
Simple test for auto attendance server
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Starting simple test...")

try:
    from flask import Flask
    print("✅ Flask import OK")
except ImportError as e:
    print(f"❌ Flask import failed: {e}")
    exit(1)

try:
    import cv2
    print("✅ OpenCV import OK")
except ImportError as e:
    print(f"❌ OpenCV import failed: {e}")

try:
    from models.database import get_db_connection
    print("✅ Database import OK")
except ImportError as e:
    print(f"❌ Database import failed: {e}")

try:
    from models.advanced_face_model import AdvancedFaceModel
    print("✅ Face model import OK")
except ImportError as e:
    print(f"❌ Face model import failed: {e}")

# Test database connection
try:
    conn = get_db_connection()
    sessions = conn.execute('SELECT * FROM attendance_sessions LIMIT 1').fetchall()
    conn.close()
    print(f"✅ Database connection OK, found {len(sessions)} session(s)")
except Exception as e:
    print(f"❌ Database error: {e}")

# Test basic Flask app
try:
    app = Flask(__name__)
    
    @app.route('/test')
    def test():
        return {'status': 'ok', 'message': 'Test successful'}
    
    @app.route('/api/test')  
    def api_test():
        return {'api': 'working', 'data': [1,2,3]}
    
    print("✅ Flask app created successfully")
    print("🚀 Starting test server on port 8888...")
    
    # Run test server
    app.run(host='0.0.0.0', port=8888, debug=False, threaded=True)
    
except Exception as e:
    print(f"❌ Flask app error: {e}")
