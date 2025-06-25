# 🔧 HƯỚNG DẪN SỬA LỖI NUMPY/OPENCV

## Vấn đề

Lỗi xung đột giữa NumPy 2.x và OpenCV do các phiên bản không tương thích.

## ✅ GIẢI PHÁP NHANH

### Bước 1: Mở Command Prompt với quyền Administrator

```bash
# Nhấn Win + R, gõ "cmd", nhấn Ctrl+Shift+Enter
```

### Bước 2: Di chuyển đến thư mục project

```bash
cd "C:\Users\hieuk\Desktop\New folder"
```

### Bước 3: Xóa và cài đặt lại packages

```bash
# Xóa packages xung đột
pip uninstall -y numpy opencv-python face-recognition

# Cài đặt phiên bản tương thích
pip install numpy==1.24.3
pip install opencv-python==4.10.0.84

# Cài đặt các package còn lại
pip install Flask==2.3.3 Pillow==10.0.1 pandas==2.1.1 openpyxl==3.1.2 python-dateutil==2.8.2 Werkzeug==2.3.7
```

### Bước 4: Khởi tạo database

```bash
python models\database.py
```

### Bước 5: Chạy ứng dụng

```bash
python app_simple.py
```

## 🌐 Truy cập ứng dụng

- URL: http://localhost:5000
- Username: admin
- Password: admin123

## 📝 LỖI THƯỜNG GẶP & CÁCH SỬA

### 1. "face_recognition" import failed

➡️ Sử dụng `app_simple.py` thay vì `app.py` (đã loại bỏ face_recognition)

### 2. "Microsoft Visual C++ 14.0 is required"

➡️ Tải Visual Studio Build Tools từ Microsoft

### 3. Lỗi quyền truy cập

➡️ Chạy Command Prompt với quyền Administrator

### 4. Python không được nhận diện

➡️ Cài đặt Python từ python.org và thêm vào PATH

## 🎯 PHIÊN BẢN ĐƠN GIẢN

Ứng dụng có 2 phiên bản:

1. **app.py** - Phiên bản đầy đủ với face_recognition (phức tạp cài đặt)
2. **app_simple.py** - Phiên bản đơn giản chỉ dùng OpenCV (dễ cài đặt)

Phiên bản đơn giản vẫn có đầy đủ tính năng:

- ✅ Quản lý lớp học, sinh viên, môn học
- ✅ Tạo ca điểm danh
- ✅ Phát hiện khuôn mặt (demo)
- ✅ Điểm danh thủ công
- ✅ Báo cáo Excel

## 🚀 CHẠY NHANH

```bash
# Cách đơn giản nhất
python app_simple.py
```

Hoặc double-click file `start_simple.bat`
