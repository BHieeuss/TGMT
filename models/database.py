import sqlite3
import os
import pandas as pd
from datetime import datetime

DATABASE_PATH = 'attendance_system.db'

def get_db_connection():
    """Tạo kết nối đến database"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Khởi tạo database và các bảng"""
    conn = get_db_connection()
    
    # Bảng lớp học
    conn.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_code TEXT UNIQUE NOT NULL,
            class_name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bảng sinh viên
    conn.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            photo_path TEXT,
            face_encoding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
    ''')
    
    # Bảng môn học
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT UNIQUE NOT NULL,
            subject_name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bảng ca điểm danh
    conn.execute('''
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            session_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects (id),
            FOREIGN KEY (class_id) REFERENCES classes (id)
        )
    ''')
    
    # Bảng điểm danh
    conn.execute('''
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            attendance_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'present',
            method TEXT DEFAULT 'face_recognition',
            confidence REAL,
            FOREIGN KEY (session_id) REFERENCES attendance_sessions (id),
            FOREIGN KEY (student_id) REFERENCES students (id),
            UNIQUE(session_id, student_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def get_dashboard_stats():
    """Lấy thống kê cho dashboard"""
    conn = get_db_connection()
    
    stats = {}
    
    # Tổng số lớp
    result = conn.execute('SELECT COUNT(*) as count FROM classes').fetchone()
    stats['total_classes'] = result['count']
    
    # Tổng số sinh viên
    result = conn.execute('SELECT COUNT(*) as count FROM students').fetchone()
    stats['total_students'] = result['count']
    
    # Tổng số môn học
    result = conn.execute('SELECT COUNT(*) as count FROM subjects').fetchone()
    stats['total_subjects'] = result['count']
    
    # Số ca điểm danh hôm nay
    today = datetime.now().strftime('%Y-%m-%d')
    result = conn.execute('SELECT COUNT(*) as count FROM attendance_sessions WHERE session_date = ?', (today,)).fetchone()
    stats['today_sessions'] = result['count']
    
    # Lịch sử điểm danh gần đây
    recent_attendance = conn.execute('''
        SELECT ar.attendance_time, s.full_name, s.student_id, 
               c.class_name, subj.subject_name, ar.status
        FROM attendance_records ar
        JOIN students s ON ar.student_id = s.id
        JOIN attendance_sessions ast ON ar.session_id = ast.id
        JOIN classes c ON s.class_id = c.id
        JOIN subjects subj ON ast.subject_id = subj.id
        ORDER BY ar.attendance_time DESC
        LIMIT 10
    ''').fetchall()
    
    stats['recent_attendance'] = [dict(row) for row in recent_attendance]
    
    conn.close()
    return stats

def import_students_from_excel(file_path, class_id):
    """
    Nhập sinh viên từ file Excel
    
    Expected Excel format:
    Cột B: MSSV
    Cột C: Họ lót  
    Cột D: Tên
    """
    try:
        # Đọc file Excel không có header
        df = pd.read_excel(file_path, header=None)
        
        # Kiểm tra xem có đủ cột không (ít nhất 4 cột: A, B, C, D)
        if df.shape[1] < 4:
            return {
                'success': False,
                'message': 'File Excel phải có ít nhất 4 cột (A, B, C, D)',
                'imported': 0,
                'errors': []
            }
        
        conn = get_db_connection()
        imported_count = 0
        errors = []
        
        # Bỏ qua dòng đầu (header) nếu có
        start_row = 1 if df.iloc[0, 1] == 'MSSV' or 'MSSV' in str(df.iloc[0, 1]) else 0
        
        for index in range(start_row, len(df)):
            try:
                # Đọc dữ liệu từ các cột B, C, D (index 1, 2, 3)
                student_id = str(df.iloc[index, 1]).strip() if pd.notna(df.iloc[index, 1]) else ''
                ho_lot = str(df.iloc[index, 2]).strip() if pd.notna(df.iloc[index, 2]) else ''
                ten = str(df.iloc[index, 3]).strip() if pd.notna(df.iloc[index, 3]) else ''
                
                # Ghép họ lót và tên thành họ tên đầy đủ
                full_name = f"{ho_lot} {ten}".strip()
                
                # Validate required fields
                if not student_id or not full_name or student_id == 'nan':
                    errors.append(f'Dòng {index + 2}: MSSV hoặc Họ tên trống')
                    continue
                
                # Check if student already exists
                existing = conn.execute(
                    'SELECT id FROM students WHERE student_id = ?', 
                    (student_id,)
                ).fetchone()
                
                if existing:
                    errors.append(f'Dòng {index + 2}: MSSV {student_id} đã tồn tại')
                    continue
                
                # Insert student
                conn.execute('''
                    INSERT INTO students (student_id, full_name, class_id)
                    VALUES (?, ?, ?)
                ''', (student_id, full_name, class_id))
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f'Dòng {index + 2}: {str(e)}')
                continue
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Đã nhập thành công {imported_count} sinh viên',
            'imported': imported_count,
            'errors': errors
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Lỗi đọc file Excel: {str(e)}',
            'imported': 0,
            'errors': []
        }

def create_excel_template():
    """Tạo file Excel template cho nhập sinh viên"""
    template_data = {
        'STT': [1, 2, 3, 4, 5],
        'MSSV': ['110121001', '110121002', '110121003', '110121004', '110121005'],
        'Họ lót': ['Nguyễn Văn', 'Trần Thị', 'Lê Minh', 'Phạm Thu', 'Hoàng Đức'],
        'Tên': ['An', 'Bình', 'Cường', 'Dung', 'Elton'],
        'Ghi chú': ['Lớp trưởng', 'Thường', 'Thường', 'Thư ký', 'Thường']
    }
    
    df = pd.DataFrame(template_data)
    template_path = 'exports/template_students.xlsx'
    
    # Tạo thư mục nếu chưa có
    os.makedirs('exports', exist_ok=True)
    
    # Tạo file Excel với format đẹp
    with pd.ExcelWriter(template_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Danh sách sinh viên', index=False)
        
        # Format worksheet
        worksheet = writer.sheets['Danh sách sinh viên']
        
        # Tô màu header
        from openpyxl.styles import PatternFill, Font, Alignment
        
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True)
        
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Adjust column widths
        column_widths = {'A': 8, 'B': 15, 'C': 20, 'D': 15, 'E': 15}
        for column, width in column_widths.items():
            worksheet.column_dimensions[column].width = width
        
        # Thêm hướng dẫn
        worksheet['A8'] = 'HƯỚNG DẪN:'
        worksheet['A9'] = '- Cột B: Mã số sinh viên (MSSV)'
        worksheet['A10'] = '- Cột C: Họ và tên lót của sinh viên'
        worksheet['A11'] = '- Cột D: Tên của sinh viên'
        worksheet['A12'] = '- Không được để trống cột B, C, D'
        worksheet['A13'] = '- Xóa các dòng ví dụ trước khi import'
        
        # Format hướng dẫn
        for row in range(8, 14):
            worksheet[f'A{row}'].font = Font(italic=True, color='666666')
    
    return template_path

if __name__ == '__main__':
    init_database()
