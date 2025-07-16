"""
Routes cho chức năng điểm danh
Bao gồm: Quản lý ca điểm danh, Điểm danh thủ công, Điểm danh AI, Điểm danh tự động
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models.database import get_db_connection
import cv2
import numpy as np
import base64
import io
import os
from PIL import Image
import json
from datetime import datetime
from auto_attendance_server import create_auto_attendance_session, stop_auto_attendance_session, get_active_sessions
import webbrowser
import threading
import time
import pickle

attendance_bp = Blueprint('attendance', __name__)

# ================================
# 1. QUẢN LÝ CA ĐIỂM DANH
# ================================

@attendance_bp.route('/sessions')
def list_sessions():
    """Danh sách ca điểm danh, chia thành đang hoạt động và đã ngưng hoạt động"""
    conn = get_db_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    # Ca đang hoạt động: end_time chưa có hoặc lớn hơn hiện tại
    active_sessions = conn.execute('''
        SELECT ast.*, s.subject_name, s.subject_code, c.class_name, c.class_code,
               COUNT(ar.id) as attendance_count
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        LEFT JOIN attendance_records ar ON ast.id = ar.session_id
        WHERE (ast.end_time IS NULL OR (ast.session_date || ' ' || ast.end_time) > ?)
        GROUP BY ast.id
        ORDER BY ast.session_date DESC, ast.start_time DESC
    ''', (now,)).fetchall()
    # Ca đã ngưng hoạt động: end_time nhỏ hơn hiện tại
    inactive_sessions = conn.execute('''
        SELECT ast.*, s.subject_name, s.subject_code, c.class_name, c.class_code,
               COUNT(ar.id) as attendance_count
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        LEFT JOIN attendance_records ar ON ast.id = ar.session_id
        WHERE (ast.end_time IS NOT NULL AND (ast.session_date || ' ' || ast.end_time) <= ?)
        GROUP BY ast.id
        ORDER BY ast.session_date DESC, ast.start_time DESC
    ''', (now,)).fetchall()
    conn.close()
    return render_template('attendance/sessions.html', active_sessions=active_sessions, inactive_sessions=inactive_sessions)

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

@attendance_bp.route('/sessions/<int:session_id>/edit', methods=['GET', 'POST'])
def edit_session(session_id):
    """Sửa ca điểm danh"""
    conn = get_db_connection()
    session = conn.execute('SELECT * FROM attendance_sessions WHERE id = ?', (session_id,)).fetchone()
    if not session:
        flash('Không tìm thấy ca điểm danh!', 'error')
        conn.close()
        return redirect(url_for('attendance.list_sessions'))

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
                UPDATE attendance_sessions
                SET session_name=?, subject_id=?, class_id=?, session_date=?, start_time=?, end_time=?
                WHERE id=?
            ''', (session_name, subject_id, class_id, session_date, start_time, end_time, session_id))
            conn.commit()
            flash('Cập nhật ca điểm danh thành công!', 'success')
            conn.close()
            return redirect(url_for('attendance.list_sessions'))
    # Lấy danh sách môn học và lớp
    subjects = conn.execute('SELECT id, subject_code, subject_name FROM subjects ORDER BY subject_name').fetchall()
    classes = conn.execute('SELECT id, class_code, class_name FROM classes ORDER BY class_name').fetchall()
    conn.close()
    return render_template('attendance/edit_session.html', session=session, subjects=subjects, classes=classes)

# ================================
# 2. ĐIỂM DANH BẰNG NHẬN DIỆN AI
# ================================

@attendance_bp.route('/collect_face_data/<int:student_id>')
def collect_face_data(student_id):
    """Trang thu thập dữ liệu khuôn mặt cho sinh viên"""
    conn = get_db_connection()
    
    student = conn.execute('''
        SELECT s.*, c.class_name, c.class_code
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.id = ?
    ''', (student_id,)).fetchone()
    
    if not student:
        flash('Không tìm thấy sinh viên!', 'error')
        return redirect(url_for('students.list_students'))
    
    conn.close()
    return render_template('students/collect_face_data.html', student=student)

@attendance_bp.route('/api/capture_face', methods=['POST'])
def capture_face():
    """API thu thập và lưu dữ liệu khuôn mặt với xử lý ảnh cao cấp"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        image_data = data.get('image')
        
        if not student_id or not image_data:
            return jsonify({'success': False, 'message': 'Thiếu dữ liệu'})
        
        # Decode base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'success': False, 'message': 'Không thể đọc ảnh'})
        
        # Get student info
        conn = get_db_connection()
        student = conn.execute('SELECT student_id FROM students WHERE id = ?', (student_id,)).fetchone()
        conn.close()
        
        if not student:
            return jsonify({'success': False, 'message': 'Không tìm thấy sinh viên'})
        
        student_code = student['student_id']
        
        # Create directory if not exists
        import os
        face_dir = os.path.join('uploads', 'faces', student_code)
        os.makedirs(face_dir, exist_ok=True)
        
        # Count existing images và kiểm tra giới hạn
        existing_files = [f for f in os.listdir(face_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        current_count = len(existing_files)
        max_images = 40  # Giới hạn 40 ảnh
        
        # Kiểm tra đã đủ 40 ảnh chưa
        if current_count >= max_images:
            return jsonify({
                'success': False, 
                'message': f'Đã đủ {max_images} ảnh cho sinh viên này! Không thể thu thập thêm.',
                'current_count': current_count,
                'max_allowed': max_images,
                'action': 'complete'
            })
        
        next_number = current_count + 1
        
        # Generate filename đơn giản: 1.jpg, 2.jpg, ..., 40.jpg
        filename = f"{next_number}.jpg"
        filepath = os.path.join(face_dir, filename)
        
        # ========== XỬ LÝ ẢNH ĐỂ KHÔI TỰ NHIÊN - GIẢM BIẾN DẠNG ==========
        
        # 1. Convert sang grayscale nhẹ nhàng
        gray_original = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Chỉ cân bằng độ sáng nhẹ nếu cần thiết
        # Kiểm tra độ sáng trung bình trước
        mean_brightness = np.mean(gray_original)
        
        if mean_brightness < 80:
            # Ảnh quá tối - cần cải thiện
            gray_enhanced = cv2.equalizeHist(gray_original)
        elif mean_brightness > 180:
            # Ảnh quá sáng - giảm độ sáng nhẹ
            gray_enhanced = cv2.convertScaleAbs(gray_original, alpha=0.8, beta=0)
        else:
            # Ảnh đã ổn - giữ nguyên
            gray_enhanced = gray_original.copy()
        
        # 3. Detect face với tham số cơ bản
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Chỉ sử dụng 1 phương pháp detect đơn giản
        faces = face_cascade.detectMultiScale(
            gray_enhanced, 
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
            maxSize=(400, 400)
        )
        
        if len(faces) == 0:
            # Thử lại với tham số dễ hơn
            faces = face_cascade.detectMultiScale(
                gray_enhanced, 
                scaleFactor=1.05,
                minNeighbors=4,
                minSize=(60, 60),
                maxSize=(500, 500)
            )
        
        if len(faces) == 0:
            return jsonify({'success': False, 'message': 'Không phát hiện khuôn mặt trong ảnh. Vui lòng đảm bảo khuôn mặt rõ nét, đủ sáng và nhìn thẳng camera.'})
        
        if len(faces) > 1:
            return jsonify({'success': False, 'message': f'Phát hiện {len(faces)} khuôn mặt, vui lòng chỉ có 1 người trong ảnh'})
        
        # 4. Lấy khuôn mặt duy nhất
        x, y, w, h = faces[0]
        
        # 5. Crop với padding vừa phải
        padding_ratio = 0.1  # Giảm padding để tự nhiên hơn
        padding_x = int(w * padding_ratio)
        padding_y = int(h * padding_ratio)
        
        x_start = max(0, x - padding_x)
        y_start = max(0, y - padding_y)
        x_end = min(gray_enhanced.shape[1], x + w + padding_x)
        y_end = min(gray_enhanced.shape[0], y + h + padding_y)
        
        # Crop từ ảnh đã xử lý nhẹ
        face_gray = gray_enhanced[y_start:y_end, x_start:x_end]
        
        if face_gray.size == 0:
            return jsonify({'success': False, 'message': 'Lỗi khi crop khuôn mặt'})
        
        # 6. Kiểm tra chất lượng ảnh cơ bản
        blur_score = cv2.Laplacian(face_gray, cv2.CV_64F).var()
        if blur_score < 50:  # Giảm threshold để dễ dàng hơn
            return jsonify({'success': False, 'message': f'Ảnh bị mờ (điểm: {blur_score:.0f}), vui lòng chụp lại rõ nét hơn'})
        
        # 7. Resize về kích thước chuẩn TỰ NHIÊN
        target_size = 128
        
        # Make square một cách nhẹ nhàng
        height, width = face_gray.shape
        if width != height:
            max_dim = max(width, height)
            delta_w = max_dim - width
            delta_h = max_dim - height
            top, bottom = delta_h // 2, delta_h - (delta_h // 2)
            left, right = delta_w // 2, delta_w - (delta_w // 2)
            
            # Pad với giá trị trung bình để tự nhiên
            mean_val = np.mean(face_gray)
            face_gray = cv2.copyMakeBorder(face_gray, top, bottom, left, right, 
                                         cv2.BORDER_CONSTANT, value=mean_val)
        
        # Resize với chất lượng cao nhưng không quá mịn
        face_resized = cv2.resize(face_gray, (target_size, target_size), 
                                interpolation=cv2.INTER_AREA)  # Đổi từ LANCZOS4 sang AREA để tự nhiên hơn
        
        # 8. XỬ LÝ TỐI THIỂU ĐỂ TRÁNH BIẾN DẠNG
        # Chỉ làm 1 bước đơn giản: cân bằng độ sáng nhẹ nếu cần
        final_brightness = np.mean(face_resized)
        
        if final_brightness < 60:
            # Quá tối - tăng độ sáng nhẹ
            face_final = cv2.convertScaleAbs(face_resized, alpha=1.2, beta=20)
        elif final_brightness > 200:
            # Quá sáng - giảm độ sáng nhẹ  
            face_final = cv2.convertScaleAbs(face_resized, alpha=0.8, beta=-10)
        else:
            # Đã ổn - giữ nguyên hoàn toàn
            face_final = face_resized.copy()
        
        # 9. Kiểm tra brightness cuối cùng
        mean_brightness = np.mean(face_final)
        if mean_brightness < 30:
            return jsonify({'success': False, 'message': f'Ảnh quá tối (độ sáng: {mean_brightness:.0f}), vui lòng chụp ở nơi sáng hơn'})
        elif mean_brightness > 230:
            return jsonify({'success': False, 'message': f'Ảnh quá sáng (độ sáng: {mean_brightness:.0f}), vui lòng tránh ánh sáng trực tiếp'})
        
        # 10. Lưu ảnh tự nhiên
        cv2.imwrite(filepath, face_final, [cv2.IMWRITE_JPEG_QUALITY, 95])  # Giảm chất lượng để tự nhiên hơn
        
        # Kiểm tra xem đã đủ 40 ảnh chưa
        remaining = max_images - next_number
        is_complete = next_number >= max_images
        
        if is_complete:
            message = f'🎉 HOÀN THÀNH! Đã thu thập đủ {max_images} ảnh chất lượng cao'
            action = 'complete'
        else:
            message = f'✅ Đã lưu ảnh {next_number}/{max_images} - Còn {remaining} ảnh'
            action = 'continue'
        
        return jsonify({
            'success': True, 
            'message': message,
            'filename': filename,
            'total_images': next_number,
            'max_images': max_images,
            'remaining': remaining,
            'is_complete': is_complete,
            'action': action,
            'progress_percent': round((next_number / max_images) * 100, 1),
            'quality_info': {
                'blur_score': round(blur_score, 1),
                'brightness': round(mean_brightness, 1),
                'original_face_size': f"{w}x{h}",
                'processed_size': f"{target_size}x{target_size}",
                'format': 'Grayscale tự nhiên - giảm biến dạng',
                'enhancements': 'Chỉ cân bằng độ sáng nhẹ khi cần thiết'
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@attendance_bp.route('/api/train_model', methods=['POST'])
def train_model():
    """API train model - Sử dụng hàm thống nhất từ ai.py"""
    try:
        # Import hàm train từ ai.py để tránh duplicate code
        from routes.ai import train_simple_model
        
        # Gọi hàm train chính
        result = train_simple_model()
        
        # Trả về JSON response
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi training: {str(e)}'})

@attendance_bp.route('/api/recognize_simple', methods=['POST'])
def recognize_simple():
    """API nhận diện khuôn mặt đơn giản - Sử dụng hàm thống nhất từ utils"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu ảnh'})
        
        # Sử dụng hàm nhận diện thống nhất từ utils
        from utils.face_recognition_utils import recognize_face_from_image
        
        # Nhận diện với confidence threshold phù hợp thực tế (110) - cao hơn mức 85-95 để đảm bảo chính xác
        recognition_result = recognize_face_from_image(image_data, confidence_threshold=110)
        
        # Trả về kết quả nhận diện với format tương thích
        if recognition_result['success']:
            faces = recognition_result.get('faces', [])
            
            # Chuyển đổi format để tương thích với frontend cũ
            recognized_faces = []
            for face in faces:
                if face['status'] == 'recognized':
                    recognized_faces.append({
                        'student_id': face['mssv'],
                        'confidence': face['confidence'],
                        'bbox': {'x': int(face['bbox']['x']), 'y': int(face['bbox']['y']), 
                                'w': int(face['bbox']['w']), 'h': int(face['bbox']['h'])}
                    })
                else:
                    recognized_faces.append({
                        'student_id': 'Unknown',
                        'confidence': face['confidence'],
                        'bbox': {'x': int(face['bbox']['x']), 'y': int(face['bbox']['y']), 
                                'w': int(face['bbox']['w']), 'h': int(face['bbox']['h'])}
                    })
            
            return jsonify({
                'success': True,
                'message': f'Nhận diện {len(recognized_faces)} khuôn mặt',
                'faces': recognized_faces,
                'total_faces': len(faces)
            })
        else:
            return jsonify({
                'success': False, 
                'message': recognition_result.get('message', 'Không nhận diện được khuôn mặt'),
                'faces': [],
                'total_faces': 0
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi nhận diện: {str(e)}'})

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

@attendance_bp.route('/face_recognition')
def face_recognition():
    """Trang chọn ca điểm danh để nhận diện khuôn mặt"""
    conn = get_db_connection()
    
    # Lấy các ca điểm danh đang hoạt động hoặc gần đây
    sessions = conn.execute('''
        SELECT ast.*, s.subject_name, s.subject_code, c.class_name, c.class_code
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        WHERE ast.session_date >= date('now', '-7 days')
        ORDER BY ast.session_date DESC, ast.start_time DESC
        LIMIT 20
    ''').fetchall()
    
    conn.close()
    return render_template('attendance/face_recognition_select.html', sessions=sessions)

@attendance_bp.route('/api/recognize_face', methods=['POST'])
def recognize_face():
    """API nhận diện khuôn mặt với hàm thống nhất"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        image_data = data.get('image')
        
        if not session_id or not image_data:
            return jsonify({'success': False, 'message': 'Thiếu dữ liệu'})
        
        # Sử dụng hàm nhận diện thống nhất
        from utils.face_recognition_utils import recognize_face_from_image
        
        # Nhận diện khuôn mặt với ngưỡng cân bằng (100) - phù hợp với thực tế confidence 85-95
        recognition_result = recognize_face_from_image(image_data, confidence_threshold=100)
        
        # Trả về kết quả nhận diện
        if recognition_result['success']:
            faces = recognition_result.get('faces', [])
            
            # Chuyển đổi format cho frontend
            detected_faces = []
            for face in faces:
                if face['status'] == 'recognized':
                    detected_faces.append({
                        'student_id': face['mssv'],
                        'name': face['mssv'],  # Có thể lookup tên từ DB
                        'confidence': face['confidence'],
                        'position': face['bbox'],
                        'status': 'recognized'
                    })
                else:
                    detected_faces.append({
                        'student_id': None,
                        'name': 'Không nhận diện được',
                        'confidence': face['confidence'],
                        'position': face['bbox'],
                        'status': face['status']
                    })
            
            return jsonify({
                'success': True,
                'faces': detected_faces,
                'message': recognition_result.get('message', 'Nhận diện hoàn tất')
            })
        else:
            return jsonify({
                'success': False, 
                'message': recognition_result.get('message', 'Không nhận diện được khuôn mặt'),
                'faces': []
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})


@attendance_bp.route('/api/mark_attendance', methods=['POST'])
def mark_attendance_api():
    """API điểm danh với hàm thống nhất"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        image_data = data.get('image')
        
        if not session_id or not image_data:
            return jsonify({'success': False, 'message': 'Thiếu dữ liệu'})
        
        # Lấy thông tin session
        conn = get_db_connection()
        session = conn.execute('''
            SELECT subject_id, class_id FROM attendance_sessions WHERE id = ?
        ''', (session_id,)).fetchone()
        conn.close()
        
        if not session:
            return jsonify({'success': False, 'message': 'Không tìm thấy ca điểm danh'})
        
        # Sử dụng hàm nhận diện và điểm danh thống nhất
        from utils.face_recognition_utils import recognize_and_mark_attendance
        
        result = recognize_and_mark_attendance(
            image_data=image_data,
            subject_id=session['subject_id'],
            session_id=session_id,
            confidence_threshold=98  # Giảm để dễ điểm danh hơn với thực tế 85-95
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})


# ================================
# DEBUG & TESTING
# ================================

@attendance_bp.route('/api/debug_recognition', methods=['POST'])
def debug_recognition():
    """API debug để kiểm tra nhận diện khuôn mặt"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        debug_mode = data.get('debug', False)
        
        if not image_data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu ảnh'})
        
        # Kiểm tra model có tồn tại không
        model_info = {}
        trainer_path = os.path.join('uploads', 'trainer.yml')
        labels_path = os.path.join('uploads', 'labels.pickle')
        
        model_info['trainer_exists'] = os.path.exists(trainer_path)
        model_info['labels_exists'] = os.path.exists(labels_path)
        
        if model_info['trainer_exists'] and model_info['labels_exists']:
            # Load labels để xem có bao nhiêu sinh viên
            try:
                with open(labels_path, 'rb') as f:
                    labels = pickle.load(f)
                model_info['total_students'] = len(labels)
                model_info['student_list'] = list(labels.keys())
            except Exception as e:
                model_info['load_error'] = str(e)
        
        # Thử nhận diện với các ngưỡng phù hợp thực tế (confidence thường 85-95)
        results = {}
        thresholds = [90, 95, 100, 105, 110, 120]  # Tập trung vào vùng thực tế
        
        for threshold in thresholds:
            try:
                from utils.face_recognition_utils import recognize_face_from_image
                result = recognize_face_from_image(image_data, confidence_threshold=threshold)
                results[f'threshold_{threshold}'] = {
                    'success': result['success'],
                    'faces_count': len(result.get('faces', [])),
                    'recognized_count': len([f for f in result.get('faces', []) if f.get('status') == 'recognized']),
                    'faces': result.get('faces', [])[:3],  # Chỉ lấy 3 face đầu để tránh quá dài
                    'message': result.get('message', '')
                }
            except Exception as e:
                results[f'threshold_{threshold}'] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'model_info': model_info,
            'recognition_results': results,
            'message': 'Debug hoàn tất'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi debug: {str(e)}'})

@attendance_bp.route('/api/model_info', methods=['GET'])
def get_model_info():
    """API lấy thông tin model"""
    try:
        info = {}
        
        # Kiểm tra files model
        trainer_path = os.path.join('uploads', 'trainer.yml')
        labels_path = os.path.join('uploads', 'labels.pickle')
        faces_dir = os.path.join('uploads', 'faces')
        
        info['trainer_exists'] = os.path.exists(trainer_path)
        info['labels_exists'] = os.path.exists(labels_path)
        info['faces_dir_exists'] = os.path.exists(faces_dir)
        
        if info['trainer_exists']:
            info['trainer_size'] = os.path.getsize(trainer_path)
            info['trainer_modified'] = datetime.fromtimestamp(os.path.getmtime(trainer_path)).strftime('%Y-%m-%d %H:%M:%S')
        
        if info['labels_exists']:
            try:
                with open(labels_path, 'rb') as f:
                    labels = pickle.load(f)
                info['total_students'] = len(labels)
                info['student_list'] = list(labels.keys())
            except Exception as e:
                info['labels_error'] = str(e)
        
        if info['faces_dir_exists']:
            students = []
            for student_dir in os.listdir(faces_dir):
                student_path = os.path.join(faces_dir, student_dir)
                if os.path.isdir(student_path):
                    image_count = len([f for f in os.listdir(student_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                    students.append({
                        'student_id': student_dir,
                        'image_count': image_count
                    })
            info['training_data'] = students
            info['total_training_students'] = len(students)
        
        return jsonify({
            'success': True,
            'model_info': info,
            'message': 'Thông tin model'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})


# ================================
# 3. ĐIỂM DANH THỦ CÔNG
# ================================

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

@attendance_bp.route('/camera')
def camera():
    """Trang điểm danh bằng camera"""
    return render_template('camera.html')

# ================================
# 4. ĐIỂM DANH TỰ ĐỘNG
# ================================

@attendance_bp.route('/sessions/create_auto', methods=['GET', 'POST'])
def create_auto_session():
    """Tạo ca điểm danh tự động"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        session_name = request.form.get('session_name')
        subject_id = request.form.get('subject_id')
        class_id = request.form.get('class_id')
        session_date = request.form.get('session_date', datetime.now().strftime('%Y-%m-%d'))
        start_time = request.form.get('start_time', datetime.now().strftime('%H:%M'))
        
        if not all([session_name, subject_id, class_id]):
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
        else:
            try:
                # Tạo session trong database
                cursor = conn.execute('''
                    INSERT INTO attendance_sessions (session_name, subject_id, class_id, session_date, start_time, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session_name, subject_id, class_id, session_date, start_time, 'active'))
                
                session_id = cursor.lastrowid
                conn.commit()
                
                # Tạo auto attendance server
                port = create_auto_attendance_session(session_id)
                
                if port:
                    # Cập nhật port vào database
                    conn.execute('''
                        UPDATE attendance_sessions SET port = ? WHERE id = ?
                    ''', (port, session_id))
                    conn.commit()
                    
                    flash(f'🎉 Tạo ca điểm danh tự động thành công!', 'success')
                    flash(f'🌐 Server đang chạy trên port: {port}', 'info')
                    flash(f'🔗 Truy cập: http://localhost:{port}', 'info')
                    
                    # Mở browser tự động
                    def open_browser():
                        import time
                        time.sleep(2)  # Đợi server khởi động hoàn toàn
                        webbrowser.open(f'http://localhost:{port}')
                    
                    threading.Timer(1.0, open_browser).start()
                    
                    return redirect(url_for('attendance.auto_session_manager'))
                else:
                    flash('❌ Không thể tạo server điểm danh tự động! Vui lòng thử lại.', 'error')
                    flash('💡 Kiểm tra: Camera có hoạt động? Model AI đã được train?', 'warning')
                    
            except Exception as e:
                flash(f'Lỗi tạo ca điểm danh: {str(e)}', 'error')
    
    # Lấy danh sách môn học và lớp
    subjects = conn.execute('SELECT id, subject_code, subject_name FROM subjects ORDER BY subject_name').fetchall()
    classes = conn.execute('SELECT id, class_code, class_name FROM classes ORDER BY class_name').fetchall()
    conn.close()
    
    return render_template('attendance/create_auto_session.html', subjects=subjects, classes=classes)

@attendance_bp.route('/auto_sessions')
def auto_session_manager():
    """Quản lý các ca điểm danh tự động"""
    # Lấy danh sách session đang hoạt động
    active_sessions = get_active_sessions()
    conn = get_db_connection()
    session_data = {}
    active_session_ids = set()
    for port, status in active_sessions.items():
        session_id = status['session_id']
        active_session_ids.add(session_id)
        session_info = conn.execute('''
            SELECT ast.*, s.subject_name, s.subject_code, c.class_name, c.class_code
            FROM attendance_sessions ast
            JOIN subjects s ON ast.subject_id = s.id
            JOIN classes c ON ast.class_id = c.id
            WHERE ast.id = ?
        ''', (session_id,)).fetchone()
        if session_info:
            session_data[port] = {
                'session_info': dict(session_info),
                'status': status,
                'url': f'http://localhost:{port}'
            }

    # Lấy tất cả ca điểm danh (bao gồm cả ca tự động và thủ công)
    all_sessions = conn.execute('''
        SELECT ast.*, s.subject_name, s.subject_code, c.class_name, c.class_code,
               (SELECT COUNT(*) FROM attendance_records ar WHERE ar.session_id = ast.id) as attendance_count
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        ORDER BY ast.session_date DESC, ast.start_time DESC
    ''').fetchall()
    conn.close()
    return render_template('attendance/auto_session_manager.html', sessions=session_data, inactive_sessions=all_sessions)

@attendance_bp.route('/auto_sessions/stop/<int:port>', methods=['POST'])
def stop_auto_session(port):
    """Dừng ca điểm danh tự động"""
    try:
        if stop_auto_attendance_session(port):
            # Cập nhật status trong database
            conn = get_db_connection()
            conn.execute('''
                UPDATE attendance_sessions SET status = 'completed' 
                WHERE port = ?
            ''', (port,))
            conn.commit()
            conn.close()
            
            flash('Đã dừng ca điểm danh tự động!', 'success')
        else:
            flash('Không thể dừng ca điểm danh!', 'error')
    except Exception as e:
        flash(f'Lỗi: {str(e)}', 'error')
    
    return redirect(url_for('attendance.auto_session_manager'))
