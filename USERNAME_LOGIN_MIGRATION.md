# 登入方式遷移：Email → Username

## 變更摘要

登入方式已從 **email** 改為 **username**。

### 變更前後對比

| 項目 | 變更前 | 變更後 |
|------|--------|--------|
| 登入欄位 | Email | 使用者名稱 (Username) |
| 登入範例 | `quan@example.com` | `quan` |
| API 欄位 | `email` | `username` |
| 唯一性驗證 | Email 唯一 | Email + Username 都唯一 |

---

## 後端變更

### 1. Schema 變更

**檔案**: `backend/app/schemas/auth.py`

```python
# 變更前
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

# 變更後
class UserLoginRequest(BaseModel):
    username: str
    password: str
```

### 2. AuthService 變更

**檔案**: `backend/app/services/auth_service.py`

#### 2.1 註冊時檢查 username 唯一性

```python
async def create_user(self, email: str, username: str, password: str) -> User:
    # 檢查 email 是否已存在
    existing_user = await self.users_collection.find_one({"email": email})
    if existing_user:
        raise ValueError("Email already registered")

    # 🆕 檢查 username 是否已存在
    existing_username = await self.users_collection.find_one({"username": username})
    if existing_username:
        raise ValueError("Username already taken")

    # ... 建立用戶
```

#### 2.2 登入驗證改用 username

```python
# 變更前
async def authenticate_user(self, email: str, password: str) -> Optional[User]:
    user_doc = await self.users_collection.find_one({"email": email})
    # ...

# 變更後
async def authenticate_user(self, username: str, password: str) -> Optional[User]:
    user_doc = await self.users_collection.find_one({"username": username})
    # ...
```

### 3. Auth Router 變更

**檔案**: `backend/app/routers/auth.py`

```python
# 變更前
user = await auth_service.authenticate_user(
    email=request.email,
    password=request.password
)

# 變更後
user = await auth_service.authenticate_user(
    username=request.username,
    password=request.password
)
```

### 4. 資料庫索引

**新增 username 唯一索引**

執行腳本：
```bash
cd backend
python scripts/init_username_index.py
```

---

## 前端變更

### 1. Types 變更

**檔案**: `frontend/src/types/auth.types.ts`

```typescript
// 變更前
export interface LoginRequest {
  email: string
  password: string
}

// 變更後
export interface LoginRequest {
  username: string
  password: string
}
```

### 2. AuthContext 變更

**檔案**: `frontend/src/contexts/AuthContext.tsx`

```typescript
// 變更前
interface AuthContextType {
  login: (email: string, password: string) => Promise<void>
}

const login = async (email: string, password: string) => {
  const { access_token } = await loginAPI({ email, password })
  // ...
}

// 變更後
interface AuthContextType {
  login: (username: string, password: string) => Promise<void>
}

const login = async (username: string, password: string) => {
  const { access_token } = await loginAPI({ username, password })
  // ...
}
```

### 3. LoginPage 變更

**檔案**: `frontend/src/pages/LoginPage.tsx`

```typescript
// 變更前
const [email, setEmail] = useState('')

<Input
  type="email"
  placeholder="your@email.com"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
/>

await login(email, password)

// 變更後
const [username, setUsername] = useState('')

<Input
  type="text"
  placeholder="username"
  value={username}
  onChange={(e) => setUsername(e.target.value)}
/>

await login(username, password)
```

### 4. RegisterPage 變更

**檔案**: `frontend/src/pages/RegisterPage.tsx`

```typescript
// 變更前
await login(email, password)  // 註冊後自動登入

// 變更後
await login(username, password)  // 註冊後自動登入
```

---

## 遷移步驟

### 步驟 1：更新資料庫

```bash
# 為 username 欄位建立唯一索引
cd backend
python scripts/init_username_index.py
```

**預期輸出**：
```
連接到 MongoDB: mongodb://localhost:27017
資料庫: refactor_agent
Collection: users
✅ 成功建立 username 索引: username_1

當前所有索引：
  - _id_: {'key': [('_id', 1)], 'v': 2}
  - email_1: {'key': [('email', 1)], 'unique': True, 'v': 2}
  - username_1: {'key': [('username', 1)], 'unique': True, 'v': 2}
```

### 步驟 2：重啟後端

```bash
# 如果使用 Docker Compose
cd devops
docker-compose restart api

# 如果本地開發
cd backend
# 重新啟動 uvicorn
```

### 步驟 3：重建前端（如果需要）

```bash
cd frontend
npm run build
```

### 步驟 4：更新現有用戶（如果有）

如果資料庫中已有用戶但 username 不唯一，需要手動處理：

