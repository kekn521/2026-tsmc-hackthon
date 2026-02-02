# SSE Stream 修復和 CLI 工具 - 更新日誌

**日期**: 2026-02-02
**版本**: v0.2.0

## 問題描述

### 問題 1: SSE 串流無資料
- 現象：test_sse_stream.py 只看到 ping 訊息，看不到 Agent 執行日誌
- 影響：無法即時監控 Agent 執行狀態

### 問題 2: Debug 訊息不足
- 現象：AI Agent 執行時缺少詳細的 debug 訊息
- 影響：難以追蹤問題和診斷錯誤

### 問題 3: 缺少簡易測試工具
- 現象：需要前端才能測試 API 功能
- 影響：開發和測試效率低

---

## 解決方案

### 修復 1: 確保 Python 輸出不被緩衝

**檔案**: `devops/base-image/Dockerfile`

**修改**:
```dockerfile
# 設定環境變數：確保 Python 輸出不被緩衝
ENV PYTHONUNBUFFERED=1
```

**效果**: 所有 Python print 和 logging 輸出會立即寫入 stdout，不會被 buffer

---

### 修復 2: 配置 ai_server.py logging

**檔案**: `agent/ai_server.py`

**修改**:
```python
import sys

# 配置 logging 輸出到 stdout（確保日誌可被收集）
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
```

**效果**: 所有 logging 訊息輸出到 stdout，可被 Docker logs 收集

---

### 修復 3: 增加詳細的 debug 訊息

**檔案**: `agent/ai_server.py` - `execute_agent()` 函數

**修改**: 在關鍵步驟增加帶 emoji 的 debug 訊息：

```python
print(f"🚀 [DEBUG] Task {task_id}: 開始執行", flush=True)
print(f"🔧 [DEBUG] Task {task_id}: 初始化 LLM", flush=True)
print(f"✅ [DEBUG] Task {task_id}: LLM 初始化完成", flush=True)
print(f"🤖 [DEBUG] Task {task_id}: 建立 RefactorAgent", flush=True)
print(f"▶️  [DEBUG] Task {task_id}: 開始執行 Agent", flush=True)
print(f"✅ [DEBUG] Task {task_id}: Agent 執行完成", flush=True)
```

**效果**: 可以清楚看到 Agent 執行的每個階段

---

### 修復 4: deep_agent.py 增加 flush

**檔案**: `agent/deep_agent.py`

**修改**: 所有 print 語句加上 `flush=True`

```python
print(f"🚀 開始執行 Agent", flush=True)
print(f"📝 User Message: {user_message}\n", flush=True)
```

**效果**: print 輸出立即顯示，不會延遲

---

### 修復 5: Backend SSE 轉發增強

**檔案**: `backend/app/routers/agent.py` - `stream_agent_logs()`

**修改**: 增加詳細的轉發 debug 訊息：

```python
logger.info(f"🔗 開始串流 AI Server 日誌: {url}")
print(f"🔗 [DEBUG] 開始連線到: {url}", flush=True)

logger.info(f"✅ SSE 連線已建立，狀態碼: {response.status_code}")
print(f"✅ [DEBUG] SSE 連線已建立", flush=True)

print(f"📨 [DEBUG] 收到 SSE 訊息 #{line_count}", flush=True)
```

**效果**: 可以追蹤 SSE 連線狀態和訊息數量

---

### 新功能: CLI 工具

**檔案**: `cli.py` (新增)

**功能**:
- ✅ 互動式使用者介面
- ✅ 完整的 API 功能測試
- ✅ 即時串流日誌顯示
- ✅ 錯誤處理和提示

**主要方法**:
- `register()` / `login()` - 使用者認證
- `create_project()` - 建立專案
- `list_projects()` - 列出專案
- `provision_project()` - Provision（支援 dev_mode）
- `run_agent()` - 執行 Agent
- `stream_logs()` - 串流日誌
- `get_agent_status()` - 查詢狀態

**使用方式**:
```bash
python3 cli.py
```

---

## 測試步驟

### 1. 重建 Docker Image

```bash
# 從專案根目錄執行
docker build -t refactor-base:latest -f devops/base-image/Dockerfile .
```

**重要**: 必須重建 image 才能應用 `PYTHONUNBUFFERED=1` 和其他修改

### 2. 啟動 Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### 3. 使用 CLI 測試

```bash
python3 cli.py
```

