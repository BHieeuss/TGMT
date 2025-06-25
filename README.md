# 🎯 Hệ thống Điểm danh Khuôn mặt

Một ứng dụng web hiện đại sử dụng công nghệ nhận diện khuôn mặt để điểm danh sinh viên tự động.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-red.svg)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)

## ✨ Tính năng chính

### 🏫 Quản lý Lớp học

- ➕ Tạo, sửa, xóa lớp học
- 👥 Gán sinh viên vào lớp
- 📊 Thống kê sĩ số theo lớp

### 👨‍🎓 Quản lý Sinh viên

- 📝 Thêm thông tin sinh viên (MSSV, họ tên, ảnh đại diện)
- 🖼️ Upload và lưu trữ ảnh khuôn mặt
- 🤖 Tự động mã hóa đặc trưng khuôn mặt

### 📚 Quản lý Môn học

- 📖 Tạo môn học mới (mã môn, tên môn)
- 🔗 Liên kết môn học với lớp

### ⏰ Tạo Ca điểm danh

- 📅 Tạo các ca điểm danh theo ngày giờ
- 🎯 Chỉ định môn học và lớp học liên quan
- ⚡ Quản lý trạng thái ca điểm danh

### 🎥 Điểm danh Khuôn mặt

- 📷 **Nhận diện tự động**: Camera tự động nhận dạng và điểm danh
- ⌨️ **Điểm danh thủ công**: Nhập MSSV để đối chiếu khuôn mặt
- 🎯 Độ chính xác cao với confidence score
- ⚡ Xử lý real-time

### 📊 Báo cáo & Thống kê

- 📈 Dashboard tổng quan với số liệu thống kê
- 📋 Lịch sử điểm danh chi tiết
- 📑 Xuất báo cáo Excel theo:
  - Ngày/khoảng thời gian
  - Lớp học cụ thể
  - Môn học cụ thể
- 📊 Thống kê tỷ lệ vắng/có mặt

## 🛠️ Công nghệ sử dụng

### Backend

- **Python 3.8+** - Ngôn ngữ lập trình chính
- **Flask 2.3** - Web framework
- **SQLite** - Cơ sở dữ liệu nhẹ
- **OpenCV 4.8** - Xử lý hình ảnh
- **face_recognition** - Nhận diện khuôn mặt
- **pandas + openpyxl** - Xuất báo cáo Excel

### Frontend

- **HTML5 + CSS3** - Cấu trúc và giao diện
- **Bootstrap 5.3** - Framework UI responsive
- **JavaScript ES6** - Tương tác người dùng
- **Font Awesome** - Icons
- **WebRTC** - Truy cập camera

### AI/ML

- **face_recognition library** - Dựa trên dlib
- **OpenCV** - Computer vision
- **NumPy** - Xử lý ma trận

## 🚀 Cài đặt và Chạy

### 1. Clone repository

```bash
git clone <repository-url>
cd face-attendance-system
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Khởi tạo database

```bash
python models/database.py
```

### 4. Chạy ứng dụng

```bash
python app.py
```

### 5. Truy cập ứng dụng

Mở trình duyệt và truy cập: `http://localhost:5000`

**Đăng nhập demo:**

- Username: `admin`
- Password: `admin123`

## 📁 Cấu trúc Project

```
face-attendance-system/
├── app.py                 # File chính Flask
├── requirements.txt       # Dependencies
├── README.md             # Tài liệu
├── models/
│   └── database.py       # Quản lý database
├── routes/
│   ├── auth.py          # Authentication
│   ├── classes.py       # Quản lý lớp học
│   ├── students.py      # Quản lý sinh viên
│   ├── subjects.py      # Quản lý môn học
│   ├── attendance.py    # Điểm danh
│   └── reports.py       # Báo cáo
├── templates/
│   ├── base.html        # Template cơ sở
│   ├── dashboard.html   # Trang chủ
│   ├── login.html       # Đăng nhập
│   ├── camera.html      # Điểm danh camera
│   └── ...              # Các template khác
├── static/
│   ├── css/
│   │   └── style.css    # CSS tùy chỉnh
│   ├── js/
│   │   └── app.js       # JavaScript chính
│   └── img/             # Hình ảnh
├── uploads/             # Ảnh sinh viên
└── exports/             # File báo cáo Excel
```

## 💡 Hướng dẫn sử dụng

### 1. Thiết lập dữ liệu ban đầu

1. **Tạo lớp học**: Vào "Quản lý > Lớp học" → "Thêm lớp học"
2. **Thêm môn học**: Vào "Quản lý > Môn học" → "Thêm môn học"
3. **Thêm sinh viên**: Vào "Quản lý > Sinh viên" → "Thêm sinh viên"
   - Upload ảnh rõ mặt của sinh viên
   - Hệ thống tự động mã hóa khuôn mặt

### 2. Tạo ca điểm danh

1. Vào "Điểm danh > Ca điểm danh" → "Tạo ca mới"
2. Chọn môn học, lớp học, ngày giờ
3. Lưu ca điểm danh

### 3. Điểm danh

#### Phương thức 1: Nhận diện tự động

1. Vào "Điểm danh camera"
2. Chọn ca điểm danh
3. Bật camera
4. Sinh viên đứng trước camera → Hệ thống tự động nhận diện

#### Phương thức 2: Điểm danh thủ công

1. Nhập MSSV của sinh viên
2. Sinh viên đứng trước camera
3. Hệ thống đối chiếu khuôn mặt với MSSV

### 4. Xem báo cáo

1. Vào "Báo cáo > Báo cáo điểm danh"
2. Chọn bộ lọc (lớp, môn, ngày)
3. Xem hoặc xuất Excel

## 🔧 Cấu hình

### Camera Requirements

- Webcam hoặc camera tích hợp
- Độ phân giải tối thiểu: 640x480
- Hỗ trợ WebRTC

### Browser Support

- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

### Performance Tips

- Sử dụng ảnh chất lượng cao cho training
- Đảm bảo ánh sáng đủ khi điểm danh
- Thường xuyên backup database

## 🤝 Contributing

1. Fork project
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Liên hệ

- 📧 Email: your-email@example.com
- 🌐 Website: https://your-website.com
- 📱 Phone: +84 XXX XXX XXX

## 🙏 Acknowledgments

- [face_recognition](https://github.com/ageitgey/face_recognition) - Amazing face recognition library
- [OpenCV](https://opencv.org/) - Computer vision library
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Bootstrap](https://getbootstrap.com/) - CSS framework

---

⭐ **Star this repo if you find it helpful!** ⭐
