"""
Face Recognition Utilities
Hàm nhận diện khuôn mặt thống nhất cho toàn bộ hệ thống
"""

import cv2
import pickle
import numpy as np
import os
import base64
import io
from PIL import Image
from datetime import datetime

def create_face_recognizer():
    """Tạo face recognizer và kiểm tra availability"""
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        return recognizer, None
    except AttributeError:
        return None, "opencv-contrib-python chưa được cài đặt. Vui lòng chạy: pip install opencv-contrib-python"

def load_trained_model(model_path="uploads/trainer.yml", labels_path="uploads/labels.pickle"):
    """Load trained model và labels"""
    try:
        # Kiểm tra files tồn tại
        if not os.path.exists(model_path) or not os.path.exists(labels_path):
            return None, None, None, "Model chưa được train"
        
        # Tạo recognizer
        recognizer, error = create_face_recognizer()
        if error:
            return None, None, None, error
        
        # Load model
        recognizer.read(model_path)
        
        # Load labels
        with open(labels_path, 'rb') as f:
            label_ids = pickle.load(f)
        
        # Tạo dict ngược để map ID về MSSV
        id_to_mssv = {v: k for k, v in label_ids.items()}
        
        # Tạo detector
        detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        return recognizer, detector, id_to_mssv, None
        
    except Exception as e:
        return None, None, None, f"Lỗi load model: {str(e)}"

