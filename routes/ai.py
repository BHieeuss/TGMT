"""
AI Management Routes with Advanced Face Recognition
Quản lý training và nhận diện AI với thuật toán nâng cao
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models.advanced_face_model import face_model
import os
import json
import sqlite3
from datetime import datetime

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

@ai_bp.route('/')
def dashboard():
    """AI Dashboard - hiển thị thông tin model và tùy chọn training"""
    model_info = face_model.get_model_info()
    
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
                
                # Kiểm tra xem sinh viên này đã được train chưa
                is_trained = student_id in face_model.student_to_label
                
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
    """Train toàn bộ model từ tất cả dữ liệu ảnh"""
    try:
        result = face_model.train_model()
        
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
        result = face_model.train_model()
        
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
    """API nhận diện khuôn mặt"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image data provided'
            })
        
        result = face_model.recognize_face(image_data)
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
        info = face_model.get_model_info()
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
    model_info = face_model.get_model_info()
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
        
        result = face_model.recognize_face(image_data)
        
        # Thêm thông tin chi tiết cho test
        if result['success'] and result.get('faces'):
            for face in result['faces']:
                if face.get('student_id'):
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
    model_info = face_model.get_model_info()
    return render_template('ai/settings.html', model_info=model_info)

@ai_bp.route('/api/reset_model', methods=['POST'])
def api_reset_model():
    """API reset model (xóa toàn bộ dữ liệu đã train)"""
    try:
        # Xóa file model
        if os.path.exists(face_model.model_path):
            os.remove(face_model.model_path)
        
        # Reset model data trong memory
        face_model.knn_classifier = None
        face_model.label_to_student = {}
        face_model.student_to_label = {}
        face_model.is_trained = False
        
        return jsonify({
            'success': True,
            'message': 'Model đã được reset thành công'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi khi reset model: {str(e)}'
        })

@ai_bp.route('/test_accuracy')
def test_accuracy():
    """Test độ chính xác của model"""
    result = face_model.test_recognition_accuracy()
    return render_template('ai/test_accuracy.html', result=result)

@ai_bp.route('/api/test_accuracy', methods=['POST'])
def api_test_accuracy():
    """API test độ chính xác"""
    result = face_model.test_recognition_accuracy()
    return jsonify(result)

@ai_bp.route('/debug_model')
def debug_model():
    """Debug thông tin chi tiết của model"""
    model_info = face_model.get_model_info()
    
    # Thêm thống kê chi tiết
    debug_info = {
        'model_status': model_info,
        'face_cascade_loaded': face_model.face_cascade is not None,
        'model_components': {
            'knn_classifier': face_model.knn_classifier is not None,
            'svm_classifier': face_model.svm_classifier is not None,
            'ensemble_classifier': face_model.ensemble_classifier is not None,
            'scaler': face_model.scaler is not None,
            'label_encoder': face_model.label_encoder is not None
        }
    }
    
    return render_template('ai/debug_model.html', debug_info=debug_info)

@ai_bp.route('/api/recognize_advanced', methods=['POST'])
def api_recognize_advanced():
    """API nhận diện với tùy chọn ensemble hoặc KNN only"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        use_ensemble = data.get('use_ensemble', True)
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image data provided'
            })
        
        result = face_model.recognize_face(image_data, use_ensemble=use_ensemble)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Recognition error: {str(e)}'
        })
