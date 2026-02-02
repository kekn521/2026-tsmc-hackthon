#!/usr/bin/env python3
"""
AI Refactor Agent - 簡易 CLI 工具

功能：
- 使用者註冊/登入
- 建立專案
- Provision 專案
- 執行 Agent
- 即時串流日誌
"""
import asyncio
import httpx
import json
import sys
from typing import Optional
from datetime import datetime


class RefactorCLI:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.token: Optional[str] = None
        self.current_project_id: Optional[str] = None

    def print_header(self, text: str):
        """印出標題"""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")

    def print_success(self, text: str):
        """印出成功訊息"""
        print(f"✅ {text}")

    def print_error(self, text: str):
        """印出錯誤訊息"""
        print(f"❌ {text}", file=sys.stderr)

    def print_info(self, text: str):
        """印出資訊"""
        print(f"ℹ️  {text}")

    def print_warning(self, text: str):
        """印出警告訊息"""
        print(f"⚠️  {text}")

    def extract_repo_name(self, repo_url: str) -> str:
        """從 repo URL 提取專案名稱"""
        try:
            # 移除查詢參數和 fragment
            url = repo_url.split('?')[0].split('#')[0]
            # 移除 .git 後綴
            url = url.rstrip('/').replace('.git', '')
            # 移除協議前綴
            url = url.replace('https://', '').replace('http://', '')
            # 提取路徑部分
            parts = url.split('/')
            # GitHub URL 格式: github.com/owner/repo[/tree/branch/...]
            # 我們需要第 3 個部分（索引 2）：github.com(0) / owner(1) / repo(2)
            if len(parts) >= 3:
                return parts[2]  # repo 名稱
            elif len(parts) == 2:
                return parts[1]  # 簡化的 URL
            return 'Unknown'
        except:
            return 'Unknown'

    async def register(self, email: str, password: str, username: Optional[str] = None) -> bool:
        """註冊新使用者"""
        try:
            # 如果沒有提供 username，從 email 生成
            if not username:
                username = email.split("@")[0]

            async with httpx.AsyncClient() as client:
                # 註冊
                response = await client.post(
                    f"{self.api_base_url}/api/v1/auth/register",
                    json={
                        "email": email,
                        "username": username,
                        "password": password
                    }
                )

                if response.status_code == 201:  # 註冊成功
                    data = response.json()
                    self.print_success(f"註冊成功！使用者: {email} ({data.get('username', username)})")

                    # 註冊成功後自動登入取得 token
                    self.print_info("正在自動登入...")
                    return await self.login(email, password)
                else:
                    self.print_error(f"註冊失敗: {response.text}")
                    return False
        except Exception as e:
            self.print_error(f"註冊錯誤: {e}")
            return False

    async def login(self, email: str, password: str) -> bool:
        """登入"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/auth/login",
                    json={"email": email, "password": password}
                )

                if response.status_code == 200:
                    data = response.json()
                    self.token = data["access_token"]
                    self.print_success(f"登入成功！使用者: {email}")
                    return True
                else:
                    self.print_error(f"登入失敗: {response.text}")
                    return False
        except Exception as e:
            self.print_error(f"登入錯誤: {e}")
            return False

    async def create_project(
        self,
        name: str,
        repo_url: str,
        branch: str = "main",
        init_prompt: str = "請分析此專案並提供重構建議"
    ) -> Optional[str]:
        """建立新專案"""
        if not self.token:
            self.print_error("請先登入！")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/projects",
                    json={
                        "repo_url": repo_url,
                        "branch": branch,
                        "init_prompt": init_prompt
                    },
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                if response.status_code == 201:
                    data = response.json()
                    project_id = data["id"]
                    self.current_project_id = project_id
                    self.print_success(f"專案建立成功！ID: {project_id}")
                    self.print_info(f"名稱: {name}")
                    self.print_info(f"Repository: {repo_url}")
                    self.print_info(f"Branch: {branch}")
                    return project_id
                else:
                    self.print_error(f"建立專案失敗: {response.text}")
                    return None
        except Exception as e:
            self.print_error(f"建立專案錯誤: {e}")
            return None

    async def list_projects(self) -> list:
        """列出所有專案"""
        if not self.token:
            self.print_error("請先登入！")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base_url}/api/v1/projects",
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                if response.status_code == 200:
                    data = response.json()
                    # API 返回的是 "projects" 不是 "items"
                    projects = data.get("projects", data.get("items", []))

                    if not projects:
                        self.print_info("目前沒有專案")
                        return []

                    self.print_header(f"專案列表 (共 {data.get('total', len(projects))} 個)")
                    for i, proj in enumerate(projects, 1):
                        repo_url = proj.get('repo_url', 'Unknown')
                        repo_name = self.extract_repo_name(repo_url)

                        print(f"{i}. [{proj['id'][:8]}] {repo_name}")
                        print(f"   狀態: {proj['status']}")
                        print(f"   Repository: {repo_url}")
                        print()

                    return projects
                else:
                    self.print_error(f"列出專案失敗: {response.text}")
                    return []
        except Exception as e:
            self.print_error(f"列出專案錯誤: {e}")
            return []

    async def provision_project(self, project_id: str, dev_mode: Optional[bool] = None) -> bool:
        """Provision 專案"""
        if not self.token:
            self.print_error("請先登入！")
            return False

        try:
            params = {}
            if dev_mode is not None:
                params["dev_mode"] = dev_mode

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/projects/{project_id}/provision",
                    params=params,
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                if response.status_code == 200:
                    data = response.json()
                    self.print_success(f"Provision 成功！")
                    self.print_info(f"Container ID: {data.get('container_id', 'N/A')}")
                    self.print_info(f"狀態: {data.get('status', 'N/A')}")
                    return True
                else:
                    self.print_error(f"Provision 失敗: {response.text}")
                    return False
        except Exception as e:
            self.print_error(f"Provision 錯誤: {e}")
            return False

    async def run_agent(self, project_id: str) -> Optional[str]:
        """執行 Agent"""
        if not self.token:
            self.print_error("請先登入！")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/projects/{project_id}/agent/run",
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                if response.status_code == 200:
                    data = response.json()
                    # API 返回的是 "run_id" 不是 "task_id"
                    run_id = data.get("run_id", data.get("task_id"))
                    self.print_success(f"Agent 已啟動！")
                    self.print_info(f"Run ID: {run_id}")
                    self.print_info(f"狀態: {data.get('status', 'RUNNING')}")
                    return run_id
                else:
                    self.print_error(f"啟動 Agent 失敗: {response.text}")
                    return None
        except Exception as e:
            self.print_error(f"啟動 Agent 錯誤: {e}")
            return None

    async def stream_logs(self, project_id: str, run_id: str):
        """串流 Agent 執行日誌"""
        if not self.token:
            self.print_error("請先登入！")
            return

        stream_completed = False
        try:
            self.print_header(f"開始串流日誌 (Run ID: {run_id[:8]}...)")
            self.print_info("按 Ctrl+C 停止串流\n")

            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET",
                    f"{self.api_base_url}/api/v1/projects/{project_id}/agent/runs/{run_id}/stream",
                    headers={"Authorization": f"Bearer {self.token}"}
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            # 解析 SSE 格式
                            if line.startswith("data: "):
                                data = line[6:]  # 移除 "data: " 前綴
                                try:
                                    # 嘗試解析 JSON
                                    json_data = json.loads(data)
                                    timestamp = json_data.get("timestamp", "")
                                    message = json_data.get("message", data)
                                    print(f"[{timestamp}] {message}")
                                except json.JSONDecodeError:
                                    # 不是 JSON，直接顯示
                                    print(data)
                            elif line.startswith("event: "):
                                event_type = line[7:]
                                if event_type != "ping":
                                    print(f"[事件] {event_type}")

            stream_completed = True
            self.print_success("\n日誌串流結束")

        except KeyboardInterrupt:
            self.print_info("\n使用者中斷串流")
            return
        except httpx.RemoteProtocolError as e:
            # 連線被關閉（可能是正常完成）
            self.print_info("\n連線已關閉，檢查執行狀態...")
            stream_completed = True
        except Exception as e:
            self.print_error(f"\n串流日誌錯誤: {e}")
            stream_completed = True

        # 串流結束後，查詢最終狀態
        if stream_completed:
            print()  # 空行
            await self._check_final_status(project_id, run_id)

    async def _check_final_status(self, project_id: str, run_id: str):
        """檢查 Agent 執行的最終狀態"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/v1/projects/{project_id}/agent/runs/{run_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "unknown")

                    # 根據狀態顯示不同訊息
                    if status == "SUCCESS":
                        self.print_success(f"✅ Agent 執行成功！")

                        # 提示可用的 artifacts
                        artifacts_path = data.get("artifacts_path")
                        if artifacts_path:
                            self.print_info(f"📁 Artifacts 路徑: {artifacts_path}")
                            self.print_info("💡 可使用 Docker 指令查看或下載檔案：")
                            print(f"   docker exec refactor-project-{project_id} ls {artifacts_path}")

                    elif status == "FAILED":
                        self.print_error(f"❌ Agent 執行失敗")
                        error_msg = data.get("error_message")
                        if error_msg:
                            self.print_error(f"錯誤訊息: {error_msg}")

                    elif status in ["RUNNING", "PENDING"]:
                        self.print_info(f"ℹ️  Agent 仍在執行中（狀態: {status}）")

                    else:
                        self.print_info(f"ℹ️  Agent 狀態: {status}")

                else:
                    self.print_warning(f"無法查詢狀態（HTTP {response.status_code}）")

        except Exception as e:
            self.print_warning(f"查詢最終狀態失敗: {e}")

    async def get_agent_status(self, project_id: str, run_id: str):
        """查詢 Agent 執行狀態"""
        if not self.token:
            self.print_error("請先登入！")
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base_url}/api/v1/projects/{project_id}/agent/runs/{run_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )

                if response.status_code == 200:
                    data = response.json()
                    self.print_header(f"Agent 狀態 (Run ID: {run_id[:8]}...)")
                    print(f"狀態: {data['status']}")
                    print(f"建立時間: {data.get('created_at', 'N/A')}")
                    print(f"開始時間: {data.get('started_at', 'N/A')}")
                    print(f"結束時間: {data.get('finished_at', 'N/A')}")
                    if data.get('error_message'):
                        print(f"錯誤訊息: {data['error_message']}")
                else:
                    self.print_error(f"查詢狀態失敗: {response.text}")
        except Exception as e:
            self.print_error(f"查詢狀態錯誤: {e}")


