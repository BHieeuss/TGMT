from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from models.database import get_db_connection
import pandas as pd
import os
from datetime import datetime, timedelta

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
def reports_home():
    """Trang báo cáo chính"""
    return render_template('reports/index.html')

@reports_bp.route('/attendance')
def attendance_report():
    """Báo cáo điểm danh"""
    conn = get_db_connection()
    
    # Lấy danh sách lớp và môn học để filter
    classes = conn.execute('SELECT id, class_code, class_name FROM classes ORDER BY class_name').fetchall()
    subjects = conn.execute('SELECT id, subject_code, subject_name FROM subjects ORDER BY subject_name').fetchall()
    
    # Lấy parameters từ request
    class_id = request.args.get('class_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Build query với điều kiện filter
    query = '''
        SELECT ast.session_date, ast.session_name, ast.start_time,
               s.subject_name, c.class_name,
               st.student_id, st.full_name,
               ar.attendance_time, ar.status, ar.method,
               CASE WHEN ar.id IS NULL THEN 'absent' ELSE ar.status END as final_status
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        JOIN students st ON st.class_id = c.id
        LEFT JOIN attendance_records ar ON ar.session_id = ast.id AND ar.student_id = st.id
        WHERE 1=1
    '''
    
    params = []
    
    if class_id:
        query += ' AND c.id = ?'
        params.append(class_id)
    
    if subject_id:
        query += ' AND s.id = ?'
        params.append(subject_id)
    
    if start_date:
        query += ' AND ast.session_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND ast.session_date <= ?'
        params.append(end_date)
    
    query += ' ORDER BY ast.session_date DESC, ast.start_time DESC, st.full_name'
    
    records = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('reports/attendance.html', 
                         records=records, 
                         classes=classes, 
                         subjects=subjects,
                         filters={
                             'class_id': class_id,
                             'subject_id': subject_id,
                             'start_date': start_date,
                             'end_date': end_date
                         })

@reports_bp.route('/export_excel')
def export_excel():
    """Xuất báo cáo Excel"""
    conn = get_db_connection()
    
    # Lấy parameters từ request
    class_id = request.args.get('class_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Nếu không có end_date, sử dụng ngày hiện tại
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Nếu không có start_date, sử dụng 30 ngày trước
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Build query
    query = '''
        SELECT ast.session_date as "Ngày", 
               ast.session_name as "Ca học",
               ast.start_time as "Giờ bắt đầu",
               s.subject_code as "Mã môn", 
               s.subject_name as "Tên môn",
               c.class_code as "Mã lớp",
               c.class_name as "Tên lớp",
               st.student_id as "MSSV", 
               st.full_name as "Họ tên",
               CASE WHEN ar.id IS NULL THEN 'Vắng' 
                    WHEN ar.status = 'present' THEN 'Có mặt'
                    ELSE ar.status END as "Trạng thái",
               ar.attendance_time as "Thời gian điểm danh",
               CASE WHEN ar.method = 'face_recognition' THEN 'Nhận diện khuôn mặt'
                    WHEN ar.method = 'manual' THEN 'Thủ công'
                    ELSE ar.method END as "Phương thức"
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        JOIN classes c ON ast.class_id = c.id
        JOIN students st ON st.class_id = c.id
        LEFT JOIN attendance_records ar ON ar.session_id = ast.id AND ar.student_id = st.id
        WHERE ast.session_date BETWEEN ? AND ?
    '''
    
    params = [start_date, end_date]
    
    if class_id:
        query += ' AND c.id = ?'
        params.append(class_id)
    
    if subject_id:
        query += ' AND s.id = ?'
        params.append(subject_id)
    
    query += ' ORDER BY ast.session_date DESC, ast.start_time DESC, st.full_name'
    
    records = conn.execute(query, params).fetchall()
    
    # Convert to DataFrame
    df = pd.DataFrame([dict(row) for row in records])
    
    if df.empty:
        flash('Không có dữ liệu để xuất!', 'warning')
        return redirect(url_for('reports.attendance_report'))
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'BaoCaoDiemDanh_{start_date}_to_{end_date}_{timestamp}.xlsx'
    filepath = os.path.join(current_app.config['EXPORT_FOLDER'], filename)
    
    # Create Excel file with formatting
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Báo cáo điểm danh', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Báo cáo điểm danh']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    conn.close()
    
    return send_file(filepath, as_attachment=True, download_name=filename)

@reports_bp.route('/statistics')
def statistics():
    """Thống kê tổng quan"""
    conn = get_db_connection()
    
    # Thống kê theo lớp
    class_stats = conn.execute('''
        SELECT c.class_name, c.class_code,
               COUNT(DISTINCT s.id) as total_students,
               COUNT(DISTINCT ar.id) as total_attendance,
               COUNT(DISTINCT ast.id) as total_sessions
        FROM classes c
        LEFT JOIN students s ON c.id = s.class_id
        LEFT JOIN attendance_sessions ast ON c.id = ast.class_id
        LEFT JOIN attendance_records ar ON ast.id = ar.session_id
        GROUP BY c.id
        ORDER BY c.class_name
    ''').fetchall()
    
    # Thống kê theo môn học
    subject_stats = conn.execute('''
        SELECT s.subject_name, s.subject_code,
               COUNT(DISTINCT ast.id) as total_sessions,
               COUNT(DISTINCT ar.id) as total_attendance
        FROM subjects s
        LEFT JOIN attendance_sessions ast ON s.id = ast.subject_id
        LEFT JOIN attendance_records ar ON ast.id = ar.session_id
        GROUP BY s.id
        ORDER BY s.subject_name
    ''').fetchall()
    
    # Thống kê điểm danh theo ngày (7 ngày gần nhất)
    daily_stats = conn.execute('''
        SELECT ast.session_date,
               COUNT(DISTINCT ast.id) as sessions,
               COUNT(DISTINCT ar.id) as total_attendance
        FROM attendance_sessions ast
        LEFT JOIN attendance_records ar ON ast.id = ar.session_id
        WHERE ast.session_date >= date('now', '-7 days')
        GROUP BY ast.session_date
        ORDER BY ast.session_date DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('reports/statistics.html',
                         class_stats=class_stats,
                         subject_stats=subject_stats,
                         daily_stats=daily_stats)
