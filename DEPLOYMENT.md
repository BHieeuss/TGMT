# 🚀 Hướng dẫn Deploy TGMT Face Attendance System

## 📋 Mục lục

1. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
2. [Deploy với Docker (Khuyến nghị)](#deploy-với-docker)
3. [Deploy thủ công](#deploy-thủ-công)
4. [Truy cập từ Internet (mạng khác)](#truy-cập-từ-internet)
5. [Deploy lên Cloud](#deploy-lên-cloud)
6. [Cấu hình và bảo mật](#cấu-hình-và-bảo-mật)
7. [Monitoring và Maintenance](#monitoring-và-maintenance)

## 🖥️ Yêu cầu hệ thống

### Minimum Requirements:

- **CPU:** 2 cores
- **RAM:** 4GB
- **Storage:** 10GB free space
- **OS:** Windows 10/11, Ubuntu 18.04+, CentOS 7+

### Recommended:

- **CPU:** 4+ cores
- **RAM:** 8GB+
- **Storage:** 50GB+ SSD
- **GPU:** Optional (for better face recognition performance)

## 🐳 Deploy với Docker (Khuyến nghị)

### Bước 1: Cài đặt Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Windows: Download Docker Desktop từ docker.com
```

### Bước 2: Clone và Deploy

```bash
# Clone repository
git clone https://github.com/BHieeuss/TGMT.git
cd TGMT

# Deploy (Linux/Mac)
chmod +x deploy.sh
./deploy.sh

# Deploy (Windows)
deploy.bat
```

### Bước 3: Truy cập ứng dụng

- **URL:** http://localhost:5000
- **Username:** admin
- **Password:** admin123

### Các lệnh Docker hữu ích:

```bash
# Xem logs
docker-compose logs -f face-attendance

# Restart ứng dụng
docker-compose restart

# Stop ứng dụng
docker-compose down

# Update và rebuild
git pull
docker-compose down
docker-compose up --build -d
```

## ⚙️ Deploy thủ công

### Bước 1: Cài đặt Python dependencies

```bash
# Tạo virtual environment
python -m venv face_attendance_env

# Activate virtual environment
# Linux/Mac:
source face_attendance_env/bin/activate
# Windows:
face_attendance_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Bước 2: Cấu hình môi trường

```bash
# Tạo file .env
export FLASK_ENV=production
export SECRET_KEY="your-super-secret-key-here"
export DATABASE_PATH="attendance_system.db"
```

### Bước 3: Chạy ứng dụng

```bash
# Development
python app.py

# Production với Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🌐 Truy cập từ Internet (mạng khác)

### Người ở mạng khác muốn truy cập website của bạn có 4 cách:

### 1. 🔧 Cấu hình Router (Port Forwarding) - Miễn phí

**Bước 1: Tìm IP nội bộ của máy bạn**
```bash
# Windows
ipconfig | findstr "IPv4"

# Hoặc chạy script
quick-deploy.bat  # Option 8
```

**Bước 2: Tìm IP công cộng của mạng**
- Truy cập: https://whatismyipaddress.com/
- Ghi lại địa chỉ IP (VD: 123.45.67.89)

**Bước 3: Cấu hình Router**
```
1. Truy cập router admin (thường là 192.168.1.1 hoặc 192.168.0.1)
2. Tìm mục "Port Forwarding" hoặc "Virtual Server"
3. Thêm rule:
   - External Port: 8080 (port từ internet)
   - Internal IP: [IP máy bạn] (VD: 192.168.1.100)
   - Internal Port: 5000 (port app)
   - Protocol: TCP
4. Save và restart router
```

**Bước 4: Chia sẻ URL**
```
http://[IP_CONG_CONG]:8080
VD: http://123.45.67.89:8080
```

### 2. 🚇 Sử dụng Ngrok - Nhanh nhất

**Cài đặt Ngrok:**
```bash
# Download từ: https://ngrok.com/download
# Hoặc dùng chocolatey:
choco install ngrok

# Đăng ký tài khoản miễn phí tại ngrok.com
```

**Chạy Ngrok:**
```bash
# Sau khi deploy app (port 5000)
ngrok http 5000

# Ngrok sẽ tạo URL public:
# https://abc123.ngrok.io -> localhost:5000
```

**Chia sẻ URL:**
```
Người khác truy cập: https://abc123.ngrok.io
Username: admin
Password: admin123
```

### 3. ☁️ Sử dụng Cloudflare Tunnel - Miễn phí

**Cài đặt Cloudflared:**
```bash
# Download từ: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
# Hoặc chạy:
winget install --id Cloudflare.cloudflared
```

**Tạo tunnel:**
```bash
# Login Cloudflare
cloudflared tunnel login

# Tạo tunnel
cloudflared tunnel create tgmt-attendance

# Chạy tunnel
cloudflared tunnel --url http://localhost:5000
```

### 4. 🏠 Sử dụng LocalTunnel - Đơn giản

**Cài đặt:**
```bash
npm install -g localtunnel
```

**Chạy:**
```bash
# Sau khi app chạy trên port 5000
lt --port 5000 --subdomain tgmt-attendance

# Sẽ tạo URL: https://tgmt-attendance.loca.lt
```

### 📱 Hướng dẫn chi tiết cho Ngrok (Khuyến nghị):

**Bước 1: Deploy app**
```bash
# Chọn 1 cách:
python-deploy.bat
# hoặc
simple-deploy.bat
```

**Bước 2: Cài Ngrok**
```bash
# Tải từ: https://ngrok.com/download
# Giải nén và copy ngrok.exe vào thư mục project
```

**Bước 3: Đăng ký và setup**
```bash
# Đăng ký tại: https://ngrok.com/signup
# Copy authtoken từ dashboard
ngrok authtoken YOUR_AUTHTOKEN
```

**Bước 4: Tạo tunnel**
```bash
ngrok http 5000
```

**Kết quả:**
```
Forwarding    https://abc123.ngrok.io -> http://localhost:5000
```

**Chia sẻ:**
- URL: https://abc123.ngrok.io
- Login: admin / admin123

### ⚠️ Lưu ý bảo mật:

1. **Đổi mật khẩu mặc định**
2. **Chỉ chia sẻ với người tin tương**
3. **Tắt tunnel khi không dùng**
4. **Sử dụng HTTPS khi có thể**

### 🔒 Nâng cao - Domain riêng:

1. **Mua domain** (VD: tgmt-attendance.com)
2. **Cấu hình DNS** trỏ về IP công cộng
3. **Setup SSL certificate** với Let's Encrypt
4. **Sử dụng Nginx reverse proxy**

## ☁️ Deploy lên Cloud (Chạy 24/7 - Không cần máy tính)

### 🚀 1. Render.com (Miễn phí - Khuyến nghị)

**Bước 1: Chuẩn bị repository**
```bash
# Push code lên GitHub (nếu chưa có)
git add .
git commit -m "Add cloud deployment"
git push origin main
```

**Bước 2: Deploy trên Render**
```
1. Truy cập: https://render.com/
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Connect GitHub repository: BHieeuss/TGMT
5. Cấu hình:
   - Name: tgmt-face-attendance
   - Environment: Docker
   - Region: Singapore (gần VN nhất)
   - Branch: main
   - Build Command: (để trống)
   - Start Command: (để trống - dùng Dockerfile)
6. Click "Create Web Service"
```

**Kết quả:**
- URL: https://tgmt-face-attendance.onrender.com
- Chạy 24/7 miễn phí
- Auto deploy khi push code mới

### 🐳 2. Railway.app (Miễn phí - Dễ dùng)

**Deploy 1-click:**
```
1. Truy cập: https://railway.app/
2. Login with GitHub
3. Click "Deploy from GitHub repo"
4. Chọn repository: BHieeuss/TGMT
5. Railway tự động detect Dockerfile và deploy
```

**URL result:** https://your-app.railway.app

### 📱 3. Vercel (Miễn phí - Nhanh)

**Chỉ cần 1 click:**
```
1. Truy cập: https://vercel.com/
2. Import Git Repository
3. Chọn BHieeuss/TGMT
4. Click Deploy
```

### 🔧 4. Heroku (Miễn phí với GitHub Student)

**Tự động deploy:**
```bash
# Tạo file cần thiết sẽ ở dưới
# Sau đó:
1. Truy cập: https://heroku.com/
2. Create new app
3. Connect GitHub repository
4. Enable automatic deploys
```

### 🌟 5. GitHub Codespaces + Port Forwarding

**Chạy trực tiếp trên GitHub:**
```
1. Vào repository GitHub
2. Click "Code" → "Codespaces" → "Create codespace"
3. Trong codespace chạy: python app.py
4. Port 5000 sẽ được forward tự động
5. URL public sẽ được tạo
```

### 🎯 Khuyến nghị theo nhu cầu:

- **Đơn giản nhất:** Render.com
- **Nhanh nhất:** Railway.app  
- **Miễn phí lâu dài:** GitHub Codespaces
- **Chuyên nghiệp:** Heroku

## 🔒 Cấu hình và Bảo mật

### 1. Environment Variables

```bash
# Tạo file .env
SECRET_KEY=your-super-secret-key-here-change-this
FLASK_ENV=production
DATABASE_PATH=/app/data/attendance_system.db
UPLOAD_FOLDER=/app/uploads
EXPORT_FOLDER=/app/exports
FACE_RECOGNITION_TOLERANCE=0.6
MAX_FACE_IMAGES_PER_STUDENT=50
```

### 2. SSL/HTTPS Setup

```bash
# Với Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Update nginx.conf với SSL configuration
```

### 3. Firewall Configuration

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 4. Database Backup

```bash
# Tạo backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp attendance_system.db backups/attendance_system_$DATE.db

# Crontab để backup hàng ngày
crontab -e
0 2 * * * /path/to/backup-script.sh
```

## 📊 Monitoring và Maintenance

### 1. Health Check

```bash
# Check application status
curl -f http://localhost:5000/health || echo "App is down"

# Docker health check
docker-compose ps
```

### 2. Log Management

```bash
# View application logs
docker-compose logs -f face-attendance

# Rotate logs (add to crontab)
0 0 * * 0 docker system prune -f
```

### 3. Performance Monitoring

```bash
# System resources
htop
df -h
docker stats

# Application metrics
curl http://localhost:5000/metrics
```

### 4. Update Process

```bash
# Update application
cd /path/to/TGMT
git pull origin main
docker-compose down
docker-compose up --build -d
```

## 🛠️ Troubleshooting

### Common Issues:

1. **Face recognition không hoạt động**

   ```bash
   # Kiểm tra camera permissions
   ls -la /dev/video*
   # Restart container
   docker-compose restart face-attendance
   ```

2. **Database locked error**

   ```bash
   # Stop all processes using database
   sudo fuser -k attendance_system.db
   docker-compose restart
   ```

3. **Memory issues**

   ```bash
   # Increase container memory
   # Update docker-compose.yml:
   mem_limit: 2g
   ```

4. **Permission errors**
   ```bash
   # Fix permissions
   sudo chown -R 1000:1000 uploads exports
   chmod -R 755 uploads exports
   ```

## 📞 Hỗ trợ

- **Issues:** [GitHub Issues](https://github.com/BHieeuss/TGMT/issues)
- **Documentation:** [Project Wiki](https://github.com/BHieeuss/TGMT/wiki)
- **Email:** your-email@example.com

## 📝 Changelog

### v1.0.0 (2024-07-20)

- Initial deployment configuration
- Docker support
- Multi-platform deployment scripts
- Production-ready configuration
