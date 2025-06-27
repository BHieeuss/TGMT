"""
Auto Attendance Server - Hệ thống điểm danh tự động
Chạy trên port riêng biệt cho từng ca điểm danh
"""

import threading
import time
import cv2
import numpy as np
# import face_recognition  # Tạm thời comment out
from flask import Flask, render_template, Response, jsonify, request
from models.database import get_db_connection
from models.advanced_face_model import AdvancedFaceModel
from datetime import datetime
import json
import os
import logging
import socketserver
from werkzeug.serving import make_server

class AutoAttendanceServer:
    def __init__(self, session_id, port):
        self.session_id = session_id
        self.port = port
        
        # Initialize Flask app with proper template and static folders
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.app = Flask(__name__, 
                        template_folder=os.path.join(current_dir, 'templates'),
                        static_folder=os.path.join(current_dir, 'static'))
        
        self.server = None
        self.camera = None
        self.face_model = None
        self.is_running = False
        self.students_data = {}
        self.attendance_count = 0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f'AutoAttendance-{port}')
        
        # Initialize face recognition model
        self.init_face_model()
        
        # Load session data
        self.load_session_data()
        
        # Setup Flask routes
        self.setup_routes()
    
    def init_face_model(self):
        """Khởi tạo model nhận diện khuôn mặt"""
        try:
            from models.advanced_face_model import AdvancedFaceModel
            self.face_model = AdvancedFaceModel()
            
            # Kiểm tra xem model đã được train chưa
            if hasattr(self.face_model, 'is_trained') and self.face_model.is_trained:
                self.logger.info("Face recognition model initialized and trained successfully")
            else:
                self.logger.warning("Face recognition model initialized but not trained yet")
                # Thử load model nếu có file
                try:
                    import os
                    model_path = os.path.join('models', 'advanced_face_model.pkl')
                    if os.path.exists(model_path):
                        self.logger.info(f"Found model file at {model_path}, attempting to load...")
                        self.face_model.load_model(model_path)
                        if hasattr(self.face_model, 'is_trained'):
                            self.logger.info(f"Model loaded, is_trained: {self.face_model.is_trained}")
                except Exception as load_error:
                    self.logger.error(f"Error loading model: {load_error}")
                
        except ImportError as e:
            self.logger.error(f"Cannot import AdvancedFaceModel: {e}")
            self.face_model = None
        except Exception as e:
            self.logger.error(f"Error initializing face model: {e}")
            self.face_model = None
    
    def load_session_data(self):
        """Tải thông tin ca điểm danh và sinh viên"""
        conn = get_db_connection()
        
        # Lấy thông tin ca điểm danh
        self.session_info = conn.execute('''
            SELECT ast.*, s.subject_name, s.subject_code, c.class_name, c.class_code
            FROM attendance_sessions ast
            JOIN subjects s ON ast.subject_id = s.id
            JOIN classes c ON ast.class_id = c.id
            WHERE ast.id = ?
        ''', (self.session_id,)).fetchone()
        
        if not self.session_info:
            conn.close()
            raise ValueError(f"Session {self.session_id} not found")
        
        # Lấy danh sách sinh viên trong lớp
        students = conn.execute('''
            SELECT id, student_id, full_name, photo_path
            FROM students
            WHERE class_id = ?
        ''', (self.session_info['class_id'],)).fetchall()
        
        # Load face encodings cho sinh viên
        for student in students:
            self.students_data[student['student_id']] = {
                'id': student['id'],
                'name': student['full_name'],
                'photo_path': student['photo_path'],
                'attended': False,
                'attendance_time': None
            }
        
        conn.close()
        self.logger.info(f"Loaded {len(self.students_data)} students for session {self.session_id}")
        
        # Load existing attendance records
        self.update_attendance_data()
    
    def setup_routes(self):
        """Thiết lập các route cho Flask app"""
        
        @self.app.route('/')
        def index():
            try:
                return render_template('auto_attendance/session.html', 
                                     session=self.session_info,
                                     students=self.students_data,
                                     attendance_count=self.attendance_count,
                                     port=self.port)
            except Exception as e:
                self.logger.error(f"Error rendering template: {e}")
                students_list = ', '.join([f"{sid}: {data['name']} ({'✓' if data['attended'] else '✗'})" for sid, data in self.students_data.items()])
                return f"""
                <html>
                <head><title>Auto Attendance Session {self.session_id}</title></head>
                <body>
                    <h1>Auto Attendance Session {self.session_id}</h1>
                    <p>Port: {self.port}</p>
                    <p>Students: {len(self.students_data)}</p>
                    <p>Attendance: {self.attendance_count}</p>
                    <img src="/video_feed" style="width:640px;height:480px;">
                    <div id="students">
                        {students_list}
                    </div>
                    <script>
                        setInterval(function() {{
                            fetch('/api/attendance')
                                .then(function(r) {{ return r.json(); }})
                                .then(function(data) {{ console.log('Attendance updated:', data); }})
                                .catch(function(e) {{ console.error('Error:', e); }});
                        }}, 3000);
                    </script>
                </body>
                </html>
                """
        
        @self.app.route('/video_feed')
        def video_feed():
            """Stream video với nhận diện khuôn mặt"""
            return Response(self.generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/attendance_status')
        def attendance_status():
            """API trả về trạng thái điểm danh"""
            # Cập nhật dữ liệu từ database
            self.update_attendance_data()
            
            return jsonify({
                'success': True,
                'students': [
                    {
                        'student_id': sid,
                        'name': data['name'],
                        'attended': data['attended'],
                        'attendance_time': data['attendance_time']
                    }
                    for sid, data in self.students_data.items()
                ],
                'attendance_count': self.attendance_count,
                'total_students': len(self.students_data)
            })
        
        @self.app.route('/recognition_status')
        def recognition_status():
            """API trả về trạng thái nhận diện"""
            return jsonify({
                'recognizing': self.camera is not None,
                'detected_faces': getattr(self, 'last_detected_faces', 0)
            })
        
        @self.app.route('/stop_session', methods=['POST'])
        def stop_session():
            """API dừng session"""
            self.stop()
            return jsonify({'success': True})
        
        @self.app.route('/api/attendance')
        def api_attendance():
            """API lấy dữ liệu điểm danh"""
            self.update_attendance_data()
            return jsonify({
                'success': True,
                'students': [
                    {
                        'student_id': sid,
                        'name': data['name'],
                        'attended': data['attended'],
                        'attendance_time': data['attendance_time']
                    }
                    for sid, data in self.students_data.items()
                ],
                'attendance_count': self.attendance_count,
                'total_students': len(self.students_data)
            })
        
        @self.app.route('/api/status')
        def api_status():
            """API trạng thái server"""
            return jsonify({
                'session_id': self.session_id,
                'port': self.port,
                'is_running': self.is_running,
                'attendance_count': self.attendance_count,
                'total_students': len(self.students_data),
                'camera_active': self.camera is not None,
                'model_ready': self.face_model is not None and getattr(self.face_model, 'is_trained', False)
            })
        
        @self.app.route('/api/recognition_status')
        def api_recognition_status():
            """API trạng thái nhận diện"""
            return jsonify({
                'success': True,
                'recognizing': self.camera is not None and self.is_running,
                'detected_faces': getattr(self, 'last_detected_faces', 0),
                'model_ready': self.face_model is not None and getattr(self.face_model, 'is_trained', False)
            })
    
    def update_attendance_data(self):
        """Cập nhật dữ liệu điểm danh từ database"""
        conn = get_db_connection()
        
        # Lấy danh sách sinh viên đã điểm danh trong ca này
        attended_records = conn.execute('''
            SELECT ar.student_id, s.student_id as student_code, s.full_name, ar.attendance_time
            FROM attendance_records ar
            JOIN students s ON ar.student_id = s.id
            WHERE ar.session_id = ?
            ORDER BY ar.attendance_time
        ''', (self.session_id,)).fetchall()
        
        # Reset attendance count
        self.attendance_count = len(attended_records)
        
        # Reset tất cả sinh viên về chưa điểm danh
        for student_id in self.students_data:
            self.students_data[student_id]['attended'] = False
            self.students_data[student_id]['attendance_time'] = None
        
        # Cập nhật trạng thái điểm danh cho những sinh viên đã điểm danh
        for record in attended_records:
            student_code = record['student_code']
            if student_code in self.students_data:
                self.students_data[student_code]['attended'] = True
                self.students_data[student_code]['attendance_time'] = record['attendance_time']
        
        conn.close()
        self.logger.info(f"Updated attendance data: {self.attendance_count}/{len(self.students_data)} students attended")
    
    def generate_frames(self):
        """Generator tạo frame video với nhận diện khuôn mặt"""
        # Khởi tạo camera
        if not self.camera:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                self.logger.error("Cannot open camera")
                return
        
        # Load face cascade cho detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        while self.is_running:
            success, frame = self.camera.read()
            if not success:
                break
            
            # Resize và flip frame
            frame = cv2.resize(frame, (640, 480))
            frame = cv2.flip(frame, 1)  # Mirror effect
            
            # Thêm status overlay
            cv2.putText(frame, f"Session: {self.session_id}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Port: {self.port}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Attendance: {self.attendance_count}/{len(self.students_data)}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            self.last_detected_faces = 0
            
            try:
                # Convert to grayscale for face detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                if len(faces) > 0:
                    self.last_detected_faces = len(faces)
                    
                    for (x, y, w, h) in faces:
                        # Draw rectangle around face
                        color = (0, 255, 255)  # Yellow for detected face
                        label = f"Face Detected"
                        
                        # Try to recognize using AI model if available
                        if self.face_model and hasattr(self.face_model, 'is_trained') and self.face_model.is_trained:
                            try:
                                # Extract face region
                                face_img = frame[y:y+h, x:x+w]
                                
                                # Convert face to base64 for AI model
                                ret, buffer = cv2.imencode('.jpg', face_img)
                                if not ret:
                                    continue
                                
                                import base64
                                face_b64 = base64.b64encode(buffer).decode('utf-8')
                                face_data = f"data:image/jpeg;base64,{face_b64}"
                                
                                # Use AI model to recognize
                                result = self.face_model.recognize_face(face_data, use_ensemble=True)
                                
                                if result and result.get('success', False) and result.get('faces'):
                                    # Get best face result
                                    best_face = None
                                    for face in result['faces']:
                                        if face.get('student_id'):  # Valid recognized face
                                            best_face = face
                                            break
                                    
                                    if best_face:
                                        student_id = best_face['student_id']
                                        confidence = best_face.get('combined_score', 0)
                                        name = self.students_data.get(student_id, {}).get('name', 'Unknown')
                                        
                                        # Check if already attended
                                        already_attended = self.students_data.get(student_id, {}).get('attended', False)
                                        
                                        if already_attended:
                                            color = (0, 255, 0)  # Green
                                            label = f"{name} - DA DIEM DANH"
                                        else:
                                            color = (0, 255, 255)  # Yellow
                                            label = f"{name} ({confidence:.2f})"
                                            
                                            # Try to save attendance
                                            success = self.save_attendance(student_id)
                                            if success:
                                                self.logger.info(f"Attendance saved for {student_id} - {name}")
                                    else:
                                        color = (0, 0, 255)  # Red
                                        label = f"Unknown (Low confidence)"
                                else:
                                    color = (0, 0, 255)  # Red
                                    label = f"Recognition Failed"
                                    
                            except Exception as model_error:
                                self.logger.error(f"AI model error: {model_error}")
                                color = (255, 0, 0)  # Blue
                                label = "Model Error"
                        else:
                            # No AI model, just detect faces
                            color = (255, 255, 0)  # Cyan
                            label = "Face - No AI Model"
                        
                        # Draw rectangle
                        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                        
                        # Draw label with background
                        (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        cv2.rectangle(frame, (x, y - text_height - 10), (x + text_width, y), color, -1)
                        cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                
                else:
                    # No faces detected
                    cv2.putText(frame, "Khong phat hien khuon mat", (10, 120), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            except Exception as e:
                self.logger.error(f"Face detection error: {e}")
                cv2.putText(frame, f"Loi nhan dien: {str(e)[:50]}", (10, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    def save_attendance(self, student_id):
        """Lưu điểm danh cho sinh viên - chỉ cho phép 1 lần duy nhất"""
        try:
            # Kiểm tra local cache trước
            if self.students_data.get(student_id, {}).get('attended', False):
                self.logger.info(f"Student {student_id} already attended (local cache)")
                return False
            
            conn = get_db_connection()
            
            # Kiểm tra database xem đã điểm danh chưa
            existing = conn.execute('''
                SELECT id FROM attendance_records 
                WHERE session_id = ? AND student_id = (
                    SELECT id FROM students WHERE student_id = ?
                )
            ''', (self.session_id, student_id)).fetchone()
            
            if existing:
                conn.close()
                self.logger.info(f"Student {student_id} already attended (database)")
                return False
            
            # Lấy thông tin sinh viên
            student_record = conn.execute('''
                SELECT id, full_name FROM students WHERE student_id = ?
            ''', (student_id,)).fetchone()
            
            if student_record:
                # Lưu bản ghi điểm danh
                conn.execute('''
                    INSERT INTO attendance_records (session_id, student_id, attendance_time, method, confidence, status)
                    VALUES (?, ?, datetime('now'), 'face_recognition_auto', ?, 'present')
                ''', (self.session_id, student_record['id'], 85.0))
                
                conn.commit()
                
                # Cập nhật local cache
                if student_id in self.students_data:
                    self.students_data[student_id]['attended'] = True
                    self.students_data[student_id]['attendance_time'] = datetime.now().strftime('%H:%M:%S')
                    self.attendance_count += 1
                
                self.logger.info(f"Attendance saved for student {student_id} - {student_record['full_name']}")
                conn.close()
                return True
            else:
                conn.close()
                self.logger.warning(f"Student {student_id} not found in database")
                return False
            
        except Exception as e:
            self.logger.error(f"Error saving attendance for {student_id}: {e}")
            return False
    
    def start_camera(self):
        """Khởi động camera"""
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise Exception("Cannot open camera")
            
            # Set camera properties for better performance
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            self.logger.info("Camera started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting camera: {e}")
            return False
    
    def start(self):
        """Khởi động server điểm danh tự động"""
        if self.is_running:
            return False
        
        # Start camera
        if not self.start_camera():
            return False
        
        try:
            # Create server
            self.server = make_server('0.0.0.0', self.port, self.app, threaded=True)
            self.is_running = True
            
            # Start server in thread
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.logger.info(f"Auto attendance server started on port {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Dừng server điểm danh tự động"""
        self.is_running = False
        
        # Stop camera
        if self.camera:
            self.camera.release()
            self.camera = None
        
        # Stop server
        if self.server:
            self.server.shutdown()
            self.server = None
        
        self.logger.info(f"Auto attendance server stopped on port {self.port}")
    
    def get_status(self):
        """Lấy trạng thái server"""
        return {
            'session_id': self.session_id,
            'port': self.port,
            'is_running': self.is_running,
            'attendance_count': self.attendance_count,
            'total_students': len(self.students_data)
        }
    
    def load_known_faces(self):
        """Load known faces - không sử dụng face_recognition nữa"""
        self.logger.info("Face recognition library not available, using AI model instead")
        # Không load faces nữa, sử dụng AI model
        pass


# Global dictionary to store running servers
active_servers = {}

def create_auto_attendance_session(session_id, start_port=8001):
    """Tạo session điểm danh tự động mới"""
    global active_servers
    
    # Find available port
    port = start_port
    while port in active_servers or not is_port_available(port):
        port += 1
    
    try:
        # Create and start server
        server = AutoAttendanceServer(session_id, port)
        if server.start():
            active_servers[port] = server
            return port
        else:
            return None
    except Exception as e:
        logging.error(f"Error creating auto attendance session: {e}")
        return None

def stop_auto_attendance_session(port):
    """Dừng session điểm danh tự động"""
    global active_servers
    
    if port in active_servers:
        active_servers[port].stop()
        del active_servers[port]
        return True
    return False

def get_active_sessions():
    """Lấy danh sách session đang hoạt động"""
    global active_servers
    return {port: server.get_status() for port, server in active_servers.items()}

def is_port_available(port):
    """Kiểm tra port có khả dụng không"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except socket.error:
            return False

if __name__ == '__main__':
    # Test server
    session_id = 1
    port = create_auto_attendance_session(session_id)
    if port:
        print(f"Auto attendance server started on port {port}")
        print(f"Access at: http://localhost:{port}")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_auto_attendance_session(port)
            print("Server stopped")
