import sqlite3
import os
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

if __name__ == '__main__':
    init_database()
