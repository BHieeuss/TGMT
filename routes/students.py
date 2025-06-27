from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models.database import get_db_connection
import os
import cv2
import numpy as np
from PIL import Image
from werkzeug.utils import secure_filename
import json

students_bp = Blueprint('students', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_face(image_path):
    """Phát hiện khuôn mặt từ ảnh (sử dụng OpenCV thay vì face_recognition)"""
    try:
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return None
            
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Initialize face detector
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            # Return basic face detection info (x, y, w, h of first face)
            x, y, w, h = faces[0]
            return [float(x), float(y), float(w), float(h)]
        return None
    except Exception as e:
        print(f"Error detecting face: {e}")
        return None

@students_bp.route('/')
def list_students():
    """Danh sách sinh viên"""
    conn = get_db_connection()
    students = conn.execute('''
        SELECT s.*, c.class_name, c.class_code
        FROM students s
        JOIN classes c ON s.class_id = c.id
        ORDER BY s.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('students/list.html', students=students)

@students_bp.route('/add', methods=['GET', 'POST'])
def add_student():
    """Thêm sinh viên mới"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        full_name = request.form.get('full_name')
        class_id = request.form.get('class_id')
        
        if not student_id or not full_name or not class_id:
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
        else:
            photo_path = None
            face_encoding = None
            
            # Xử lý upload ảnh
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"{student_id}_{file.filename}")
                    photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(photo_path)
                    
                    # Mã hóa khuôn mặt
                    face_encoding = encode_face(photo_path)
                    if face_encoding:
                        face_encoding = json.dumps(face_encoding)
                    else:
                        flash('Không thể nhận diện khuôn mặt trong ảnh. Vui lòng thử ảnh khác!', 'warning')
            
            try:
                conn.execute('''
                    INSERT INTO students (student_id, full_name, class_id, photo_path, face_encoding)
                    VALUES (?, ?, ?, ?, ?)
                ''', (student_id, full_name, class_id, photo_path, face_encoding))
                conn.commit()
                flash('Thêm sinh viên thành công!', 'success')
                return redirect(url_for('students.list_students'))
            except Exception as e:
                flash('MSSV đã tồn tại!', 'error')
    
    # Lấy danh sách lớp học
    classes = conn.execute('SELECT id, class_code, class_name FROM classes ORDER BY class_name').fetchall()
    conn.close()
    
    return render_template('students/add.html', classes=classes)

@students_bp.route('/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    """Sửa thông tin sinh viên"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        student_code = request.form.get('student_id')
        full_name = request.form.get('full_name')
        class_id = request.form.get('class_id')
        
        if not student_code or not full_name or not class_id:
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
        else:
            # Lấy thông tin sinh viên hiện tại
            current_student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
            photo_path = current_student['photo_path']
            face_encoding = current_student['face_encoding']
            
            # Xử lý upload ảnh mới
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename != '' and allowed_file(file.filename):
                    # Xóa ảnh cũ nếu có
                    if photo_path and os.path.exists(photo_path):
                        os.remove(photo_path)
                    
                    filename = secure_filename(f"{student_code}_{file.filename}")
                    photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(photo_path)
                    
                    # Mã hóa khuôn mặt mới
                    new_face_encoding = encode_face(photo_path)
                    if new_face_encoding:
                        face_encoding = json.dumps(new_face_encoding)
                    else:
                        flash('Không thể nhận diện khuôn mặt trong ảnh mới!', 'warning')
            
            try:
                conn.execute('''
                    UPDATE students 
                    SET student_id = ?, full_name = ?, class_id = ?, photo_path = ?, face_encoding = ?
                    WHERE id = ?
                ''', (student_code, full_name, class_id, photo_path, face_encoding, student_id))
                conn.commit()
                flash('Cập nhật sinh viên thành công!', 'success')
                return redirect(url_for('students.list_students'))
            except Exception as e:
                flash('MSSV đã tồn tại!', 'error')
    
    # Lấy thông tin sinh viên và danh sách lớp
    student_info = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    classes = conn.execute('SELECT id, class_code, class_name FROM classes ORDER BY class_name').fetchall()
    conn.close()
    
    if not student_info:
        flash('Không tìm thấy sinh viên!', 'error')
        return redirect(url_for('students.list_students'))
    
    return render_template('students/edit.html', student_info=student_info, classes=classes)

@students_bp.route('/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    """Xóa sinh viên"""
    conn = get_db_connection()
    
    # Lấy thông tin sinh viên để xóa ảnh
    student = conn.execute('SELECT photo_path FROM students WHERE id = ?', (student_id,)).fetchone()
    
    if student and student['photo_path'] and os.path.exists(student['photo_path']):
        os.remove(student['photo_path'])
    
    conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()
    
    flash('Xóa sinh viên thành công!', 'success')
    return redirect(url_for('students.list_students'))

@students_bp.route('/api/by_class/<int:class_id>')
def api_students_by_class(class_id):
    """API lấy danh sách sinh viên theo lớp"""
    conn = get_db_connection()
    students = conn.execute('''
        SELECT id, student_id, full_name 
        FROM students 
        WHERE class_id = ? 
        ORDER BY full_name
    ''', (class_id,)).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in students])

@students_bp.route('/api/all')
def api_all_students():
    """API lấy tất cả sinh viên"""
    conn = get_db_connection()
    students = conn.execute('''
        SELECT s.student_id, s.full_name, c.class_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        ORDER BY s.full_name
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in students])

