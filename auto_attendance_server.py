"""
Auto Attendance Server - Hệ thống điểm danh tự động
Chạy trên port riêng biệt cho từng ca điểm danh
Sử dụng hàm nhận diện thống nhất
"""

import threading
import time
import cv2
import numpy as np
import base64
from flask import Flask, render_template, Response, jsonify, request
from models.database import get_db_connection
from utils.face_recognition_utils import recognize_face_from_image, mark_attendance
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
        self.is_running = False
        self.students_data = {}
        self.attendance_count = 0
        self.marked_students = set()  # Theo dõi sinh viên đã điểm danh
        
        # Recognition log storage
        self.recognition_log = []
        self.max_log_size = 50  # Giới hạn số lượng log
        self.log_lock = threading.Lock()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f'AutoAttendance-{port}')
        
        # Initialize session data
        self.init_session_data()
        
        # Cache model ready status để tránh lag
        self._model_ready_cache = None
        self._model_check_time = 0
        self._model_cache_timeout = 10  # Cache 10 giây
        
        # Setup Flask routes
        self.setup_routes()
    
    def init_session_data(self):
        """Khởi tạo dữ liệu ca điểm danh"""
        try:
            # Load session data
            self.load_session_data()
            self.logger.info(f"Session {self.session_id} initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing session data: {e}")
            self.session_info = None
            self.students_data = {}
    
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
        
        # Load student data
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
        
        @self.app.route('/api/recognition_log')
        def api_recognition_log():
            """API lấy log nhận diện"""
            with self.log_lock:
                return jsonify({
                    'success': True,
                    'logs': self.recognition_log.copy()
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
                'model_ready': self._check_model_ready()
            })
        
        @self.app.route('/api/recognition_status')
        def api_recognition_status():
            """API trạng thái nhận diện"""
            return jsonify({
                'success': True,
                'recognizing': self.camera is not None and self.is_running,
                'detected_faces': getattr(self, 'last_detected_faces', 0),
                'model_ready': self._check_model_ready()
            })
        
        @self.app.route('/api/debug')
        def debug_info():
            """API debug thông tin hệ thống"""
            return jsonify({
                'success': True,
                'debug_info': {
                    'session_id': self.session_id,
                    'port': self.port,
                    'is_running': self.is_running,
                    'model_ready': self._check_model_ready(),
                    'camera_available': self.camera is not None and self.camera.isOpened() if self.camera else False,
                    'total_students': len(self.students_data),
                    'attendance_count': self.attendance_count,
                    'marked_students': len(self.marked_students),
                    'recognition_log_count': len(self.recognition_log),
                    'last_detected_faces': getattr(self, 'last_detected_faces', 0)
                },
                'message': 'Debug info retrieved'
            })
    
    def add_recognition_log(self, log_type, student_id=None, student_name=None, confidence=None, reason=None):
        """Thêm log nhận diện"""
        with self.log_lock:
            log_entry = {
                'type': log_type,
                'timestamp': datetime.now().isoformat(),
                'student_id': student_id,
                'student_name': student_name,
                'confidence': confidence,
                'reason': reason
            }
            
            # Thêm vào đầu list
            self.recognition_log.insert(0, log_entry)
            
            # Giới hạn số lượng log
            if len(self.recognition_log) > self.max_log_size:
                self.recognition_log = self.recognition_log[:self.max_log_size]
    
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
        """Generator tạo frame video với nhận diện khuôn mặt - 2 giây quét 1 lần"""
        # Khởi tạo camera
        if not self.camera:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                self.logger.error("Cannot open camera")
                return
        
        # Load face cascade cho detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Thiết lập thời gian quét - GIẢM ĐỘ TRỄ
        last_recognition_time = 0
        recognition_interval = 1.5  # Giảm từ 2s xuống 1.5s để phản hồi nhanh hơn
        
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
            cv2.putText(frame, f"Confidence Range: 85-100", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Hiển thị thời gian đến lần quét tiếp theo
            current_time = time.time()
            time_since_last = current_time - last_recognition_time
            time_to_next = max(0, recognition_interval - time_since_last)
            cv2.putText(frame, f"Next scan: {time_to_next:.1f}s", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            self.last_detected_faces = 0
            
            try:
                # Convert to grayscale for face detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                if len(faces) > 0:
                    self.last_detected_faces = len(faces)
                    
                    # Chỉ thực hiện nhận diện AI nếu đã đủ 2 giây
                    should_recognize = (current_time - last_recognition_time) >= recognition_interval
                    
                    for (x, y, w, h) in faces:
                        # Luôn vẽ box phát hiện face
                        color = (0, 255, 255)  # Yellow for detected face
                        label = f"Face Detected"
                        
                        # Thực hiện nhận diện AI nếu đã đủ thời gian
                        if should_recognize and self._check_model_ready():
                            try:
                                # TỐI ƯU HÓA: Chỉ xử lý vùng face thay vì toàn bộ frame
                                # Crop vùng face với padding nhẹ
                                padding = 20
                                face_x_start = max(0, x - padding)
                                face_y_start = max(0, y - padding)
                                face_x_end = min(frame.shape[1], x + w + padding)
                                face_y_end = min(frame.shape[0], y + h + padding)
                                
                                face_region = frame[face_y_start:face_y_end, face_x_start:face_x_end]
                                
                                # Convert vùng face to base64 (nhanh hơn nhiều)
                                ret, buffer = cv2.imencode('.jpg', face_region, [cv2.IMWRITE_JPEG_QUALITY, 85])
                                if not ret:
                                    continue
                                
                                import base64
                                face_b64 = base64.b64encode(buffer).decode('utf-8')
                                
                                # Gọi hàm nhận diện với confidence threshold phù hợp thực tế
                                result = recognize_face_from_image(face_b64, confidence_threshold=110)  # Cao hơn 100 một chút để lọc kết quả tốt
                                
                                if result and result.get('success', False) and result.get('faces'):
                                    # Xử lý kết quả nhận diện
                                    for face_data in result['faces']:
                                        # Kiểm tra có nhận diện được không
                                        if face_data.get('status') == 'recognized':
                                            student_id = face_data['mssv']
                                            confidence = face_data.get('confidence', 0)
                                            
                                            # Lấy vị trí face từ bbox - ĐIỀU CHỈNH OFFSET
                                            bbox = face_data.get('bbox', {})
                                            if bbox:
                                                # Điều chỉnh tọa độ về frame gốc
                                                face_x = face_x_start + bbox.get('x', 0)
                                                face_y = face_y_start + bbox.get('y', 0)
                                                face_w = bbox.get('w', w)
                                                face_h = bbox.get('h', h)
                                            else:
                                                face_x, face_y, face_w, face_h = x, y, w, h
                                            
                                            # Kiểm tra đã điểm danh chưa
                                            if student_id in self.marked_students:
                                                color = (0, 255, 0)  # Green
                                                label = f"{student_id} - DA DIEM DANH"
                                                # Log duplicate
                                                self.add_recognition_log('duplicate', student_id, student_id, confidence, 'Sinh viên đã điểm danh trước đó')
                                            else:
                                                # Kiểm tra confidence threshold - ĐIỀU CHỈNH CHO THỰC TẾ 85-95
                                                if 85 <= confidence <= 100:  # Cho phép điểm danh với confidence 85-100
                                                    color = (0, 255, 255)  # Yellow
                                                    label = f"{student_id} ({confidence:.1f})"
                                                    
                                                    # Lưu điểm danh
                                                    success = self.save_attendance(student_id, confidence)
                                                    if success:
                                                        self.marked_students.add(student_id)
                                                        self.logger.info(f"Attendance saved for {student_id} (confidence: {confidence:.1f})")
                                                        color = (0, 255, 0)  # Green
                                                        label = f"{student_id} - DIEM DANH OK"
                                                        # Log success
                                                        self.add_recognition_log('success', student_id, student_id, confidence, 'Điểm danh thành công')
                                                elif confidence < 85:
                                                    color = (255, 0, 0)  # Blue
                                                    label = f"{student_id} (Low: {confidence:.1f})"
                                                    # Log failed
                                                    self.add_recognition_log('failed', student_id, student_id, confidence, f'Độ tin cậy thấp (<85): {confidence:.1f}')
                                                else:  # confidence > 100
                                                    color = (255, 0, 0)  # Blue  
                                                    label = f"{student_id} (High: {confidence:.1f})"
                                                    # Log failed
                                                    self.add_recognition_log('failed', student_id, student_id, confidence, f'Độ tin cậy quá cao (>100): {confidence:.1f}')
                                            
                                            # Vẽ box và label
                                            cv2.rectangle(frame, (face_x, face_y), (face_x + face_w, face_y + face_h), color, 3)
                                            cv2.putText(frame, label, (face_x, face_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                                            
                                        else:
                                            # Không nhận diện được (status != 'recognized')
                                            bbox = face_data.get('bbox', {})
                                            if bbox:
                                                # Điều chỉnh tọa độ về frame gốc
                                                face_x = face_x_start + bbox.get('x', 0)
                                                face_y = face_y_start + bbox.get('y', 0)
                                                face_w = bbox.get('w', w)
                                                face_h = bbox.get('h', h)
                                            else:
                                                face_x, face_y, face_w, face_h = x, y, w, h
                                            
                                            color = (0, 0, 255)  # Red
                                            label = "KHONG XAC DINH"
                                            cv2.rectangle(frame, (face_x, face_y), (face_x + face_w, face_y + face_h), color, 3)
                                            cv2.putText(frame, label, (face_x, face_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                                            # Log unknown face
                                            self.add_recognition_log('failed', None, 'Unknown', face_data.get('confidence', 0), 'Không nhận diện được')
                                
                                elif result and result.get('success', False) and len(result.get('faces', [])) == 0:
                                    # Không phát hiện khuôn mặt từ AI
                                    pass  # Sử dụng detection từ cascade
                                
                                else:
                                    # Lỗi AI hoặc không có kết quả
                                    color = (128, 128, 128)  # Gray
                                    label = "Recognition Failed"
                                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                                    cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                                    
                                # Cập nhật thời gian sau khi nhận diện
                                last_recognition_time = current_time
                                    
                            except Exception as model_error:
                                self.logger.error(f"AI model error: {model_error}")
                                color = (255, 0, 0)  # Blue
                                label = "Model Error"
                                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                                last_recognition_time = current_time  # Cập nhật thời gian dù có lỗi
                        else:
                            # Không có AI model hoặc chưa đủ thời gian
                            if should_recognize:
                                color = (255, 255, 0)  # Cyan
                                label = "Face - No AI Model"
                            else:
                                color = (128, 128, 128)  # Gray
                                label = f"Face - Wait {time_to_next:.1f}s"
                            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                else:
                    # No faces detected
                    cv2.putText(frame, "Khong phat hien khuon mat", (10, 180), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    # Log detection status occasionally
                    if hasattr(self, 'last_detection_log_time'):
                        if time.time() - self.last_detection_log_time > 5:  # Every 5 seconds
                            self.add_recognition_log('detection', None, None, None, 'Không phát hiện khuôn mặt')
                            self.last_detection_log_time = time.time()
                    else:
                        self.last_detection_log_time = time.time()
            
            except Exception as e:
                self.logger.error(f"Face detection error: {e}")
                cv2.putText(frame, f"Loi nhan dien: {str(e)[:50]}", (10, 180), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Thêm delay nhỏ để tránh tải CPU quá cao
            time.sleep(0.1)  # 100ms delay giữa các frame
    
    def save_attendance(self, student_id, confidence=0.85):
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
                # Lưu bản ghi điểm danh với confidence score thực tế
                conn.execute('''
                    INSERT INTO attendance_records (session_id, student_id, attendance_time, method, confidence, status)
                    VALUES (?, ?, datetime('now'), 'face_recognition_auto', ?, 'present')
                ''', (self.session_id, student_record['id'], confidence))  # Lưu confidence thực tế 85-100
                
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
    
    def _check_model_ready(self):
        """Kiểm tra model đã sẵn sàng hay chưa - CÓ CACHE ĐỂ TRÁNH LAG"""
        current_time = time.time()
        
        # Sử dụng cache nếu còn hiệu lực
        if (self._model_ready_cache is not None and 
            current_time - self._model_check_time < self._model_cache_timeout):
            return self._model_ready_cache
        
        # Kiểm tra lại model
        try:
            from utils.face_recognition_utils import load_trained_model
            recognizer, detector, id_to_mssv, error = load_trained_model()
            result = error is None and recognizer is not None
            
            # Cache kết quả
            self._model_ready_cache = result
            self._model_check_time = current_time
            
            return result
        except Exception as e:
            self.logger.error(f"Error checking model ready: {e}")
            # Cache kết quả false
            self._model_ready_cache = False
            self._model_check_time = current_time
            return False


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
