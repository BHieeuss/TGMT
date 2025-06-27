"""
Advanced Face Recognition Model using OpenCV with Multiple Algorithms
Sử dụng OpenCV kết hợp nhiều thuật toán để train và nhận diện khuôn mặt chính xác cao
"""
import cv2
import os
import numpy as np
import pickle
import json
from datetime import datetime
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from scipy import ndimage
from scipy.spatial.distance import euclidean
import sqlite3
import logging

class AdvancedFaceModel:
    def __init__(self, model_path="models/advanced_face_model.pkl"):
        self.model_path = model_path
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize multiple classifiers for ensemble
        self.knn_classifier = None
        self.svm_classifier = None
        self.ensemble_classifier = None
        self.scaler = None
        self.label_encoder = None
        
        # Model parameters
        self.image_size = (120, 120)
        self.confidence_threshold = 0.4
        self.ensemble_threshold = 0.6
        
        # Training data storage
        self.features = []
        self.labels = []
        self.student_to_label = {}
        self.label_to_student = {}
        self.is_trained = False
        
        # Load existing model if available
        self.load_model()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def augment_image(self, img, num_augmentations=5):
        """Tạo dữ liệu augmentation để tăng độ chính xác"""
        augmented_images = [img]  # Original image
        
        for _ in range(num_augmentations):
            augmented = img.copy()
            
            # Random rotation (-15 to 15 degrees)
            angle = np.random.uniform(-15, 15)
            M = cv2.getRotationMatrix2D((img.shape[1]//2, img.shape[0]//2), angle, 1)
            augmented = cv2.warpAffine(augmented, M, (img.shape[1], img.shape[0]))
            
            # Random brightness adjustment
            brightness = np.random.uniform(0.8, 1.2)
            augmented = cv2.convertScaleAbs(augmented, alpha=brightness, beta=0)
            
            # Random contrast adjustment
            contrast = np.random.uniform(0.8, 1.2)
            augmented = cv2.convertScaleAbs(augmented, alpha=contrast, beta=0)
            
            # Random noise
            noise = np.random.normal(0, 0.1, augmented.shape).astype(np.uint8)
            augmented = cv2.add(augmented, noise)
            
            # Random gaussian blur
            if np.random.random() > 0.5:
                augmented = cv2.GaussianBlur(augmented, (3, 3), 0)
            
            augmented_images.append(augmented)
        
        return augmented_images
    
    def extract_advanced_features(self, face_img):
        """Trích xuất features nâng cao từ khuôn mặt"""
        # Resize to standard size
        face_resized = cv2.resize(face_img, self.image_size)
        
        # Apply histogram equalization
        face_eq = cv2.equalizeHist(face_resized)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        face_clahe = clahe.apply(face_resized)
        
        # Apply bilateral filter to reduce noise while preserving edges
        face_filtered = cv2.bilateralFilter(face_clahe, 9, 75, 75)
        
        # Extract multiple feature representations
        features = []
        
        # 1. Raw pixel values (normalized)
        pixels = face_filtered.flatten() / 255.0
        features.extend(pixels)
        
        # 2. LBP (Local Binary Pattern) features
        try:
            from skimage.feature import local_binary_pattern
            lbp = local_binary_pattern(face_filtered, 24, 8, method='uniform')
            lbp_hist, _ = np.histogram(lbp.ravel(), bins=26, range=(0, 26))
            lbp_hist = lbp_hist.astype(float)
            lbp_hist /= (lbp_hist.sum() + 1e-7)  # Normalize
            features.extend(lbp_hist)
        except ImportError:
            # If scikit-image not available, use simple gradient features
            grad_x = cv2.Sobel(face_filtered, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(face_filtered, cv2.CV_64F, 0, 1, ksize=3)
            gradient_mag = np.sqrt(grad_x**2 + grad_y**2)
            grad_features = gradient_mag.flatten()[:100]  # Take first 100 features
            features.extend(grad_features / 255.0)
        
        return np.array(features)
        self.knn_classifier = None
        self.label_to_student = {}
        self.student_to_label = {}
        self.is_trained = False
        self.load_model()
    
    def extract_face_features(self, image_path, face_size=(120, 120)):
        """Trích xuất đặc trưng khuôn mặt từ ảnh với cải tiến"""
        try:
            # Đọc ảnh
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # Chuyển sang grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Cải thiện chất lượng ảnh
            gray = cv2.bilateralFilter(gray, 9, 75, 75)  # Giảm noise
            
            # Detect khuôn mặt với parameters tốt hơn
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1,     # Giảm từ 1.3 xuống 1.1 để detect tốt hơn
                minNeighbors=3,      # Giảm từ 5 xuống 3
                minSize=(50, 50)     # Kích thước tối thiểu
            )
            
            if len(faces) == 0:
                return None
            
            # Lấy khuôn mặt lớn nhất (thường là chính xác nhất)
            largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
            (x, y, w, h) = largest_face
            
            # Mở rộng vùng face một chút để có thêm context
            padding = int(0.1 * min(w, h))
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(gray.shape[1] - x, w + 2*padding)
            h = min(gray.shape[0] - y, h + 2*padding)
            
            face_roi = gray[y:y+h, x:x+w]
            
            # Resize về kích thước chuẩn (tăng từ 100x100 lên 120x120)
            face_resized = cv2.resize(face_roi, face_size)
            
            # Chuẩn hóa histogram và contrast
            face_normalized = cv2.equalizeHist(face_resized)
            
            # Thêm Gaussian blur nhẹ để giảm noise
            face_normalized = cv2.GaussianBlur(face_normalized, (3, 3), 0)
            
            return face_normalized.flatten()
            
        except Exception as e:
            print(f"Error extracting features from {image_path}: {e}")
            return None
    
    def train_model(self):
        """Train model từ dữ liệu ảnh đã thu thập"""
        try:
            faces_folder = "uploads/faces"
            if not os.path.exists(faces_folder):
                return {"success": False, "message": "Thư mục faces không tồn tại"}
            
            features = []
            labels = []
            student_info = {}
            
            # Đọc dữ liệu sinh viên từ database
            conn = sqlite3.connect('attendance_system.db')
            cursor = conn.cursor()
            cursor.execute("SELECT student_id, full_name FROM students")
            students = cursor.fetchall()
            conn.close()
            
            # Tạo mapping student_id -> label number
            for idx, (student_id, full_name) in enumerate(students):
                self.student_to_label[student_id] = idx
                self.label_to_student[idx] = {
                    'student_id': student_id,
                    'name': full_name
                }
            
            # Thu thập features từ tất cả ảnh
            for student_id in os.listdir(faces_folder):
                student_folder = os.path.join(faces_folder, student_id)
                if not os.path.isdir(student_folder):
                    continue
                
                if student_id not in self.student_to_label:
                    continue
                
                label = self.student_to_label[student_id]
                image_count = 0
                
                for image_file in os.listdir(student_folder):
                    if image_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        image_path = os.path.join(student_folder, image_file)
                        feature = self.extract_face_features(image_path)
                        
                        if feature is not None:
                            features.append(feature)
                            labels.append(label)
                            image_count += 1
                
                student_info[student_id] = {
                    'name': self.label_to_student[label]['name'],
                    'image_count': image_count
                }
            
            if len(features) == 0:
                return {"success": False, "message": "Không tìm thấy dữ liệu training"}
            
            # Chuyển đổi sang numpy arrays
            X = np.array(features)
            y = np.array(labels)
            
            # Chuẩn hóa dữ liệu để cải thiện performance
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Train KNN classifier với parameters tốt hơn
            n_neighbors = min(5, len(X) // 2)  # Tự động điều chỉnh k dựa trên số lượng dữ liệu
            self.knn_classifier = KNeighborsClassifier(
                n_neighbors=n_neighbors, 
                weights='distance',
                metric='euclidean'
            )
            self.knn_classifier.fit(X_scaled, y)
            
            self.is_trained = True
            
            # Lưu model
            self.save_model()
            
            return {
                "success": True,
                "message": f"Training thành công với {len(features)} ảnh từ {len(student_info)} sinh viên",
                "student_count": len(student_info),
                "image_count": len(features),
                "students": student_info
            }
            
        except Exception as e:
            return {"success": False, "message": f"Lỗi training: {str(e)}"}
    
    def recognize_face(self, image_data):
        """Nhận diện khuôn mặt từ ảnh"""
        try:
            if not self.is_trained or self.knn_classifier is None:
                return {"success": False, "message": "Model chưa được train"}
            
            # Xử lý ảnh base64
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                # Remove data URL prefix
                image_data = image_data.split(',')[1]
            
            # Decode base64
            import base64
            image_bytes = base64.b64decode(image_data)
            
            # Chuyển thành numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return {"success": False, "message": "Không thể đọc ảnh"}
            
            # Chuyển sang grayscale và cải thiện chất lượng
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.bilateralFilter(gray, 9, 75, 75)  # Giảm noise
            
            # Detect khuôn mặt với parameters tốt hơn
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=3,
                minSize=(50, 50)
            )
            
            if len(faces) == 0:
                return {"success": False, "message": "Không phát hiện khuôn mặt"}
            
            results = []
            
            # Nhận diện từng khuôn mặt
            for (x, y, w, h) in faces:
                # Mở rộng vùng face
                padding = int(0.1 * min(w, h))
                x_pad = max(0, x - padding)
                y_pad = max(0, y - padding)
                w_pad = min(gray.shape[1] - x_pad, w + 2*padding)
                h_pad = min(gray.shape[0] - y_pad, h + 2*padding)
                
                face_roi = gray[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
                face_resized = cv2.resize(face_roi, (120, 120))
                face_normalized = cv2.equalizeHist(face_resized)
                face_normalized = cv2.GaussianBlur(face_normalized, (3, 3), 0)
                
                feature = face_normalized.flatten().reshape(1, -1)
                
                # Chuẩn hóa feature nếu có scaler
                if hasattr(self, 'scaler') and self.scaler is not None:
                    feature = self.scaler.transform(feature)
                
                # Dự đoán với nhiều neighbors để có kết quả tốt hơn
                prediction = self.knn_classifier.predict(feature)[0]
                distances, indices = self.knn_classifier.kneighbors(feature, n_neighbors=min(5, len(self.knn_classifier._fit_X)))
                
                # Tính confidence dựa trên khoảng cách trung bình
                avg_distance = np.mean(distances)
                confidence = 1.0 / (1.0 + avg_distance)
                
                # Giảm threshold xuống để dễ nhận diện hơn
                if confidence > 0.3:  # Giảm từ 0.6 xuống 0.3 (30%)
                    student_info = self.label_to_student[prediction]
                    results.append({
                        'student_id': student_info['student_id'],
                        'name': student_info['name'],
                        'confidence': float(confidence),
                        'distance': float(avg_distance),
                        'position': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
                    })
            
            if results:
                return {
                    "success": True,
                    "faces": results,
                    "face_count": len(results)
                }
            else:
                return {
                    "success": False,
                    "message": "Không nhận diện được khuôn mặt (confidence thấp)"
                }
                
        except Exception as e:
            return {"success": False, "message": f"Lỗi nhận diện: {str(e)}"}
    
    def detect_face_only(self, image_data):
        """Chỉ detect khuôn mặt, không nhận diện"""
        try:
            # Xử lý ảnh base64
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            import base64
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return {"success": False, "face_count": 0}
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            return {
                "success": True,
                "face_count": len(faces),
                "faces": [{'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)} for (x, y, w, h) in faces]
            }
            
        except Exception as e:
            return {"success": False, "face_count": 0, "error": str(e)}
    
    def save_model(self):
        """Lưu model"""
        try:
            model_data = {
                'knn_classifier': self.knn_classifier,
                'scaler': getattr(self, 'scaler', None),
                'label_to_student': self.label_to_student,
                'student_to_label': self.student_to_label,
                'is_trained': self.is_trained,
                'trained_at': datetime.now().isoformat()
            }
            
            # Tạo thư mục nếu chưa có
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
        except Exception as e:
            print(f"Error saving model: {e}")
    
    def load_model(self):
        """Load model đã lưu"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.knn_classifier = model_data.get('knn_classifier')
                self.scaler = model_data.get('scaler')
                self.label_to_student = model_data.get('label_to_student', {})
                self.student_to_label = model_data.get('student_to_label', {})
                self.is_trained = model_data.get('is_trained', False)
                
        except Exception as e:
            print(f"Error loading model: {e}")
            self.is_trained = False
    
    def get_model_info(self):
        """Lấy thông tin model"""
        faces_folder = "uploads/faces"
        student_data = {}
        total_images = 0
        
        if os.path.exists(faces_folder):
            for student_id in os.listdir(faces_folder):
                student_folder = os.path.join(faces_folder, student_id)
                if os.path.isdir(student_folder):
                    image_count = len([f for f in os.listdir(student_folder) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                    student_data[student_id] = image_count
                    total_images += image_count
        
        return {
            'is_trained': self.is_trained,
            'model_exists': os.path.exists(self.model_path),
            'students_count': len(self.student_to_label),
            'total_images': total_images,
            'student_data': student_data,
            'model_path': self.model_path
        }

# Tạo instance global để tương thích ngược
from models.advanced_face_model import face_model

# Deprecated - Use advanced_face_model instead
# This file is kept for backward compatibility only
