from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.database import get_db_connection
from datetime import datetime

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route('/')
def list_subjects():
    """Danh sách môn học với thống kê"""
    conn = get_db_connection()
    
    # Lấy danh sách môn học với thống kê
    subjects = conn.execute('''
        SELECT s.*, 
               COUNT(DISTINCT ast.id) as session_count,
               COUNT(DISTINCT ar.id) as attendance_count
        FROM subjects s
        LEFT JOIN attendance_sessions ast ON s.id = ast.subject_id
        LEFT JOIN attendance_records ar ON ast.id = ar.session_id
        GROUP BY s.id
        ORDER BY s.created_at DESC
    ''').fetchall()
    
    # Thống kê tổng quan
    total_subjects = len(subjects)
    active_subjects = len([s for s in subjects if s['session_count'] > 0])
    total_sessions = sum(s['session_count'] for s in subjects)
    total_attendance = sum(s['attendance_count'] for s in subjects)
    avg_attendance = round(total_attendance / max(total_sessions, 1) * 100) if total_sessions > 0 else 0
    
    conn.close()
    
    return render_template('subjects/list.html', 
                         subjects=subjects,
                         active_subjects=active_subjects,
                         total_sessions=total_sessions,
                         avg_attendance=avg_attendance)

@subjects_bp.route('/add', methods=['GET', 'POST'])
def add_subject():
    """Thêm môn học mới"""
    if request.method == 'POST':
        subject_code = request.form.get('subject_code')
        subject_name = request.form.get('subject_name')
        description = request.form.get('description', '')
        
        if not subject_code or not subject_name:
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
            return render_template('subjects/add.html')
        
        try:
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO subjects (subject_code, subject_name, description)
                VALUES (?, ?, ?)
            ''', (subject_code, subject_name, description))
            conn.commit()
            conn.close()
            
            flash('Thêm môn học thành công!', 'success')
            return redirect(url_for('subjects.list_subjects'))
        except Exception as e:
            flash('Mã môn học đã tồn tại!', 'error')
    
    return render_template('subjects/add.html')

@subjects_bp.route('/edit/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    """Sửa thông tin môn học"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        subject_code = request.form.get('subject_code')
        subject_name = request.form.get('subject_name')
        description = request.form.get('description', '')
        
        if not subject_code or not subject_name:
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
        else:
            try:
                conn.execute('''
                    UPDATE subjects 
                    SET subject_code = ?, subject_name = ?, description = ?
                    WHERE id = ?
                ''', (subject_code, subject_name, description, subject_id))
                conn.commit()
                flash('Cập nhật môn học thành công!', 'success')
                return redirect(url_for('subjects.list_subjects'))
            except Exception as e:
                flash('Mã môn học đã tồn tại!', 'error')
    
    # Lấy thông tin môn học và thống kê
    subject_info = conn.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,)).fetchone()
    
    if not subject_info:
        flash('Không tìm thấy môn học!', 'error')
        conn.close()
        return redirect(url_for('subjects.list_subjects'))
    
    # Thống kê cho môn học này
    session_count = conn.execute('''
        SELECT COUNT(*) as count FROM attendance_sessions WHERE subject_id = ?
    ''', (subject_id,)).fetchone()['count']
    
    attendance_count = conn.execute('''
        SELECT COUNT(*) as count 
        FROM attendance_records ar
        JOIN attendance_sessions ast ON ar.session_id = ast.id
        WHERE ast.subject_id = ?
    ''', (subject_id,)).fetchone()['count']
    
    conn.close()
    
    return render_template('subjects/edit.html', 
                         subject_info=subject_info,
                         session_count=session_count,
                         attendance_count=attendance_count)

@subjects_bp.route('/delete/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    """Xóa môn học"""
    conn = get_db_connection()
    
    # Kiểm tra xem môn học có ca điểm danh không
    session_count = conn.execute('SELECT COUNT(*) as count FROM attendance_sessions WHERE subject_id = ?', (subject_id,)).fetchone()
    
    if session_count['count'] > 0:
        flash('Không thể xóa môn học đã có ca điểm danh!', 'error')
    else:
        conn.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
        conn.commit()
        flash('Xóa môn học thành công!', 'success')
    
    conn.close()
    return redirect(url_for('subjects.list_subjects'))

@subjects_bp.route('/api/list')
def api_list_subjects():
    """API lấy danh sách môn học"""
    conn = get_db_connection()
    subjects = conn.execute('SELECT id, subject_code, subject_name FROM subjects ORDER BY subject_name').fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in subjects])

@subjects_bp.route('/api/details/<int:subject_id>')
def api_subject_details(subject_id):
    """API lấy chi tiết môn học"""
    conn = get_db_connection()
    
    # Lấy thông tin môn học
    subject = conn.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,)).fetchone()
    
    if not subject:
        conn.close()
        return jsonify({'error': 'Subject not found'}), 404
    
    # Thống kê
    session_count = conn.execute('''
        SELECT COUNT(*) as count FROM attendance_sessions WHERE subject_id = ?
    ''', (subject_id,)).fetchone()['count']
    
    total_attendance = conn.execute('''
        SELECT COUNT(*) as count 
        FROM attendance_records ar
        JOIN attendance_sessions ast ON ar.session_id = ast.id
        WHERE ast.subject_id = ?
    ''', (subject_id,)).fetchone()['count']
    
    # Tính tỷ lệ điểm danh trung bình
    avg_attendance_query = conn.execute('''
        SELECT AVG(attendance_rate) as avg_rate
        FROM (
            SELECT 
                ast.id,
                COUNT(ar.id) * 100.0 / MAX(1, (
                    SELECT COUNT(*) FROM students s 
                    WHERE s.class_id = ast.class_id
                )) as attendance_rate
            FROM attendance_sessions ast
            LEFT JOIN attendance_records ar ON ast.id = ar.session_id
            WHERE ast.subject_id = ?
            GROUP BY ast.id
        )
    ''', (subject_id,)).fetchone()
    
    avg_attendance = round(avg_attendance_query['avg_rate'] or 0)
    
    conn.close()
    
    return jsonify({
        'subject_code': subject['subject_code'],
        'subject_name': subject['subject_name'],
        'description': subject['description'],
        'created_at': subject['created_at'],
        'session_count': session_count,
        'total_attendance': total_attendance,
        'avg_attendance': avg_attendance
    })

@subjects_bp.route('/export/excel')
def export_excel():
    """Xuất danh sách môn học ra Excel"""
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        conn = get_db_connection()
        
        # Lấy dữ liệu môn học với thống kê
        subjects_data = conn.execute('''
            SELECT s.subject_code as 'Mã môn', 
                   s.subject_name as 'Tên môn học',
                   s.description as 'Mô tả',
                   s.created_at as 'Ngày tạo',
                   COUNT(DISTINCT ast.id) as 'Số ca điểm danh',
                   COUNT(DISTINCT ar.id) as 'Tổng lượt điểm danh'
            FROM subjects s
            LEFT JOIN attendance_sessions ast ON s.id = ast.subject_id
            LEFT JOIN attendance_records ar ON ast.id = ar.session_id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        ''').fetchall()
        
        conn.close()
        
        # Chuyển đổi sang DataFrame
        df = pd.DataFrame([dict(row) for row in subjects_data])
        
        # Tạo file Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Danh sách môn học', index=False)
            
            # Format worksheet
            worksheet = writer.sheets['Danh sách môn học']
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
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'danh_sach_mon_hoc_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except ImportError:
        flash('Cần cài đặt pandas và openpyxl để xuất Excel!', 'error')
        return redirect(url_for('subjects.list_subjects'))
    except Exception as e:
        flash(f'Lỗi xuất Excel: {str(e)}', 'error')
        return redirect(url_for('subjects.list_subjects'))

@subjects_bp.route('/export/<int:subject_id>')
def export_subject_data(subject_id):
    """Xuất dữ liệu chi tiết của một môn học"""
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        conn = get_db_connection()
        
        # Lấy thông tin môn học
        subject = conn.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,)).fetchone()
        
        if not subject:
            flash('Không tìm thấy môn học!', 'error')
            return redirect(url_for('subjects.list_subjects'))
        
        # Lấy dữ liệu ca điểm danh
        sessions_data = conn.execute('''
            SELECT ast.session_name as 'Tên ca điểm danh',
                   c.class_name as 'Lớp học',
                   ast.session_date as 'Ngày',
                   ast.start_time as 'Giờ bắt đầu',
                   ast.end_time as 'Giờ kết thúc',
                   ast.status as 'Trạng thái',
                   COUNT(ar.id) as 'Số lượt điểm danh'
            FROM attendance_sessions ast
            JOIN classes c ON ast.class_id = c.id
            LEFT JOIN attendance_records ar ON ast.id = ar.session_id
            WHERE ast.subject_id = ?
            GROUP BY ast.id
            ORDER BY ast.session_date DESC, ast.start_time DESC
        ''', (subject_id,)).fetchall()
        
        conn.close()
        
        # Tạo file Excel với nhiều sheet
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet thông tin môn học
            subject_info = pd.DataFrame([{
                'Mã môn': subject['subject_code'],
                'Tên môn học': subject['subject_name'],
                'Mô tả': subject['description'] or '',
                'Ngày tạo': subject['created_at']
            }])
            subject_info.to_excel(writer, sheet_name='Thông tin môn học', index=False)
            
            # Sheet ca điểm danh
            if sessions_data:
                sessions_df = pd.DataFrame([dict(row) for row in sessions_data])
                sessions_df.to_excel(writer, sheet_name='Ca điểm danh', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'mon_hoc_{subject["subject_code"]}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except ImportError:
        flash('Cần cài đặt pandas và openpyxl để xuất Excel!', 'error')
        return redirect(url_for('subjects.list_subjects'))
    except Exception as e:
        flash(f'Lỗi xuất dữ liệu: {str(e)}', 'error')
        return redirect(url_for('subjects.list_subjects'))
