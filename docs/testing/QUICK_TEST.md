# 快速測試指南 ⚡

## 一鍵測試（最快方式）

```bash
# 1. 啟動服務（分 3 個終端視窗）
# 終端 1: MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:7

# 終端 2: Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# 終端 3: CLI 測試
python3 cli.py
```

## 互動流程（全部使用預設值）

啟動 CLI 後，**只需按 3 次 Enter**：

```
步驟 1: 登入/註冊
請選擇 (1=登入, 2=註冊, d=使用預設帳號登入, Enter=使用預設帳號登入):
👉 [按 Enter]  ← 使用預設測試帳號

步驟 2: 選擇專案
使用現有專案 (輸入編號) 或建立新專案 (輸入 n): n
是否使用預設測試專案？(Enter=是, n=自訂):
👉 [按 Enter]  ← 使用預設測試專案

步驟 3: Provision 專案
ℹ️  使用全域開發模式設定
（自動使用 .env 中的 DEV_MODE 設定，無需手動選擇）

步驟 4: 執行 Agent
（自動執行）

步驟 5: 串流日誌
（自動串流，按 Ctrl+C 可停止）
```

## 預設值說明

- **測試帳號**:
  - Email: `test@example.com`
  - Username: `test` (自動從 email 生成)
  - Password: `testpass123`
- **測試專案**: Racing Car Katas - 程式碼重構練習專案
  - Repository: `https://github.com/emilybache/Racing-Car-Katas.git`
  - Branch: `main`
- **開發模式**: 自動使用 `.env` 中的 `DEV_MODE` 設定
- **提示詞**: "請分析此專案的程式碼結構，並提供重構建議"

## 預期結果

你應該看到：

```
✅ 登入成功！使用者: test@example.com
✅ 使用預設專案: 測試專案
✅ 專案建立成功！ID: 507f1f77bcf86cd799439011
✅ Provision 成功！
✅ Agent 已啟動！

開始串流日誌...
[2026-02-02T12:34:56] 🚀 開始執行 Agent
[2026-02-02T12:34:57] 🔧 初始化 LLM...
[2026-02-02T12:34:58] ✅ LLM 初始化完成
[2026-02-02T12:34:59] 🤖 建立 RefactorAgent...
[2026-02-02T12:35:00] ✅ RefactorAgent 建立完成
[2026-02-02T12:35:01] ▶️  執行 Agent...
[2026-02-02T12:35:02] 🚀 開始執行 Agent
[2026-02-02T12:35:03] 📝 User Message: 請分析此專案...
[2026-02-02T12:35:05] 💬 AI Response: ...
```

## 如果出錯

### 1. 登入失敗
```bash
# 檢查 Backend 是否運行
curl http://localhost:8000/api/v1/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

### 2. Provision 失敗
```bash
# 檢查 Docker
docker ps

# 檢查 base image
docker images | grep refactor-base
```

### 3. 日誌串流無資料
```bash
# 檢查容器日誌
docker logs refactor-project-{project_id}

# 確認已重建 image
docker build -t refactor-base:latest -f devops/base-image/Dockerfile .
```

## 進階選項

如果不想使用預設值：

- **自訂帳號**: 步驟 1 選擇 `2` (註冊) 或 `1` (登入)
- **自訂專案**: 步驟 2 選擇 `n`
- **啟用開發模式**: 步驟 3 輸入 `y`

## 下一步

測試成功後：
- 查看 artifacts: `docker exec refactor-project-{id} ls /workspace/artifacts`
- 下載 plan.json: `docker cp refactor-project-{id}:/workspace/artifacts/plan.json .`
- 檢查日誌: `docker logs refactor-project-{id}`

---

**享受測試！** 🚀