def recognize_face_from_image(image_data, confidence_threshold=100):
    """
    Nhận diện khuôn mặt từ ảnh base64 - CẢI THIỆN ĐỘ CHÍNH XÁC
    
    Args:
        image_data: Base64 image data hoặc numpy array
        confidence_threshold: Ngưỡng confidence (mặc định 100) - ĐÂY LÀ DISTANCE/ERROR VALUE
                             Giá trị càng THẤP thì càng tin cậy (khác với percentage)
                             Thực tế: Confidence thường 85-95, nên:
                             - 100-110: Cân bằng (nhận diện tốt)
                             - 95-100: Dễ nhận diện (cho điểm danh)
                             - 110-120: Nghiêm ngặt (cho test)
    
    Returns:
        dict: {
            'success': bool,
            'faces': list of {'mssv': str, 'confidence': float, 'bbox': dict},
            'message': str
        }
    """
    try:
        # Load model
        recognizer, detector, id_to_mssv, error = load_trained_model()
        if error:
            return {'success': False, 'faces': [], 'message': error}
        
        # Xử lý ảnh input
        if isinstance(image_data, str):
            # Base64 string
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            # Numpy array
            frame = image_data
        
        if frame is None:
            return {'success': False, 'faces': [], 'message': 'Không thể đọc ảnh'}
        
        # Chuyển sang grayscale (giống mẫu)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # CẢI THIỆN CHẤT LƯỢNG ẢNH - PIPELINE TƯƠNG TỰ THU THẬP
        # 1. Histogram equalization
        gray = cv2.equalizeHist(gray)
        
        # 2. Giảm nhiễu
        gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 3. CLAHE để cải thiện local contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # 4. Gamma correction
        gamma = 1.1
        gray = np.power(gray / 255.0, gamma) * 255.0
        gray = np.uint8(np.clip(gray, 0, 255))
        
        # 5. Sharpening nhẹ
        kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
        gray_sharp = cv2.filter2D(gray, -1, kernel)
        gray = cv2.addWeighted(gray, 0.8, gray_sharp, 0.2, 0)
        
        # Detect faces với tham số tối ưu - NHIỀU PHƯƠNG PHÁP
        all_faces = []
        
        # Phương pháp 1: Chuẩn
        faces_1 = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50), maxSize=(400, 400))
        
        # Phương pháp 2: Nhạy cảm hơn
        faces_2 = detector.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=4, minSize=(40, 40), maxSize=(350, 350))
        
        # Phương pháp 3: Chính xác hơn
        faces_3 = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=6, minSize=(60, 60), maxSize=(300, 300))
        
        # Gộp và loại bỏ duplicate
        for faces_set in [faces_1, faces_2, faces_3]:
            for face in faces_set:
                # Kiểm tra xem face này có quá gần với face đã có không
                is_duplicate = False
                for existing_face in all_faces:
                    if abs(face[0] - existing_face[0]) < 30 and abs(face[1] - existing_face[1]) < 30:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    all_faces.append(face)
        
        faces = all_faces
        
        recognized_faces = []
        
        # Xử lý từng khuôn mặt với pipeline cải thiện
        for (x, y, w, h) in faces:
            # Crop ROI với padding nhẹ
            padding = 5
            x_start = max(0, x - padding)
            y_start = max(0, y - padding)
            x_end = min(gray.shape[1], x + w + padding)
            y_end = min(gray.shape[0], y + h + padding)
            
            roi = gray[y_start:y_end, x_start:x_end]
            
            # Resize ROI về kích thước chuẩn nếu cần (giống training)
            if roi.shape[0] != roi.shape[1]:
                # Make square
                max_dim = max(roi.shape[0], roi.shape[1])
                roi_square = np.zeros((max_dim, max_dim), dtype=np.uint8)
                roi_square[:roi.shape[0], :roi.shape[1]] = roi
                roi = roi_square
            
            # Resize về 128x128 (giống training)
            roi = cv2.resize(roi, (128, 128), interpolation=cv2.INTER_LANCZOS4)
            
            # Predict với ROI đã chuẩn hóa
            id_, conf = recognizer.predict(roi)
            
            # KIỂM TRA CONFIDENCE - THAY ĐỔI NGƯỠNG
            # Confidence thấp = nhận diện tốt
            # Confidence cao = không chắc chắn
            status = 'unidentified'
            mssv = 'KHONG XAC DINH'
            
            if conf < confidence_threshold:
                potential_mssv = id_to_mssv.get(id_, 'UNKNOWN')
                if potential_mssv != 'UNKNOWN':
                    mssv = potential_mssv
                    status = 'recognized'
                else:
                    mssv = 'UNKNOWN'
                    status = 'unknown'
            
            recognized_faces.append({
                'mssv': mssv,
                'confidence': float(conf),
                'bbox': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
                'status': status
            })
        
        # Thông báo chi tiết về kết quả
        total_faces = len(faces)
        recognized_count = len([f for f in recognized_faces if f["status"] == "recognized"])
        
        if total_faces == 0:
            message = "Không phát hiện khuôn mặt nào. Vui lòng đảm bảo khuôn mặt rõ ràng và đủ sáng."
        elif recognized_count == 0:
            message = f"Phát hiện {total_faces} khuôn mặt nhưng không nhận diện được ai. Có thể chưa thu thập dữ liệu hoặc model chưa chính xác."
        else:
            message = f"Phát hiện {total_faces} khuôn mặt, nhận diện được {recognized_count} sinh viên"
        
        return {
            'success': True,
            'faces': recognized_faces,
            'message': message
        }
        
    except Exception as e:
        return {'success': False, 'faces': [], 'message': f'Lỗi nhận diện: {str(e)}'}

