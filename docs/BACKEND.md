# Backend 技術文件

> 本文件記錄 AI 舊程式碼智能重構系統的後端架構、API 設計與實作細節

**最後更新**: 2026-02-02

---

## 目錄

1. [架構總覽](#架構總覽)
2. [核心模組](#核心模組)
3. [資料模型](#資料模型)
4. [API 端點規格](#api-端點規格)
5. [服務層設計](#服務層設計)
6. [認證機制](#認證機制)
7. [開發模式](#開發模式)
8. [錯誤處理](#錯誤處理)
9. [部署配置](#部署配置)

---

## 架構總覽

### 技術棧

- **框架**: FastAPI 0.109.0 (Python 3.11+)
- **資料庫**: MongoDB 7 (非同步驅動 motor)
- **容器管理**: Docker (使用 subprocess 呼叫 CLI)
- **LLM 整合**:
  - Anthropic Claude (透過 API)
  - Google Vertex AI Gemini (透過 Google Cloud SDK)
- **認證**: JWT (HS256)
- **SSE 串流**: sse-starlette

### 系統架構圖

```
┌─────────────┐
│   Frontend  │
│  (React)    │
└──────┬──────┘
       │ HTTP/SSE
       │
┌──────▼────────────────────────────────────────┐
│           Backend API (FastAPI)               │
│  ┌─────────────┐  ┌────────────┐             │
│  │   Routers   │  │  Services  │             │
│  │  - auth     │  │  - auth    │             │
│  │  - projects │  │  - project │             │
│  │  - agent    │  │  - container│            │
│  └─────────────┘  └────────────┘             │
│         │                 │                   │
│         ▼                 ▼                   │
│  ┌──────────────┐  ┌──────────────┐          │
│  │   MongoDB    │  │    Docker    │          │
│  │  (Database)  │  │   (Containers)│         │
│  └──────────────┘  └──────┬───────┘          │
└────────────────────────────┼──────────────────┘
                             │
                ┌────────────▼────────────┐
                │  Container AI Server    │
                │  (LangChain Deep Agent) │
                │  - /run (啟動 Agent)    │
                │  - /tasks (查詢狀態)    │
                │  - /stream (SSE 日誌)   │
                └─────────────────────────┘
```

### 資料流

1. **專案建立** → `POST /api/v1/projects` → MongoDB
2. **Provision** → `POST /projects/{id}/provision` → 建立 Docker 容器 → Clone Repository
3. **執行 Agent** → `POST /projects/{id}/agent/run` → 呼叫容器內 AI Server `/run` → 背景執行
4. **查詢狀態** → `GET /projects/{id}/agent/runs/{run_id}` → 代理查詢容器 `/tasks/{run_id}`
5. **串流日誌** → `GET /projects/{id}/agent/runs/{run_id}/stream` → SSE 轉發容器日誌

---

## 核心模組

### 目錄結構

```
backend/
├── app/
│   ├── main.py                 # FastAPI 應用入口
│   ├── config.py               # 配置管理
│   ├── database/
│   │   ├── mongodb.py          # MongoDB 連線管理
│   │   └── __init__.py
│   ├── models/                 # 資料模型 (Pydantic)
│   │   ├── project.py          # Project, ProjectStatus
│   │   ├── user.py             # User
│   │   └── __init__.py
│   ├── schemas/                # API Schema (請求/回應)
│   │   ├── auth.py             # 認證相關 Schema
│   │   ├── project.py          # 專案 CRUD Schema
│   │   ├── provision.py        # Provision 回應
│   │   ├── execution.py        # 執行指令 Schema
│   │   └── __init__.py
│   ├── routers/                # API 路由
│   │   ├── auth.py             # 認證 API
│   │   ├── projects.py         # 專案 CRUD + 容器操作
│   │   ├── agent.py            # Agent 執行 (代理 AI Server)
│   │   ├── health.py           # 健康檢查
│   │   └── __init__.py
│   ├── services/               # 業務邏輯層
│   │   ├── auth_service.py     # 用戶認證 + JWT
│   │   ├── project_service.py  # 專案管理 + 狀態變更
│   │   ├── container_service.py # Docker 容器操作
│   │   ├── log_service.py      # 日誌串流 (SSE)
│   │   └── __init__.py
│   ├── dependencies/           # FastAPI 依賴注入
│   │   ├── auth.py             # get_current_user, get_auth_service
│   │   └── __init__.py
│   └── utils/                  # 工具函數
│       ├── mongodb_helpers.py  # ObjectId 轉換
│       └── __init__.py
├── tests/                      # 測試程式
├── requirements.txt            # Python 依賴
└── .env.example                # 環境變數範本
```

### 關鍵檔案說明

#### `app/main.py`
- FastAPI 應用入口
- CORS 中介層配置
- 路由註冊
- 應用生命週期管理 (lifespan)

#### `app/config.py`
- 使用 Pydantic Settings 管理配置
- 支援 `.env` 檔案
- 主要配置項:
  - MongoDB 連線
  - Docker 設定 (base image, network, volume)
  - LLM 設定 (Anthropic, Vertex AI)
  - JWT 設定
  - 開發模式 (DEV_MODE)

#### `app/database/mongodb.py`
- MongoDB 非同步連線管理
- 使用 `motor` 驅動 (Motor: asyncio MongoDB driver)
- 提供 `get_database()` 依賴注入函數

---

## 資料模型

### Project (專案模型)

**檔案**: `backend/app/models/project.py`

```python
class ProjectStatus(str, Enum):
    CREATED = "CREATED"           # 已建立
    PROVISIONING = "PROVISIONING" # 正在建立容器
    READY = "READY"               # 容器就緒
    RUNNING = "RUNNING"           # 正在執行 Agent
    STOPPED = "STOPPED"           # 已停止
    FAILED = "FAILED"             # 失敗
    DELETED = "DELETED"           # 已刪除

class Project(BaseModel):
    id: str                       # MongoDB _id
    repo_url: str                 # Git Repository URL
    branch: str = "main"          # Git Branch
    init_prompt: str              # Agent 初始提示
    status: ProjectStatus         # 專案狀態
    container_id: Optional[str]   # Docker 容器 ID
    owner_id: str                 # 擁有者用戶 ID
    owner_email: Optional[str]    # 擁有者 Email (冗餘欄位)
    created_at: datetime          # 建立時間
    updated_at: datetime          # 更新時間
    last_error: Optional[str]     # 最後錯誤訊息
```

**狀態轉換流程**:
```
CREATED → PROVISIONING → READY → RUNNING → READY
                ↓           ↓        ↓
              FAILED     STOPPED  FAILED
```

**MongoDB Collection**: `projects`

**索引建議**:
- `owner_id` (單欄位索引，加速用戶專案查詢)
- `created_at` (降序，加速時間排序)

### User (用戶模型)

**檔案**: `backend/app/models/user.py`

```python
class User(BaseModel):
    id: Optional[str]             # MongoDB _id
    email: EmailStr               # 唯一，用於登入
    username: str                 # 用戶名稱
    password_hash: str            # bcrypt hash
    is_active: bool = True        # 帳號啟用狀態
    created_at: datetime          # 建立時間
    updated_at: datetime          # 更新時間
```

**MongoDB Collection**: `users`

**索引建議**:
- `email` (唯一索引)

---

## API 端點規格

### 認證 API (`/api/v1/auth`)

#### POST /auth/register
**註冊新用戶**

```json
// Request
{
  "email": "user@example.com",
  "username": "testuser",
  "password": "securepassword"
}

// Response (201 Created)
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "testuser",
  "is_active": true,
  "created_at": "2026-02-02T12:00:00Z"
}
```

#### POST /auth/login
**用戶登入**

```json
// Request
{
  "email": "user@example.com",
  "password": "securepassword"
}

// Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### GET /auth/me
**取得當前用戶資訊**

需要 `Authorization: Bearer <token>` header

```json
// Response
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "testuser",
  "is_active": true,
  "created_at": "2026-02-02T12:00:00Z"
}
```

### 專案 API (`/api/v1/projects`)

#### POST /projects
**建立專案** (需認證)

```json
// Request
{
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main",
  "init_prompt": "請分析這個專案並提出重構建議"
}

// Response (201 Created)
{
  "id": "507f1f77bcf86cd799439011",
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main",
  "init_prompt": "請分析這個專案並提出重構建議",
  "status": "CREATED",
  "container_id": null,
  "owner_id": "507f191e810c19729de860ea",
  "created_at": "2026-02-02T12:00:00Z",
  "updated_at": "2026-02-02T12:00:00Z"
}
```

#### GET /projects/{project_id}
**查詢專案** (需認證)

Query 參數:
- `include_docker_status`: boolean (預設 true，附加 Docker 容器即時狀態)

```json
// Response
{
  "id": "507f1f77bcf86cd799439011",
  "repo_url": "https://github.com/user/repo.git",
  "status": "READY",
  "container_id": "abc123def456",
  "docker_status": {
    "id": "abc123def456",
    "name": "refactor-project-507f1f77bcf86cd799439011",
    "status": "running",
    "image": "refactor-base:latest"
  }
}
```

#### GET /projects
**列出專案** (需認證)

Query 參數:
- `skip`: int (預設 0)
- `limit`: int (預設 100)

只返回當前用戶擁有的專案。

```json
// Response
{
  "total": 5,
  "projects": [...]
}
```

#### PUT /projects/{project_id}
**更新專案** (需認證)

**重要限制**: 專案 Provision 後 (`status != CREATED`) 無法修改 `repo_url`

```json
// Request
{
  "init_prompt": "新的提示內容"
}

// Response
{
  "id": "507f1f77bcf86cd799439011",
  "init_prompt": "新的提示內容",
  ...
}
```

#### POST /projects/{project_id}/provision
**Provision 專案** (需認證)

建立 Docker 容器並 clone repository

Query 參數:
- `dev_mode`: boolean | null (覆蓋全域 DEV_MODE 設定)
  - `true`: 強制啟用開發模式 (掛載本機 agent)
  - `false`: 強制停用開發模式 (使用 image 內建 agent)
  - `null` (預設): 使用 `.env` 中的 `DEV_MODE` 設定

```json
// Response
{
  "message": "專案 provision 成功",
  "project_id": "507f1f77bcf86cd799439011",
  "container_id": "abc123def456",
  "status": "READY"
}
```

**錯誤處理**: 失敗時自動清理容器，狀態設為 `FAILED`，錯誤記錄在 `last_error`

#### POST /projects/{project_id}/exec
**執行容器指令** (需認證)

```json
// Request
{
  "command": "ls -la /workspace/repo",
  "workdir": "/workspace/repo"
}

// Response
{
  "exit_code": 0,
  "stdout": "...",
  "stderr": ""
}
```

#### GET /projects/{project_id}/logs/stream
**SSE 串流容器日誌** (需認證)

Query 參數:
- `follow`: boolean (預設 true，持續串流)
- `tail`: int (預設 100，最後 N 行)

```
GET /api/v1/projects/{id}/logs/stream?follow=true&tail=100

event: log
data: Container log line 1

event: log
data: Container log line 2

event: ping
data: keep-alive
```

#### POST /projects/{project_id}/stop
**停止容器** (需認證)

```json
// Response
{
  "id": "507f1f77bcf86cd799439011",
  "status": "STOPPED",
  ...
}
```

#### DELETE /projects/{project_id}
**刪除專案和容器** (需認證)

Response: `204 No Content`

### Agent API (`/api/v1/projects/{project_id}/agent`)

**設計原則**: Backend 不維護 Agent Run 狀態，所有查詢轉發到容器內 AI Server

#### POST /agent/run
**啟動 Agent 執行** (需認證)

**前置條件**: 專案狀態必須為 `READY`

```json
// Response
{
  "run_id": "task_abc123",
  "project_id": "507f1f77bcf86cd799439011",
  "status": "RUNNING",
  "iteration_index": 0,
  "phase": "plan",
  "created_at": "2026-02-02T12:00:00Z",
  "message": "Agent 任務已啟動，正在背景執行"
}
```

**實作細節**:
1. 驗證專案狀態 (`READY`)
2. 呼叫容器內 AI Server: `POST http://refactor-project-{id}:8000/run`
3. 立即返回 `run_id` (task_id)
4. Agent 在容器內背景執行

#### GET /agent/runs
**列出所有 Agent Runs** (需認證)

```json
// Response
{
  "total": 3,
  "runs": [
    {
      "id": "task_abc123",
      "project_id": "507f1f77bcf86cd799439011",
      "status": "DONE",
      "phase": "plan",
      "created_at": "2026-02-02T12:00:00Z",
      "finished_at": "2026-02-02T12:05:00Z"
    }
  ]
}
```

**狀態映射**:
- AI Server `pending/running` → Backend `RUNNING`
- AI Server `success` → Backend `DONE`
- AI Server `failed` → Backend `FAILED`

#### GET /agent/runs/{run_id}
**查詢 Agent Run 詳細狀態** (需認證)

```json
// Response
{
  "id": "task_abc123",
  "project_id": "507f1f77bcf86cd799439011",
  "status": "DONE",
  "phase": "plan",
  "created_at": "2026-02-02T12:00:00Z",
  "finished_at": "2026-02-02T12:05:00Z",
  "error_message": null
}
```

#### GET /agent/runs/{run_id}/stream
**SSE 串流 Agent 日誌** (需認證)

轉發容器內 AI Server 的 SSE stream

```
GET /api/v1/projects/{id}/agent/runs/{run_id}/stream

event: log
data: {"level": "info", "message": "開始分析程式碼庫..."}

event: progress
data: {"step": 1, "total": 5, "message": "讀取檔案"}

event: complete
data: {"status": "success", "message": "分析完成"}
```

---

## 服務層設計

### ProjectService

**檔案**: `backend/app/services/project_service.py`

**職責**:
- 專案 CRUD 操作
- 專案狀態管理
- 與 ContainerService 協作完成 Provision

**關鍵方法**:

```python
class ProjectService:
    async def create_project(request, owner_id) -> Project
    async def get_project_by_id(project_id) -> Optional[Project]
    async def get_project_with_docker_status(project_id) -> Optional[dict]
    async def list_projects(skip, limit, owner_id) -> tuple[List[Project], int]
    async def update_project(project_id, update) -> Optional[Project]
    async def provision_project(project_id, dev_mode) -> Optional[Project]
    async def stop_project(project_id) -> Optional[Project]
    async def delete_project(project_id) -> bool
    async def _update_project_status(project_id, status, ...) -> None
```

**狀態變更邏輯**:
- `provision_project`: `CREATED` → `PROVISIONING` → `READY` (或 `FAILED`)
- `stop_project`: `READY` → `STOPPED`
- 錯誤時自動設為 `FAILED`，並記錄 `last_error`

### ContainerService

**檔案**: `backend/app/services/container_service.py`

**職責**:
- Docker 容器生命週期管理
- 使用 `subprocess` 呼叫 Docker CLI (非 Docker SDK)

**關鍵方法**:

```python
class ContainerService:
    def create_container(project_id, image, dev_mode, **kwargs) -> Dict
    def start_container(container_id) -> None
    def stop_container(container_id, timeout) -> None
    def remove_container(container_id, force) -> None
    def get_container_status(container_id) -> Optional[Dict]
    def get_container_info(container_id) -> Optional[Dict]
    def clone_repository(container_id, repo_url, branch, target_dir) -> Dict
    def exec_command(container_id, command, workdir) -> Dict
    def exec_command_with_env(container_id, command, env_vars, workdir) -> Dict
```

**容器命名規則**: `refactor-project-{project_id}`

**Volume 掛載**:
- 生產模式:
  ```
  {DOCKER_VOLUME_PREFIX}/{project_id}/repo → /workspace/repo
  {DOCKER_VOLUME_PREFIX}/{project_id}/artifacts → /workspace/artifacts
  ```
- 開發模式 (額外掛載):
  ```
  {AGENT_HOST_PATH} → /workspace/agent:ro
  ```

**資源限制**:
- CPU: 2 cores (可在 `config.py` 調整 `container_cpu_limit`)
- Memory: 2GB (可調整 `container_memory_limit`)

### AuthService

**檔案**: `backend/app/services/auth_service.py`

**職責**:
- 用戶註冊、登入、驗證
- JWT Token 生成與驗證
- 密碼 Hash (bcrypt)

**關鍵方法**:

```python
class AuthService:
    async def create_user(email, username, password) -> User
    async def authenticate_user(email, password) -> Optional[User]
    def create_access_token(user_id, email) -> tuple[str, int]
    async def get_user_by_id(user_id) -> Optional[User]
    async def verify_token(token) -> Optional[User]
```

### LogService

**檔案**: `backend/app/services/log_service.py`

**職責**:
- 容器日誌串流 (SSE)
- Keep-alive ping 機制 (30 秒)

**關鍵方法**:

```python
class LogService:
    async def stream_container_logs(container_id, follow, tail) -> AsyncGenerator
```

---

## 認證機制

### JWT 認證流程

1. **註冊/登入** → 取得 `access_token`
2. **後續請求** → 帶上 `Authorization: Bearer <token>` header
3. **Backend 驗證** → 使用 `get_current_user` dependency

### JWT Payload 結構

```json
{
  "sub": "user_id",           // Subject (用戶 ID)
  "email": "user@example.com",
  "exp": 1707139200           // Expiration time (Unix timestamp)
}
```

### 實作細節

**檔案**: `backend/app/dependencies/auth.py`

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """解析 JWT Token 並返回當前用戶"""
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return user
```

**所有需認證的端點**:
- 使用 `current_user: User = Depends(get_current_user)` 依賴注入
- 自動驗證 Token 有效性
- 自動從資料庫載入用戶資訊

### 權限控制

**專案權限**:
- 僅擁有者 (`project.owner_id == current_user.id`) 可操作專案
- 在 Router 層驗證 (每個端點獨立檢查)

**範例** (`backend/app/routers/projects.py:64-67`):
```python
if project.owner_id != current_user.id:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="無權限訪問此專案"
    )
```

---

## 開發模式

### 概述

開發模式允許動態掛載本機 Agent 程式碼到容器，避免每次修改都重建 Docker Image。

### 配置方式

#### 方式 1: 全域配置 (`.env`)

```bash
DEV_MODE=true
AGENT_HOST_PATH=/Users/quan/auto-refactor-agent/agent
```

#### 方式 2: API 層級覆蓋

```bash
# 單獨為某個專案啟用開發模式
POST /api/v1/projects/{id}/provision?dev_mode=true

# 單獨為某個專案停用開發模式
POST /api/v1/projects/{id}/provision?dev_mode=false
```

### 實作邏輯

**檔案**: `backend/app/services/container_service.py:33-76`

```python
def create_container(self, project_id, image, dev_mode, **kwargs):
    # 決定是否啟用開發模式
    use_dev_mode = dev_mode if dev_mode is not None else settings.dev_mode

    if use_dev_mode:
        # 掛載本機 agent 程式碼
        volume_args.extend([
            "-v", f"{settings.agent_host_path}:/workspace/agent:ro"
        ])
    else:
        # 使用 image 內建的 agent
        pass
```

### 驗證機制

**檔案**: `backend/app/config.py:56-75`

```python
@field_validator('agent_host_path')
def validate_agent_path(cls, v):
    if not v:
        return v

    # 檢查目錄存在
    if not os.path.isdir(v):
        raise ValueError(f"AGENT_HOST_PATH 目錄不存在: {v}")

    # 檢查必要檔案
    if not os.path.isfile(os.path.join(v, "ai_server.py")):
        raise ValueError(f"AGENT_HOST_PATH 缺少 ai_server.py 檔案")

    return v
```

### 注意事項

1. `AGENT_HOST_PATH` 必須是**絕對路徑**
2. 目錄內必須包含 `ai_server.py`
3. Agent 程式碼以**唯讀模式**掛載 (`:ro`)
4. 生產環境請保持 `DEV_MODE=false`

---

## 錯誤處理

### Provision 失敗回滾

**檔案**: `backend/app/services/project_service.py:265-281`

```python
except Exception as e:
    error_msg = str(e)
    logger.error(f"Provision 失敗: {error_msg}")

    # 清理容器
    if container_id:
        container_service.remove_container(container_id, force=True)

    # 更新狀態為 FAILED
    await self._update_project_status(
        project_id, ProjectStatus.FAILED, last_error=error_msg
    )

    raise
```

**機制**:
1. 捕獲 Provision 過程中的所有異常
2. 自動清理已建立的容器 (`force=True`)
3. 更新專案狀態為 `FAILED`
4. 錯誤訊息記錄在 `last_error` 欄位
5. 重新拋出異常，返回 HTTP 500

### 狀態一致性檢查

**檔案**: `backend/app/services/project_service.py:56-86`

```python
async def get_project_with_docker_status(self, project_id):
    """查詢專案並附加 Docker 容器狀態"""
    project = await self.get_project_by_id(project_id)

    if project.container_id:
        docker_status = container_service.get_container_status(project.container_id)

        if not docker_status:
            # 容器在 Docker 中不存在 - 狀態不一致
            result["docker_status"] = {
                "status": "not_found",
                "inconsistent": True
            }
            logger.warning(f"狀態不一致: 容器 {container_id} 在 Docker 中不存在")
```

**使用方式**:
```bash
GET /api/v1/projects/{id}?include_docker_status=true
```

### Agent 執行錯誤處理

**容器內 AI Server 負責錯誤處理**，Backend 僅代理查詢:

```python
# backend/app/routers/agent.py:77-79
except httpx.HTTPError as e:
    logger.error(f"AI Server 呼叫失敗: {e}")
    raise HTTPException(status_code=503, detail=f"AI Server 錯誤: {str(e)}")
```

---

## 部署配置

### 環境變數 (`.env`)

**必填項**:
```bash
# MongoDB
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DATABASE=refactor_agent

# JWT 認證
JWT_SECRET_KEY=your-secret-key-change-in-production

# Docker
DOCKER_BASE_IMAGE=refactor-base:latest
DOCKER_NETWORK=refactor-network
DOCKER_VOLUME_PREFIX=/tmp/refactor-workspaces
```

**可選項**:
```bash
# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
DEBUG=false

# 開發模式
DEV_MODE=false
AGENT_HOST_PATH=/path/to/agent

# 容器資源
CONTAINER_CPU_LIMIT=2.0
CONTAINER_MEMORY_LIMIT=2g

# Git
GIT_CLONE_TIMEOUT=300
GIT_DEPTH=1

# Log
LOG_LEVEL=INFO
```

**說明**:
- LLM 相關配置 (如 `ANTHROPIC_API_KEY`, `LLM_PROVIDER`, `GCP_PROJECT_ID` 等) 由容器內的 AI Server 自行處理，不需要在後端 `.env` 中設定

### Docker Compose 部署

**檔案**: `devops/docker-compose.yml`

```yaml
services:
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

  api:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://mongodb:27017
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - mongodb
```

**啟動指令**:
```bash
# 啟動所有服務
docker-compose -f devops/docker-compose.yml up -d

# 查看日誌
docker-compose -f devops/docker-compose.yml logs -f api

# 停止服務
docker-compose -f devops/docker-compose.yml down
```

### 本地開發

```bash
# 啟動 MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:7

# 啟動 Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 健康檢查

**端點**: `GET /health`

```json
// Response
{
  "status": "healthy",
  "timestamp": "2026-02-02T12:00:00Z"
}
```

---

## 測試

### 測試結構

```
backend/tests/
├── conftest.py                # pytest fixtures
├── test_projects.py           # 專案 CRUD 測試
├── test_agent_run.py          # Agent 執行測試
├── test_execution.py          # 容器指令執行測試
├── test_logs.py               # 日誌串流測試
├── test_lifecycle.py          # 專案生命週期測試
├── test_error_handling.py     # 錯誤處理測試
└── test_integration_e2e.py    # 端到端整合測試
```

### 執行測試

```bash
cd backend

# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/test_projects.py

# 執行特定測試 (使用 -k 過濾)
pytest -k test_create_project

# 顯示測試覆蓋率
pytest --cov=app --cov-report=html

# 執行測試並顯示詳細輸出
pytest -v -s
```

### 測試配置

**檔案**: `backend/tests/conftest.py`

```python
@pytest.fixture
async def test_db():
    """測試用資料庫"""
    # 使用獨立測試資料庫
    await mongodb.connect(database_name="test_refactor_agent")
    yield mongodb.db
    # 清理測試資料
    await mongodb.db.client.drop_database("test_refactor_agent")
    await mongodb.disconnect()

@pytest.fixture
async def test_client(test_db):
    """測試用 HTTP Client"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

---

## 附錄

### 常見問題

**Q: 為何使用 subprocess 而非 Docker SDK?**
A: Docker SDK 需要 `/var/run/docker.sock` 掛載權限，且在某些環境 (如 Cloud Run) 不可用。subprocess 調用 CLI 更靈活。

**Q: Agent Run 為何不存 MongoDB?**
A: 採用 Container AI Server 架構，每個容器獨立管理執行狀態，Backend 僅代理查詢，減少資料同步複雜度。

**Q: 如何擴展支援多 LLM Provider?**
A: 在 `config.py` 新增 Provider 配置，在 Container AI Server (`agent/ai_server.py`) 中根據 `LLM_PROVIDER` 環境變數選擇對應的 LLM 客戶端。

**Q: 如何限制用戶專案數量?**
A: 在 `ProjectService.create_project` 中新增檢查邏輯:
```python
existing_count = await self.collection.count_documents({"owner_id": owner_id})
if existing_count >= MAX_PROJECTS_PER_USER:
    raise ValueError("已達專案數量上限")
```

### 版本歷史

- **v0.1.0** (2026-01-30)
  - 初始版本
  - 基礎專案 CRUD + JWT 認證
  - Docker 容器管理
  - Container AI Server 整合

- **v0.2.0** (2026-02-02)
  - 新增開發模式支援
  - SSE 日誌串流優化
  - 新增 Vertex AI Gemini 支援
  - 狀態一致性檢查

---

**文件維護**:
此文件應在每次後端架構或 API 變更時同步更新。建議在 Pull Request 中包含文件更新。
