from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
import os
import sqlite3
from datetime import datetime
# Conditional imports for cloud deployment
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("⚠️  OpenCV not available - face recognition disabled for cloud deployment")

from PIL import Image
import base64
import io
import pandas as pd
try:
    import pickle
except ImportError:
    pickle = None
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)

# Load configuration based on environment
config_name = os.environ.get('FLASK_ENV', 'development')
if config_name == 'production' or os.environ.get('DOCKER_ENV'):
    config_name = 'docker'

try:
    from config import config
    app.config.from_object(config[config_name])
except ImportError:
    # Fallback to basic configuration if config.py doesn't exist
    app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
    app.config['EXPORT_FOLDER'] = os.environ.get('EXPORT_FOLDER', 'exports')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload and export directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

# Decorator để kiểm tra đăng nhập
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Vui lòng đăng nhập để truy cập!', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

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

# Health check endpoint for monitoring
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers"""
    try:
        # Check database connection
        from models.database import get_db_connection
        conn = get_db_connection()
        conn.execute('SELECT 1').fetchone()
        conn.close()
        
        # Check upload directory
        upload_accessible = os.path.exists(app.config['UPLOAD_FOLDER']) and os.access(app.config['UPLOAD_FOLDER'], os.W_OK)
        
        # Check export directory
        export_accessible = os.path.exists(app.config['EXPORT_FOLDER']) and os.access(app.config['EXPORT_FOLDER'], os.W_OK)
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': 'ok',
                'upload_folder': 'ok' if upload_accessible else 'error',
                'export_folder': 'ok' if export_accessible else 'error'
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """Trang chủ - kiểm tra đăng nhập"""
    from flask import session
    
    # Kiểm tra xem user đã đăng nhập chưa
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    # Nếu đã đăng nhập, hiển thị dashboard
    from models.database import get_dashboard_stats
    stats = get_dashboard_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/camera')
@login_required
def camera():
    """Trang điểm danh bằng camera"""
    return render_template('camera.html')

@app.route('/capture_faces')
@login_required
def capture_faces():
    """Trang thu thập dữ liệu khuôn mặt sinh viên"""
    return render_template('capture_faces.html')

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# Initialize OpenCV face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

@app.route('/api/detect_face', methods=['POST'])
@login_required
def detect_face():
    """API phát hiện khuôn mặt đơn giản"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu ảnh'})
        
        # Decode base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to grayscale
        image_array = np.array(image)
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_array
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
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
@login_required
def capture_face():
    """API thu thập dữ liệu khuôn mặt sinh viên - quy trình đơn giản như script mẫu"""
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
        
        # Convert PIL image to OpenCV format
        image_array = np.array(image)
        if len(image_array.shape) == 3:  # Color image
            image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        else:
            image_bgr = cv2.cvtColor(image_array, cv2.COLOR_GRAY2BGR)
        
        # Convert to grayscale - giống script mẫu
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # Detect faces - giống script mẫu
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(50, 50)
        )
        
        if len(faces) == 0:
            return jsonify({'success': False, 'message': 'Không phát hiện khuôn mặt trong ảnh'})
        
        # Get the largest face (assuming it's the main subject)
        largest_face = max(faces, key=lambda face: face[2] * face[3])
        x, y, w, h = largest_face
        
        # Crop face region - giống script mẫu, không padding phức tạp
        face_roi = gray[y:y+h, x:x+w]
        
        # Resize to 128x128 - giống script mẫu
        face_resized = cv2.resize(face_roi, (128, 128))
        
        # Không xử lý phức tạp khác - lưu trực tiếp như script mẫu
        face_final = face_resized
        
        # Create student directory if not exists
        student_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', student_id)
        os.makedirs(student_dir, exist_ok=True)
        
        # Count existing ORIGINAL images only (không tính augmented)
        existing_files = [f for f in os.listdir(student_dir) 
                         if f.endswith('.jpg') and '_aug_' not in f]
        image_count = len(existing_files) + 1
        
        # Save processed face image (grayscale) with sequential numbering
        face_filename = f"{student_id}_{image_count:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        face_path = os.path.join(student_dir, face_filename)
        
        # Save as high-quality grayscale image (like the sample images)
        cv2.imwrite(face_path, face_final, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        # Store face data in database - đơn giản hóa
        face_encoding = {
            'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h),
            'face_file': face_filename,
            'capture_time': datetime.now().isoformat(),
            'processed': True,
            'standard_size': (128, 128),
            'quality_score': float(min(1.0, (w * h) / (gray.shape[0] * gray.shape[1] * 0.1)))
        }
        
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
            'message': f'Thu thập ảnh #{image_count} thành công cho {student["full_name"]} (quy trình đơn giản)',
            'student': {
                'id': student_id,
                'name': student['full_name'],
                'face_file': face_filename,
                'image_count': image_count,
                'total_images': image_count,
                'processed_info': {
                    'size': (128, 128),
                    'simple_processing': True,
                    'grayscale_crop_only': True
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route('/test-camera')
@login_required
def test_camera():
    """Trang test camera đơn giản"""
    return render_template('test_camera.html')

@app.route('/api/student_images/<student_id>')
@login_required
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
@login_required
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

# API routes cho subjects by class
@app.route('/api/subjects_by_class/<int:class_id>')
@login_required
def api_subjects_by_class(class_id):
    """API lấy danh sách môn học có ca điểm danh cho lớp này"""
    from models.database import get_db_connection
    conn = get_db_connection()
    subjects = conn.execute('''
        SELECT DISTINCT s.id, s.subject_code, s.subject_name
        FROM subjects s
        JOIN attendance_sessions ast ON s.id = ast.subject_id
        WHERE ast.class_id = ?
        ORDER BY s.subject_name
    ''', (class_id,)).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in subjects])

@app.route('/api/face_collection_status/<student_id>')
@login_required
def get_face_collection_status(student_id):
    """API kiểm tra trạng thái thu thập khuôn mặt"""
    try:
        student_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', student_id)
        
        if not os.path.exists(student_dir):
            return jsonify({
                'success': True,
                'student_id': student_id,
                'image_count': 0,
                'progress_percent': 0,
                'is_complete': False,
                'can_train': False,
                'status': 'not_started'
            })
        
        # Đếm ảnh hiện có
        image_files = [f for f in os.listdir(student_dir) if f.lower().endswith('.jpg')]
        image_count = len(image_files)
        
        # Tính trạng thái
        progress_percent = (image_count / 40) * 100
        is_complete = image_count >= 40
        can_train = image_count >= 10  # Tối thiểu 10 ảnh để train
        
        if image_count == 0:
            status = 'not_started'
        elif image_count < 10:
            status = 'collecting'
        elif image_count < 40:
            status = 'ready_for_train'
        else:
            status = 'complete'
        
        return jsonify({
            'success': True,
            'student_id': student_id,
            'image_count': image_count,
            'total_target': 40,
            'progress_percent': round(progress_percent, 1),
            'is_complete': is_complete,
            'can_train': can_train,
            'status': status,
            'images': [f"/uploads/faces/{student_id}/{img}" for img in sorted(image_files)[-5:]]  # 5 ảnh gần nhất
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route('/api/reset_face_collection/<student_id>', methods=['POST'])
@login_required
def reset_face_collection(student_id):
    """API reset thu thập khuôn mặt (xóa tất cả ảnh)"""
    try:
        student_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', student_id)
        
        if os.path.exists(student_dir):
            import shutil
            shutil.rmtree(student_dir)
            
        # Cập nhật database
        from models.database import get_db_connection
        conn = get_db_connection()
        conn.execute('UPDATE students SET photo_path = NULL WHERE student_id = ?', (student_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Đã reset thu thập khuôn mặt cho sinh viên {student_id}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

if __name__ == '__main__':
    # Khởi tạo database
    from models.database import init_database
    init_database()
    
    # Cloud deployment support
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("🎯 Face Attendance System Starting...")
    print(f"📱 Access at: http://localhost:{port}")
    print("👤 Login: admin / admin123")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