def mark_attendance(mssv, subject_id, session_id=None):
    """
    Đánh dấu điểm danh cho sinh viên - logic giống code mẫu
    
    Args:
        mssv: Mã số sinh viên
        subject_id: ID môn học
        session_id: ID ca điểm danh (optional)
    
    Returns:
        dict: {'success': bool, 'message': str, 'timestamp': str}
    """
    try:
        import sqlite3
        
        # Kết nối database
        conn = sqlite3.connect('attendance_system.db')
        c = conn.cursor()
        
        # Timestamp (giống mẫu)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Kiểm tra sinh viên đã điểm danh chưa
        if session_id:
            # Kiểm tra theo session cụ thể
            c.execute("""
                SELECT id FROM attendance_records 
                WHERE student_id = (SELECT id FROM students WHERE student_id = ?) 
                AND session_id = ? 
                AND DATE(created_at) = DATE(?)
            """, (mssv, session_id, now))
        else:
            # Kiểm tra theo subject và ngày
            c.execute("""
                SELECT ar.id FROM attendance_records ar
                JOIN attendance_sessions ases ON ar.session_id = ases.id
                WHERE ar.student_id = (SELECT id FROM students WHERE student_id = ?) 
                AND ases.subject_id = ? 
                AND DATE(ar.created_at) = DATE(?)
            """, (mssv, subject_id, now))
        
        existing = c.fetchone()
        if existing:
            conn.close()
            return {
                'success': False, 
                'message': f'{mssv} đã điểm danh rồi',
                'timestamp': now
            }
        
        # Lấy thông tin sinh viên
        c.execute("SELECT id, full_name FROM students WHERE student_id = ?", (mssv,))
        student = c.fetchone()
        if not student:
            conn.close()
            return {
                'success': False, 
                'message': f'Không tìm thấy sinh viên {mssv}',
                'timestamp': now
            }
        
        student_db_id, student_name = student
        
        # Tìm session phù hợp
        if not session_id:
            # Tìm session active cho subject này
            c.execute("""
                SELECT id FROM attendance_sessions 
                WHERE subject_id = ? 
                AND is_active = 1 
                AND DATE(created_at) = DATE(?)
                ORDER BY created_at DESC LIMIT 1
            """, (subject_id, now))
            session_result = c.fetchone()
            if session_result:
                session_id = session_result[0]
            else:
                conn.close()
                return {
                    'success': False, 
                    'message': f'Không tìm thấy ca điểm danh active cho môn học',
                    'timestamp': now
                }
        
        # Insert attendance record (giống logic mẫu)
        c.execute("""
            INSERT INTO attendance_records (student_id, session_id, status, created_at) 
            VALUES (?, ?, 'present', ?)
        """, (student_db_id, session_id, now))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True, 
            'message': f'✅ {student_name} ({mssv}) điểm danh lúc {now}',
            'timestamp': now
        }
        
    except Exception as e:
        return {
            'success': False, 
            'message': f'Lỗi điểm danh: {str(e)}',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def recognize_and_mark_attendance(image_data, subject_id, session_id=None, confidence_threshold=98):
    """
    Nhận diện khuôn mặt và đánh dấu điểm danh - CẢI THIỆN ĐỘ TIN CẬY
    
    Args:
        image_data: Base64 image data
        subject_id: ID môn học
        confidence_threshold: Ngưỡng confidence (mặc định 98) - ĐÂY LÀ DISTANCE/ERROR VALUE
                             Thực tế confidence 85-95, nên 98 phù hợp cho điểm danh
        session_id: ID ca điểm danh
        confidence_threshold: Ngưỡng confidence (mặc định 120) - ĐÂY LÀ DISTANCE/ERROR VALUE
                             Giá trị càng THẤP thì càng tin cậy (khác với percentage)
                             Khuyến nghị: 80-120 cho cân bằng, 60-80 cho nhận diện nhiều, 120-150 cho chính xác cao
    
    Returns:
        dict: {
            'success': bool,
            'faces': list,
            'attendance_results': list,
            'message': str
        }
    """
    try:
        # Nhận diện khuôn mặt
        recognition_result = recognize_face_from_image(image_data, confidence_threshold)
        
        if not recognition_result['success']:
            return {
                'success': False,
                'faces': [],
                'attendance_results': [],
                'message': recognition_result['message']
            }
        
        faces = recognition_result['faces']
        attendance_results = []
        
        # Đánh dấu điểm danh cho từng khuôn mặt được nhận diện
        for face in faces:
            if face['status'] == 'recognized' and face['mssv'] != 'UNKNOWN':
                attendance_result = mark_attendance(face['mssv'], subject_id, session_id)
                attendance_results.append({
                    'mssv': face['mssv'],
                    'confidence': face['confidence'],
                    'attendance': attendance_result
                })
        
        # Tổng kết
        successful_marks = len([r for r in attendance_results if r['attendance']['success']])
        total_recognized = len([f for f in faces if f['status'] == 'recognized'])
        
        return {
            'success': True,
            'faces': faces,
            'attendance_results': attendance_results,
            'message': f'Nhận diện {len(faces)} khuôn mặt, điểm danh thành công {successful_marks}/{total_recognized} sinh viên'
        }
        
    except Exception as e:
        return {
            'success': False,
            'faces': [],
            'attendance_results': [],
            'message': f'Lỗi: {str(e)}'
        }
