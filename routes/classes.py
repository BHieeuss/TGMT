from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.database import get_db_connection

classes_bp = Blueprint('classes', __name__)

@classes_bp.route('/')
def list_classes():
    """Danh sách lớp học"""
    conn = get_db_connection()
    classes = conn.execute('''
        SELECT c.*, COUNT(s.id) as student_count
        FROM classes c
        LEFT JOIN students s ON c.id = s.class_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('classes/list.html', classes=classes)

@classes_bp.route('/add', methods=['GET', 'POST'])
def add_class():
    """Thêm lớp học mới"""
    if request.method == 'POST':
        class_code = request.form.get('class_code')
        class_name = request.form.get('class_name')
        description = request.form.get('description', '')
        
        if not class_code or not class_name:
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
            return render_template('classes/add.html')
        
        try:
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO classes (class_code, class_name, description)
                VALUES (?, ?, ?)
            ''', (class_code, class_name, description))
            conn.commit()
            conn.close()
            
            flash('Thêm lớp học thành công!', 'success')
            return redirect(url_for('classes.list_classes'))
        except Exception as e:
            flash('Mã lớp đã tồn tại!', 'error')
    
    return render_template('classes/add.html')

@classes_bp.route('/edit/<int:class_id>', methods=['GET', 'POST'])
def edit_class(class_id):
    """Sửa thông tin lớp học"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        class_code = request.form.get('class_code')
        class_name = request.form.get('class_name')
        description = request.form.get('description', '')
        
        if not class_code or not class_name:
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
        else:
            try:
                conn.execute('''
                    UPDATE classes 
                    SET class_code = ?, class_name = ?, description = ?
                    WHERE id = ?
                ''', (class_code, class_name, description, class_id))
                conn.commit()
                flash('Cập nhật lớp học thành công!', 'success')
                return redirect(url_for('classes.list_classes'))
            except Exception as e:
                flash('Mã lớp đã tồn tại!', 'error')
    
    class_info = conn.execute('SELECT * FROM classes WHERE id = ?', (class_id,)).fetchone()
    conn.close()
    
    if not class_info:
        flash('Không tìm thấy lớp học!', 'error')
        return redirect(url_for('classes.list_classes'))
    
    return render_template('classes/edit.html', class_info=class_info)

@classes_bp.route('/delete/<int:class_id>', methods=['POST'])
def delete_class(class_id):
    """Xóa lớp học"""
    conn = get_db_connection()
    
    # Kiểm tra xem lớp có sinh viên không
    student_count = conn.execute('SELECT COUNT(*) as count FROM students WHERE class_id = ?', (class_id,)).fetchone()
    
    if student_count['count'] > 0:
        flash('Không thể xóa lớp đã có sinh viên!', 'error')
    else:
        conn.execute('DELETE FROM classes WHERE id = ?', (class_id,))
        conn.commit()
        flash('Xóa lớp học thành công!', 'success')
    
    conn.close()
    return redirect(url_for('classes.list_classes'))

@classes_bp.route('/api/list')
def api_list_classes():
    """API lấy danh sách lớp học"""
    conn = get_db_connection()
    classes = conn.execute('SELECT id, class_code, class_name FROM classes ORDER BY class_name').fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in classes])
