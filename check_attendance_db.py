#!/usr/bin/env python3
"""
Script kiểm tra chi tiết database điểm danh
"""
import sqlite3
from datetime import datetime

def check_attendance_data():
    print("🔍 Kiểm tra chi tiết dữ liệu điểm danh...")
    
    conn = sqlite3.connect('attendance_system.db')
    conn.row_factory = sqlite3.Row
    
    print("\n📊 1. Kiểm tra cấu trúc bảng attendance_records:")
    schema = conn.execute("PRAGMA table_info(attendance_records)").fetchall()
    for col in schema:
        print(f"   - {col['name']}: {col['type']} (NOT NULL: {col['notnull']})")
    
    print("\n📊 2. Tổng quan dữ liệu:")
    
    # Số lượng bản ghi trong từng bảng
    classes_count = conn.execute("SELECT COUNT(*) as count FROM classes").fetchone()['count']
    students_count = conn.execute("SELECT COUNT(*) as count FROM students").fetchone()['count']
    subjects_count = conn.execute("SELECT COUNT(*) as count FROM subjects").fetchone()['count']
    sessions_count = conn.execute("SELECT COUNT(*) as count FROM attendance_sessions").fetchone()['count']
    records_count = conn.execute("SELECT COUNT(*) as count FROM attendance_records").fetchone()['count']
    
    print(f"   - Classes: {classes_count}")
    print(f"   - Students: {students_count}")
    print(f"   - Subjects: {subjects_count}")
    print(f"   - Sessions: {sessions_count}")
    print(f"   - Attendance Records: {records_count}")
    
    print("\n📊 3. Chi tiết attendance_sessions:")
    sessions = conn.execute('''
        SELECT ast.id, ast.session_name, ast.session_date, ast.start_time,
               c.class_name, s.subject_name
        FROM attendance_sessions ast
        JOIN classes c ON ast.class_id = c.id
        JOIN subjects s ON ast.subject_id = s.id
        ORDER BY ast.session_date DESC
    ''').fetchall()
    
    if sessions:
        for session in sessions:
            print(f"   📅 Session {session['id']}: {session['session_name']}")
            print(f"       Class: {session['class_name']}")
            print(f"       Subject: {session['subject_name']}")
            print(f"       Date: {session['session_date']} {session['start_time']}")
    else:
        print("   ❌ Không có session nào!")
    
    print("\n📊 4. Chi tiết attendance_records:")
    records = conn.execute('''
        SELECT ar.id, ar.session_id, ar.student_id, ar.attendance_time, ar.status, ar.method,
               s.student_id as student_code, s.full_name
        FROM attendance_records ar
        JOIN students s ON ar.student_id = s.id
        ORDER BY ar.attendance_time DESC
    ''').fetchall()
    
    if records:
        for record in records:
            print(f"   ✅ Record {record['id']}: {record['student_code']} - {record['full_name']}")
            print(f"       Session: {record['session_id']}")
            print(f"       Status: {record['status']}")
            print(f"       Time: {record['attendance_time']}")
            print(f"       Method: {record['method']}")
    else:
        print("   ❌ Không có attendance records nào!")
    
    print("\n📊 5. Kiểm tra liên kết giữa sessions và records:")
    session_record_check = conn.execute('''
        SELECT ast.id as session_id, ast.session_name,
               COUNT(ar.id) as record_count
        FROM attendance_sessions ast
        LEFT JOIN attendance_records ar ON ast.id = ar.session_id
        GROUP BY ast.id
        ORDER BY ast.session_date DESC
    ''').fetchall()
    
    for check in session_record_check:
        print(f"   📋 Session {check['session_id']} ({check['session_name']}): {check['record_count']} records")
    
    print("\n📊 6. Kiểm tra student IDs:")
    students = conn.execute('SELECT id, student_id, full_name FROM students').fetchall()
    print("   Students in database:")
    for student in students:
        print(f"   - ID: {student['id']}, MSSV: {student['student_id']}, Name: {student['full_name']}")
    
    print("\n📊 7. Kiểm tra foreign key constraints:")
    # Check if attendance_records có student_id hợp lệ
    invalid_student_records = conn.execute('''
        SELECT ar.id, ar.student_id 
        FROM attendance_records ar
        LEFT JOIN students s ON ar.student_id = s.id
        WHERE s.id IS NULL
    ''').fetchall()
    
    if invalid_student_records:
        print("   ❌ Invalid student_id in attendance_records:")
        for record in invalid_student_records:
            print(f"       Record {record['id']} has invalid student_id: {record['student_id']}")
    else:
        print("   ✅ All student_id references are valid")
    
    # Check if attendance_records có session_id hợp lệ
    invalid_session_records = conn.execute('''
        SELECT ar.id, ar.session_id 
        FROM attendance_records ar
        LEFT JOIN attendance_sessions ast ON ar.session_id = ast.id
        WHERE ast.id IS NULL
    ''').fetchall()
    
    if invalid_session_records:
        print("   ❌ Invalid session_id in attendance_records:")
        for record in invalid_session_records:
            print(f"       Record {record['id']} has invalid session_id: {record['session_id']}")
    else:
        print("   ✅ All session_id references are valid")
    
    conn.close()
    print("\n✅ Kiểm tra hoàn tất!")

def test_export_query():
    print("\n🧪 Test query xuất Excel:")
    
    conn = sqlite3.connect('attendance_system.db')
    conn.row_factory = sqlite3.Row
    
    # Lấy class_id đầu tiên để test
    first_class = conn.execute('SELECT id FROM classes LIMIT 1').fetchone()
    if not first_class:
        print("❌ Không có class nào để test!")
        return
    
    class_id = first_class['id']
    print(f"Testing với class_id: {class_id}")
    
    # Test query giống như trong export function
    students = conn.execute('''
        SELECT s.id, s.student_id, s.full_name
        FROM students s
        WHERE s.class_id = ?
        ORDER BY s.student_id
    ''', (class_id,)).fetchall()
    
    print(f"Students found: {len(students)}")
    for student in students:
        print(f"  - {student['student_id']}: {student['full_name']} (DB ID: {student['id']})")
    
    # Test sessions query
    sessions = conn.execute('''
        SELECT ast.id, ast.session_date, ast.session_name, ast.start_time,
               s.subject_code, s.subject_name
        FROM attendance_sessions ast
        JOIN subjects s ON ast.subject_id = s.id
        WHERE ast.class_id = ?
        ORDER BY ast.session_date, ast.start_time
    ''', (class_id,)).fetchall()
    
    print(f"Sessions found: {len(sessions)}")
    for session in sessions:
        print(f"  - Session {session['id']}: {session['session_date']} - {session['session_name']}")
    
    # Test attendance query
    attendance_records = conn.execute('''
        SELECT ar.student_id, ar.session_id, ar.status, ar.attendance_time
        FROM attendance_records ar
        JOIN attendance_sessions ast ON ar.session_id = ast.id
        WHERE ast.class_id = ?
    ''', (class_id,)).fetchall()
    
    print(f"Attendance records found: {len(attendance_records)}")
    for record in attendance_records:
        print(f"  - Student {record['student_id']}, Session {record['session_id']}: {record['status']}")
    
    conn.close()

if __name__ == "__main__":
    check_attendance_data()
    test_export_query()