async def show_main_menu(cli: RefactorCLI):
    """顯示主選單"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                    主選單                                 ║")
    print("╠═══════════════════════════════════════════════════════════╣")
    print("║  專案管理                                                 ║")
    print("║    1. 📋 列出所有專案                                     ║")
    print("║    2. ➕ 建立新專案                                       ║")
    print("║    3. 🗑️  刪除專案                                        ║")
    print("║                                                           ║")
    print("║  容器管理                                                 ║")
    print("║    4. 🚀 Provision 專案（建立容器）                       ║")
    print("║    5. ⏹️  停止專案容器                                    ║")
    print("║                                                           ║")
    print("║  Agent 執行                                               ║")
    print("║    6. 🤖 執行 AI Agent                                    ║")
    print("║    7. 📊 串流日誌                                         ║")
    print("║    8. 📈 查詢 Agent 狀態                                  ║")
    print("║                                                           ║")
    print("║    0. 👋 登出/退出                                        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()


async def handle_list_projects(cli: RefactorCLI):
    """處理列出專案"""
    projects = await cli.list_projects()
    if projects:
        choice = input("\n選擇專案編號（設為當前專案）或按 Enter 返回: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(projects):
            selected_proj = projects[int(choice) - 1]
            cli.current_project_id = selected_proj["id"]
            repo_name = cli.extract_repo_name(selected_proj.get('repo_url', 'Unknown'))
            cli.print_success(f"已設定當前專案: {repo_name} (ID: {cli.current_project_id[:8]}...)")


async def handle_delete_project(cli: RefactorCLI):
    """處理刪除專案"""
    projects = await cli.list_projects()
    if not projects:
        return

    choice = input("\n請選擇要刪除的專案編號（或按 Enter 取消）: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(projects)):
        cli.print_info("已取消")
        return

    project = projects[int(choice) - 1]
    project_id = project["id"]
    repo_name = cli.extract_repo_name(project.get('repo_url', 'Unknown'))

    confirm = input(f"⚠️  確定要刪除專案 '{repo_name}' (ID: {project_id[:8]}...) 嗎？(yes/no): ").strip().lower()
    if confirm != "yes":
        cli.print_info("已取消刪除")
        return

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{cli.api_base_url}/api/v1/projects/{project_id}",
                headers={"Authorization": f"Bearer {cli.token}"}
            )

            if response.status_code == 200:
                cli.print_success(f"專案已刪除: {repo_name}")
                if cli.current_project_id == project_id:
                    cli.current_project_id = None
            else:
                error_msg = response.text if response.text else f"HTTP {response.status_code}"
                cli.print_error(f"刪除失敗: {error_msg}")
    except Exception as e:
        cli.print_error(f"刪除錯誤: {e}")


async def handle_stop_project(cli: RefactorCLI):
    """處理停止專案"""
    if not cli.current_project_id:
        cli.print_error("請先選擇專案（功能 1）")
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{cli.api_base_url}/api/v1/projects/{cli.current_project_id}/stop",
                headers={"Authorization": f"Bearer {cli.token}"}
            )

            if response.status_code == 200:
                cli.print_success("專案容器已停止")
            else:
                cli.print_error(f"停止失敗: {response.text}")
    except Exception as e:
        cli.print_error(f"停止錯誤: {e}")


async def handle_stream_logs(cli: RefactorCLI):
    """處理串流日誌"""
    if not cli.current_project_id:
        cli.print_error("請先選擇專案（功能 1）")
        return

    run_id = input("請輸入 Run ID（或按 Enter 使用最新的）: ").strip()

    if not run_id:
        # 取得最新的 run_id
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{cli.api_base_url}/api/v1/projects/{cli.current_project_id}/agent/runs",
                    headers={"Authorization": f"Bearer {cli.token}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    # API 返回格式: {"total": n, "runs": [...]}
                    runs = data.get("runs", data.get("items", []))

                    if runs and len(runs) > 0:
                        # 取第一個 run 的 ID
                        first_run = runs[0]
                        run_id = first_run.get("id", first_run.get("run_id", first_run.get("task_id")))

                        if run_id:
                            cli.print_info(f"使用最新 Run ID: {run_id[:8]}...")
                        else:
                            cli.print_error("無法取得 Run ID（Run 記錄中缺少 ID）")
                            cli.print_info(f"Run 資料: {first_run}")
                            return
                    else:
                        cli.print_error("沒有找到任何 Agent Run")
                        cli.print_info("請先使用功能 6 執行 Agent")
                        return
                else:
                    cli.print_error(f"取得 Run 列表失敗: HTTP {response.status_code}")
                    return
        except Exception as e:
            cli.print_error(f"取得 Run 列表失敗: {e}")
            return

    await cli.stream_logs(cli.current_project_id, run_id)


async def handle_agent_status(cli: RefactorCLI):
    """處理查詢 Agent 狀態"""
    if not cli.current_project_id:
        cli.print_error("請先選擇專案（功能 1）")
        return

    run_id = input("請輸入 Run ID: ").strip()
    if not run_id:
        cli.print_error("Run ID 不可為空")
        return

    await cli.get_agent_status(cli.current_project_id, run_id)


async def interactive_mode():
    """互動模式"""
    cli = RefactorCLI()

    # 預設測試帳號
    DEFAULT_EMAIL = "test@example.com"
    DEFAULT_PASSWORD = "testpass123"

    print("""
