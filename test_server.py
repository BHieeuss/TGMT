#!/usr/bin/env python3

"""
Test script for auto attendance server
"""

import sys
import time
import requests
from auto_attendance_server import create_auto_attendance_session, stop_auto_attendance_session

def test_server():
    """Test auto attendance server"""
    print("Testing auto attendance server...")
    
    # Tạo session điểm danh tự động
    session_id = 1
    port = create_auto_attendance_session(session_id)
    
    if not port:
        print("❌ Failed to create auto attendance session")
        return False
    
    print(f"✅ Auto attendance server started on port {port}")
    print(f"📍 Access at: http://localhost:{port}")
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        # Test main page
        response = requests.get(f"http://localhost:{port}/", timeout=5)
        if response.status_code == 200:
            print("✅ Main page accessible")
        else:
            print(f"❌ Main page error: {response.status_code}")
        
        # Test API endpoints
        api_endpoints = ['/api/attendance', '/api/status', '/api/recognition_status']
        
        for endpoint in api_endpoints:
            try:
                response = requests.get(f"http://localhost:{port}{endpoint}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {endpoint}: {data}")
                else:
                    print(f"❌ {endpoint} error: {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint} error: {e}")
        
        # Test video feed (just check if endpoint exists)
        try:
            response = requests.get(f"http://localhost:{port}/video_feed", timeout=5, stream=True)
            if response.status_code == 200:
                print("✅ Video feed accessible")
            else:
                print(f"❌ Video feed error: {response.status_code}")
        except Exception as e:
            print(f"❌ Video feed error: {e}")
        
    except Exception as e:
        print(f"❌ Server test error: {e}")
    
    # Stop server
    if stop_auto_attendance_session(port):
        print(f"✅ Server stopped successfully")
    else:
        print(f"❌ Failed to stop server")
    
    return True

if __name__ == '__main__':
    try:
        test_server()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
