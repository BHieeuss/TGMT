from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models.database import get_db_connection
import cv2
import numpy as np
import base64
import io
from PIL import Image
import json
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/sessions')
def list_sessions():
    """Danh sách ca điểm danh"""
    conn = get_db_connection()
    sessions = conn.execute('''
        SELECT ast.*, s.subject_name, s.subject_code, c.class_name, c.class_code,
               COUNT(ar.id) as attendance_count
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        LEFT JOIN attendance_records ar ON ast.id = ar.session_id
        GROUP BY ast.id
        ORDER BY ast.session_date DESC, ast.start_time DESC
    ''').fetchall()
    conn.close()
    
    return render_template('attendance/sessions.html', sessions=sessions)

@attendance_bp.route('/sessions/add', methods=['GET', 'POST'])
def add_session():
    """Thêm ca điểm danh mới"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        session_name = request.form.get('session_name')
        subject_id = request.form.get('subject_id')
        class_id = request.form.get('class_id')
        session_date = request.form.get('session_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        if not all([session_name, subject_id, class_id, session_date, start_time]):
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
        else:
            conn.execute('''
                INSERT INTO attendance_sessions (session_name, subject_id, class_id, session_date, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_name, subject_id, class_id, session_date, start_time, end_time))
            conn.commit()
            flash('Tạo ca điểm danh thành công!', 'success')
            return redirect(url_for('attendance.list_sessions'))
    
    # Lấy danh sách môn học và lớp
    subjects = conn.execute('SELECT id, subject_code, subject_name FROM subjects ORDER BY subject_name').fetchall()
    classes = conn.execute('SELECT id, class_code, class_name FROM classes ORDER BY class_name').fetchall()
    conn.close()
    
    return render_template('attendance/add_session.html', subjects=subjects, classes=classes)

@attendance_bp.route('/sessions/<int:session_id>')
def session_detail(session_id):
    """Chi tiết ca điểm danh"""
    conn = get_db_connection()
    
    # Thông tin ca điểm danh
    session = conn.execute('''
        SELECT ast.*, s.subject_name, s.subject_code, c.class_name, c.class_code
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        WHERE ast.id = ?
    ''', (session_id,)).fetchone()
    
    if not session:
        flash('Không tìm thấy ca điểm danh!', 'error')
        return redirect(url_for('attendance.list_sessions'))
    
    # Danh sách sinh viên trong lớp và trạng thái điểm danh
    students_attendance = conn.execute('''
        SELECT s.id, s.student_id, s.full_name, s.photo_path,
               ar.attendance_time, ar.status, ar.method, ar.confidence
        FROM students s
        LEFT JOIN attendance_records ar ON s.id = ar.student_id AND ar.session_id = ?
        WHERE s.class_id = ?
        ORDER BY s.full_name
    ''', (session_id, session['class_id'])).fetchall()
    
    conn.close()
    
    return render_template('attendance/session_detail.html', 
                         session=session, 
                         students_attendance=students_attendance)

@attendance_bp.route('/face_recognition/<int:session_id>')
def face_recognition_page(session_id):
    """Trang điểm danh bằng nhận diện khuôn mặt"""
    conn = get_db_connection()
    
    session = conn.execute('''
        SELECT ast.*, s.subject_name, c.class_name
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        WHERE ast.id = ?
    ''', (session_id,)).fetchone()
    
    if not session:
        flash('Không tìm thấy ca điểm danh!', 'error')
        return redirect(url_for('attendance.list_sessions'))
    
    conn.close()
    return render_template('attendance/face_recognition.html', session=session)

@attendance_bp.route('/api/recognize_face', methods=['POST'])
def recognize_face():
    """API nhận diện khuôn mặt (đơn giản hóa với OpenCV)"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        image_data = data.get('image')
        
        if not session_id or not image_data:
            return jsonify({'success': False, 'message': 'Thiếu dữ liệu'})
        
        # Decode base64 image
        image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64,
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert PIL image to numpy array
        image_array = np.array(image)
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        
        # Initialize face detector
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return jsonify({'success': False, 'message': 'Không tìm thấy khuôn mặt trong ảnh'})
        
        # Get session info
        conn = get_db_connection()
        session_info = conn.execute('''
            SELECT class_id FROM attendance_sessions WHERE id = ?
        ''', (session_id,)).fetchone()
          # For enhanced demo: try to match faces using basic image comparison
        students = conn.execute('''
            SELECT id, student_id, full_name, face_encoding
            FROM students 
            WHERE class_id = ? AND face_encoding IS NOT NULL
            ORDER BY full_name
        ''', (session_info['class_id'],)).fetchall()
        
        if not students:
            conn.close()
            return jsonify({'success': False, 'message': 'Không có sinh viên nào có dữ liệu khuôn mặt trong lớp này'})
        
        # Simple face matching using position comparison (demo logic)
        best_match = None
        for student in students:
            if student['face_encoding']:
                try:
                    import json
                    stored_data = json.loads(student['face_encoding'].replace("'", '"'))
                    if 'face_file' in stored_data:
                        # In a real system, this would do actual face comparison
                        # For demo, we'll use the first student with face data
                        best_match = student
                        break
                except:
                    continue        
        if not best_match:
            conn.close()
            return jsonify({'success': False, 'message': 'Không nhận diện được khuôn mặt'})
        
        # Check if already attended
        existing = conn.execute('''
            SELECT id FROM attendance_records 
            WHERE session_id = ? AND student_id = ?
        ''', (session_id, best_match['id'])).fetchone()
        
        if existing:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'{best_match["full_name"]} đã điểm danh rồi!'
            })
        
        # Record attendance
        conn.execute('''
            INSERT INTO attendance_records (session_id, student_id, status, method, confidence)
            VALUES (?, ?, 'present', 'face_recognition', ?)
        ''', (session_id, best_match['id'], 85.0))  # Demo confidence
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Điểm danh thành công cho {best_match["full_name"]} (Demo)',            'student': {
                'id': best_match['student_id'],
                'name': best_match['full_name'],
                'confidence': 85.0
            }
        })
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@attendance_bp.route('/api/manual_attendance', methods=['POST'])
def manual_attendance():
    """API điểm danh thủ công bằng MSSV"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        student_id = data.get('student_id')
        
        if not session_id or not student_id:
            return jsonify({'success': False, 'message': 'Thiếu dữ liệu'})
        
        conn = get_db_connection()
        
        # Find student by student_id and session's class
        student = conn.execute('''
            SELECT s.id, s.student_id, s.full_name
            FROM students s
            JOIN attendance_sessions ast ON s.class_id = ast.class_id
            WHERE s.student_id = ? AND ast.id = ?
        ''', (student_id, session_id)).fetchone()
        
        if not student:
            conn.close()
            return jsonify({'success': False, 'message': 'Không tìm thấy sinh viên trong lớp này'})
        
        # Check if already attended
        existing = conn.execute('''
            SELECT id FROM attendance_records 
            WHERE session_id = ? AND student_id = ?
        ''', (session_id, student['id'])).fetchone()
        
        if existing:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'{student["full_name"]} đã điểm danh rồi!'
            })
        
        # Record attendance
        conn.execute('''
            INSERT INTO attendance_records (session_id, student_id, status, method)
            VALUES (?, ?, 'present', 'manual')
        ''', (session_id, student['id']))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Điểm danh thành công cho {student["full_name"]}',
            'student': {
                'id': student['student_id'],
                'name': student['full_name']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@attendance_bp.route('/sessions/<int:session_id>/delete', methods=['POST'])
def delete_session(session_id):
    """Xóa ca điểm danh"""
    conn = get_db_connection()
    
    # Xóa các bản ghi điểm danh trước
    conn.execute('DELETE FROM attendance_records WHERE session_id = ?', (session_id,))
    
    # Xóa ca điểm danh
    conn.execute('DELETE FROM attendance_sessions WHERE id = ?', (session_id,))
    conn.commit()
    conn.close()
    
    flash('Xóa ca điểm danh thành công!', 'success')
    return redirect(url_for('attendance.list_sessions'))

@attendance_bp.route('/api/active_sessions')
def api_active_sessions():
    """API lấy danh sách ca điểm danh đang hoạt động"""
    conn = get_db_connection()
    
    # Lấy ca điểm danh của ngày hôm nay
    today = datetime.now().strftime('%Y-%m-%d')
    sessions = conn.execute('''
        SELECT ast.id, ast.session_name, ast.session_date, ast.start_time,
               s.subject_name, c.class_name
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        WHERE ast.session_date = ? AND ast.status = 'active'
        ORDER BY ast.start_time
    ''', (today,)).fetchall()
    
    conn.close()
    return jsonify([dict(row) for row in sessions])

@attendance_bp.route('/api/session_attendance/<int:session_id>')
def api_session_attendance(session_id):
    """API lấy danh sách điểm danh của ca"""
    conn = get_db_connection()
    
    attendance = conn.execute('''
        SELECT ar.attendance_time, ar.method,
               s.student_id, s.full_name
        FROM attendance_records ar
        JOIN students s ON ar.student_id = s.id
        WHERE ar.session_id = ?
        ORDER BY ar.attendance_time DESC
    ''', (session_id,)).fetchall()
    
    conn.close()
    return jsonify([dict(row) for row in attendance])
