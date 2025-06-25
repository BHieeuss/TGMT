from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.database import get_db_connection

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route('/')
def list_subjects():
    """Danh sách môn học"""
    conn = get_db_connection()
    subjects = conn.execute('SELECT * FROM subjects ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('subjects/list.html', subjects=subjects)

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
    
    subject_info = conn.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,)).fetchone()
    conn.close()
    
    if not subject_info:
        flash('Không tìm thấy môn học!', 'error')
        return redirect(url_for('subjects.list_subjects'))
    
    return render_template('subjects/edit.html', subject_info=subject_info)

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