@students_bp.route('/api/captured_faces')
def api_captured_faces():
    """API lấy danh sách khuôn mặt đã thu thập"""
    conn = get_db_connection()
    faces = conn.execute('''
        SELECT s.student_id, s.full_name, s.face_encoding, s.photo_path
        FROM students s
        WHERE s.face_encoding IS NOT NULL AND s.face_encoding != ''
        ORDER BY s.created_at DESC
    ''').fetchall()
    
    result = []
    for face in faces:
        if face['face_encoding']:
            try:
                import json
                encoding_data = json.loads(face['face_encoding'].replace("'", '"'))
                if 'face_file' in encoding_data:
                    result.append({
                        'student_id': face['student_id'],
                        'full_name': face['full_name'],
                        'face_file': encoding_data['face_file']
                    })
            except:
                pass
    
    conn.close()
    return jsonify(result)

@students_bp.route('/api/student_faces/<student_id>')
def api_student_faces(student_id):
    """API lấy thông tin số ảnh khuôn mặt của sinh viên"""
    conn = get_db_connection()
    
    # Đếm số file ảnh trong thư mục uploads của sinh viên
    uploads_dir = os.path.join(current_app.static_folder, '..', 'uploads')
    count = 0
    
    if os.path.exists(uploads_dir):
        for filename in os.listdir(uploads_dir):
            if filename.startswith(f"face_{student_id}_") and filename.endswith(('.jpg', '.jpeg', '.png')):
                count += 1
    
    # Lấy thông tin sinh viên
    student = conn.execute('''
        SELECT student_id, full_name
        FROM students
        WHERE student_id = ?
    ''', (student_id,)).fetchone()
    
    conn.close()
    
    if student:
        return jsonify({
            'success': True,
            'student_id': student['student_id'],
            'student_name': student['full_name'],
            'count': count
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Không tìm thấy sinh viên'
        })

@students_bp.route('/collect_face_data')
@students_bp.route('/collect_face_data/<int:student_id>')
def collect_face_data(student_id=None):
    """Trang thu thập dữ liệu khuôn mặt"""
    conn = get_db_connection()
    
    if student_id:
        # Thu thập cho sinh viên cụ thể
        student = conn.execute('''
            SELECT s.*, c.class_name, c.class_code
            FROM students s
            JOIN classes c ON s.class_id = c.id
            WHERE s.id = ?
        ''', (student_id,)).fetchone()
        
        if not student:
            flash('Không tìm thấy sinh viên!', 'error')
            return redirect(url_for('students.collect_face_data'))
        
        conn.close()
        return render_template('students/collect_face_data.html', student=student)
    else:
        # Hiển thị danh sách sinh viên để chọn
        students = conn.execute('''
            SELECT s.*, c.class_name, c.class_code
            FROM students s
            JOIN classes c ON s.class_id = c.id
            ORDER BY c.class_name, s.full_name
        ''').fetchall()
        
        conn.close()
        return render_template('students/select_student_for_collection.html', students=students)
