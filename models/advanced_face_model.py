"""
Advanced Face Recognition Model using OpenCV with Multiple Algorithms
Sử dụng OpenCV kết hợp nhiều thuật toán để train và nhận diện khuôn mặt chính xác cao
"""
import cv2
import os
import numpy as np
import pickle
import json
import base64
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
from skimage.feature import local_binary_pattern

class AdvancedFaceModel:
    def __init__(self, model_path="models/advanced_face_model.pkl"):
        # Setup logging first
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.model_path = model_path
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize multiple classifiers for ensemble
        self.knn_classifier = None
        self.svm_classifier = None
        self.ensemble_classifier = None
        self.scaler = None
        self.label_encoder = None
        
        # Model parameters - Thiết lập ngưỡng phù hợp để tránh vật thể che mặt
        self.image_size = (120, 120)
        self.confidence_threshold = 0.4  # Giảm từ 0.6 xuống 0.4
        self.ensemble_threshold = 0.4     # Giảm từ 0.6 xuống 0.4
        self.face_quality_threshold = 0.3 # Giảm từ 0.75 xuống 0.3 để dễ nhận diện hơn
        self.min_face_size = (60, 60)     # Giảm kích thước tối thiểu
        
        # Training data storage
        self.features = []
        self.labels = []
        self.student_to_label = {}
        self.label_to_student = {}
        self.is_trained = False
        
        # Load existing model if available
        self.load_model()
    
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
    
    def load_model(self):
        """Load trained model"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    
                self.knn_classifier = model_data.get('knn_classifier')
                self.svm_classifier = model_data.get('svm_classifier')
                self.ensemble_classifier = model_data.get('ensemble_classifier')
                self.scaler = model_data.get('scaler')
                self.label_encoder = model_data.get('label_encoder')
                self.student_to_label = model_data.get('student_to_label', {})
                self.label_to_student = model_data.get('label_to_student', {})
                
                if self.ensemble_classifier is not None:
                    self.is_trained = True
                    self.logger.info("Model loaded successfully")
                    
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            self.is_trained = False
    
    def save_model(self):
        """Save trained model"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            model_data = {
                'knn_classifier': self.knn_classifier,
                'svm_classifier': self.svm_classifier,
                'ensemble_classifier': self.ensemble_classifier,
                'scaler': self.scaler,
                'label_encoder': self.label_encoder,
                'student_to_label': self.student_to_label,
                'label_to_student': self.label_to_student,
                'created_at': datetime.now().isoformat()
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.logger.info("Model saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            return False
    
    def train_model(self, faces_dir="uploads/faces"):
        """Train model với ensemble của nhiều classifiers"""
        try:
            if not os.path.exists(faces_dir):
                return {"success": False, "message": "Thư mục faces không tồn tại"}
            
            all_features = []
            all_labels = []
            student_info = {}
            
            # Get student info from database
            conn = sqlite3.connect('attendance_system.db')
            cursor = conn.cursor()
            cursor.execute("SELECT student_id, full_name FROM students")
            students = cursor.fetchall()
            
            for student_id, full_name in students:
                student_folder = os.path.join(faces_dir, str(student_id))
                if not os.path.exists(student_folder):
                    continue
                
                student_features = []
                image_files = [f for f in os.listdir(student_folder) 
                             if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                
                if len(image_files) < 3:  # Cần ít nhất 3 ảnh
                    continue
                
                for img_file in image_files:
                    img_path = os.path.join(student_folder, img_file)
                    img = cv2.imread(img_path)
                    if img is None:
                        continue
                    
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Detect face
                    faces = self.face_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=3, minSize=(50, 50)
                    )
                    
                    if len(faces) == 0:
                        continue
                    
                    # Get largest face
                    largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
                    (x, y, w, h) = largest_face
                    
                    # Add padding
                    padding = int(0.1 * min(w, h))
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    w = min(gray.shape[1] - x, w + 2*padding)
                    h = min(gray.shape[0] - y, h + 2*padding)
                    
                    face_roi = gray[y:y+h, x:x+w]
                    
                    # Generate augmented images for better training
                    augmented_faces = self.augment_image(face_roi, num_augmentations=3)
                    
                    for aug_face in augmented_faces:
                        features = self.extract_advanced_features(aug_face)
                        if features is not None and len(features) > 0:
                            student_features.append(features)
                
                if len(student_features) >= 5:  # Cần ít nhất 5 features (bao gồm augmented)
                    all_features.extend(student_features)
                    all_labels.extend([student_id] * len(student_features))
                    student_info[student_id] = {"name": full_name, "image_count": len(student_features)}
            
            conn.close()
            
            if len(all_features) < 5:
                return {"success": False, "message": "Không đủ dữ liệu để train. Cần ít nhất 5 features."}
            
            # Kiểm tra số lượng class (sinh viên)
            unique_students = list(set(all_labels))
            if len(unique_students) < 1:
                return {
                    "success": False, 
                    "message": "Không có sinh viên nào để train model."
                }
            
            # Convert to numpy arrays
            X = np.array(all_features)
            y = np.array(all_labels)
            
            # Encode labels
            self.label_encoder = LabelEncoder()
            y_encoded = self.label_encoder.fit_transform(y)
            
            # Update label mappings
            self.student_to_label = {}
            self.label_to_student = {}
            for i, student_id in enumerate(self.label_encoder.classes_):
                label = i
                self.student_to_label[student_id] = label
                self.label_to_student[label] = {
                    'student_id': student_id,
                    'name': student_info[student_id]['name']
                }
            
            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Split data for validation - chỉ split nếu có đủ dữ liệu
            if len(X_scaled) >= 10 and len(unique_students) >= 2:
                try:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X_scaled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
                    )
                except ValueError:
                    # Nếu không thể stratify (ít data), dùng random split
                    X_train, X_test, y_train, y_test = train_test_split(
                        X_scaled, y_encoded, test_size=0.2, random_state=42
                    )
            else:
                # Nếu ít dữ liệu, sử dụng toàn bộ dữ liệu cho training và testing
                X_train = X_test = X_scaled
                y_train = y_test = y_encoded
            
            # Train multiple classifiers
            # 1. KNN Classifier - xử lý trường hợp 1 class
            n_neighbors = min(3, len(X_train))  # Sử dụng min với số samples thay vì unique classes
            if len(unique_students) == 1:
                # Với 1 sinh viên, sử dụng KNN với n_neighbors = 1
                n_neighbors = 1
            
            self.knn_classifier = KNeighborsClassifier(
                n_neighbors=n_neighbors,
                weights='distance',
                metric='euclidean'
            )
            
            # 2. SVM Classifier - chỉ tạo nếu có nhiều hơn 1 class
            if len(unique_students) > 1:
                self.svm_classifier = SVC(
                    kernel='rbf',
                    C=1.0,
                    gamma='scale',
                    probability=True,
                    random_state=42
                )
            else:
                self.svm_classifier = None
            
            # 3. Random Forest Classifier - chỉ tạo nếu có nhiều hơn 1 class
            if len(unique_students) > 1:
                rf_classifier = RandomForestClassifier(
                    n_estimators=50,  # Giảm để tránh overfitting với ít data
                    max_depth=5,
                    random_state=42
                )
                
                # Create ensemble classifier
                self.ensemble_classifier = VotingClassifier(
                    estimators=[
                        ('knn', self.knn_classifier),
                        ('svm', self.svm_classifier),
                        ('rf', rf_classifier)
                    ],
                    voting='soft'  # Use probability-based voting
                )
            else:
                # Với 1 sinh viên, chỉ sử dụng KNN classifier
                self.ensemble_classifier = self.knn_classifier
            
            # Train classifiers
            self.knn_classifier.fit(X_train, y_train)
            
            # Chỉ train SVM nếu có nhiều hơn 1 class
            if len(unique_students) > 1:
                self.svm_classifier.fit(X_train, y_train)
                # Train ensemble (nếu khác với KNN)
                self.ensemble_classifier.fit(X_train, y_train)
            else:
                # Với 1 class, không train SVM và ensemble = KNN
                self.svm_classifier = None
            
            # Evaluate performance
            train_score = self.ensemble_classifier.score(X_train, y_train)
            test_score = self.ensemble_classifier.score(X_test, y_test)
            
            # Cross-validation score - chỉ làm nếu có đủ data và nhiều hơn 1 class
            if len(X_scaled) >= 6 and len(unique_students) > 1:
                try:
                    cv_scores = cross_val_score(self.ensemble_classifier, X_scaled, y_encoded, cv=min(3, len(X_scaled)//2))
                    cv_mean = float(cv_scores.mean())
                    cv_std = float(cv_scores.std())
                except Exception:
                    cv_mean = cv_std = 0.0
            else:
                cv_mean = cv_std = 0.0
            
            self.is_trained = True
            self.save_model()
            
            return {
                "success": True,
                "message": f"Training thành công với {len(X)} features từ {len(student_info)} sinh viên",
                "student_count": len(student_info),
                "feature_count": len(X),
                "train_accuracy": float(train_score),
                "test_accuracy": float(test_score),
                "cv_mean_accuracy": cv_mean,
                "cv_std_accuracy": cv_std,
                "students": student_info
            }
            
        except Exception as e:
            self.logger.error(f"Training error: {e}")
            return {"success": False, "message": f"Lỗi training: {str(e)}"}
    
    def recognize_face(self, image_data, use_ensemble=True):
        """Nhận diện khuôn mặt với confidence cao hơn"""
        try:
            if not self.is_trained or self.ensemble_classifier is None:
                return {"success": False, "message": "Model chưa được train"}
            
            # Process image data
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return {"success": False, "message": "Không thể đọc ảnh"}
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Detect faces with better parameters
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.05,  # More sensitive detection
                minNeighbors=5,    # Tăng từ 3 lên 5 để giảm false positive
                minSize=(60, 60),  # Tăng kích thước tối thiểu
                maxSize=(300, 300)
            )
            
            if len(faces) == 0:
                return {"success": False, "message": "Không phát hiện khuôn mặt"}
            
            results = []
            rejected_faces = []  # Danh sách khuôn mặt bị từ chối
            
            # Định nghĩa threshold ở đây để tránh lỗi scope
            threshold = self.ensemble_threshold if use_ensemble else self.confidence_threshold
            
            for (x, y, w, h) in faces:
                # Add padding
                padding = int(0.1 * min(w, h))
                x_pad = max(0, x - padding)
                y_pad = max(0, y - padding)
                w_pad = min(gray.shape[1] - x_pad, w + 2*padding)
                h_pad = min(gray.shape[0] - y_pad, h + 2*padding)
                
                face_roi = gray[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
                
                # Kiểm tra chất lượng khuôn mặt
                face_bgr = img[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]  # Khuôn mặt màu cho kiểm tra
                quality_score, is_valid, quality_reasons = self.assess_face_quality(face_bgr)
                
                # Extract advanced features (cho cả khuôn mặt không đạt chất lượng để có thông tin debug)
                features = self.extract_advanced_features(face_roi)
                if features is None:
                    continue
                
                # Scale features
                features = features.reshape(1, -1)
                features_scaled = self.scaler.transform(features)
                
                if use_ensemble:
                    # Use ensemble prediction
                    prediction = self.ensemble_classifier.predict(features_scaled)[0]
                    prediction_proba = self.ensemble_classifier.predict_proba(features_scaled)[0]
                    confidence = float(np.max(prediction_proba))
                    
                    # Additional confidence check with individual classifiers
                    knn_proba = self.knn_classifier.predict_proba(features_scaled)[0]
                    
                    # Chỉ sử dụng SVM nếu có
                    if self.svm_classifier is not None:
                        svm_proba = self.svm_classifier.predict_proba(features_scaled)[0]
                        max_individual_conf = max(np.max(knn_proba), np.max(svm_proba))
                    else:
                        max_individual_conf = np.max(knn_proba)
                    
                    # Combined confidence (ensemble + individual max)
                    final_confidence = (confidence + max_individual_conf) / 2
                    
                else:
                    # Use KNN only
                    prediction = self.knn_classifier.predict(features_scaled)[0]
                    distances, indices = self.knn_classifier.kneighbors(features_scaled, n_neighbors=3)
                    avg_distance = np.mean(distances)
                    final_confidence = 1.0 / (1.0 + avg_distance)
                
                # Kết hợp confidence với quality score
                combined_score = final_confidence * quality_score
                
                # Thông tin cơ bản của khuôn mặt
                face_info = {
                    'confidence': float(final_confidence),
                    'quality_score': float(quality_score),
                    'combined_score': float(combined_score),
                    'method': 'ensemble' if use_ensemble else 'knn',
                    'position': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
                    'quality_reasons': quality_reasons if quality_reasons else []
                }
                
                if combined_score > threshold and is_valid:
                    # Khuôn mặt đạt yêu cầu
                    student_info = self.label_to_student[prediction]
                    face_info.update({
                        'student_id': student_info['student_id'],
                        'name': student_info['name']
                    })
                    results.append(face_info)
                else:
                    # Khuôn mặt không đạt yêu cầu nhưng vẫn lưu để debug
                    try:
                        student_info = self.label_to_student[prediction]
                        face_info.update({
                            'student_id': None,  # Không trả về student_id để đánh dấu bị từ chối
                            'rejected_name': student_info['name'],  # Tên ứng viên bị từ chối
                            'rejection_reason': f"Combined score {combined_score:.3f} < {threshold} hoặc chất lượng thấp"
                        })
                    except:
                        face_info.update({
                            'student_id': None,
                            'rejected_name': 'Không xác định',
                            'rejection_reason': f"Combined score {combined_score:.3f} < {threshold} hoặc chất lượng thấp"
                        })
                    
                    rejected_faces.append(face_info)
                    self.logger.info(f"Khuôn mặt bị từ chối: confidence={final_confidence:.3f}, quality={quality_score:.3f}, combined={combined_score:.3f} < {threshold}")
            
            # Trả về kết quả bao gồm cả accepted và rejected faces
            all_faces = results + rejected_faces
            
            if results:
                # Sort by combined score
                results.sort(key=lambda x: x['combined_score'], reverse=True)
                return {
                    "success": True,
                    "faces": all_faces,  # Bao gồm cả accepted và rejected
                    "message": f"Nhận diện được {len(results)} khuôn mặt, {len(rejected_faces)} khuôn mặt không đạt yêu cầu"
                }
            else:
                return {
                    "success": False, 
                    "faces": all_faces,  # Vẫn trả về rejected faces để debug
                    "message": f"Không nhận diện được khuôn mặt nào (yêu cầu combined score > {threshold:.1%} và chất lượng tốt)"
                }
                
        except Exception as e:
            self.logger.error(f"Recognition error: {e}")
            return {"success": False, "message": f"Lỗi nhận diện: {str(e)}"}
    
    def get_model_info(self):
        """Lấy thông tin model"""
        try:
            if not self.is_trained:
                return {"success": False, "message": "Model chưa được train"}
            
            return {
                "success": True,
                "is_trained": self.is_trained,
                "student_count": len(self.student_to_label),
                "students": list(self.label_to_student.values()),
                "model_path": self.model_path,
                "image_size": self.image_size,
                "confidence_threshold": self.confidence_threshold,
                "ensemble_threshold": self.ensemble_threshold
            }
            
        except Exception as e:
            return {"success": False, "message": f"Lỗi lấy thông tin model: {str(e)}"}
    
    def test_recognition_accuracy(self, test_dir="uploads/faces"):
        """Test độ chính xác của model trên dữ liệu test"""
        try:
            if not self.is_trained:
                return {"success": False, "message": "Model chưa được train"}
            
            results = {"total": 0, "correct": 0, "details": []}
            
            for student_id in self.student_to_label.keys():
                student_folder = os.path.join(test_dir, str(student_id))
                if not os.path.exists(student_folder):
                    continue
                
                image_files = [f for f in os.listdir(student_folder) 
                             if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                
                for img_file in image_files[-3:]:  # Test với 3 ảnh cuối
                    img_path = os.path.join(student_folder, img_file)
                    img = cv2.imread(img_path)
                    if img is None:
                        continue
                    
                    # Convert to base64 for recognition
                    _, buffer = cv2.imencode('.jpg', img)
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # Test recognition
                    result = self.recognize_face(img_base64)
                    results["total"] += 1
                    
                    if result["success"] and len(result["faces"]) > 0:
                        predicted_id = result["faces"][0]["student_id"]
                        confidence = result["faces"][0]["confidence"]
                        
                        if predicted_id == student_id:
                            results["correct"] += 1
                            results["details"].append({
                                "image": img_file,
                                "expected": student_id,
                                "predicted": predicted_id,
                                "confidence": confidence,
                                "status": "correct"
                            })
                        else:
                            results["details"].append({
                                "image": img_file,
                                "expected": student_id,
                                "predicted": predicted_id,
                                "confidence": confidence,
                                "status": "incorrect"
                            })
                    else:
                        results["details"].append({
                            "image": img_file,
                            "expected": student_id,
                            "predicted": None,
                            "confidence": 0.0,
                            "status": "not_recognized"
                        })
            
            accuracy = results["correct"] / results["total"] if results["total"] > 0 else 0
            
            return {
                "success": True,
                "accuracy": accuracy,
                "total_tests": results["total"],
                "correct_predictions": results["correct"],
                "details": results["details"]
            }
            
        except Exception as e:
            return {"success": False, "message": f"Lỗi test accuracy: {str(e)}"}
    
    def assess_face_quality(self, face_img):
        """
        Đánh giá chất lượng khuôn mặt để tránh nhận diện sai, đặc biệt phát hiện vật thể che mặt
        Returns: (quality_score, is_valid, reasons)
        """
        reasons = []
        quality_score = 1.0
        
        # 1. Kiểm tra kích thước khuôn mặt
        if face_img.shape[0] < self.min_face_size[0] or face_img.shape[1] < self.min_face_size[1]:
            quality_score -= 0.3
            reasons.append("Khuôn mặt quá nhỏ")
        
        # 2. Kiểm tra độ mờ (blur detection)
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY) if len(face_img.shape) == 3 else face_img
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 50:  # Giảm từ 100 xuống 50 - ít nghiêm ngặt hơn
            quality_score -= 0.2  # Giảm từ 0.4 xuống 0.2
            reasons.append("Ảnh bị mờ")
        
        # 3. Kiểm tra độ sáng
        mean_brightness = np.mean(gray)
        if mean_brightness < 30:  # Giảm từ 50 xuống 30
            quality_score -= 0.2  # Giảm từ 0.3 xuống 0.2
            reasons.append("Ảnh quá tối")
        elif mean_brightness > 220:  # Tăng từ 200 lên 220
            quality_score -= 0.2  # Giảm từ 0.3 xuống 0.2
            reasons.append("Ảnh quá sáng")
        
        # 4. Kiểm tra độ tương phản
        contrast = gray.std()
        if contrast < 30:  # Độ tương phản thấp
            quality_score -= 0.2
            reasons.append("Độ tương phản thấp")
        
        # 5. Kiểm tra vùng mắt (đặc trưng quan trọng của khuôn mặt)
        try:
            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            eyes = eye_cascade.detectMultiScale(gray, 1.1, 3, minSize=(10, 10))
            if len(eyes) < 1:  # Giảm từ 2 xuống 1 - chỉ cần 1 mắt
                quality_score -= 0.3  # Giảm từ 0.5 xuống 0.3
                reasons.append("Không phát hiện đủ mắt (có thể bị che)")
        except:
            quality_score -= 0.2  # Giảm từ 0.3 xuống 0.2
            reasons.append("Lỗi phát hiện mắt")
        
        # 6. Kiểm tra mũi (vùng quan trọng khác)
        try:
            nose_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
            noses = nose_cascade.detectMultiScale(gray, 1.1, 3, minSize=(15, 15))
            if len(noses) == 0:
                quality_score -= 0.3
                reasons.append("Không phát hiện mũi (có thể bị che)")
        except:
            pass  # Không bắt buộc phải có mũi
        
        # 7. Kiểm tra entropy (thông tin trong ảnh)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten()
        hist = hist[hist > 0]  # Loại bỏ bins trống
        entropy = -np.sum(hist * np.log2(hist + 1e-7))
        if entropy < 6:  # Entropy thấp = ít thông tin
            quality_score -= 0.2
            reasons.append("Thiếu thông tin chi tiết")
        
        # 8. Phát hiện vật thể che mặt bằng phân tích vùng
        h, w = gray.shape
        
        # Chia khuôn mặt thành các vùng quan trọng
        upper_face = gray[0:h//3, :]  # Vùng trán và mắt
        middle_face = gray[h//3:2*h//3, :]  # Vùng mũi và má
        lower_face = gray[2*h//3:h, :]  # Vùng miệng và cằm
        
        # Kiểm tra độ đồng nhất trong các vùng (phát hiện vật thể lạ)
        for region_name, region in [("vùng trên", upper_face), ("vùng giữa", middle_face), ("vùng dưới", lower_face)]:
            region_std = np.std(region)
            region_mean = np.mean(region)
            
            # Nếu vùng quá đồng nhất (có thể là tay che hoặc vật thể)
            if region_std < 15:
                quality_score -= 0.4
                reasons.append(f"Phát hiện vật thể che ở {region_name}")
            
            # Kiểm tra vùng quá sáng hoặc quá tối bất thường
            if region_mean < 30 or region_mean > 220:
                quality_score -= 0.2
                reasons.append(f"Độ sáng bất thường ở {region_name}")
        
        # 9. Phát hiện màu da (tay) bằng HSV
        if len(face_img.shape) == 3:
            hsv = cv2.cvtColor(face_img, cv2.COLOR_BGR2HSV)
            
            # Ngưỡng màu da phổ biến
            skin_lower = np.array([0, 20, 70])
            skin_upper = np.array([20, 255, 255])
            
            skin_mask = cv2.inRange(hsv, skin_lower, skin_upper)
            skin_ratio = np.sum(skin_mask > 0) / (h * w)
            
            # Nếu quá nhiều vùng màu da (có thể là tay che)
            if skin_ratio > 0.8:
                quality_score -= 0.3
                reasons.append("Phát hiện quá nhiều vùng màu da (nghi tay che)")
        
        # 10. Phát hiện cạnh không đều (vật thể che)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (h * w)
        
        # Quá ít cạnh = có thể bị che, quá nhiều cạnh = nhiễu
        if edge_density < 0.05:
            quality_score -= 0.3
            reasons.append("Quá ít đặc trưng cạnh (có thể bị che)")
        elif edge_density > 0.4:
            quality_score -= 0.2
            reasons.append("Quá nhiều nhiễu trong ảnh")
        
        # 11. Kiểm tra gradient trong vùng trung tâm
        center_region = gray[h//4:3*h//4, w//4:3*w//4]
        grad_x = cv2.Sobel(center_region, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(center_region, cv2.CV_64F, 0, 1, ksize=3)
        grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        avg_gradient = np.mean(grad_magnitude)
        if avg_gradient < 20:  # Gradient thấp = vùng đồng nhất
            quality_score -= 0.3
            reasons.append("Vùng trung tâm thiếu chi tiết (nghi bị che)")
        
        # 12. Kiểm tra tỷ lệ vùng sáng/tối bất thường
        bright_pixels = np.sum(gray > 180)
        dark_pixels = np.sum(gray < 70)
        total_pixels = h * w
        
        bright_ratio = bright_pixels / total_pixels
        dark_ratio = dark_pixels / total_pixels
        
        if bright_ratio > 0.6:  # Quá nhiều vùng sáng
            quality_score -= 0.3
            reasons.append("Quá nhiều vùng sáng bất thường")
        
        if dark_ratio > 0.6:  # Quá nhiều vùng tối
            quality_score -= 0.3
            reasons.append("Quá nhiều vùng tối bất thường")
        
        # Đảm bảo quality_score không âm
        quality_score = max(0.0, quality_score)
        
        is_valid = quality_score >= self.face_quality_threshold
        
        return quality_score, is_valid, reasons

# Create global instance (for backward compatibility)
face_model = AdvancedFaceModel()
