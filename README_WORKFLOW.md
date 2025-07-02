# 🔄 Luồng Hoạt động Hệ thống Điểm danh Khuôn mặt

**Hệ thống:** Điểm danh Sinh viên bằng AI Face Recognition  
**Framework:** Python Flask + SQLite + OpenCV  
**Ngày cập nhật:** 03/07/2025

## 📋 Mục lục

- [Luồng Kỹ thuật](#luồng-kỹ-thuật)
- [Luồng Người dùng](#luồng-người-dùng)
- [Architecture Overview](#architecture-overview)
- [Database Flow](#database-flow)
- [Authentication Flow](#authentication-flow)
- [Face Recognition Pipeline](#face-recognition-pipeline)
- [Performance Metrics](#performance-metrics)
- [Error Handling](#error-handling)
- [System Monitoring](#system-monitoring)

---

## 🏗️ Luồng Kỹ thuật

### 🎯 Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[Web Browser]
        CAM[Camera/Webcam]
    end
    
    subgraph "Flask Application"
        APP[app.py - Main Flask App]
        AUTH[auth.py - Authentication]
        ROUTES[Route Blueprints]
    end
    
    subgraph "AI Processing"
        FACE[Face Recognition AI]
        CV[OpenCV Processing]
        MODEL[ML Models]
    end
    
    subgraph "Data Layer"
        DB[SQLite Database]
        FILES[File Storage]
        EXPORT[Excel Export]
    end
    
    UI --> APP
    CAM --> FACE
    APP --> AUTH
    APP --> ROUTES
    ROUTES --> FACE
    FACE --> CV
    CV --> MODEL
    ROUTES --> DB
    ROUTES --> FILES
    DB --> EXPORT
    
    style APP fill:#e1f5fe
    style FACE fill:#f3e5f5
    style DB fill:#e8f5e8
```

### 🔄 System Initialization Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant Database
    participant AI_Module
    
    User->>Browser: Khởi động ứng dụng
    Browser->>Flask: Request to localhost:5000
    Flask->>Database: Kiểm tra connection
    Flask->>AI_Module: Load ML models
    AI_Module-->>Flask: Models ready
    Database-->>Flask: DB ready
    Flask-->>Browser: Redirect to /login
    Browser-->>User: Hiển thị trang login
```

---

## 👤 Luồng Người dùng

### 🚪 User Journey - Toàn bộ quy trình

```mermaid
journey
    title Hành trình Người dùng trong Hệ thống
    section Đăng nhập
      Truy cập website: 5: User
      Nhập username/password: 4: User
      Xác thực thành công: 5: User, System
    section Quản lý Dữ liệu
      Tạo lớp học: 4: User
      Thêm sinh viên: 4: User
      Thu thập dữ liệu khuôn mặt: 3: User, System
      Tạo môn học: 4: User
    section Điểm danh
      Tạo ca điểm danh: 4: User
      Chọn thuật toán AI: 4: User
      Bắt đầu nhận diện: 5: System
      Xem kết quả: 5: User, System
    section Báo cáo
      Chọn lớp/môn học: 4: User
      Xuất Excel: 5: System
      Tải file báo cáo: 5: User
```

### 🎯 Main User Workflows

```mermaid
flowchart TD
    START([Khởi động Hệ thống]) --> LOGIN{Đã đăng nhập?}
    LOGIN -->|Chưa| AUTH[Trang Đăng nhập]
    LOGIN -->|Rồi| DASH[Dashboard]
    
    AUTH --> CHECK{Credentials?}
    CHECK -->|Sai| AUTH
    CHECK -->|Đúng| DASH
    
    DASH --> MGMT[Quản lý Dữ liệu]
    DASH --> ATTEND[Điểm danh]
    DASH --> REPORT[Báo cáo]
    DASH --> AI_SET[Cài đặt AI]
    
    subgraph "Quản lý Dữ liệu"
        MGMT --> CLASS[Quản lý Lớp]
        MGMT --> STUDENT[Quản lý Sinh viên]
        MGMT --> SUBJECT[Quản lý Môn học]
        STUDENT --> COLLECT[Thu thập Khuôn mặt]
    end
    
    subgraph "Điểm danh"
        ATTEND --> CREATE_SESSION[Tạo Ca điểm danh]
        CREATE_SESSION --> SELECT_AI[Chọn Thuật toán]
        SELECT_AI --> START_CAM[Bật Camera]
        START_CAM --> RECOGNIZE[Nhận diện]
        RECOGNIZE --> SAVE_RESULT[Lưu Kết quả]
    end
    
    subgraph "Báo cáo"
        REPORT --> SELECT_CLASS[Chọn Lớp]
        SELECT_CLASS --> SELECT_SUBJECT[Chọn Môn]
        SELECT_SUBJECT --> EXPORT[Xuất Excel]
    end
    
    style DASH fill:#e3f2fd
    style RECOGNIZE fill:#f3e5f5
    style EXPORT fill:#e8f5e8
```

---

## 🔐 Authentication Flow

### 🛡️ Security và Session Management

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Flask
    participant Session
    participant Database
    
    User->>Browser: Nhập URL bất kỳ
    Browser->>Flask: Request với session
    Flask->>Session: Kiểm tra session['user_id']
    
    alt Session exists
        Session-->>Flask: Valid user_id
        Flask-->>Browser: Cho phép truy cập
    else No session
        Session-->>Flask: No user_id
        Flask-->>Browser: Redirect to /login
        Browser->>User: Hiển thị login form
        User->>Browser: Submit credentials
        Browser->>Flask: POST /login
        Flask->>Database: Verify user
        alt Valid credentials
            Database-->>Flask: User data
            Flask->>Session: Set session['user_id']
            Flask-->>Browser: Redirect to dashboard
        else Invalid credentials
            Database-->>Flask: No match
            Flask-->>Browser: Login failed message
        end
    end
```

### 🔒 Route Protection Pattern

```mermaid
graph LR
    REQUEST[HTTP Request] --> CHECK{@login_required?}
    CHECK -->|Yes| SESSION{Session exists?}
    CHECK -->|No| ALLOW[Allow Access]
    
    SESSION -->|Yes| ROUTE[Execute Route]
    SESSION -->|No| LOGIN[Redirect to Login]
    
    ROUTE --> RESPONSE[Return Response]
    LOGIN --> AUTH_PAGE[Login Page]
    
    style SESSION fill:#fff3e0
    style LOGIN fill:#ffebee
    style ROUTE fill:#e8f5e8
```

---

## 🤖 Face Recognition Pipeline

### 🎥 Real-time Recognition Flow

```mermaid
flowchart TD
    START([Bắt đầu Điểm danh]) --> INIT[Khởi tạo Camera]
    INIT --> MODEL{Chọn Model}
    
    MODEL -->|OpenCV| OPENCV[OpenCV Haar Cascade]
    MODEL -->|Face Recognition| FACEREC[face_recognition Library]
    MODEL -->|Advanced| ADVANCED[Custom Deep Learning]
    
    OPENCV --> CAPTURE[Capture Frame]
    FACEREC --> CAPTURE
    ADVANCED --> CAPTURE
    
    CAPTURE --> DETECT[Detect Faces]
    DETECT --> FOUND{Faces Found?}
    
    FOUND -->|No| CAPTURE
    FOUND -->|Yes| ENCODE[Encode Face Features]
    
    ENCODE --> COMPARE[So sánh với Database]
    COMPARE --> MATCH{Match Found?}
    
    MATCH -->|Yes| IDENTIFY[Xác định Sinh viên]
    MATCH -->|No| UNKNOWN[Unknown Face]
    
    IDENTIFY --> RECORD[Ghi nhận Điểm danh]
    UNKNOWN --> CAPTURE
    RECORD --> DISPLAY[Hiển thị Kết quả]
    DISPLAY --> CONTINUE{Tiếp tục?}
    
    CONTINUE -->|Yes| CAPTURE
    CONTINUE -->|No| END([Kết thúc])
    
    style DETECT fill:#e1f5fe
    style IDENTIFY fill:#e8f5e8
    style RECORD fill:#fff3e0
```

### 🧠 AI Model Comparison

```mermaid
graph TD
    subgraph "OpenCV Model"
        OCV_SPEED[⚡ Tốc độ: Rất nhanh]
        OCV_ACC[🎯 Độ chính xác: Trung bình]
        OCV_RES[💾 Tài nguyên: Ít]
    end
    
    subgraph "Face Recognition Model"
        FR_SPEED[⚡ Tốc độ: Trung bình]
        FR_ACC[🎯 Độ chính xác: Cao]
        FR_RES[💾 Tài nguyên: Vừa]
    end
    
    subgraph "Advanced AI Model"
        ADV_SPEED[⚡ Tốc độ: Chậm]
        ADV_ACC[🎯 Độ chính xác: Rất cao]
        ADV_RES[💾 Tài nguyên: Nhiều]
    end
    
    USECASE[Lựa chọn theo Use Case] --> OCV_SPEED
    USECASE --> FR_ACC
    USECASE --> ADV_ACC
    
    style OCV_SPEED fill:#ffcdd2
    style FR_ACC fill:#fff9c4
    style ADV_ACC fill:#c8e6c9
```

---

## 🗄️ Database Flow

### 📊 Database Schema Relationships

```mermaid
erDiagram
    USERS ||--o{ CLASSES : creates
    CLASSES ||--o{ STUDENTS : contains
    CLASSES ||--o{ SUBJECTS : has
    SUBJECTS ||--o{ ATTENDANCE_SESSIONS : includes
    STUDENTS ||--o{ ATTENDANCE_RECORDS : participates
    ATTENDANCE_SESSIONS ||--o{ ATTENDANCE_RECORDS : records
    
    USERS {
        int id PK
        string username
        string password_hash
        datetime created_at
    }
    
    CLASSES {
        int id PK
        string name
        string description
        int user_id FK
        datetime created_at
    }
    
    STUDENTS {
        int id PK
        string student_id
        string full_name
        string email
        int class_id FK
        datetime created_at
    }
    
    SUBJECTS {
        int id PK
        string name
        string description
        int class_id FK
        datetime created_at
    }
    
    ATTENDANCE_SESSIONS {
        int id PK
        string session_name
        int subject_id FK
        datetime created_at
        string status
    }
    
    ATTENDANCE_RECORDS {
        int id PK
        int student_id FK
        int session_id FK
        datetime timestamp
        string status
    }
```

### 💾 Data Processing Flow

```mermaid
sequenceDiagram
    participant UI as Web Interface
    participant Route as Flask Route
    participant DB as Database
    participant AI as AI Module
    participant Storage as File Storage
    
    Note over UI,Storage: Quy trình Thu thập Dữ liệu Khuôn mặt
    
    UI->>Route: Chọn sinh viên
    Route->>DB: Lấy thông tin sinh viên
    DB-->>Route: Student data
    Route-->>UI: Hiển thị camera
    
    UI->>AI: Capture face images
    AI->>AI: Augmentation (rotation, brightness)
    AI->>Storage: Lưu ảnh gốc + augmented
    AI-->>UI: Feedback quá trình
    
    UI->>Route: Hoàn thành thu thập
    Route->>AI: Train/Update model
    AI->>Storage: Lưu model mới
    AI-->>Route: Training complete
    Route-->>UI: Thông báo thành công
```

---

## 📈 Performance Metrics

### ⚡ Response Time Analysis

```mermaid
graph LR
    subgraph "Performance Benchmarks"
        LOGIN[Login: ~200ms]
        DASHBOARD[Dashboard: ~300ms]
        FACE_DETECT[Face Detection: ~100ms]
        RECOGNITION[Recognition: ~500ms]
        EXPORT[Excel Export: ~2s]
    end
    
    subgraph "Optimization Targets"
        OPT1[Database queries < 100ms]
        OPT2[Face recognition < 300ms]
        OPT3[File operations < 1s]
    end
    
    LOGIN --> OPT1
    FACE_DETECT --> OPT2
    EXPORT --> OPT3
    
    style LOGIN fill:#c8e6c9
    style FACE_DETECT fill:#fff9c4
    style EXPORT fill:#ffcdd2
```

### 🔍 Accuracy Metrics

| Model | Speed | Accuracy | Resource Usage | Best Use Case |
|-------|-------|----------|----------------|---------------|
| OpenCV | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | Demo, Testing |
| Face Recognition | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Production |
| Advanced AI | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | High Security |

---

## 🚨 Error Handling

### 🛠️ Troubleshooting Flowchart

```mermaid
flowchart TD
    ERROR[Lỗi xảy ra] --> TYPE{Loại lỗi?}
    
    TYPE -->|Camera| CAM_ERROR[Camera không hoạt động]
    TYPE -->|Recognition| AI_ERROR[AI không nhận diện]
    TYPE -->|Database| DB_ERROR[Database lỗi]
    TYPE -->|File| FILE_ERROR[File không tải được]
    
    CAM_ERROR --> CAM_CHECK{Camera connected?}
    CAM_CHECK -->|No| CAM_FIX[Kết nối camera]
    CAM_CHECK -->|Yes| CAM_PERM[Kiểm tra quyền camera]
    
    AI_ERROR --> MODEL_CHECK{Model loaded?}
    MODEL_CHECK -->|No| LOAD_MODEL[Load lại model]
    MODEL_CHECK -->|Yes| RETRAIN[Cần train lại?]
    
    DB_ERROR --> DB_CHECK{Database exists?}
    DB_CHECK -->|No| CREATE_DB[Tạo database mới]
    DB_CHECK -->|Yes| DB_REPAIR[Sửa database]
    
    FILE_ERROR --> PERM_CHECK{Quyền ghi file?}
    PERM_CHECK -->|No| FIX_PERM[Sửa quyền thư mục]
    PERM_CHECK -->|Yes| DISK_SPACE[Kiểm tra dung lượng]
    
    style ERROR fill:#ffcdd2
    style CAM_FIX fill:#c8e6c9
    style LOAD_MODEL fill:#c8e6c9
    style CREATE_DB fill:#c8e6c9
```

### 🔧 Common Issues & Solutions

```mermaid
graph TD
    subgraph "Camera Issues"
        C1[Camera không bật được]
        C2[Hình ảnh bị mờ]
        C3[FPS quá thấp]
    end
    
    subgraph "AI Issues"
        A1[Không nhận diện được]
        A2[Nhận diện sai người]
        A3[Model load chậm]
    end
    
    subgraph "Solutions"
        S1[Kiểm tra driver camera]
        S2[Điều chỉnh ánh sáng]
        S3[Giảm resolution]
        S4[Thu thập thêm dữ liệu]
        S5[Train lại model]
        S6[Tối ưu model size]
    end
    
    C1 --> S1
    C2 --> S2
    C3 --> S3
    A1 --> S4
    A2 --> S5
    A3 --> S6
    
    style C1 fill:#ffcdd2
    style A1 fill:#ffcdd2
    style S1 fill:#c8e6c9
    style S4 fill:#c8e6c9
```

### 📋 Troubleshooting Guide

| Lỗi | Triệu chứng | Nguyên nhân | Giải pháp |
|-----|-------------|-------------|-----------|
| 📷 **Camera không hoạt động** | Màn hình đen, không có video | Browser chưa cấp quyền | Vào Settings → Privacy → Camera → Allow |
| 🧠 **Không nhận diện được** | "Không tìm thấy sinh viên" | Chưa thu thập đủ dữ liệu | Thu thập thêm 10-15 ảnh khuôn mặt |
| 📊 **Xuất Excel lỗi** | File không tải về | Lỗi permissions | Tạo thư mục `exports` với quyền write |
| 🗄️ **Database locked** | "Database is locked" | Nhiều connections | Restart server, đóng tất cả connections |
| 🌐 **Server không phản hồi** | Trang trắng/timeout | Server crash | Restart bằng `python app.py` |

---

## 📊 System Monitoring

### 📈 Real-time Dashboard Metrics

```mermaid
graph LR
    subgraph "System Health"
        CPU[CPU Usage]
        RAM[Memory Usage]
        DISK[Disk Space]
        CAM[Camera Status]
    end
    
    subgraph "Application Metrics"
        USERS[Active Users]
        SESSIONS[Active Sessions]
        ACCURACY[Recognition Accuracy]
        SPEED[Processing Speed]
    end
    
    subgraph "Alerts"
        HIGH_CPU[CPU > 80%]
        LOW_DISK[Disk < 10%]
        CAM_FAIL[Camera Offline]
        LOW_ACC[Accuracy < 90%]
    end
    
    CPU --> HIGH_CPU
    DISK --> LOW_DISK
    CAM --> CAM_FAIL
    ACCURACY --> LOW_ACC
    
    style HIGH_CPU fill:#ffcdd2
    style LOW_DISK fill:#ffcdd2
    style CAM_FAIL fill:#ffcdd2
    style LOW_ACC fill:#fff9c4
```

### ⏱️ Performance Timeline

```mermaid
gantt
    title Thời gian xử lý các tác vụ hệ thống
    dateFormat X
    axisFormat %L ms
    
    section Authentication
    Login process: 0, 200
    Session check: 0, 50
    
    section Face Recognition
    Camera init: 0, 300
    Face detection: 0, 100
    Face recognition: 0, 500
    
    section Data Operations
    Database query: 0, 50
    Excel export: 0, 2000
    Model training: 0, 10000
```

---

## 🎯 Conclusion

Hệ thống điểm danh khuôn mặt được thiết kế với kiến trúc modular, dễ bảo trì và mở rộng. Luồng hoạt động được tối ưu để đảm bảo hiệu suất cao và trải nghiệm người dùng mượt mà.

### 🔑 Key Benefits

1. **🚀 High Performance**: Xử lý real-time với multiple AI models
2. **🔒 Secure**: Session-based authentication với route protection
3. **📱 Responsive**: Mobile-friendly interface
4. **📊 Analytics**: Comprehensive reporting và export capabilities
5. **🛠️ Maintainable**: Clean code structure với detailed documentation

### 🎯 Future Enhancements

- [ ] API REST cho mobile app
- [ ] Cloud deployment support
- [ ] Advanced analytics dashboard
- [ ] Multi-tenant support
- [ ] Real-time notifications
- [ ] Integration với hệ thống LMS

---

*📝 Document được cập nhật thường xuyên để phản ánh các thay đổi trong hệ thống.*
