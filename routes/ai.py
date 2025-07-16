"""
AI Management Routes with Simple Face Recognition
Quản lý training và nhận diện AI với thuật toán đơn giản LBPH
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import os
import json
import sqlite3
import cv2
import numpy as np
import pickle
from PIL import Image
import base64
import io
from datetime import datetime

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

def get_model_info():
    """Lấy thông tin model đơn giản"""
    trainer_path = os.path.join('uploads', 'trainer.yml')
    labels_path = os.path.join('uploads', 'labels.pickle')
    
    info = {
        'is_trained': os.path.exists(trainer_path) and os.path.exists(labels_path),
        'model_path': trainer_path,
        'labels_path': labels_path,
        'total_students': 0,
        'students': []
    }
    
    if info['is_trained']:
        try:
            with open(labels_path, 'rb') as f:
                label_ids = pickle.load(f)
            info['total_students'] = len(label_ids)
            info['students'] = list(label_ids.keys())
        except:
            info['is_trained'] = False
    
    return info

def train_simple_model():
    """Train model đơn giản theo mẫu LBPHFaceRecognizer"""
    try:
        # Kiểm tra xem cv2.face có sẵn không
        try:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            return {
                'success': False, 
                'message': 'Lỗi: opencv-contrib-python chưa được cài đặt. Vui lòng chạy: pip install opencv-contrib-python'
            }
        except Exception:
            return {
                'success': False, 
                'message': 'Lỗi: Không thể tạo LBPH Face Recognizer. Vui lòng cài đặt opencv-contrib-python'
            }
        
        detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        x_train, y_labels, label_ids = [], [], {}
        current_id = 0
        
        # Đường dẫn thư mục faces (dataset)
        faces_dir = os.path.join('uploads', 'faces')
        
        if not os.path.exists(faces_dir):
            return {'success': False, 'message': 'Thư mục faces không tồn tại'}
        
        # Duyệt qua tất cả thư mục sinh viên (giống os.walk)
        for student_id in os.listdir(faces_dir):
            student_dir = os.path.join(faces_dir, student_id)
            if not os.path.isdir(student_dir):
                continue
                
            # Gán ID cho sinh viên
            if student_id not in label_ids:
                label_ids[student_id] = current_id
                current_id += 1
            
            id_ = label_ids[student_id]
            
            # Duyệt qua tất cả file ảnh trong thư mục sinh viên
            for file in os.listdir(student_dir):
                if file.endswith('.jpg'):
                    path = os.path.join(student_dir, file)
                    
                    # Đọc ảnh và chuyển sang grayscale (giống mẫu)
                    image = Image.open(path).convert("L")
                    image_np = np.array(image, "uint8")
                    
                    # Detect faces trong ảnh
                    faces = detector.detectMultiScale(image_np, 1.3, 5)
                    
                    # Thêm từng khuôn mặt vào training data
                    for (x, y, w, h) in faces:
                        x_train.append(image_np[y:y+h, x:x+w])
                        y_labels.append(id_)
        
        if len(x_train) == 0:
            return {'success': False, 'message': 'Không tìm thấy dữ liệu training'}
        
        # Lưu labels (giống mẫu)
        labels_path = os.path.join('uploads', 'labels.pickle')
        with open(labels_path, 'wb') as f:
            pickle.dump(label_ids, f)
        
        # Train model (giống mẫu)
        recognizer.train(x_train, np.array(y_labels))
        
        # Lưu model (giống mẫu)
        trainer_path = os.path.join('uploads', 'trainer.yml')
        recognizer.save(trainer_path)
        
        return {
            'success': True,
            'message': f'Huấn luyện xong! Đã train với {len(x_train)} ảnh của {len(label_ids)} sinh viên',
            'training_info': {
                'total_images': len(x_train),
                'total_students': len(label_ids),
                'students': list(label_ids.keys())
            }
        }
        
    except Exception as e:
        return {'success': False, 'message': f'Lỗi training: {str(e)}'}

def recognize_simple_face(image_data):
    """Nhận diện khuôn mặt sử dụng hàm thống nhất với độ tin cậy phù hợp thực tế (ngưỡng 105)"""
    try:
        # Sử dụng hàm nhận diện thống nhất
        from utils.face_recognition_utils import recognize_face_from_image
        
        # Nhận diện với confidence threshold = 105 (hơi cao hơn thực tế 85-95 để cân bằng)
        result = recognize_face_from_image(image_data, confidence_threshold=105)
        
        if result['success']:
            # Chuyển đổi format để tương thích với frontend
            faces = []
            for face in result['faces']:
                faces.append({
                    'student_id': face['mssv'],
                    'confidence': face['confidence'],
                    'bbox': face['bbox'],
                    'status': face['status']
                })
            
            return {
                'success': True,
                'message': result['message'],
                'faces': faces,
                'face_count': len(faces)
            }
        else:
            return {
                'success': False,
                'message': result['message'],
                'face_count': 0,
                'faces': []
            }
        
    except Exception as e:
        return {'success': False, 'message': f'Lỗi nhận diện: {str(e)}', 'face_count': 0, 'faces': []}

@ai_bp.route('/')
def dashboard():
    """AI Dashboard đơn giản"""
    model_info = get_model_info()
    
    # Lấy thông tin sinh viên từ database
    conn = sqlite3.connect('attendance_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, full_name FROM students")
    students_db = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    
    # Kiểm tra số lượng ảnh của từng sinh viên
    faces_folder = "uploads/faces"
    student_stats = []
    
    if os.path.exists(faces_folder):
        for student_id in os.listdir(faces_folder):
            student_folder = os.path.join(faces_folder, student_id)
            if os.path.isdir(student_folder):
                image_count = len([f for f in os.listdir(student_folder) 
                                 if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
                
                # Kiểm tra xem sinh viên này có trong model chưa
                is_trained = student_id in model_info['students']
                
                student_name = students_db.get(student_id, f"Student {student_id}")
                
                student_stats.append({
                    'student_id': student_id,
                    'student_name': student_name,
                    'image_count': image_count,
                    'is_trained': is_trained
                })
    
    return render_template('ai/dashboard.html', 
                         model_info=model_info,
                         student_stats=student_stats)

@ai_bp.route('/train', methods=['POST'])
def train_model():
    """Train model đơn giản"""
    try:
        result = train_simple_model()
        
        if result['success']:
            flash(f"✅ {result['message']}", 'success')
        else:
            flash(f"❌ {result['message']}", 'error')
            
        return redirect(url_for('ai.dashboard'))
        
    except Exception as e:
        flash(f"❌ Lỗi khi train model: {str(e)}", 'error')
        return redirect(url_for('ai.dashboard'))

@ai_bp.route('/train/<student_id>', methods=['POST'])
def train_student(student_id):
    """Train model cho một sinh viên cụ thể (sử dụng train chung)"""
    try:
        result = train_simple_model()
        
        if result['success']:
            flash(f"✅ Model đã được train với dữ liệu mới", 'success')
        else:
            flash(f"❌ {result['message']}", 'error')
            
        return redirect(url_for('ai.dashboard'))
        
    except Exception as e:
        flash(f"❌ Lỗi khi train model: {str(e)}", 'error')
        return redirect(url_for('ai.dashboard'))

@ai_bp.route('/api/recognize', methods=['POST'])
def api_recognize_face():
    """API nhận diện khuôn mặt đơn giản"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image data provided'
            })
        
        result = recognize_simple_face(image_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error in face recognition: {str(e)}',
            'face_count': 0,
            'faces': []
        })

