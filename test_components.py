#!/usr/bin/env python3

"""
Test model AI và camera
"""

import cv2
import os
import sys

def test_camera():
    """Test camera"""
    print("Testing camera...")
    try:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("❌ Cannot open camera")
            return False
        
        # Test reading frame
        ret, frame = camera.read()
        if ret:
            print(f"✅ Camera working - frame size: {frame.shape}")
        else:
            print("❌ Cannot read frame from camera")
            camera.release()
            return False
        
        camera.release()
        return True
    except Exception as e:
        print(f"❌ Camera error: {e}")
        return False

def test_face_model():
    """Test face recognition model"""
    print("Testing face recognition model...")
    try:
        from models.advanced_face_model import AdvancedFaceModel
        
        model = AdvancedFaceModel()
        print(f"✅ Model imported successfully")
        
        # Check if trained
        is_trained = getattr(model, 'is_trained', False)
        print(f"Model is_trained: {is_trained}")
        
        # Check model file
        model_path = os.path.join('models', 'advanced_face_model.pkl')
        if os.path.exists(model_path):
            print(f"✅ Model file exists: {model_path}")
            
            # Try to load
            try:
                model.load_model(model_path)
                is_trained_after_load = getattr(model, 'is_trained', False)
                print(f"Model is_trained after load: {is_trained_after_load}")
                
                # Check model components
                if hasattr(model, 'face_encodings') and model.face_encodings:
                    print(f"✅ Model has {len(model.face_encodings)} face encodings")
                else:
                    print("❌ Model has no face encodings")
                
                if hasattr(model, 'student_ids') and model.student_ids:
                    print(f"✅ Model has {len(model.student_ids)} student IDs")
                    print(f"Student IDs: {model.student_ids}")
                else:
                    print("❌ Model has no student IDs")
                    
            except Exception as load_error:
                print(f"❌ Error loading model: {load_error}")
        else:
            print(f"❌ Model file not found: {model_path}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import model: {e}")
        return False
    except Exception as e:
        print(f"❌ Model error: {e}")
        return False

def test_database():
    """Test database connection"""
    print("Testing database...")
    try:
        from models.database import get_db_connection
        
        conn = get_db_connection()
        
        # Test students table
        students = conn.execute('SELECT COUNT(*) as count FROM students').fetchone()
        print(f"✅ Database connected - {students['count']} students")
        
        # Test sessions
        sessions = conn.execute('SELECT COUNT(*) as count FROM attendance_sessions').fetchone()
        print(f"✅ {sessions['count']} attendance sessions")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == '__main__':
    print("🔍 Testing Auto Attendance System Components...")
    print("=" * 50)
    
    # Test camera
    camera_ok = test_camera()
    print()
    
    # Test model
    model_ok = test_face_model()
    print()
    
    # Test database
    db_ok = test_database()
    print()
    
    print("=" * 50)
    if camera_ok and model_ok and db_ok:
        print("✅ All components working!")
    else:
        print("❌ Some components have issues")
        if not camera_ok:
            print("  - Camera not working")
        if not model_ok:
            print("  - Face recognition model not working")
        if not db_ok:
            print("  - Database not working")
