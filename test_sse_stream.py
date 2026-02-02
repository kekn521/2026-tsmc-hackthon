#!/usr/bin/env python3
"""測試 AI Server SSE Stream 功能

使用方式：
1. 啟動後端 API 和容器
2. 執行此腳本： python test_sse_stream.py
"""

import httpx
import asyncio
import sys
import json
from datetime import datetime


# 配置
API_BASE_URL = "http://localhost:8000"
PROJECT_ID = None  # 從命令列參數或手動輸入
RUN_ID = None


def log(message: str):
    """帶時間戳的日誌輸出"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")


async def register_user(email: str, username: str, password: str):
    """註冊新使用者"""
    log(f"📝 正在註冊新帳號: {email} (username: {username})")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/register",
                json={
                    "email": email,
                    "username": username,
                    "password": password
                }
            )
            response.raise_for_status()
            data = response.json()
            log(f"✅ 註冊成功！")
            return data["access_token"]
        except httpx.HTTPError as e:
            log(f"❌ 註冊失敗: {e}")
            if hasattr(e, 'response') and e.response:
                log(f"   錯誤詳情: {e.response.text}")
            return None


async def get_auth_token():
    """登入並取得 JWT token"""
    log("🔐 正在登入...")

    # 固定測試帳號
    email = "test_sse@example.com"
    password = "testpass123456"

    log(f"   使用測試帳號: {email}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json={"email": email, "password": password}
            )
            response.raise_for_status()
            data = response.json()
            token = data["access_token"]
            log(f"✅ 登入成功！Token: {token[:20]}...")
            return token
        except httpx.HTTPError as e:
            log(f"❌ 登入失敗: {e}")
            log("💡 測試帳號可能不存在，請先執行以下指令建立：")
            log("   python -c 'import asyncio, httpx; asyncio.run(httpx.AsyncClient().post(\"http://localhost:8000/api/v1/auth/register\", json={\"email\":\"test_sse@example.com\",\"username\":\"test_sse\",\"password\":\"testpass123456\"}))'")
            sys.exit(1)


async def list_projects(token: str):
    """列出專案並選擇一個"""
    log("📋 正在取得專案列表...")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/v1/projects",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        data = response.json()

        projects = data.get("projects", [])
        if not projects:
            log("❌ 沒有找到任何專案")
            log("💡 請先建立一個專案並 provision")
            sys.exit(1)

        log(f"\n找到 {len(projects)} 個專案：")
        for i, proj in enumerate(projects):
            log(f"  {i+1}. [{proj['status']}] {proj['repo_url']} (ID: {proj['id']})")

        choice = input(f"\n請選擇專案 (1-{len(projects)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(projects):
                return projects[idx]["id"]
        except ValueError:
            pass

        log("❌ 無效的選擇")
        sys.exit(1)


async def start_agent_run(token: str, project_id: str):
    """啟動 Agent Run"""
    log(f"\n🚀 正在啟動 Agent Run (project_id={project_id})...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/projects/{project_id}/agent/run",
                headers={"Authorization": f"Bearer {token}"},
                json={}
            )
            response.raise_for_status()
            data = response.json()

            run_id = data["run_id"]
            log(f"✅ Agent Run 已啟動！")
            log(f"   Run ID: {run_id}")
            log(f"   Status: {data['status']}")
            log(f"   Phase: {data['phase']}")

            return run_id

        except httpx.HTTPError as e:
            log(f"❌ 啟動失敗: {e}")
            if hasattr(e, 'response') and e.response:
                log(f"   錯誤詳情: {e.response.text}")
            sys.exit(1)


async def test_sse_stream(token: str, project_id: str, run_id: str):
    """測試 SSE 串流（支援結構化事件顯示）"""
    log(f"\n📡 開始測試 SSE 串流...")
    log(f"   URL: /api/v1/projects/{project_id}/agent/runs/{run_id}/stream")
    log(f"\n{'='*60}")
    log("開始接收 SSE 事件（按 Ctrl+C 停止）：")
    log(f"{'='*60}\n")

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET",
                f"{API_BASE_URL}/api/v1/projects/{project_id}/agent/runs/{run_id}/stream",
                headers={"Authorization": f"Bearer {token}"}
            ) as response:
                response.raise_for_status()

                event_count = 0
                current_event = None

                async for line in response.aiter_lines():
                    if line:
                        event_count += 1

                        # 解析 SSE 格式
                        if line.startswith("event: "):
                            current_event = line[7:]  # 移除 "event: " 前綴

                        elif line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前綴

                            # 嘗試解析 JSON
                            try:
                                data = json.loads(data_str)

                                # 根據事件類型美化顯示
                                if current_event == "log":
                                    timestamp = data.get("timestamp", "")
                                    message = data.get("message", "")
                                    log(f"{timestamp} {message}")

                                elif current_event == "ai_content":
                                    content = data.get("content", "")
                                    print(content, end="", flush=True)

                                elif current_event == "tool_calls":
                                    print("\n")
                                    log("🔧 [Tool Calls] 偵測到工具調用:")
                                    for i, tool_call in enumerate(data.get("tool_calls", []), 1):
                                        log(f"  #{i} {tool_call.get('name')}")
                                        log(f"      ID: {tool_call.get('id')}")
                                        log(f"      Args: {json.dumps(tool_call.get('args', {}), indent=8, ensure_ascii=False)}")

                                elif current_event == "token_usage":
                                    print("\n")
                                    log(f"📊 [Token Usage]")
                                    log(f"  Input:  {data.get('input_tokens', 0):,} tokens")
                                    log(f"  Output: {data.get('output_tokens', 0):,} tokens")
                                    log(f"  Total:  {data.get('total_tokens', 0):,} tokens")

                                elif current_event == "response_metadata":
                                    print("\n")
                                    log(f"ℹ️  [Response Metadata]")
                                    log(json.dumps(data.get('metadata', {}), indent=2, ensure_ascii=False))

                                elif current_event == "tools_execution":
                                    print("\n")
                                    log(f"🛠️  [Tools Execution] {len(data.get('results', []))} result(s)")
                                    for i, result in enumerate(data.get("results", []), 1):
                                        log(f"  #{i} 📄 {result.get('name')}")
                                        log(f"     ID: {result.get('tool_call_id', 'N/A')[:20]}...")
                                        content = result.get('content', '')
                                        if content:
                                            for line in content.split('\n')[:10]:  # 只顯示前 10 行
                                                log(f"     {line}")
                                            if result.get('content_length', 0) > 500:
                                                log(f"     ... (共 {result.get('content_length')} 字元)")

                                elif current_event == "status":
                                    print("\n")
                                    status = data.get("status", "unknown")
                                    log(f"✅ 任務完成，狀態: {status}")
                                    if data.get("error_message"):
                                        log(f"❌ 錯誤: {data.get('error_message')}")

                                else:
                                    # 未知事件類型，直接顯示
                                    log(f"[{current_event}] {data_str}")

                            except json.JSONDecodeError:
                                # 不是 JSON，直接顯示
                                log(f"[{current_event}] {data_str}")

                            current_event = None

                log(f"\n{'='*60}")
                log(f"✅ 串流結束！共接收 {event_count} 行")
                log(f"{'='*60}")

    except KeyboardInterrupt:
        log(f"\n\n⚠️  使用者中斷")
    except httpx.HTTPError as e:
        log(f"\n❌ SSE 串流失敗: {e}")
        if hasattr(e, 'response') and e.response:
            log(f"   錯誤詳情: {e.response.text}")


async def check_agent_status(token: str, project_id: str, run_id: str):
    """檢查 Agent 執行狀態"""
    log(f"\n🔍 檢查 Agent 執行狀態...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/projects/{project_id}/agent/runs/{run_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            data = response.json()

            log(f"   狀態: {data['status']}")
            log(f"   階段: {data['phase']}")
            log(f"   建立時間: {data.get('created_at', 'N/A')}")
            log(f"   完成時間: {data.get('finished_at', 'N/A')}")
            if data.get('error_message'):
                log(f"   錯誤訊息: {data['error_message']}")

        except httpx.HTTPError as e:
            log(f"❌ 查詢失敗: {e}")


async def main():
    """主程式"""
    print("\n" + "="*60)
    print("  AI Server SSE Stream 測試腳本")
    print("="*60 + "\n")

    # 1. 登入取得 token
    token = await get_auth_token()

    # 2. 選擇專案
    project_id = await list_projects(token)

    # 3. 自動啟動新的 Agent Run
    log("\n🚀 正在啟動 Agent Run...")
    run_id = await start_agent_run(token, project_id)

    # 4. 測試 SSE 串流
    await test_sse_stream(token, project_id, run_id)

    # 5. 檢查最終狀態
    await check_agent_status(token, project_id, run_id)

    log("\n✅ 測試完成！")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 再見！")