@ai_bp.route('/api/model_info')
def api_model_info():
    """API lấy thông tin model"""
    try:
        info = get_model_info()
        return jsonify({
            'success': True,
            'data': info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@ai_bp.route('/test')
def test():
    """Trang test nhận diện khuôn mặt"""
    model_info = get_model_info()
    return render_template('ai/test_recognition.html', model_info=model_info)

@ai_bp.route('/api/test_recognize', methods=['POST'])
def api_test_recognize():
    """API test nhận diện khuôn mặt với thông tin chi tiết"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image data provided'
            })
        
        result = recognize_simple_face(image_data)
        
        # Thêm thông tin chi tiết cho test
        if result['success'] and result.get('faces'):
            for face in result['faces']:
                if face.get('student_id') and face['student_id'] != 'Unknown':
                    # Lấy thông tin sinh viên từ database
                    try:
                        conn = sqlite3.connect('attendance_system.db')
                        cursor = conn.cursor()
                        cursor.execute("SELECT full_name, class_id FROM students WHERE student_id = ?", (face['student_id'],))
                        student_data = cursor.fetchone()
                        if student_data:
                            face['student_info'] = {
                                'full_name': student_data[0],
                                'class_id': student_data[1]
                            }
                        conn.close()
                    except:
                        face['student_info'] = {'full_name': face['student_id']}
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error in face recognition test: {str(e)}',
            'face_count': 0,
            'faces': []
        })

@ai_bp.route('/settings')
def settings():
    """Trang cài đặt AI model"""
    model_info = get_model_info()
    return render_template('ai/settings.html', model_info=model_info)

@ai_bp.route('/api/reset_model', methods=['POST'])
def api_reset_model():
    """API reset model (xóa toàn bộ dữ liệu đã train)"""
    try:
        trainer_path = os.path.join('uploads', 'trainer.yml')
        labels_path = os.path.join('uploads', 'labels.pickle')
        
        # Xóa file model
        if os.path.exists(trainer_path):
            os.remove(trainer_path)
        if os.path.exists(labels_path):
            os.remove(labels_path)
        
        return jsonify({
            'success': True,
            'message': 'Model đã được reset thành công'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi khi reset model: {str(e)}'
        })

@ai_bp.route('/debug_model')
def debug_model():
    """Debug thông tin chi tiết của model"""
    model_info = get_model_info()
    
    # Thêm thống kê chi tiết
    debug_info = {
        'model_status': model_info,
        'simple_lbph_model': True,
        'model_files': {
            'trainer_yml': os.path.exists(os.path.join('uploads', 'trainer.yml')),
            'labels_pickle': os.path.exists(os.path.join('uploads', 'labels.pickle')),
        }
    }
    
    return render_template('ai/debug_model.html', debug_info=debug_info)

@ai_bp.route('/test_accuracy')
def test_accuracy():
    """Test độ chính xác của model đơn giản"""
    model_info = get_model_info()
    
    if not model_info['is_trained']:
        result = {
            'success': False,
            'message': 'Model chưa được train',
            'accuracy': 0,
            'total_tests': 0,
            'correct_predictions': 0
        }
    else:
        # Thực hiện test đơn giản
        result = test_simple_accuracy()
    
    return render_template('ai/test_accuracy.html', result=result)

@ai_bp.route('/api/test_accuracy', methods=['POST'])
def api_test_accuracy():
    """API test độ chính xác đơn giản"""
    try:
        model_info = get_model_info()
        
        if not model_info['is_trained']:
            return jsonify({
                'success': False,
                'message': 'Model chưa được train',
                'accuracy': 0
            })
        
        result = test_simple_accuracy()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi test accuracy: {str(e)}',
            'accuracy': 0
        })

def test_simple_accuracy():
    """Test độ chính xác model sử dụng hàm thống nhất với độ tin cậy phù hợp thực tế (ngưỡng 105)"""
    try:
        from utils.face_recognition_utils import recognize_face_from_image, load_trained_model
        
        # Kiểm tra model
        recognizer, detector, id_to_mssv, error = load_trained_model()
        if error:
            return {'success': False, 'message': error}
        
        # Test trên một số ảnh từ dataset
        faces_dir = os.path.join('uploads', 'faces')
        
        if not os.path.exists(faces_dir):
            return {'success': False, 'message': 'Thư mục faces không tồn tại'}
        
        total_tests = 0
        correct_predictions = 0
        test_results = []
        
        # Test trên từng student
        for student_id in os.listdir(faces_dir):
            student_dir = os.path.join(faces_dir, student_id)
            if not os.path.isdir(student_dir):
                continue
            
            # Lấy một vài ảnh để test (tối đa 3 ảnh)
            files = [f for f in os.listdir(student_dir) if f.endswith('.jpg')][:3]
            
            for file in files:
                path = os.path.join(student_dir, file)
                
                try:
                    # Đọc ảnh và chuyển thành base64
                    import base64
                    with open(path, 'rb') as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    
                    # Test nhận diện với confidence threshold = 105 (phù hợp thực tế 85-95)
                    result = recognize_face_from_image(img_data, confidence_threshold=105)
                    
                    total_tests += 1
                    predicted_student = 'Unknown'
                    confidence = 999
                    
                    if result['success'] and result['faces']:
                        for face in result['faces']:
                            if face['status'] == 'recognized':
                                predicted_student = face['mssv']
                                confidence = face['confidence']
                                break
                    
                    # Điều kiện nhận diện chính xác: predicted == actual và confidence < 105
                    is_correct = predicted_student == student_id and confidence < 105
                    
                    if is_correct:
                        correct_predictions += 1
                    
                    test_results.append({
                        'actual': student_id,
                        'predicted': predicted_student,
                        'confidence': confidence,
                        'correct': is_correct,
                        'file': file
                    })
                    
                except Exception as file_error:
                    # Bỏ qua file bị lỗi
                    continue
        
        accuracy = (correct_predictions / total_tests * 100) if total_tests > 0 else 0
        
        return {
            'success': True,
            'message': f'Test hoàn thành trên {total_tests} ảnh với confidence threshold = 105 (phù hợp thực tế 85-95)',
            'accuracy': round(accuracy, 2),
            'total_tests': total_tests,
            'correct_predictions': correct_predictions,
            'test_results': test_results[:10]  # Chỉ hiển thị 10 kết quả đầu
        }
        
    except Exception as e:
        return {'success': False, 'message': f'Lỗi test accuracy: {str(e)}'}
