from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models.database import get_db_connection
import cv2
import numpy as np
import base64
import io
from PIL import Image
import json
from datetime import datetime
from auto_attendance_server import create_auto_attendance_session, stop_auto_attendance_session, get_active_sessions
import webbrowser
import threading
import time

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
    """API nhận diện khuôn mặt với AI model"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        image_data = data.get('image')
        
        if not session_id or not image_data:
            return jsonify({'success': False, 'message': 'Thiếu dữ liệu'})
        
        # Sử dụng AI model để nhận diện
        from models.advanced_face_model import face_model
        
        if not face_model.is_trained:
            return jsonify({'success': False, 'message': 'Model AI chưa được train'})
        
        # Nhận diện khuôn mặt - sử dụng ensemble=True để có kết quả tốt nhất
        recognition_result = face_model.recognize_face(image_data, use_ensemble=True)
        
        # Trả về kết quả chi tiết bao gồm cả những khuôn mặt không nhận diện được
        if recognition_result['success']:
            # Trả về tất cả kết quả, bao gồm cả những khuôn mặt không đạt ngưỡng
            all_faces = recognition_result.get('faces', [])
            
            # Thêm thông tin về những khuôn mặt được phát hiện nhưng không đạt ngưỡng
            # (model có thể detect nhưng confidence/quality thấp)
            detected_faces = []
            
            for face in all_faces:
                # Chỉ thêm vào detected_faces những khuôn mặt có student_id (đã train)
                if face.get('student_id'):
                    detected_faces.append(face)
                else:
                    # Khuôn mặt phát hiện được nhưng không đủ điều kiện
                    # Tạo face record cho việc hiển thị debug info
                    detected_faces.append({
                        'student_id': None,
                        'name': 'Không nhận diện được',
                        'confidence': face.get('confidence', 0),
                        'quality_score': face.get('quality_score', 0),
                        'combined_score': face.get('combined_score', 0),
                        'quality_reasons': face.get('quality_reasons', []),
                        'position': face.get('position', {})
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
        
        # Lấy khuôn mặt có confidence cao nhất trong số những khuôn mặt được nhận diện
        valid_faces = [f for f in recognition_result.get('faces', []) if f.get('student_id')]
        
        if not valid_faces:
            return jsonify({
                'success': False, 
                'message': 'Không nhận diện được sinh viên nào có độ tin cậy đủ cao',
                'faces': recognition_result.get('faces', [])
            })
        
        best_face = max(valid_faces, key=lambda x: x.get('combined_score', x.get('confidence', 0)))
        
        # Kiểm tra combined score nếu có
        min_score = best_face.get('combined_score', best_face['confidence'])
        if min_score < 0.6:  # Giữ ngưỡng 0.6 như yêu cầu
            quality_info = ""
            if 'quality_score' in best_face:
                quality_info = f" (chất lượng: {best_face['quality_score']:.1%})"
            return jsonify({
                'success': False, 
                'message': f'Độ tin cậy thấp ({min_score:.1%}){quality_info}, không đủ tin cậy để điểm danh',
                'faces': recognition_result.get('faces', [])
            })
        
        student_id = best_face['student_id']
        
        # Get session info và kiểm tra sinh viên có trong lớp không
        conn = get_db_connection()
        session_info = conn.execute('''
            SELECT class_id FROM attendance_sessions WHERE id = ?
        ''', (session_id,)).fetchone()
        
        student = conn.execute('''
            SELECT id, student_id, full_name 
            FROM students 
            WHERE student_id = ? AND class_id = ?
        ''', (student_id, session_info['class_id'])).fetchone()
        
        if not student:
            conn.close()
            return jsonify({'success': False, 'message': f'Sinh viên {student_id} không thuộc lớp này'})
        
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
        final_confidence = best_face.get('combined_score', best_face['confidence'])
        conn.execute('''
            INSERT INTO attendance_records (session_id, student_id, status, method, confidence)
            VALUES (?, ?, 'present', 'face_recognition', ?)
        ''', (session_id, student['id'], final_confidence * 100))
        conn.commit()
        conn.close()
        
        # Tạo message chi tiết
        quality_info = ""
        if 'quality_score' in best_face:
            quality_info = f" - Chất lượng: {best_face['quality_score']:.1%}"
        
        return jsonify({
            'success': True,
            'message': f'Điểm danh thành công cho {student["full_name"]} (Độ tin cậy: {final_confidence:.1%}){quality_info}',
            'student': {
                'id': student['student_id'],
                'name': student['full_name'],
                'confidence': best_face['confidence'] * 100
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

@attendance_bp.route('/camera')
def camera():
    """Trang điểm danh bằng camera"""
    return render_template('camera.html')

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
    
    # Lấy thông tin từ database
    conn = get_db_connection()
    session_data = {}
    
    for port, status in active_sessions.items():
        session_id = status['session_id']
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
    
    conn.close()
    
    return render_template('attendance/auto_session_manager.html', sessions=session_data)

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
