# 🚀 Quick Deploy Guide

## Deploy ngay trong 5 phút!

### Cách 1: Docker (Khuyến nghị) 🐳

```bash
# 1. Cài Docker Desktop (nếu chưa có)
# Download từ: https://www.docker.com/products/docker-desktop

# 2. Clone repo
git clone https://github.com/BHieeuss/TGMT.git
cd TGMT

# 3. Deploy (Windows)
deploy.bat

# 3. Deploy (Linux/Mac)
chmod +x deploy.sh
./deploy.sh
```

### Cách 2: Quick Deploy Script 🎯

```bash
# Windows
quick-deploy.bat

# Chọn option 1 để deploy với Docker
# Hoặc option 2 để deploy thủ công
```

### Truy cập ứng dụng 🌐

- **URL:** http://localhost:5000
- **Username:** admin
- **Password:** admin123

### Lệnh hữu ích 🛠️

```bash
# Xem logs
docker-compose logs -f face-attendance

# Restart
docker-compose restart

# Stop
docker-compose down

# Backup
backup.sh  # Linux/Mac
# hoặc sử dụng quick-deploy.bat option 5
```

## Cần hỗ trợ? 🆘

- Đọc [DEPLOYMENT.md](DEPLOYMENT.md) để biết chi tiết
- Kiểm tra [Issues](https://github.com/BHieeuss/TGMT/issues)

---

**⚡ Tip:** Chạy `quick-deploy.bat` để có menu tương tác dễ sử dụng!
