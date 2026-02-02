# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

AI 舊程式碼智能重構系統 - 一個前後端分離的大型專案，提供基於 LangChain Deep Agents 框架的智能程式碼分析與重構服務。

## 核心架構

### 系統組成

1. **Backend (FastAPI)** - 提供 RESTful API，管理專案生命週期、Docker 容器和 AI Agent 執行
2. **Frontend (React + Vite)** - 使用者介面，基於 TypeScript + Tailwind CSS + shadcn/ui
3. **MongoDB** - 持久化專案、使用者和 Agent 執行狀態
4. **Docker Containers** - 為每個專案提供隔離的執行環境
5. **Deep Agent (LangChain)** - 使用 `deepagents` 框架進行程式碼分析和重構計劃生成

### 資料流架構

```
用戶 → Frontend → Backend API → ProjectService/AgentRunService
                                    ↓
                            Docker Container (隔離環境)
                                    ↓
                            Deep Agent (LangChain)
                                    ↓
                            生成 plan.json/plan.md
```

### 核心服務層

- **ProjectService** (`backend/app/services/project_service.py`) - 管理專案 CRUD 和狀態
- **AgentRunService** (`backend/app/services/agent_run_service.py`) - 追蹤 AI Agent 執行狀態和迭代
- **DeepAgent** (`backend/app/services/deep_agent.py`) - 封裝 LangChain Deep Agents 框架，執行程式碼分析
- **ContainerService** (`backend/app/services/container_service.py`) - Docker 容器生命週期管理

### 資料模型設計

- **Project** - 專案基本資訊 (repo_url, branch, init_prompt, status, container_id, owner_id)
- **AgentRun** - Agent 執行記錄 (project_id, iteration_index, phase, status, artifacts_path)
- **User** - 使用者帳號 (email, hashed_password, JWT 認證)

### Agent 執行流程

1. **PLAN Phase** - Deep Agent 分析程式碼庫，生成重構計劃 (plan.json + plan.md)
2. **TEST Phase** - (Phase 3 實作) 驗證重構計劃可行性
3. **EXEC Phase** - (Phase 3 實作) 執行實際重構操作

執行方式：背景任務 (FastAPI BackgroundTasks)，立即返回 run_id，非同步執行。

## 常用指令

### 開發環境設置

```bash
# 建立虛擬環境並安裝依賴
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 設定環境變數
cp backend/.env.example backend/.env
# 編輯 .env 填入 ANTHROPIC_API_KEY
```

### Docker 環境

```bash
# 建立基礎容器映像（包含 Agent 程式碼）
# 重要：必須從專案根目錄執行，以便正確複製 agent/ 目錄
docker build -t refactor-base:latest -f devops/base-image/Dockerfile .

# 驗證 Agent 已包含在 image 中
docker run --rm refactor-base:latest ls -la /workspace/agent/

# 啟動所有服務 (MongoDB + API + Frontend)
docker-compose -f devops/docker-compose.yml up -d

# 查看服務狀態
docker-compose -f devops/docker-compose.yml ps

# 查看 API 日誌
docker-compose -f devops/docker-compose.yml logs -f api

# 停止服務
docker-compose -f devops/docker-compose.yml down

# 停止並清除資料
docker-compose -f devops/docker-compose.yml down -v
```

### 開發模式 (Development Mode)

在開發 Agent 程式碼時，啟用開發模式避免每次修改都重建 image：

```bash
# 1. 編輯 backend/.env
DEV_MODE=true
AGENT_HOST_PATH=/Users/quan/auto-refactor-agent/agent  # 使用絕對路徑

# 2. 重啟 Backend
cd backend
uvicorn app.main:app --reload

# 3. Provision 專案（agent 程式碼會動態掛載）
curl -X POST "http://localhost:8000/api/v1/projects/{id}/provision"

# 4. 修改 agent/*.py 檔案後，容器內立即生效
```

**注意事項**：
- `AGENT_HOST_PATH` 必須是絕對路徑且目錄必須存在
- 目錄內必須包含 `ai_server.py` 檔案
- Agent 程式碼以唯讀模式掛載到容器
- 生產環境請保持 `DEV_MODE=false`

**API 層級控制**：
```bash
# 單獨為某個專案啟用開發模式
POST /api/v1/projects/{id}/provision?dev_mode=true

# 單獨為某個專案停用開發模式
POST /api/v1/projects/{id}/provision?dev_mode=false
```

### 本地開發 (不使用 Docker Compose)

```bash
# 啟動 MongoDB (需要 Docker)
docker run -d --name mongodb -p 27017:27017 mongo:7

# 啟動 Backend API
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 啟動 Frontend
cd frontend
npm install
npm run dev  # 預設在 http://localhost:5173
```

### 測試

```bash
# 執行所有測試
cd backend
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

### 前端開發

```bash
# Linting
cd frontend
npm run lint

# 建立 production build
npm run build

# 預覽 production build
npm run preview
```

### MongoDB 操作

```bash
# 進入 MongoDB shell (在 Docker 容器中)
docker exec -it refactor-mongodb mongosh refactor_agent

# 查看所有專案
db.projects.find()

# 查看所有 agent_runs
db.agent_runs.find()

