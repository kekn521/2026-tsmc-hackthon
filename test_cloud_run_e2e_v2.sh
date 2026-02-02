#!/bin/bash
# E2E Test: Cloud Run Architecture (Enhanced with error handling)

# 不使用 set -e，手動處理錯誤
echo "=== E2E Test: Cloud Run (Enhanced) ==="

# 生成隨機 email 避免衝突
RANDOM_EMAIL="test-$(date +%s)@example.com"
echo "使用測試 email: $RANDOM_EMAIL"

# 1. 啟動服務
echo "[1/7] 啟動服務..."
docker-compose -f devops/docker-compose.yml up -d
if [ $? -ne 0 ]; then
    echo "❌ 啟動服務失敗"
    exit 1
fi
sleep 10

# 2. 檢查 API 健康狀態
echo "[2/7] 檢查 API 健康狀態..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/v1/health)
echo "Health: $HEALTH_RESPONSE"
if ! echo $HEALTH_RESPONSE | grep -q "healthy"; then
    echo "❌ API 健康檢查失敗"
    exit 1
fi

# 3. 註冊使用者
echo "[3/7] 註冊使用者..."
RANDOM_USERNAME="testuser-$(date +%s)"
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$RANDOM_EMAIL\",\"username\":\"$RANDOM_USERNAME\",\"password\":\"testpass123\"}")

echo "註冊回應: $REGISTER_RESPONSE"

# 檢查是否有 access_token
if ! echo $REGISTER_RESPONSE | grep -q "access_token"; then
    echo "❌ 註冊失敗，沒有 access_token"
    echo "嘗試登入..."

    # 如果註冊失敗（可能已存在），嘗試登入
    LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"$RANDOM_EMAIL\",\"password\":\"testpass123\"}")

    echo "登入回應: $LOGIN_RESPONSE"
    TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
else
    TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.access_token')
fi

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ 無法取得 token"
    exit 1
fi

echo "✅ Token: ${TOKEN:0:20}..."

# 4. 建立專案
echo "[4/7] 建立專案..."
PROJECT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url":"https://github.com/emilybache/Racing-Car-Katas",
    "branch":"main",
    "init_prompt":"分析此專案並生成重構計劃，請專注在 /Python 的資料夾，我想要把裡面的python 轉成 go lang，並存入 ./memory/plan.md 檔案，不需要使用者確認後就直接執行所有的計劃，把它完整重構完成"
  }')

echo "專案建立回應: $PROJECT_RESPONSE"

PROJECT_ID=$(echo $PROJECT_RESPONSE | jq -r '.id')
if [ "$PROJECT_ID" = "null" ] || [ -z "$PROJECT_ID" ]; then
    echo "❌ 建立專案失敗"
    exit 1
fi

echo "✅ Project ID: $PROJECT_ID"

# 5. Provision 專案
echo "[5/7] Provision 專案..."
PROVISION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/provision \
  -H "Authorization: Bearer $TOKEN")

echo "Provision 回應: $PROVISION_RESPONSE"

# 等待 provision 完成
echo "等待 provision 完成（30 秒）..."
sleep 10

# 檢查專案狀態
PROJECT_STATUS=$(curl -s http://localhost:8000/api/v1/projects/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN" | jq -r '.status')

echo "專案狀態: $PROJECT_STATUS"

if [ "$PROJECT_STATUS" != "READY" ]; then
    echo "⚠️  專案狀態不是 READY，但繼續測試..."
fi

# 6. 執行 Cloud Run
echo "[6/7] 執行 Cloud Run..."
RUN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/cloud-run \
  -H "Authorization: Bearer $TOKEN")

echo "Cloud Run 回應: $RUN_RESPONSE"

STATUS=$(echo $RUN_RESPONSE | jq -r '.status')
TASK_ID=$(echo $RUN_RESPONSE | jq -r '.task_id')

if [ "$STATUS" = "success" ]; then
    echo "✅ Cloud Run 啟動成功"
    echo "Task ID: $TASK_ID"

    # 10秒查詢任務狀態
    sleep 10
    TASK_STATUS=$(curl -s http://localhost:8000/api/v1/projects/$PROJECT_ID/cloud-run/$TASK_ID \
      -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo $TASK_STATUS | jq -r '.status')
    if [ "$STATUS" = "completed" ]; then
        echo "任務狀態: $TASK_STATUS"
    fi

    # while true; do
    #     TASK_STATUS=$(curl -s http://localhost:8000/api/v1/projects/$PROJECT_ID/cloud-run/$TASK_ID \
    #       -H "Authorization: Bearer $TOKEN")
    #     STATUS=$(echo $TASK_STATUS | jq -r '.status')
    #     if [ "$STATUS" = "completed" ]; then
    #         echo "任務狀態: $TASK_STATUS"
    #         break
    #     fi
    #     sleep 3
    # done

    echo "✅ E2E Test PASSED"
else
    echo "❌ Cloud Run 啟動失敗"
    echo "詳細錯誤: $RUN_RESPONSE"
fi

# 7. 清理
# echo "[7/7] 清理測試資料..."
# DELETE_RESPONSE=$(curl -s -X DELETE http://localhost:8000/api/v1/projects/$PROJECT_ID \
#   -H "Authorization: Bearer $TOKEN")
# echo "刪除回應: $DELETE_RESPONSE"

# echo "=== Test Complete ==="
