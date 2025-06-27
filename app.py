from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import os
import sqlite3
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import base64
import io
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['EXPORT_FOLDER'] = 'exports'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload and export directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

# Import routes
from routes.auth import auth_bp
from routes.classes import classes_bp
from routes.students import students_bp
from routes.subjects import subjects_bp
from routes.attendance import attendance_bp
from routes.reports import reports_bp
from routes.ai import ai_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(classes_bp, url_prefix='/classes')
app.register_blueprint(students_bp, url_prefix='/students')
app.register_blueprint(subjects_bp, url_prefix='/subjects')
app.register_blueprint(attendance_bp, url_prefix='/attendance')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(ai_bp)

@app.route('/')
def index():
    """Dashboard trang chủ"""
    from models.database import get_dashboard_stats
    stats = get_dashboard_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/camera')
def camera():
    """Trang điểm danh bằng camera"""
    return render_template('camera.html')

@app.route('/capture_faces')
def capture_faces():
    """Trang thu thập dữ liệu khuôn mặt sinh viên"""
    return render_template('capture_faces.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# Initialize OpenCV face detector and AI model
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
from models.advanced_face_model import face_model

@app.route('/api/detect_face', methods=['POST'])
def detect_face():
    """API phát hiện và nhận diện khuôn mặt"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu ảnh'})
        
        # Try AI recognition first if model is available
        if face_model.is_trained:
            ai_result = face_model.recognize_face(image_data)
            if ai_result['success']:
                return jsonify({
                    'success': True,
                    'message': f'Phát hiện {ai_result["face_count"]} khuôn mặt',
                    'face_count': ai_result['face_count'],
                    'faces': ai_result['faces'],
                    'method': 'ai_recognition'
                })
        
        # Fallback to basic face detection
        basic_result = face_model.detect_face_only(image_data)
        return jsonify({
            'success': basic_result['success'],
            'message': f'Phát hiện {basic_result["face_count"]} khuôn mặt',
            'face_count': basic_result['face_count'],
            'method': 'basic_detection'
        })
        
        if len(faces) > 0:
            return jsonify({
                'success': True, 
                'message': f'Phát hiện {len(faces)} khuôn mặt',
                'face_count': len(faces),
                'method': 'basic_detection'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Không phát hiện khuôn mặt nào'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route('/api/capture_face', methods=['POST'])
def capture_face():
    """API thu thập dữ liệu khuôn mặt sinh viên"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        image_data = data.get('image')
        
        if not student_id or not image_data:
            return jsonify({'success': False, 'message': 'Thiếu dữ liệu'})
        
        # Decode base64 image
        image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64,
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert PIL image to numpy array
        image_array = np.array(image)
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return jsonify({'success': False, 'message': 'Không phát hiện khuôn mặt trong ảnh'})
        
        # Get the largest face (assuming it's the main subject)
        largest_face = max(faces, key=lambda face: face[2] * face[3])
        x, y, w, h = largest_face
        
        # Crop face region
        face_roi = image_array[y:y+h, x:x+w]
        face_image = Image.fromarray(face_roi)
        
        # Create student directory if not exists
        student_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', student_id)
        os.makedirs(student_dir, exist_ok=True)
        
        # Count existing images to generate sequential filename
        existing_files = [f for f in os.listdir(student_dir) if f.endswith('.jpg')]
        image_count = len(existing_files) + 1
        
        # Save face image with sequential numbering
        face_filename = f"{student_id}_{image_count:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        face_path = os.path.join(student_dir, face_filename)
        face_image.save(face_path)
        
        # Store face data in database (using simple coordinates as "encoding")
        face_encoding = {
            'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h),
            'face_file': face_filename,
            'capture_time': datetime.now().isoformat()
        }
        
        # Calculate quality score based on face size
        quality_score = min(1.0, (w * h) / (image_array.shape[0] * image_array.shape[1] * 0.1))
        
        # Update student record with face data
        from models.database import get_db_connection
        conn = get_db_connection()
        
        # Check if student exists
        student = conn.execute('SELECT id, full_name FROM students WHERE student_id = ?', (student_id,)).fetchone()
        if not student:
            conn.close()
            return jsonify({'success': False, 'message': 'Không tìm thấy sinh viên với MSSV này'})
        
        # Update student's photo_path to point to the latest image
        relative_face_path = os.path.join('faces', student_id, face_filename)
        conn.execute('''
            UPDATE students 
            SET photo_path = ?, face_encoding = ?
            WHERE student_id = ?
        ''', (relative_face_path, str(face_encoding), student_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Thu thập ảnh #{image_count} thành công cho {student["full_name"]}',
            'student': {
                'id': student_id,
                'name': student['full_name'],
                'face_file': face_filename,
                'image_count': image_count,
                'total_images': image_count
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route('/test-camera')
def test_camera():
    """Trang test camera đơn giản"""
    return render_template('test_camera.html')

@app.route('/api/student_images/<student_id>')
def get_student_images(student_id):
    """API lấy danh sách ảnh của sinh viên từ thư mục"""
    try:
        student_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', student_id)
        
        if not os.path.exists(student_dir):
            return jsonify({
                'success': True,
                'student_id': student_id,
                'image_count': 0,
                'images': []
            })
        
        # Get all image files
        image_files = [f for f in os.listdir(student_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        image_files.sort()  # Sort by filename (chronological due to timestamp)
        
        # Create image URLs
        images = []
        for img_file in image_files:
            images.append({
                'filename': img_file,
                'url': f"/uploads/faces/{student_id}/{img_file}",
                'path': os.path.join(student_dir, img_file)
            })
        
        return jsonify({
            'success': True,
            'student_id': student_id,
            'image_count': len(images),
            'images': images
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route('/uploads/faces/<student_id>/<filename>')
def serve_face_image(student_id, filename):
    """Serve face images từ thư mục của sinh viên"""
    try:
        face_path = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', student_id, filename)
        if os.path.exists(face_path):
            return send_file(face_path)
        else:
            return "File not found", 404
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    # Khởi tạo database
    from models.database import init_database
    init_database()
    
    print("🎯 Face Attendance System Starting...")
    print("📱 Access at: http://localhost:5000")
    print("👤 Login: admin / admin123")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
