from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from models.database import get_db_connection, import_students_from_excel, create_excel_template
import os
import cv2
import numpy as np
from PIL import Image
from werkzeug.utils import secure_filename
import json
from functools import wraps

# Import login_required decorator từ app.py
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        if not session.get('logged_in'):
            flash('Vui lòng đăng nhập để truy cập!', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


students_bp = Blueprint('students', __name__)

# =========================
# EXPORT ATTENDANCE EXCEL
# =========================
@students_bp.route('/export_attendance_excel')
def export_attendance_excel():
    """Xuất file Excel điểm danh cho lớp theo môn học"""
    import pandas as pd
    from flask import send_file
    from datetime import datetime
    
    class_id = request.args.get('class_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    
    if not class_id:
        flash('Thiếu thông tin lớp!', 'error')
        return redirect(url_for('students.list_students'))
    
    conn = get_db_connection()
    
    # Lấy thông tin lớp
    class_info = conn.execute('SELECT * FROM classes WHERE id = ?', (class_id,)).fetchone()
    if not class_info:
        flash('Không tìm thấy lớp!', 'error')
        return redirect(url_for('students.list_students'))
    
    # Lấy danh sách sinh viên trong lớp
    students = conn.execute('''
        SELECT s.id, s.student_id, s.full_name
        FROM students s
        WHERE s.class_id = ?
        ORDER BY s.student_id
    ''', (class_id,)).fetchall()
    
    if not students:
        flash('Lớp này chưa có sinh viên!', 'error')
        return redirect(url_for('students.list_students'))
    
    # Query attendance sessions và records
    if subject_id:
        # Lấy thông tin môn học
        subject_info = conn.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,)).fetchone()
        subject_name = subject_info['subject_name'] if subject_info else 'Unknown'
        
        # Lấy các ca điểm danh của môn học cụ thể
        sessions = conn.execute('''
            SELECT id, session_date, session_name
            FROM attendance_sessions
            WHERE class_id = ? AND subject_id = ?
            ORDER BY session_date
        ''', (class_id, subject_id)).fetchall()
        
        # Lấy dữ liệu điểm danh với student_id (MSSV), không phải database ID
        attendance_data = conn.execute('''
            SELECT s.student_id as student_code, ast.session_date, ar.status
            FROM attendance_records ar
            JOIN attendance_sessions ast ON ar.session_id = ast.id
            JOIN students s ON ar.student_id = s.id
            WHERE ast.class_id = ? AND ast.subject_id = ?
        ''', (class_id, subject_id)).fetchall()
        
        filename_suffix = f"{class_info['class_code']}_{subject_info['subject_code']}" if subject_info else class_info['class_code']
    else:
        # Lấy tất cả các ca điểm danh của lớp
        sessions = conn.execute('''
            SELECT ast.id, ast.session_date, ast.session_name, s.subject_name
            FROM attendance_sessions ast
            JOIN subjects s ON ast.subject_id = s.id
            WHERE ast.class_id = ?
            ORDER BY ast.session_date
        ''', (class_id,)).fetchall()
        
        # Lấy tất cả dữ liệu điểm danh với student_id (MSSV), không phải database ID
        attendance_data = conn.execute('''
            SELECT s.student_id as student_code, ast.session_date, ar.status
            FROM attendance_records ar
            JOIN attendance_sessions ast ON ar.session_id = ast.id
            JOIN students s ON ar.student_id = s.id
            WHERE ast.class_id = ?
        ''', (class_id,)).fetchall()
        
        subject_name = "Tất cả môn"
        filename_suffix = class_info['class_code']
    
    conn.close()
    
    # Tạo DataFrame cho sinh viên
    df_students = pd.DataFrame([{
        'MSSV': student['student_id'],
        'Họ và tên': student['full_name']
    } for student in students])
    
    # Tạo dictionary để mapping attendance data
    attendance_dict = {}
    for record in attendance_data:
        key = (record['student_code'], record['session_date'])
        attendance_dict[key] = 'Có mặt' if record['status'] == 'present' else 'Vắng'
    
    # Tạo các cột ngày từ sessions
    session_dates = sorted(set([session['session_date'] for session in sessions]))
    
    # Thêm cột điểm danh cho từng ngày
    for session_date in session_dates:
        column_name = f"Ngày {datetime.strptime(session_date, '%Y-%m-%d').strftime('%d/%m/%Y')}"
        df_students[column_name] = df_students['MSSV'].apply(
            lambda mssv: attendance_dict.get((mssv, session_date), 'Vắng')
        )
    
    # Thống kê tổng
    if session_dates:
        attendance_columns = [f"Ngày {datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')}" for date in session_dates]
        df_students['Tổng có mặt'] = df_students[attendance_columns].apply(
            lambda row: sum(1 for val in row if val == 'Có mặt'), axis=1
        )
        df_students['Tổng vắng'] = df_students[attendance_columns].apply(
            lambda row: sum(1 for val in row if val == 'Vắng'), axis=1
        )
        df_students['Tỷ lệ có mặt (%)'] = (df_students['Tổng có mặt'] / len(session_dates) * 100).round(1)
    
    # Tạo file Excel với tên file format: MaLop - Mon - Ngay
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    if subject_id and subject_info:
        filename = f"{class_info['class_code']} - {subject_info['subject_code']} - {current_date}.xlsx"
    else:
        filename = f"{class_info['class_code']} - TatCa - {current_date}.xlsx"
    
    file_path = f'exports/{filename}'
    
    # Đảm bảo thư mục exports tồn tại
    os.makedirs('exports', exist_ok=True)
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        # Sheet 1: Dữ liệu điểm danh
        df_students.to_excel(writer, sheet_name='Điểm danh', index=False)
        
        # Sheet 2: Thống kê tổng quan
        summary_data = {
            'Thông tin': [
                'Lớp học',
                'Môn học', 
                'Tổng số sinh viên',
                'Tổng số buổi học',
                'Ngày xuất báo cáo'
            ],
            'Giá trị': [
                f"{class_info['class_name']} ({class_info['class_code']})",
                subject_name,
                len(students),
                len(session_dates),
                datetime.now().strftime('%d/%m/%Y %H:%M')
            ]
        }
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Thông tin', index=False)
        
        # Format Excel
        workbook = writer.book
        worksheet = writer.sheets['Điểm danh']
        
        # Auto-fit columns
        for column in worksheet.columns:
            max_length = 0
            column_name = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_name].width = adjusted_width
    
    return send_file(file_path, as_attachment=True, download_name=filename)

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
    """Danh sách sinh viên, hỗ trợ lọc theo class_id (query string)"""
    conn = get_db_connection()
    class_id = request.args.get('class_id', type=int)
    class_info = None
    if class_id:
        students = conn.execute('''
            SELECT s.*, c.class_name, c.class_code
            FROM students s
            JOIN classes c ON s.class_id = c.id
            WHERE s.class_id = ?
            ORDER BY s.created_at DESC
        ''', (class_id,)).fetchall()
        class_info = conn.execute('SELECT * FROM classes WHERE id = ?', (class_id,)).fetchone()
    else:
        students = conn.execute('''
            SELECT s.*, c.class_name, c.class_code
            FROM students s
            JOIN classes c ON s.class_id = c.id
            ORDER BY s.created_at DESC
        ''').fetchall()
    conn.close()
    return render_template('students/list.html', students=students, class_info=class_info)

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

