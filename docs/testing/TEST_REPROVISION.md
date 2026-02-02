# 測試指南：重新 Provision 停止的專案

## 測試目的

驗證停止的專案（狀態 STOPPED）可以重新 provision 並變回 READY 狀態。

## 測試步驟

### 方法 1: 使用 CLI

```bash
# 1. 啟動 CLI
python3 cli.py

# 2. 登入（按 Enter 使用預設帳號）

# 3. 建立新專案或選擇現有專案
選擇功能: 2  # 建立新專案
按 Enter  # 使用預設測試專案

# 4. Provision 專案
選擇功能: 4  # Provision 專案
# 等待完成，專案狀態變為 READY

# 5. 停止專案
選擇功能: 5  # 停止專案容器
# 專案狀態變為 STOPPED

# 6. 重新 Provision（這是新功能！）
選擇功能: 4  # 再次 Provision
# 應該看到：
# - 清理舊容器的訊息
# - 建立新容器
# - 專案狀態變回 READY
```

**預期結果**：
- ✅ 停止的專案可以成功 provision
- ✅ 舊容器被自動清理
- ✅ 新容器建立成功
- ✅ 專案狀態從 STOPPED → PROVISIONING → READY
- ✅ 可以繼續執行 Agent

---

### 方法 2: 使用 API

```bash
# 1. 登入取得 token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'

# 儲存 token
export TOKEN="your_access_token"

# 2. 建立專案
PROJECT_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url":"https://github.com/octocat/Hello-World.git",
    "branch":"main",
    "init_prompt":"分析程式碼"
  }')

PROJECT_ID=$(echo $PROJECT_RESPONSE | jq -r '.id')
echo "專案 ID: $PROJECT_ID"

# 3. Provision 專案
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/provision" \
  -H "Authorization: Bearer $TOKEN"

# 等待完成，查詢狀態
curl "http://localhost:8000/api/v1/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.status'
# 應顯示: "READY"

# 4. 停止專案
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/stop" \
  -H "Authorization: Bearer $TOKEN"

# 查詢狀態
curl "http://localhost:8000/api/v1/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.status'
# 應顯示: "STOPPED"

# 5. 重新 Provision（測試新功能）
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/provision" \
  -H "Authorization: Bearer $TOKEN"

# 查詢狀態
curl "http://localhost:8000/api/v1/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.status'
# 應顯示: "READY"
```

**預期結果**：
- ✅ API 返回 200 OK（不是 400 錯誤）
- ✅ 專案狀態成功從 STOPPED 變為 READY
- ✅ container_id 更新為新容器的 ID

---

## 驗證檢查清單

### Backend 日誌檢查

查看 Backend 日誌，應該看到：

```
INFO:     清理舊容器: abc123def456
INFO:     已刪除舊容器: abc123def456
INFO:     建立專案目錄: /tmp/refactor-workspaces/{project_id}
INFO:     建立容器: 專案 {project_id}
INFO:     Clone repository: https://github.com/...
INFO:     專案 {project_id} provision 完成
```

### Docker 容器檢查

```bash
# 查看容器列表
docker ps -a | grep refactor-project

# 應該只看到一個新容器（舊容器已被刪除）
# 容器狀態應該是 Up
```

### 資料庫檢查

```bash
# 進入 MongoDB
docker exec -it mongodb mongosh refactor_agent

# 查詢專案
db.projects.findOne({"_id": ObjectId("project_id")})

# 檢查欄位：
# - status: "READY"
# - container_id: 新容器 ID
# - last_error: null 或空
# - updated_at: 最近的時間戳
```

---

## 錯誤處理測試

### 測試情境 1: 非法狀態嘗試 Provision

```bash
# 當專案狀態為 READY 時，不應該允許 provision
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/provision" \
  -H "Authorization: Bearer $TOKEN"

# 預期: 400 錯誤
# 訊息: "專案狀態必須為 CREATED 或 STOPPED,目前為 READY"
```

### 測試情境 2: 容器不存在但狀態為 STOPPED

```bash
# 手動刪除容器但不更新資料庫
docker rm -f refactor-project-{project_id}

# 嘗試 re-provision
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/provision" \
  -H "Authorization: Bearer $TOKEN"

# 預期: 成功（系統會忽略清理失敗的警告並繼續）
```

---

## 已知限制

1. **容器內資料會遺失**：重新 provision 會建立全新容器，之前在容器內的修改會遺失
2. **需要網路連線**：重新 clone repository 需要網路連線
3. **耗時操作**：重新 provision 需要重新 clone repository，可能需要一些時間

---

## 回報問題

如果測試失敗，請記錄：
1. Backend 日誌（完整錯誤訊息）
2. Docker 容器狀態（`docker ps -a`）
3. 資料庫中的專案狀態
4. 重現步驟

提交 Issue 到 GitHub。

---

**測試成功！** 🎉

停止的專案現在可以無縫重新 provision 並繼續使用了。
