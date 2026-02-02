# API 文件

> AI 舊程式碼智能重構系統 - REST API 完整規格

**Base URL**: `http://localhost:8000` (開發環境)
**API Version**: v1
**最後更新**: 2026-02-02

---

## 目錄

- [認證機制](#認證機制)
- [錯誤回應格式](#錯誤回應格式)
- [認證 API](#認證-api)
  - [POST /api/v1/auth/register](#post-apiv1authregister)
  - [POST /api/v1/auth/login](#post-apiv1authlogin)
  - [GET /api/v1/auth/me](#get-apiv1authme)
- [專案 API](#專案-api)
  - [POST /api/v1/projects](#post-apiv1projects)
  - [GET /api/v1/projects](#get-apiv1projects)
  - [GET /api/v1/projects/{id}](#get-apiv1projectsid)
  - [PUT /api/v1/projects/{id}](#put-apiv1projectsid)
  - [POST /api/v1/projects/{id}/provision](#post-apiv1projectsidprovision)
  - [POST /api/v1/projects/{id}/exec](#post-apiv1projectsidexec)
  - [GET /api/v1/projects/{id}/logs/stream](#get-apiv1projectsidlogsstream)
  - [POST /api/v1/projects/{id}/stop](#post-apiv1projectsidstop)
  - [DELETE /api/v1/projects/{id}](#delete-apiv1projectsid)
- [Agent API](#agent-api)
  - [POST /api/v1/projects/{id}/agent/run](#post-apiv1projectsidagentrun)
  - [GET /api/v1/projects/{id}/agent/runs](#get-apiv1projectsidagentruns)
  - [GET /api/v1/projects/{id}/agent/runs/{run_id}](#get-apiv1projectsidagentrunsrun_id)
  - [GET /api/v1/projects/{id}/agent/runs/{run_id}/stream](#get-apiv1projectsidagentrunsrun_idstream)

---

## 認證機制

### JWT Bearer Token

所有需要認證的端點（標註 🔒）需要在 HTTP Header 中提供 JWT Token：

```http
Authorization: Bearer <access_token>
```

### 取得 Token

1. 使用 [POST /auth/register](#post-apiv1authregister) 註冊帳號
2. 使用 [POST /auth/login](#post-apiv1authlogin) 登入取得 `access_token`
3. 在後續請求中帶上 Token

### Token 過期

- 預設過期時間：24 小時
- Token 過期後需重新登入

---

## 錯誤回應格式

所有錯誤回應遵循統一格式：

```json
{
  "detail": "錯誤訊息描述"
}
```

### HTTP 狀態碼

| 狀態碼 | 說明 |
|--------|------|
| 200 | 成功 |
| 201 | 建立成功 |
| 204 | 成功（無回應內容）|
| 400 | 請求錯誤（參數不正確）|
| 401 | 未認證（Token 無效或過期）|
| 403 | 無權限（非專案擁有者）|
| 404 | 資源不存在 |
| 500 | 伺服器錯誤 |
| 503 | 服務不可用（容器或 AI Server 錯誤）|

---

## 認證 API

### POST /api/v1/auth/register

註冊新用戶帳號。

**認證**: 無需認證

#### Request Body

```json
{
  "email": "user@example.com",
  "username": "testuser",
  "password": "password123"
}
```

**欄位說明**:

| 欄位 | 類型 | 必填 | 限制 | 說明 |
|------|------|------|------|------|
| email | string | ✅ | Email 格式 | 用戶 Email（必須唯一）|
| username | string | ✅ | 3-50 字元 | 用戶名稱 |
| password | string | ✅ | 8-100 字元 | 密碼 |

#### Response (201 Created)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "testuser",
  "is_active": true,
  "created_at": "2026-02-02T12:00:00Z"
}
```

#### 錯誤回應

**400 Bad Request** - Email 已存在
```json
{
  "detail": "Email already exists"
}
```

---

### POST /api/v1/auth/login

用戶登入，取得 JWT Token。

**認證**: 無需認證

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**欄位說明**:

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| email | string | ✅ | 用戶 Email |
| password | string | ✅ | 密碼 |

#### Response (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MDdmMWY3N2JjZjg2Y2Q3OTk0MzkwMTEiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJleHAiOjE3MDcyMjU2MDB9.xxxxx",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**欄位說明**:

| 欄位 | 類型 | 說明 |
|------|------|------|
| access_token | string | JWT Token（用於後續認證）|
| token_type | string | Token 類型（固定為 "bearer"）|
| expires_in | integer | Token 有效期限（秒數）|

#### 錯誤回應

**401 Unauthorized** - Email 或密碼錯誤
```json
{
  "detail": "Incorrect email or password"
}
```

---

### GET /api/v1/auth/me

取得當前已登入用戶的資訊。

**認證**: 🔒 需要 Bearer Token

#### Request

無需 Request Body

#### Response (200 OK)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "testuser",
  "is_active": true,
  "created_at": "2026-02-02T12:00:00Z"
}
```

#### 錯誤回應

**401 Unauthorized** - Token 無效或過期
```json
{
  "detail": "Invalid authentication"
}
```

---

## 專案 API

### POST /api/v1/projects

建立新專案。

**認證**: 🔒 需要 Bearer Token

#### Request Body

```json
{
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main",
  "init_prompt": "請分析這個專案並提出重構建議"
}
```

**欄位說明**:

| 欄位 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| repo_url | string | ✅ | - | Git Repository URL |
| branch | string | ❌ | "main" | Git 分支名稱 |
| init_prompt | string | ✅ | - | Agent 初始提示（任務描述）|

#### Response (201 Created)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main",
  "init_prompt": "請分析這個專案並提出重構建議",
  "status": "CREATED",
  "container_id": null,
  "created_at": "2026-02-02T12:00:00Z",
  "updated_at": "2026-02-02T12:00:00Z",
  "last_error": null,
  "docker_status": null
}
```

**專案狀態說明**:

| 狀態 | 說明 |
|------|------|
| CREATED | 已建立（尚未 Provision）|
| PROVISIONING | 正在建立容器 |
| READY | 容器就緒（可執行 Agent）|
| RUNNING | Agent 執行中 |
| STOPPED | 已停止 |
| FAILED | 失敗（查看 last_error）|

---

### GET /api/v1/projects

列出當前用戶的所有專案。

**認證**: 🔒 需要 Bearer Token

#### Query Parameters

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| skip | integer | ❌ | 0 | 跳過前 N 筆 |
| limit | integer | ❌ | 100 | 限制回傳筆數 |

#### Request

```http
GET /api/v1/projects?skip=0&limit=10
```

#### Response (200 OK)

```json
{
  "total": 5,
  "projects": [
    {
      "id": "507f1f77bcf86cd799439011",
      "repo_url": "https://github.com/user/repo.git",
      "branch": "main",
      "init_prompt": "重構建議",
      "status": "READY",
      "container_id": "abc123def456",
      "created_at": "2026-02-02T12:00:00Z",
      "updated_at": "2026-02-02T12:05:00Z",
      "last_error": null
    }
  ]
}
```

---

### GET /api/v1/projects/{id}

查詢專案詳細資訊（包含 Docker 容器即時狀態）。

**認證**: 🔒 需要 Bearer Token

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Query Parameters

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| include_docker_status | boolean | ❌ | true | 是否查詢 Docker 容器即時狀態 |

#### Request

```http
GET /api/v1/projects/507f1f77bcf86cd799439011?include_docker_status=true
```

#### Response (200 OK)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main",
  "init_prompt": "重構建議",
  "status": "READY",
  "container_id": "abc123def456",
  "created_at": "2026-02-02T12:00:00Z",
  "updated_at": "2026-02-02T12:05:00Z",
  "last_error": null,
  "docker_status": {
    "id": "abc123def456",
    "name": "refactor-project-507f1f77bcf86cd799439011",
    "status": "running",
    "image": "refactor-base:latest"
  }
}
```

**docker_status 欄位** (when `include_docker_status=true`):

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | string | 容器 ID（短格式）|
| name | string | 容器名稱 |
| status | string | Docker 狀態（running, exited, etc.）|
| image | string | 使用的 Docker Image |
| inconsistent | boolean | 狀態不一致標記（容器在 Docker 中不存在但 DB 有記錄）|

#### 錯誤回應

**403 Forbidden** - 非專案擁有者
```json
{
  "detail": "無權限訪問此專案"
}
```

**404 Not Found** - 專案不存在
```json
{
  "detail": "專案不存在"
}
```

---

### PUT /api/v1/projects/{id}

更新專案資訊。

**認證**: 🔒 需要 Bearer Token

**重要限制**: Provision 後（狀態 != CREATED）無法修改 `repo_url`

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Request Body

所有欄位皆為可選，僅更新提供的欄位。

```json
{
  "branch": "develop",
  "init_prompt": "新的任務描述"
}
```

**欄位說明**:

| 欄位 | 類型 | 限制 | 說明 |
|------|------|------|------|
| repo_url | string | ⚠️ Provision 後無法修改 | Git Repository URL |
| branch | string | - | Git 分支名稱 |
| init_prompt | string | - | Agent 初始提示 |
| status | string | - | 專案狀態 |

#### Response (200 OK)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "repo_url": "https://github.com/user/repo.git",
  "branch": "develop",
  "init_prompt": "新的任務描述",
  "status": "CREATED",
  "container_id": null,
  "created_at": "2026-02-02T12:00:00Z",
  "updated_at": "2026-02-02T12:10:00Z",
  "last_error": null
}
```

#### 錯誤回應

**400 Bad Request** - 嘗試修改已 Provision 專案的 repo_url
```json
{
  "detail": "專案已經 Provision，無法修改 Repository URL"
}
```

---

### POST /api/v1/projects/{id}/provision

Provision 專案：建立 Docker 容器並 clone repository。

**認證**: 🔒 需要 Bearer Token

**前置條件**: 專案狀態必須為 `CREATED`

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Query Parameters

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| dev_mode | boolean | ❌ | null | 覆蓋全域 DEV_MODE 設定<br>• true: 強制啟用開發模式（掛載本機 agent）<br>• false: 強制停用開發模式（使用 image 內建 agent）<br>• null: 使用 .env 中的 DEV_MODE 設定 |

#### Request

```http
POST /api/v1/projects/507f1f77bcf86cd799439011/provision?dev_mode=false
```

#### Response (200 OK)

```json
{
  "message": "專案 provision 成功",
  "project_id": "507f1f77bcf86cd799439011",
  "container_id": "abc123def456",
  "status": "READY"
}
```

#### 錯誤回應

**400 Bad Request** - 專案狀態不正確
```json
{
  "detail": "專案狀態必須為 CREATED,目前為 READY"
}
```

**500 Internal Server Error** - Provision 失敗
```json
{
  "detail": "Provision 失敗: Clone repository 失敗"
}
```

**說明**:
- Provision 失敗時會自動清理已建立的容器
- 專案狀態會設為 `FAILED`，錯誤訊息記錄在 `last_error` 欄位

---

### POST /api/v1/projects/{id}/exec

在專案容器中執行指令。

**認證**: 🔒 需要 Bearer Token

**前置條件**: 專案必須已 Provision（有 container_id）

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Request Body

```json
{
  "command": "ls -la /workspace/repo",
  "workdir": "/workspace/repo"
}
```

**欄位說明**:

| 欄位 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| command | string | ✅ | - | 要執行的指令 |
| workdir | string | ❌ | "/workspace/repo" | 工作目錄 |

#### Response (200 OK)

```json
{
  "exit_code": 0,
  "stdout": "total 12\ndrwxr-xr-x 3 root root  96 Feb  2 12:00 .\ndrwxr-xr-x 4 root root 128 Feb  2 12:00 ..\n-rw-r--r-- 1 root root 1234 Feb  2 12:00 README.md\n",
  "stderr": ""
}
```

**欄位說明**:

| 欄位 | 類型 | 說明 |
|------|------|------|
| exit_code | integer | 指令退出代碼（0 表示成功）|
| stdout | string | 標準輸出 |
| stderr | string | 標準錯誤 |

#### 錯誤回應

**400 Bad Request** - 專案尚未 Provision
```json
{
  "detail": "專案尚未 provision,請先執行 provision"
}
```

---

### GET /api/v1/projects/{id}/logs/stream

SSE 串流容器日誌。

**認證**: 🔒 需要 Bearer Token

**前置條件**: 專案必須已 Provision

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Query Parameters

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| follow | boolean | ❌ | true | 是否持續串流（類似 tail -f）|
| tail | integer | ❌ | 100 | 顯示最後 N 行日誌 |

#### Request

```http
GET /api/v1/projects/507f1f77bcf86cd799439011/logs/stream?follow=true&tail=100
Accept: text/event-stream
```

#### Response (200 OK)

```
Content-Type: text/event-stream

event: log
data: [2026-02-02 12:00:00] Container started

event: log
data: [2026-02-02 12:00:05] Cloning repository...

event: log
data: [2026-02-02 12:00:10] Clone complete

event: ping
data: keep-alive
```

**SSE Event 類型**:

| Event | 說明 |
|-------|------|
| log | 日誌訊息 |
| ping | Keep-alive 心跳（每 30 秒）|

---

### POST /api/v1/projects/{id}/stop

停止專案容器。

**認證**: 🔒 需要 Bearer Token

**前置條件**: 專案必須已 Provision

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Request

無需 Request Body

#### Response (200 OK)

```json
{
  "id": "507f1f77bcf86cd799439011",
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main",
  "init_prompt": "重構建議",
  "status": "STOPPED",
  "container_id": "abc123def456",
  "created_at": "2026-02-02T12:00:00Z",
  "updated_at": "2026-02-02T12:15:00Z",
  "last_error": null
}
```

#### 錯誤回應

**400 Bad Request** - 專案尚未 Provision
```json
{
  "detail": "專案尚未 provision,沒有容器可停止"
}
```

---

### DELETE /api/v1/projects/{id}

刪除專案和容器。

**認證**: 🔒 需要 Bearer Token

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Request

無需 Request Body

#### Response (204 No Content)

無回應內容

**說明**:
- 會同時刪除 MongoDB 專案記錄和 Docker 容器
- 容器刪除失敗不會影響資料庫記錄的刪除

---

## Agent API

### POST /api/v1/projects/{id}/agent/run

啟動 AI Agent 執行（異步模式）。

**認證**: 🔒 需要 Bearer Token

**前置條件**: 專案狀態必須為 `READY`

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Request

無需 Request Body

#### Response (200 OK)

```json
{
  "run_id": "task_abc123xyz",
  "project_id": "507f1f77bcf86cd799439011",
  "status": "RUNNING",
  "iteration_index": 0,
  "phase": "plan",
  "created_at": "2026-02-02T12:00:00Z",
  "message": "Agent 任務已啟動，正在背景執行"
}
```

**欄位說明**:

| 欄位 | 類型 | 說明 |
|------|------|------|
| run_id | string | Agent Run ID（用於後續查詢）|
| project_id | string | 專案 ID |
| status | string | 執行狀態（RUNNING, DONE, FAILED）|
| iteration_index | integer | 迭代索引（目前固定為 0）|
| phase | string | 執行階段（plan, test, exec）|
| created_at | string | 建立時間（ISO 8601）|
| message | string | 提示訊息 |

**執行流程**:
1. Backend 驗證專案狀態
2. 呼叫容器內 AI Server `POST /run`
3. 立即返回 `run_id`
4. Agent 在容器內背景執行

#### 錯誤回應

**400 Bad Request** - 專案狀態不正確
```json
{
  "detail": "專案狀態必須為 READY，目前為 CREATED"
}
```

**503 Service Unavailable** - AI Server 錯誤
```json
{
  "detail": "AI Server 錯誤: Connection refused"
}
```

---

### GET /api/v1/projects/{id}/agent/runs

列出專案的所有 Agent Runs。

**認證**: 🔒 需要 Bearer Token

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |

#### Request

```http
GET /api/v1/projects/507f1f77bcf86cd799439011/agent/runs
```

#### Response (200 OK)

```json
{
  "total": 3,
  "runs": [
    {
      "id": "task_abc123xyz",
      "project_id": "507f1f77bcf86cd799439011",
      "iteration_index": 0,
      "phase": "plan",
      "status": "DONE",
      "created_at": "2026-02-02T12:00:00Z",
      "updated_at": "2026-02-02T12:05:00Z",
      "finished_at": "2026-02-02T12:05:30Z",
      "error_message": null
    },
    {
      "id": "task_def456uvw",
      "project_id": "507f1f77bcf86cd799439011",
      "iteration_index": 0,
      "phase": "plan",
      "status": "FAILED",
      "created_at": "2026-02-02T11:00:00Z",
      "updated_at": "2026-02-02T11:02:00Z",
      "finished_at": "2026-02-02T11:02:15Z",
      "error_message": "Code analysis failed: timeout"
    }
  ]
}
```

**狀態映射**（AI Server → Backend）:

| AI Server Status | Backend Status |
|------------------|----------------|
| pending | RUNNING |
| running | RUNNING |
| success | DONE |
| failed | FAILED |

---

### GET /api/v1/projects/{id}/agent/runs/{run_id}

查詢 Agent Run 詳細狀態。

**認證**: 🔒 需要 Bearer Token

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |
| run_id | string | Agent Run ID |

#### Request

```http
GET /api/v1/projects/507f1f77bcf86cd799439011/agent/runs/task_abc123xyz
```

#### Response (200 OK)

```json
{
  "id": "task_abc123xyz",
  "project_id": "507f1f77bcf86cd799439011",
  "iteration_index": 0,
  "phase": "plan",
  "status": "DONE",
  "created_at": "2026-02-02T12:00:00Z",
  "updated_at": "2026-02-02T12:05:00Z",
  "finished_at": "2026-02-02T12:05:30Z",
  "error_message": null
}
```

**欄位說明**:

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | string | Agent Run ID |
| project_id | string | 專案 ID |
| iteration_index | integer | 迭代索引 |
| phase | string | 執行階段（plan, test, exec）|
| status | string | 執行狀態（RUNNING, DONE, FAILED）|
| created_at | string | 建立時間 |
| updated_at | string | 更新時間 |
| finished_at | string | 完成時間（null 表示尚未完成）|
| error_message | string | 錯誤訊息（僅 status=FAILED 時）|

#### 錯誤回應

**503 Service Unavailable** - 無法查詢任務狀態
```json
{
  "detail": "無法查詢任務狀態"
}
```

---

### GET /api/v1/projects/{id}/agent/runs/{run_id}/stream

SSE 串流 Agent 執行日誌（轉發容器的 stream）。

**認證**: 🔒 需要 Bearer Token

#### Path Parameters

| 參數 | 類型 | 說明 |
|------|------|------|
| id | string | 專案 ID |
| run_id | string | Agent Run ID |

#### Request

```http
GET /api/v1/projects/507f1f77bcf86cd799439011/agent/runs/task_abc123xyz/stream
Accept: text/event-stream
```

#### Response (200 OK)

```
Content-Type: text/event-stream

event: log
data: {"level": "info", "message": "開始分析程式碼庫...", "timestamp": "2026-02-02T12:00:00Z"}

event: log
data: {"level": "info", "message": "讀取 Python 檔案: src/main.py", "timestamp": "2026-02-02T12:00:02Z"}

event: progress
data: {"step": 1, "total": 5, "message": "程式碼掃描中", "timestamp": "2026-02-02T12:00:05Z"}

event: log
data: {"level": "info", "message": "分析完成，生成重構計劃...", "timestamp": "2026-02-02T12:05:00Z"}

event: complete
data: {"status": "success", "message": "分析完成", "artifacts": ["plan.json", "plan.md"], "timestamp": "2026-02-02T12:05:30Z"}
```

**SSE Event 類型**:

| Event | 說明 | Data 格式 |
|-------|------|-----------|
| log | 日誌訊息 | `{"level": "info/warn/error", "message": "...", "timestamp": "..."}` |
| progress | 進度更新 | `{"step": 1, "total": 5, "message": "...", "timestamp": "..."}` |
| complete | 執行完成 | `{"status": "success/failed", "message": "...", "timestamp": "..."}` |
| error | 錯誤訊息 | `"錯誤描述"` |

**說明**:
- 此端點轉發容器內 AI Server 的 SSE stream
- 連線會持續到 Agent 執行完成或發生錯誤
- 建議使用 EventSource API 或支援 SSE 的 HTTP Client

---

## 附錄

### 範例：完整流程

```bash
# 1. 註冊用戶
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dev@example.com",
    "username": "developer",
    "password": "secure123"
  }'

# 2. 登入取得 Token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dev@example.com",
    "password": "secure123"
  }' | jq -r '.access_token')

# 3. 建立專案
PROJECT_ID=$(curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/legacy-code.git",
    "branch": "main",
    "init_prompt": "分析專案並提出重構建議"
  }' | jq -r '.id')

# 4. Provision 專案
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/provision \
  -H "Authorization: Bearer $TOKEN"

# 5. 啟動 Agent
RUN_ID=$(curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/agent/run \
  -H "Authorization: Bearer $TOKEN" | jq -r '.run_id')

# 6. 串流 Agent 日誌（使用 curl）
curl -N -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/projects/$PROJECT_ID/agent/runs/$RUN_ID/stream

# 7. 查詢 Agent 執行狀態
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/projects/$PROJECT_ID/agent/runs/$RUN_ID
```

### 範例：JavaScript/TypeScript Client

```typescript
// 使用 axios + eventsource
import axios from 'axios';
import { EventSourcePolyfill } from 'event-source-polyfill';

const API_BASE = 'http://localhost:8000';
const token = 'your-access-token';

// 建立 axios instance
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

// 建立專案
const { data: project } = await api.post('/api/v1/projects', {
  repo_url: 'https://github.com/user/repo.git',
  branch: 'main',
  init_prompt: '重構建議'
});

// Provision 專案
await api.post(`/api/v1/projects/${project.id}/provision`);

// 啟動 Agent
const { data: run } = await api.post(`/api/v1/projects/${project.id}/agent/run`);

// 串流 Agent 日誌
const eventSource = new EventSourcePolyfill(
  `${API_BASE}/api/v1/projects/${project.id}/agent/runs/${run.run_id}/stream`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

eventSource.addEventListener('log', (event) => {
  const log = JSON.parse(event.data);
  console.log(`[${log.level}] ${log.message}`);
});

eventSource.addEventListener('complete', (event) => {
  const result = JSON.parse(event.data);
  console.log('Agent 執行完成:', result);
  eventSource.close();
});

eventSource.addEventListener('error', (event) => {
  console.error('SSE 錯誤:', event);
  eventSource.close();
});
```

---

**文件版本**: v1.0.0
**最後更新**: 2026-02-02
**維護者**: Backend Team