@students_bp.route('/by_class/<int:class_id>')
def list_students_by_class(class_id):
    """Danh sách sinh viên theo lớp"""
    conn = get_db_connection()
    students = conn.execute('''
        SELECT s.*, c.class_name, c.class_code
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.class_id = ?
        ORDER BY s.created_at DESC
    ''', (class_id,)).fetchall()
    class_info = conn.execute('SELECT * FROM classes WHERE id = ?', (class_id,)).fetchone()
    conn.close()
    return render_template('students/list.html', students=students, class_info=class_info)

# API endpoint để lấy môn học theo lớp cho modal export
@students_bp.route('/api/subjects_by_class/<int:class_id>')
def api_subjects_by_class(class_id):
    """API lấy danh sách môn học có ca điểm danh cho lớp này"""
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

# =========================
# IMPORT STUDENTS FROM EXCEL
# =========================
@students_bp.route('/import_excel', methods=['GET', 'POST'])
@login_required
def import_excel():
    """Import sinh viên từ file Excel"""
    if request.method == 'GET':
        # Hiển thị form upload
        conn = get_db_connection()
        classes = conn.execute('SELECT * FROM classes ORDER BY class_name').fetchall()
        conn.close()
        return render_template('students/import_excel.html', classes=classes)
    
    # Xử lý POST request
    if 'excel_file' not in request.files:
        flash('Không có file được chọn!', 'error')
        return redirect(request.url)
    
    file = request.files['excel_file']
    class_id = request.form.get('class_id', type=int)
    
    if file.filename == '':
        flash('Không có file được chọn!', 'error')
        return redirect(request.url)
    
    if not class_id:
        flash('Vui lòng chọn lớp học!', 'error')
        return redirect(request.url)
    
    if file and file.filename.lower().endswith(('.xlsx', '.xls')):
        try:
            # Lưu file tạm thời
            filename = secure_filename(file.filename)
            temp_path = os.path.join('uploads', 'temp_' + filename)
            
            # Tạo thư mục nếu chưa có
            os.makedirs('uploads', exist_ok=True)
            
            file.save(temp_path)
            
            # Import sinh viên
            result = import_students_from_excel(temp_path, class_id)
            
            # Xóa file tạm
            os.remove(temp_path)
            
            if result['success']:
                flash(result['message'], 'success')
                if result['errors']:
                    flash(f"Có {len(result['errors'])} lỗi: {'; '.join(result['errors'][:3])}", 'warning')
            else:
                flash(result['message'], 'error')
                
        except Exception as e:
            flash(f'Lỗi xử lý file: {str(e)}', 'error')
    else:
        flash('Chỉ chấp nhận file Excel (.xlsx, .xls)!', 'error')
    
    return redirect(url_for('students.list_students'))

@students_bp.route('/download_template')
@login_required
def download_template():
    """Tải template Excel mẫu"""
    try:
        template_path = create_excel_template()
        return send_file(
            template_path,
            as_attachment=True,
            download_name='template_students.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Lỗi tạo template: {str(e)}', 'error')
        return redirect(url_for('students.list_students'))
