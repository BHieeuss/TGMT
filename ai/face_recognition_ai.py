"""
Face Recognition AI Module
Xử lý training và nhận diện khuôn mặt sinh viên
"""

import os
import cv2
import numpy as np
import face_recognition
import pickle
from datetime import datetime
import sqlite3
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import logging
from typing import List, Tuple, Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceRecognitionAI:
    """Lớp chính xử lý nhận diện khuôn mặt"""
    
    def __init__(self, model_path="ai/models"):
        """
        Khởi tạo AI module
        Args:
            model_path: Đường dẫn lưu model
        """
        self.model_path = model_path
        self.encodings_file = os.path.join(model_path, "face_encodings.pkl")
        self.model_file = os.path.join(model_path, "face_classifier.pkl")
        self.label_encoder_file = os.path.join(model_path, "label_encoder.pkl")
        
        # Tạo thư mục models nếu chưa có
        os.makedirs(model_path, exist_ok=True)
        
        # Initialize models
        self.face_encodings = []
        self.face_labels = []
        self.classifier = None
        self.label_encoder = None
        
        # Load existing model if available
        self.load_model()
    
    def load_model(self):
        """Load model đã train từ file"""
        try:
            if os.path.exists(self.encodings_file):
                with open(self.encodings_file, 'rb') as f:
                    data = pickle.load(f)
                    self.face_encodings = data['encodings']
                    self.face_labels = data['labels']
                logger.info(f"Đã load {len(self.face_encodings)} face encodings")
            
            if os.path.exists(self.model_file):
                with open(self.model_file, 'rb') as f:
                    self.classifier = pickle.load(f)
                logger.info("Đã load face classifier")
            
            if os.path.exists(self.label_encoder_file):
                with open(self.label_encoder_file, 'rb') as f:
                    self.label_encoder = pickle.load(f)
                logger.info("Đã load label encoder")
                
        except Exception as e:
            logger.error(f"Lỗi khi load model: {str(e)}")
    
    def save_model(self):
        """Lưu model sau khi train"""
        try:
            # Save encodings
            with open(self.encodings_file, 'wb') as f:
                pickle.dump({
                    'encodings': self.face_encodings,
                    'labels': self.face_labels
                }, f)
            
            # Save classifier
            if self.classifier:
                with open(self.model_file, 'wb') as f:
                    pickle.dump(self.classifier, f)
            
            # Save label encoder
            if self.label_encoder:
                with open(self.label_encoder_file, 'wb') as f:
                    pickle.dump(self.label_encoder, f)
            
            logger.info("Đã lưu model thành công")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu model: {str(e)}")
    
    def extract_faces_from_folder(self, student_folder: str, student_id: str) -> List[np.ndarray]:
        """
        Trích xuất face encodings từ thư mục ảnh của sinh viên
        Args:
            student_folder: Đường dẫn thư mục ảnh sinh viên
            student_id: MSSV
        Returns:
            List face encodings
        """
        encodings = []
        
        if not os.path.exists(student_folder):
            logger.warning(f"Thư mục không tồn tại: {student_folder}")
            return encodings
        
        image_files = [f for f in os.listdir(student_folder) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        logger.info(f"Đang xử lý {len(image_files)} ảnh cho sinh viên {student_id}")
        
        for i, image_file in enumerate(image_files):
            try:
                image_path = os.path.join(student_folder, image_file)
                
                # Load ảnh
                image = cv2.imread(image_path)
                if image is None:
                    continue
                
                # Convert BGR to RGB
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Detect faces và extract encodings
                face_locations = face_recognition.face_locations(rgb_image)
                face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                
                if face_encodings:
                    # Chỉ lấy face đầu tiên nếu có nhiều face
                    encodings.append(face_encodings[0])
                    logger.debug(f"Đã extract encoding từ {image_file}")
                else:
                    logger.warning(f"Không phát hiện face trong {image_file}")
                    
            except Exception as e:
                logger.error(f"Lỗi khi xử lý {image_file}: {str(e)}")
                continue
        
        logger.info(f"Đã extract {len(encodings)} face encodings cho sinh viên {student_id}")
        return encodings
    
    def train_model(self, faces_folder: str = "uploads/faces") -> Dict:
        """
        Train model nhận diện khuôn mặt từ dữ liệu trong thư mục faces
        Args:
            faces_folder: Đường dẫn thư mục chứa ảnh faces
        Returns:
            Dict kết quả training
        """
        logger.info("Bắt đầu training model...")
        
        # Reset data
        self.face_encodings = []
        self.face_labels = []
        
        if not os.path.exists(faces_folder):
            return {
                'success': False,
                'message': f'Thư mục {faces_folder} không tồn tại'
            }
        
        # Duyệt qua từng thư mục sinh viên
        student_folders = [f for f in os.listdir(faces_folder) 
                          if os.path.isdir(os.path.join(faces_folder, f))]
        
        if not student_folders:
            return {
                'success': False,
                'message': 'Không có dữ liệu training nào'
            }
        
        total_encodings = 0
        students_processed = 0
        
        for student_id in student_folders:
            student_path = os.path.join(faces_folder, student_id)
            
            # Extract encodings cho sinh viên này
            encodings = self.extract_faces_from_folder(student_path, student_id)
            
            if encodings:
                self.face_encodings.extend(encodings)
                self.face_labels.extend([student_id] * len(encodings))
                total_encodings += len(encodings)
                students_processed += 1
                logger.info(f"Đã xử lý sinh viên {student_id}: {len(encodings)} encodings")
        
        if total_encodings == 0:
            return {
                'success': False,
                'message': 'Không có face encoding nào được tạo'
            }
        
        logger.info(f"Tổng cộng: {total_encodings} encodings từ {students_processed} sinh viên")
        
        # Train classifier
        try:
            # Encode labels
            self.label_encoder = LabelEncoder()
            encoded_labels = self.label_encoder.fit_transform(self.face_labels)
            
            # Convert encodings to numpy array
            X = np.array(self.face_encodings)
            y = encoded_labels
            
            # Split data for validation
            if len(X) > 10:  # Chỉ split nếu có đủ dữ liệu
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y
                )
            else:
                X_train, X_test, y_train, y_test = X, X, y, y
            
            # Train SVM classifier
            self.classifier = SVC(
                kernel='rbf',
                probability=True,
                gamma='scale',
                C=1.0
            )
            
            self.classifier.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = self.classifier.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Save model
            self.save_model()
            
            logger.info(f"Training hoàn thành với độ chính xác: {accuracy:.2%}")
            
            return {
                'success': True,
                'message': 'Training thành công!',
                'stats': {
                    'total_students': students_processed,
                    'total_images': total_encodings,
                    'accuracy': f"{accuracy:.2%}",
                    'model_saved': True
                }
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi training classifier: {str(e)}")
            return {
                'success': False,
                'message': f'Lỗi training: {str(e)}'
            }
    
    def recognize_face(self, image_data, confidence_threshold=0.6) -> Dict:
        """
        Nhận diện khuôn mặt từ ảnh
        Args:
            image_data: Dữ liệu ảnh (base64 hoặc numpy array)
            confidence_threshold: Ngưỡng tin cậy
        Returns:
            Dict kết quả nhận diện
        """
        try:
            # Xử lý input image
            if isinstance(image_data, str):
                # Base64 string
                if 'data:image' in image_data:
                    image_data = image_data.split(',')[1]
                
                image_bytes = base64.b64decode(image_data)
                image = cv2.imdecode(
                    np.frombuffer(image_bytes, np.uint8), 
                    cv2.IMREAD_COLOR
                )
            else:
                image = image_data
            
            if image is None:
                return {
                    'success': False,
                    'message': 'Không thể đọc ảnh'
                }
            
            # Convert to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_image)
            
            if not face_locations:
                return {
                    'success': False,
                    'message': 'Không phát hiện khuôn mặt trong ảnh'
                }
            
            # Extract encodings
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            if not face_encodings:
                return {
                    'success': False,
                    'message': 'Không thể extract face encoding'
                }
            
            # Predict với classifier
            if not self.classifier or not self.label_encoder:
                return {
                    'success': False,
                    'message': 'Model chưa được train. Vui lòng train model trước.'
                }
            
            results = []
            
            for i, face_encoding in enumerate(face_encodings):
                # Predict
                probabilities = self.classifier.predict_proba([face_encoding])[0]
                best_match_index = np.argmax(probabilities)
                confidence = probabilities[best_match_index]
                
                if confidence >= confidence_threshold:
                    student_id = self.label_encoder.inverse_transform([best_match_index])[0]
                    
                    # Get student info from database
                    student_info = self.get_student_info(student_id)
                    
                    results.append({
                        'student_id': student_id,
                        'student_name': student_info.get('name', 'Không rõ'),
                        'confidence': float(confidence),
                        'face_location': face_locations[i]
                    })
                else:
                    results.append({
                        'student_id': 'unknown',
                        'student_name': 'Không nhận diện được',
                        'confidence': float(confidence),
                        'face_location': face_locations[i]
                    })
            
            return {
                'success': True,
                'face_count': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi nhận diện: {str(e)}")
            return {
                'success': False,
                'message': f'Lỗi nhận diện: {str(e)}'
            }
    
    def get_student_info(self, student_id: str) -> Dict:
        """Lấy thông tin sinh viên từ database"""
        try:
            conn = sqlite3.connect('attendance_system.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT student_id, full_name, class_id 
                FROM students 
                WHERE student_id = ?
            """, (student_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'name': result[1],
                    'class_id': result[2]
                }
            else:
                return {'id': student_id, 'name': 'Không rõ', 'class_id': None}
                
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin sinh viên: {str(e)}")
            return {'id': student_id, 'name': 'Không rõ', 'class_id': None}
    
    def get_model_info(self) -> Dict:
        """Lấy thông tin model hiện tại"""
        return {
            'model_trained': self.classifier is not None,
            'total_students': len(set(self.face_labels)) if self.face_labels else 0,
            'total_encodings': len(self.face_encodings),
            'model_path': self.model_path,
            'files_exist': {
                'encodings': os.path.exists(self.encodings_file),
                'classifier': os.path.exists(self.model_file),
                'label_encoder': os.path.exists(self.label_encoder_file)
            }
        }

# Tạo instance global
face_ai = FaceRecognitionAI()
