#!/usr/bin/env python3
"""快速建立測試專案"""

import httpx
import asyncio
import sys


API_BASE_URL = "http://localhost:8000"


async def create_and_provision_project():
    """建立並 provision 一個測試專案"""
    print("\n" + "="*60)
    print("  快速建立測試專案")
    print("="*60 + "\n")

    # 1. 使用固定測試帳號登入
    email = "test_sse@example.com"
    password = "testpass123456"

    async with httpx.AsyncClient() as client:
        print(f"\n🔐 正在登入測試帳號: {email}")
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json={"email": email, "password": password}
            )
            response.raise_for_status()
            token = response.json()["access_token"]
            print("✅ 登入成功！")
        except Exception as e:
            print(f"❌ 登入失敗: {e}")
            print("💡 請確保後端正在運行")
            sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 2. 建立專案
    print("\n📦 正在建立專案...")
    repo_url = input("Repo URL (預設: https://github.com/anthropics/anthropic-sdk-python.git): ").strip()
    if not repo_url:
        repo_url = "https://github.com/anthropics/anthropic-sdk-python.git"

    branch = input("Branch (預設: main): ").strip() or "main"
    init_prompt = input("Init Prompt (預設: 分析此專案的架構): ").strip() or "分析此專案的架構"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/projects",
            headers=headers,
            json={
                "repo_url": repo_url,
                "branch": branch,
                "init_prompt": init_prompt
            }
        )
        response.raise_for_status()
        project = response.json()
        project_id = project["id"]
        print(f"✅ 專案已建立！ID: {project_id}")

    # 3. Provision 專案
    print(f"\n🔧 正在 provision 專案...")
    print("⏳ 這可能需要幾分鐘（建立容器 + clone repo）...")

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/projects/{project_id}/provision",
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            print(f"✅ Provision 完成！")
            print(f"   Container ID: {result['container_id']}")
            print(f"   Status: {result['status']}")
        except httpx.HTTPError as e:
            print(f"❌ Provision 失敗: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   錯誤詳情: {e.response.text}")
            sys.exit(1)

    print("\n" + "="*60)
    print(f"✅ 測試專案準備完成！")
    print(f"   Project ID: {project_id}")
    print(f"\n現在可以執行: python test_sse_stream.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(create_and_provision_project())
    except KeyboardInterrupt:
        print("\n\n👋 取消操作")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        sys.exit(1)
