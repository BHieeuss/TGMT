"""
Script test chức năng điểm danh tự động
"""
from models.database import get_db_connection
from auto_attendance_server import create_auto_attendance_session, stop_auto_attendance_session, get_active_sessions
import time

def test_auto_attendance():
    print("=== Test Chức Năng Điểm Danh Tự Động ===")
    
    # Tạo dữ liệu test
    conn = get_db_connection()
    
    # Thêm ca điểm danh test
    cursor = conn.execute('''
        INSERT INTO attendance_sessions (session_name, subject_id, class_id, session_date, start_time, status)
        VALUES (?, ?, ?, date('now'), time('now'), 'active')
    ''', ('Test Auto Session', 1, 1))
    
    session_id = cursor.lastrowid
    conn.commit()
    print(f"Tạo ca điểm danh test với ID: {session_id}")
    
    # Tạo auto attendance server
    try:
        port = create_auto_attendance_session(session_id)
        if port:
            print(f"Server điểm danh tự động đã khởi động trên port: {port}")
            print(f"Truy cập tại: http://localhost:{port}")
            
            # Kiểm tra active sessions
            active_sessions = get_active_sessions()
            print(f"Số ca đang hoạt động: {len(active_sessions)}")
            
            # Cập nhật port vào database
            conn.execute('''
                UPDATE attendance_sessions SET port = ? WHERE id = ?
            ''', (port, session_id))
            conn.commit()
            
            print("\n=== Hướng dẫn test ===")
            print("1. Mở browser và truy cập URL trên")
            print("2. Cho phép truy cập camera")
            print("3. Đưa khuôn mặt vào camera để test nhận diện")
            print("4. Mỗi sinh viên chỉ được điểm danh 1 lần duy nhất")
            print("5. Nhấn Enter để dừng server test...")
            
            input()  # Đợi user nhấn Enter
            
            # Dừng server
            if stop_auto_attendance_session(port):
                print(f"Đã dừng server trên port {port}")
            else:
                print("Lỗi khi dừng server")
                
        else:
            print("Không thể tạo server điểm danh tự động")
            
    except Exception as e:
        print(f"Lỗi: {e}")
    
    finally:
        # Xóa dữ liệu test
        conn.execute('DELETE FROM attendance_records WHERE session_id = ?', (session_id,))
        conn.execute('DELETE FROM attendance_sessions WHERE id = ?', (session_id,))
        conn.commit()
        conn.close()
        print("Đã dọn dẹp dữ liệu test")

if __name__ == '__main__':
    test_auto_attendance()