依照互動提示完成：
1. 註冊/登入
2. 建立或選擇專案
3. Provision 專案
4. 執行 Agent
5. 觀察即時日誌

### 4. 預期結果

**正常輸出**:
```
[2026-02-02T12:34:56] 🚀 開始執行 Agent
[2026-02-02T12:34:57] 🔧 初始化 LLM...
[2026-02-02T12:34:58] ✅ LLM 初始化完成
[2026-02-02T12:34:59] 🤖 建立 RefactorAgent...
[2026-02-02T12:35:00] ✅ RefactorAgent 建立完成
[2026-02-02T12:35:01] ▶️  執行 Agent...
[2026-02-02T12:35:02] 🚀 開始執行 Agent
[2026-02-02T12:35:03] 📝 User Message: ...
[2026-02-02T12:35:05] 💬 AI Response: ...
```

**不應該出現**:
- 長時間只有 ping 訊息
- 空白輸出
- 連線超時

---

## 文件更新

### 新增文件

1. **CLI_USAGE.md** - CLI 工具完整使用指南
   - 功能說明
   - 使用範例
   - 常見問題排除
   - 進階用法

2. **CHANGELOG_SSE_FIX.md** - 本次更新日誌

### 更新文件

1. **CLAUDE.md** - 已在先前更新中加入開發模式說明

---

## 向後相容性

✅ **完全相容** - 所有修改都是向下相容的：

- Dockerfile 環境變數不影響現有功能
- ai_server.py logging 配置只是增加輸出
- debug 訊息不影響核心邏輯
- CLI 是新增工具，不影響現有程式碼

---

## 已知限制

### 1. ChunkParser 輸出未完全優化
- 目前只在 deep_agent.py 主要輸出點加 flush
- ChunkParser 內部的 print 未全部加 flush
- **影響**: 部分詳細資訊可能有輕微延遲
- **優先級**: 低（主要訊息已可見）

### 2. CLI 功能尚不完整
- 缺少專案刪除功能
- 缺少 artifacts 下載功能
- 無命令列參數模式（只有互動模式）
- **優先級**: 中（可後續迭代）

### 3. 錯誤處理可加強
- CLI 的錯誤訊息可以更詳細
- SSE 斷線重連機制待實作
- **優先級**: 中

---

## 下一步計劃

### Phase 1: 完善 CLI (優先級: 高)
- [ ] 增加命令列參數模式
- [ ] 增加專案刪除功能
- [ ] 增加 artifacts 下載功能
- [ ] 增加彩色輸出（使用 rich 或 colorama）

### Phase 2: SSE 穩定性 (優先級: 中)
- [ ] 實作 SSE 斷線重連
- [ ] 增加心跳檢測
- [ ] 優化大量日誌的傳輸

### Phase 3: 監控和可觀測性 (優先級: 中)
- [ ] 增加 Agent 執行時間統計
- [ ] 增加 token usage 追蹤
- [ ] 實作進度百分比顯示

---

## 變更檔案清單

### 核心修改
- ✅ `devops/base-image/Dockerfile` - 加入 PYTHONUNBUFFERED
- ✅ `agent/ai_server.py` - logging 配置 + debug 訊息
- ✅ `agent/deep_agent.py` - print flush
- ✅ `backend/app/routers/agent.py` - SSE 轉發增強

### 新增檔案
- ✅ `cli.py` - CLI 工具
- ✅ `CLI_USAGE.md` - CLI 使用指南
- ✅ `CHANGELOG_SSE_FIX.md` - 本文件

### 測試檔案
- ✅ `test_sse_stream.py` - 已在先前簡化（自動啟動 Agent Run）

---

## 驗證清單

開發者請確認以下項目：

- [ ] 重建 Docker image
- [ ] Backend 可正常啟動
- [ ] MongoDB 正在運行
- [ ] Docker daemon 正在運行
- [ ] 使用 CLI 建立專案成功
- [ ] Provision 成功建立容器
- [ ] Agent 執行成功
- [ ] SSE 串流可看到完整日誌
- [ ] 錯誤時有清楚的錯誤訊息

---

## 貢獻者

- [@quan] - SSE 修復和 CLI 工具實作

---

## 參考資源

- [FastAPI SSE Documentation](https://fastapi.tiangolo.com/advanced/custom-response/#using-streamingresponse-with-file-like-objects)
- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Docker ENV Instruction](https://docs.docker.com/engine/reference/builder/#env)