# 清空資料庫 (開發用)
db.projects.deleteMany({})
db.agent_runs.deleteMany({})
db.users.deleteMany({})
```

### 初始化 MongoDB 索引

```bash
cd backend
python scripts/init_agent_run_indexes.py
```

## 重要技術細節

### JWT 認證流程

1. 註冊/登入 → `/api/v1/auth/register` 或 `/api/v1/auth/login`
2. 取得 `access_token` (JWT)
3. 後續請求帶上 `Authorization: Bearer <token>` header
4. Backend 使用 `get_current_user` dependency 驗證和解析 token

### Docker 容器隔離機制

- 每個專案建立獨立容器 (使用 `refactor-base:latest` 映像)
- **Agent 程式碼已烤進 base image**，位於 `/workspace/agent/`
- 容器名稱格式: `refactor-project-{project_id}`
- 工作區掛載: `{DOCKER_VOLUME_PREFIX}/{project_id}:/workspace`
- 無需動態掛載 Agent 程式碼（已內建）
- 資源限制: CPU 2 core, Memory 2GB (可在 config.py 調整)

### SSE 日誌串流

- Endpoint: `GET /api/v1/projects/{id}/logs/stream`
- Query 參數: `follow` (持續串流), `tail` (最後 N 行)
- 使用 `sse-starlette` 實作
- Keep-alive: 每 30 秒發送 ping event

### Deep Agent (LangChain) 整合

- 使用 `deepagents` 套件 (LangChain Deep Agents 框架)
- 內建工具: `write_todos`, `read_file`, `write_file`, `edit_file`, `ls`, `task`
- 配置: `working_directory` 設定為專案工作區路徑
- 輸出: 生成 `plan.json` (結構化資料) 和 `plan.md` (人類可讀)

### 錯誤處理機制

- **Provision 失敗回滾**: 自動清理已建立的容器，狀態設為 FAILED，錯誤記錄在 `last_error`
- **狀態一致性檢查**: `include_docker_status=true` 查詢參數可檢查資料庫與 Docker 狀態是否一致
- **Agent 失敗處理**: 背景任務中發生錯誤會自動呼叫 `mark_failed()`，記錄 error_message

## API 端點概覽

### 認證
- `POST /api/v1/auth/register` - 註冊新使用者
- `POST /api/v1/auth/login` - 登入取得 JWT token

### 專案管理
- `POST /api/v1/projects` - 建立專案
- `GET /api/v1/projects` - 列出所有專案
- `GET /api/v1/projects/{id}` - 查詢專案 (支援 `include_docker_status=true`)
- `POST /api/v1/projects/{id}/provision` - Provision 專案 (建立容器、clone repo)
- `POST /api/v1/projects/{id}/exec` - 在容器中執行指令
- `GET /api/v1/projects/{id}/logs/stream` - SSE 日誌串流
- `POST /api/v1/projects/{id}/stop` - 停止容器
- `DELETE /api/v1/projects/{id}` - 刪除專案和容器

### Agent 管理
- `POST /api/v1/projects/{id}/agent/run` - 啟動 Agent (背景執行)
- `GET /api/v1/projects/{id}/agent/runs` - 列出所有 Agent Runs
- `GET /api/v1/projects/{id}/agent/runs/{run_id}` - 查詢 Agent Run 狀態
- `GET /api/v1/projects/{id}/agent/runs/{run_id}/artifacts/plan.json` - 下載 plan.json
- `GET /api/v1/projects/{id}/agent/runs/{run_id}/artifacts/plan.md` - 下載 plan.md

## 資料庫設計要點

### Collections
- `projects` - 專案資訊
- `agent_runs` - Agent 執行記錄
- `users` - 使用者帳號

### 索引 (建議設置)
- `projects.owner_id` - 加速使用者專案查詢
- `agent_runs.project_id` - 加速專案相關 runs 查詢
- `agent_runs.created_at` (desc) - 加速時間排序

## 開發注意事項

### 新增 API 端點流程
1. 在 `backend/app/schemas/` 定義請求/回應 Schema (Pydantic)
2. 在 `backend/app/models/` 定義資料模型 (如需持久化)
3. 在 `backend/app/services/` 實作業務邏輯
4. 在 `backend/app/routers/` 定義路由和端點
5. 在 `backend/app/main.py` 註冊 Router
6. 在 `backend/tests/` 撰寫測試

### 前端 API 整合
- API Base URL 透過環境變數 `VITE_API_BASE_URL` 設定
- 使用 axios 作為 HTTP client
- JWT token 應存在 localStorage 或 sessionStorage
- 所有需認證的請求需帶上 `Authorization: Bearer <token>` header

### Docker 權限要求
- Backend API 容器需掛載 `/var/run/docker.sock` 以管理其他容器
- 開發環境可能需要將使用者加入 `docker` group

### 環境變數重要欄位
- `ANTHROPIC_API_KEY` - 必填，用於 Deep Agent LLM 呼叫
- `JWT_SECRET_KEY` - 生產環境務必更換
- `MONGODB_URL` - 開發環境為 `mongodb://mongodb:27017`，本地測試為 `mongodb://localhost:27017`
- `DOCKER_VOLUME_PREFIX` - 專案工作區路徑，預設 `/tmp/refactor-workspaces`
- ~~`AGENT_RUNTIME_HOST_PATH`~~ - **已棄用**，Agent 已內建於 base image

### 測試策略
- 使用 pytest + pytest-asyncio 測試非同步程式碼
- 使用 httpx.AsyncClient 測試 API 端點
- 使用 `conftest.py` 定義共用 fixtures (test_db, test_client)
- 測試檔案命名: `test_*.py`

## 技術棧版本

- Python 3.11+
- FastAPI 0.109.0
- MongoDB 7
- React 18.2.0
- Vite 5
- TypeScript 5.3.3
- LangChain Deep Agents (deepagents >= 0.3.0)
- Docker SDK 6.1.3

## 已知限制與未來開發

- Agent 執行目前僅實作 PLAN phase，TEST 和 EXEC phase 待 Phase 3 實作
- 前端 UI 尚在開發中
- 尚未實作 Agent 執行的中斷/取消機制
- 容器資源監控功能待開發
- 多 LLM provider 支援 (目前僅 Anthropic)
