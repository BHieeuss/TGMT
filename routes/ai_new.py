"""
AI Management Routes
Quản lý training và nhận diện AI
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models.face_recognition_model import face_model
import os
import json
from datetime import datetime

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

@ai_bp.route('/')
def dashboard():
    """AI Dashboard - hiển thị thông tin model và tùy chọn training"""
    model_info = face_model.get_model_info()
    
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
                is_trained = student_id in [sid for sid, name in model_info.get('students', [])]
                
                student_info = face_model.get_student_info(student_id)
                student_name = student_info['full_name'] if student_info else f"Student {student_id}"
                
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
        result = face_model.train_from_folder()
        
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
    """Train model cho một sinh viên cụ thể"""
    try:
        result = face_model.add_student_to_model(student_id)
        
        if result['success']:
            flash(f"✅ {result['message']}", 'success')
        else:
            flash(f"❌ {result['message']}", 'error')
            
        return redirect(url_for('ai.dashboard'))
        
    except Exception as e:
        flash(f"❌ Lỗi khi train sinh viên {student_id}: {str(e)}", 'error')
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
def test_recognition():
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
        if result['success'] and result['faces']:
            for face in result['faces']:
                if face['student_id']:
                    student_info = face_model.get_student_info(face['student_id'])
                    if student_info:
                        face['student_info'] = student_info
        
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
        face_model.known_face_encodings = []
        face_model.known_face_names = []
        face_model.known_face_ids = []
        
        return jsonify({
            'success': True,
            'message': 'Model đã được reset thành công'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi khi reset model: {str(e)}'
        })