```javascript
// 連接到 MongoDB
use refactor_agent

// 檢查是否有重複的 username
db.users.aggregate([
  { $group: { _id: "$username", count: { $sum: 1 } } },
  { $match: { count: { $gt: 1 } } }
])

// 如果有重複，需要手動更新
db.users.updateOne(
  { email: "user@example.com" },
  { $set: { username: "unique_username" } }
)
```

---

## 測試驗證

### 測試案例 1：新用戶註冊

1. 訪問 `/register`
2. 填寫表單：
   - Email: `test@example.com`
   - Username: `testuser`
   - Password: `test123456`
3. 點擊「註冊」
4. **驗證**：
   - ✅ 註冊成功
   - ✅ 自動登入成功
   - ✅ 跳轉到專案列表

### 測試案例 2：Username 重複

1. 嘗試註冊一個已存在的 username
2. **驗證**：
   - ✅ 顯示錯誤：「Username already taken」

### 測試案例 3：使用 Username 登入

1. 訪問 `/login`
2. 輸入：
   - 使用者名稱: `quan`
   - 密碼: `quan12345`
3. 點擊「登入」
4. **驗證**：
   - ✅ 登入成功
   - ✅ 跳轉到專案列表

### 測試案例 4：錯誤的 Username

1. 訪問 `/login`
2. 輸入不存在的 username
3. **驗證**：
   - ✅ 顯示錯誤：「Incorrect username or password」

---

## API 變更

### POST /api/v1/auth/login

**變更前**：
```json
{
  "email": "quan@example.com",
  "password": "quan12345"
}
```

**變更後**：
```json
{
  "username": "quan",
  "password": "quan12345"
}
```

**回應**（不變）：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### POST /api/v1/auth/register

**無變更**，仍需提供 email 和 username：
```json
{
  "email": "test@example.com",
  "username": "testuser",
  "password": "test123456"
}
```

---

## 向後相容性

⚠️ **不向後相容**

此變更 **不向後相容**。所有使用 email 登入的現有用戶端都需要更新為使用 username。

### 如果需要支援兩種登入方式

可以修改 `authenticate_user` 方法支援 email 或 username：

```python
async def authenticate_user(self, username_or_email: str, password: str) -> Optional[User]:
    # 嘗試使用 username 查詢
    user_doc = await self.users_collection.find_one({"username": username_or_email})

    # 如果找不到，嘗試使用 email 查詢
    if not user_doc:
        user_doc = await self.users_collection.find_one({"email": username_or_email})

    if not user_doc:
        return None

    # ... 驗證密碼
```

但建議統一使用 username 以避免混淆。

---

## 故障排除

### 問題 1：登入失敗，提示 "Incorrect username or password"

**可能原因**：
1. Username 拼寫錯誤
2. 密碼錯誤
3. 用戶不存在

**解決方案**：
```bash
# 檢查用戶是否存在
mongo refactor_agent --eval 'db.users.findOne({username: "quan"})'

# 查看所有用戶的 username
mongo refactor_agent --eval 'db.users.find({}, {username: 1, email: 1})'
```

### 問題 2：註冊失敗，提示 "Username already taken"

**原因**：Username 已被使用

**解決方案**：
- 使用不同的 username
- 或檢查並刪除重複的用戶（如果是測試資料）

### 問題 3：前端仍顯示 "Email" 欄位

**原因**：前端未重新載入或快取問題

**解決方案**：
```bash
# 清除瀏覽器快取
# 或使用無痕模式測試

# 重新建置前端
cd frontend
rm -rf node_modules/.vite
npm run dev
```

---

## 修改的檔案清單

### 後端
- ✅ `backend/app/schemas/auth.py`
- ✅ `backend/app/services/auth_service.py`
- ✅ `backend/app/routers/auth.py`
- ✅ `backend/scripts/init_username_index.py` (新增)

### 前端
- ✅ `frontend/src/types/auth.types.ts`
- ✅ `frontend/src/contexts/AuthContext.tsx`
- ✅ `frontend/src/pages/LoginPage.tsx`
- ✅ `frontend/src/pages/RegisterPage.tsx`

---

## 總結

✅ **已完成**：
- 後端支援使用 username 登入
- 前端登入頁面改為輸入 username
- Username 唯一性驗證
- 資料庫索引建立
- 所有相關程式碼更新

🎯 **使用者體驗改善**：
- 登入更簡潔（不需輸入完整 email）
- Username 更好記憶
- 符合常見應用習慣

🔒 **安全性維持**：
- Username 唯一性確保
- 密碼驗證機制不變
- JWT token 機制不變
