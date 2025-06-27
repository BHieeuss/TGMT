from models.database import get_db_connection

conn = get_db_connection()

# Tạo dữ liệu test
try:
    # Thêm môn học test
    conn.execute('INSERT OR IGNORE INTO subjects (subject_code, subject_name) VALUES (?, ?)', ('CS101', 'Lập trình Python'))
    conn.execute('INSERT OR IGNORE INTO subjects (subject_code, subject_name) VALUES (?, ?)', ('CS102', 'Cơ sở dữ liệu'))
    
    # Thêm lớp học test  
    conn.execute('INSERT OR IGNORE INTO classes (class_code, class_name) VALUES (?, ?)', ('IT01', 'Công nghệ thông tin 01'))
    conn.execute('INSERT OR IGNORE INTO classes (class_code, class_name) VALUES (?, ?)', ('IT02', 'Công nghệ thông tin 02'))
    
    conn.commit()
    print('Đã tạo dữ liệu test')
    
    # Kiểm tra dữ liệu
    subjects = conn.execute('SELECT * FROM subjects').fetchall()
    classes = conn.execute('SELECT * FROM classes').fetchall()
    
    print(f'Số môn học: {len(subjects)}')
    print(f'Số lớp: {len(classes)}')
    
except Exception as e:
    print(f'Lỗi: {e}')
finally:
    conn.close()
