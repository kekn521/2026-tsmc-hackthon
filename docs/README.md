# 文件索引

> AI 舊程式碼智能重構系統 - 完整文件導覽

---

## 📚 核心文件

### [API.md](./API.md)
**REST API 完整規格**

詳細記錄所有 API 端點的：
- Request Payload 結構
- Response 格式
- 認證機制
- 錯誤處理
- 使用範例（curl, JavaScript/TypeScript）

適合：前端開發、API 整合、第三方串接

---

### [BACKEND.md](./BACKEND.md)
**後端技術文件**

包含：
- 架構總覽（技術棧、系統架構圖、資料流）
- 核心模組（目錄結構、關鍵檔案說明）
- 資料模型（Project, User, ProjectStatus）
- 服務層設計（ProjectService, ContainerService, AuthService）
- 認證機制（JWT 流程、權限控制）
- 開發模式（DEV_MODE 配置）
- 錯誤處理（失敗回滾、狀態一致性）
- 部署配置（環境變數、Docker Compose、測試）

適合：後端開發、系統維護、架構理解

---

## 📖 使用指南

### [guides/CLI_MENU_GUIDE.md](./guides/CLI_MENU_GUIDE.md)
**CLI 主選單模式使用指南**

互動式 CLI 工具完整操作說明：
- 主選單功能介紹
- 專案管理流程
- Agent 執行與監控
- 快捷鍵與操作技巧

適合：CLI 用戶、本地開發測試

---

### [guides/CLI_USAGE.md](./guides/CLI_USAGE.md)
**CLI 命令列使用說明**

CLI 指令模式操作：
- 指令語法
- 參數說明
- 常用場景範例

適合：腳本自動化、CI/CD 整合

---

## 🧪 測試文件

### [testing/QUICK_TEST.md](./testing/QUICK_TEST.md)
**快速測試指南**

一鍵測試流程和常見測試場景。

---

### [testing/TEST_REPROVISION.md](./testing/TEST_REPROVISION.md)
**Reprovision 測試指南**

測試停止專案重新 Provision 的流程。

---

### [testing/TEST_SSE_GUIDE.md](./testing/TEST_SSE_GUIDE.md)
**SSE 串流測試指南**

測試 Server-Sent Events 日誌串流功能。

---

## 📦 歷史文件

### [archives/](./archives/)
存放臨時變更日誌和開發筆記：
- `CHANGELOG_SSE_FIX.md` - SSE Stream 修復記錄
- `CLI_UPDATE.md` - CLI 工具更新記錄

這些文件保留作為開發歷史參考，不建議依賴其內容。

---

## 🔍 快速查找

### 我想...

- **整合 API** → [API.md](./API.md)
- **了解後端架構** → [BACKEND.md](./BACKEND.md)
- **使用 CLI 工具** → [guides/CLI_MENU_GUIDE.md](./guides/CLI_MENU_GUIDE.md)
- **執行測試** → [testing/QUICK_TEST.md](./testing/QUICK_TEST.md)
- **設定開發環境** → [BACKEND.md#部署配置](./BACKEND.md#部署配置)
- **理解認證機制** → [API.md#認證機制](./API.md#認證機制)
- **查詢資料模型** → [BACKEND.md#資料模型](./BACKEND.md#資料模型)

---

## 📝 文件維護

**重要**：當後端程式碼（`backend/` 目錄）有任何更新時，請同步更新相關文件：

- API 端點變更 → 更新 `API.md`
- 架構或服務層變更 → 更新 `BACKEND.md`
- CLI 功能變更 → 更新 `guides/CLI_*.md`

---

**文件版本**: v1.0.0
**最後更新**: 2026-02-02