╔══════════════════════════════════════════════════════════╗
║     AI 舊程式碼智能重構系統 - CLI 工具                  ║
╚══════════════════════════════════════════════════════════╝
    """)

    # 1. 登入或註冊
    while not cli.token:
        cli.print_header("步驟 1: 登入/註冊")
        cli.print_info(f"預設測試帳號: {DEFAULT_EMAIL} / {DEFAULT_PASSWORD}")
        action = input("請選擇 (1=登入, 2=註冊, d=使用預設帳號登入, Enter=使用預設帳號登入): ").strip()

        # 預設選項或使用預設帳號
        if action == "" or action.lower() == "d":
            email = DEFAULT_EMAIL
            password = DEFAULT_PASSWORD
            cli.print_info(f"使用預設帳號: {email}")
            # 嘗試登入，失敗則自動註冊
            success = await cli.login(email, password)
            if not success:
                cli.print_info("預設帳號不存在，自動註冊...")
                success = await cli.register(email, password)
        else:
            email = input("Email (Enter=使用預設): ").strip() or DEFAULT_EMAIL
            password = input("Password (Enter=使用預設): ").strip() or DEFAULT_PASSWORD

            if action == "1":
                success = await cli.login(email, password)
            elif action == "2":
                success = await cli.register(email, password)
            else:
                cli.print_error("無效選項")
                continue

        if not success:
            retry = input("\n是否重試？(y/n): ").strip().lower()
            if retry != "y":
                return

    # 2. 主選單循環
    while True:
        await show_main_menu(cli)

        # 顯示當前專案
        if cli.current_project_id:
            cli.print_info(f"當前專案: {cli.current_project_id[:8]}...")
        else:
            cli.print_info("當前專案: 未選擇")

        choice = input("請選擇功能 (0-8): ").strip()

        try:
            if choice == "0":
                cli.print_success("感謝使用！再見 👋")
                break
            elif choice == "1":
                await handle_list_projects(cli)
            elif choice == "2":
                project_id = await create_new_project(cli)
                if project_id:
                    cli.current_project_id = project_id
            elif choice == "3":
                await handle_delete_project(cli)
            elif choice == "4":
                if not cli.current_project_id:
                    cli.print_error("請先選擇專案（功能 1）")
                else:
                    await cli.provision_project(cli.current_project_id, dev_mode=None)
            elif choice == "5":
                await handle_stop_project(cli)
            elif choice == "6":
                if not cli.current_project_id:
                    cli.print_error("請先選擇專案（功能 1）")
                else:
                    run_id = await cli.run_agent(cli.current_project_id)
                    if run_id:
                        cli.print_info("💡 可使用功能 7 串流日誌")
            elif choice == "7":
                await handle_stream_logs(cli)
            elif choice == "8":
                await handle_agent_status(cli)
            else:
                cli.print_error("無效選項，請輸入 0-8")
        except KeyboardInterrupt:
            print("\n")
            cli.print_info("操作已中斷")
            continue
        except Exception as e:
            cli.print_error(f"發生錯誤: {e}")

        # 暫停一下，讓使用者看到結果
        if choice != "0":
            input("\n按 Enter 繼續...")


async def create_new_project(cli: RefactorCLI) -> Optional[str]:
    """建立新專案的互動流程"""
    cli.print_header("建立新專案")

    # 預設測試專案
    DEFAULT_NAME = "測試專案"
    DEFAULT_REPO = "https://github.com/octocat/Hello-World.git"
    DEFAULT_BRANCH = "main"
    DEFAULT_PROMPT = "分析此專案並生成重構計劃，請專注在 /Python 的資料夾，我想要把裡面的python 轉成 go lang，並存入 ./memory/plan.md 檔案，不需要使用者確認後就直接執行所有的計劃，把它完整重構完成"

    cli.print_info(f"預設測試 Repository: {DEFAULT_REPO}")
    use_default = input("是否使用預設測試專案？(Enter=是, n=自訂): ").strip().lower()

    if use_default == "" or use_default == "y":
        name = DEFAULT_NAME
        repo_url = DEFAULT_REPO
        branch = DEFAULT_BRANCH
        init_prompt = DEFAULT_PROMPT
        cli.print_success(f"使用預設專案: {name}")
    else:
        name = input("專案名稱: ").strip()
        repo_url = input("Repository URL: ").strip()
        branch = input("Branch (預設 main): ").strip() or "main"
        init_prompt = input("初始提示詞 (Enter=使用預設): ").strip() or DEFAULT_PROMPT

    return await cli.create_project(name, repo_url, branch, init_prompt)


def main():
    """主程式"""
    try:
        asyncio.run(interactive_mode())
    except KeyboardInterrupt:
        print("\n\n👋 感謝使用！")
    except Exception as e:
        print(f"\n❌ 程式錯誤: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
