# 課程選課系統 - 後端 API

## 專案簡介

本系統是一個為大專院校打造的線上課程選課系統後端 API，採用 Django REST Framework 開發，提供完整的選課功能與 RESTful API 介面。

## 主要功能

- **使用者認證系統**：支援學生、教師、管理員三種角色
- **課程管理**：課程查詢、篩選、搜尋功能
- **選課作業**：選課、退選，支援完整的業務規則檢查
- **課表查詢**：查看已選課程與時間表
- **API 文件**：自動生成的 Swagger/OpenAPI 文件

## 技術架構

- **框架**：Django 5.2 + Django REST Framework
- **資料庫**：PostgreSQL 15
- **認證**：Session Authentication (可擴充 JWT)
- **API 文件**：drf-yasg (Swagger/OpenAPI)
- **部署**：Docker + Docker Compose

## 專案結構

```
course_selection_project/
├── course_selection_project/    # 專案設定
│   ├── settings.py              # Django 設定檔
│   ├── urls.py                  # 全域路由
│   └── wsgi.py                  # WSGI 進入點
├── accounts/                    # 使用者相關應用
│   ├── models.py                # User 模型 (擴充 AbstractUser)
│   ├── serializers.py           # 使用者資料序列化器
│   ├── views.py                 # 認證相關 API 視圖
│   └── urls.py                  # 認證路由
├── courses/                     # 課程選課核心應用
│   ├── models.py                # Course, Enrollment, CourseTimeSlot 模型
│   ├── serializers.py           # 課程相關序列化器
│   ├── services.py              # 業務邏輯服務層
│   ├── views.py                 # 課程與選課 API 視圖
│   ├── urls.py                  # 課程相關路由
│   └── management/commands/     # 資料初始化指令
├── docker-compose.yml           # Docker 服務配置
├── Dockerfile                   # 應用 Docker 建置檔
└── requirements.txt             # Python 依賴套件
```

## 環境需求

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (推薦)

## 快速開始

### 方法一：使用 Docker (推薦)

1. **複製專案**
```bash
git clone <your-repo-url>
cd course_selection_project
```

2. **啟動服務**
```bash
docker-compose up -d
```

3. **初始化資料庫**
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_code
```

4. **建立管理員帳號**
```bash
docker-compose exec web python manage.py createsuperuser
```

### 方法二：本地開發

1. **設定 Python 環境**
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **設定 PostgreSQL**
```bash
# 確保 PostgreSQL 運行，並建立資料庫
createdb course_selection_db
```

3. **設定環境變數** (可選)
```bash
export DATABASE_URL=postgresql://dylan:ji3cl3x04@localhost:5432/course_selection_db
```

4. **執行遷移與初始化**
```bash
python manage.py migrate
python manage.py seed_code
python manage.py runserver
```

## API 端點

### 認證相關
- `POST /api/auth/login/` - 使用者登入
- `POST /api/auth/logout/` - 使用者登出
- `GET /api/auth/me/` - 取得當前使用者資訊
- `POST /api/auth/register/` - 使用者註冊

### 課程相關
- `GET /api/courses/` - 取得課程列表 (支援搜尋與篩選)
- `GET /api/courses/{id}/` - 取得特定課程詳情

### 選課相關
- `GET /api/enrollments/` - 取得已選課程列表
- `POST /api/enrollments/` - 選課
- `DELETE /api/enrollments/{id}/` - 退選
- `GET /api/enrollments/my-courses/` - 取得我的課表

## 選課規則

系統會自動檢查以下選課規則：

1. **修課門數限制**：最少 2 門，最多 8 門課程
2. **人數上限檢查**：課程額滿後無法選修
3. **時間衝突檢測**：自動偵測並防止時間重疊的課程
4. **重複選課防護**：防止選擇相同課程

## 測試資料

執行 `python manage.py seed_code` 後會建立：

- **管理員**：admin / admin123
- **教師**：teacher001-003 / password123  
- **學生**：student001-020 / password123
- **課程**：10 門測試課程 (含必修與選修)
- **時間表**：每門課程 1-2 個時段

## API 文件

啟動服務後可在以下位置查看 API 文件：
- Swagger UI: `http://localhost:8000/swagger/`
- OpenAPI JSON: `http://localhost:8000/swagger.json`

## 開發工具

### 管理指令

```bash
# 建立測試資料
python manage.py seed_code

# 清除並重建測試資料  
python manage.py seed_code --clear

# 建立 Django 管理員
python manage.py createsuperuser

# 執行測試
python manage.py test
```

### Django 管理後台

訪問 `http://localhost:8000/admin/` 使用管理員帳號登入，可管理：
- 使用者帳號
- 課程資料  
- 選課記錄
- 課程時間設定

## 部署說明

### Docker 部署

```bash
# 建置映像
docker build -t course-selection-api .

# 使用 Docker Compose 部署
docker-compose up -d

# 檢查服務狀態
docker-compose ps
```

### 環境變數設定

建議在正式環境設定以下環境變數：

```env
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@host:port/dbname
ALLOWED_HOSTS=your-domain.com
```

## 測試

```bash
# 執行所有測試
python manage.py test

# 執行特定應用測試
python manage.py test accounts
python manage.py test courses

# 產生測試覆蓋率報告
coverage run --source='.' manage.py test
coverage html
```

## 故障排除

### 常見問題

1. **資料庫連線錯誤**
   - 確認 PostgreSQL 服務運行
   - 檢查 `settings.py` 中的資料庫設定

2. **CORS 錯誤**  
   - 檢查 `ALLOWED_HOSTS` 設定
   - 確認前端 URL 在 `CORS_ALLOWED_ORIGINS` 中

3. **認證問題**
   - 確認 Session 設定正確
   - 檢查 CSRF 設定

### 日誌查看

```bash
# Docker 環境查看日誌
docker-compose logs web

# 查看資料庫日誌
docker-compose logs db
```