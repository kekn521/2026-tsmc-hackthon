"""Container AI Server - HTTP interface for CloudRun (Async Task Pattern)"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
import logging
import uuid
import traceback

from agent.models import AnthropicModelProvider
from agent.deep_agent import RefactorAgent

app = FastAPI(title="AI Server", version="1.0.0")
logger = logging.getLogger(__name__)

# 任務狀態枚舉
class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

# 內存任務儲存（單容器內有效）
tasks: Dict[str, Dict] = {}

# 日誌儲存（用於 stream）
task_logs: Dict[str, list] = {}

class RunRequest(BaseModel):
    init_prompt: str
    verbose: bool = True

class CloneRequest(BaseModel):
    repo_url: str
    branch: str = "main"

class RunResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None


def log_task(task_id: str, message: str):
    """記錄任務日誌（用於 stream）"""
    if task_id not in task_logs:
        task_logs[task_id] = []
    timestamp = datetime.utcnow().isoformat()
    task_logs[task_id].append({"timestamp": timestamp, "message": message})
    logger.info(f"[{task_id}] {message}")


def execute_agent(task_id: str, init_prompt: str, verbose: bool):
    """背景執行 Agent（在 BackgroundTasks 中執行）"""
    try:
        # 初始化日誌
        task_logs[task_id] = []

        # 更新狀態為 RUNNING
        tasks[task_id]["status"] = TaskStatus.RUNNING
        tasks[task_id]["started_at"] = datetime.utcnow().isoformat()
        log_task(task_id, "開始執行 Agent")

        # 初始化 LLM
        log_task(task_id, "初始化 LLM...")
        provider = AnthropicModelProvider()
        model = provider.get_model()

        # 建立並執行 RefactorAgent
        log_task(task_id, "建立 RefactorAgent...")
        agent = RefactorAgent(model, verbose=verbose)

        log_task(task_id, f"執行 Agent，init_prompt: {init_prompt[:100]}...")
        agent.run(user_message=init_prompt)

        # 標記完成
        tasks[task_id]["status"] = TaskStatus.SUCCESS
        tasks[task_id]["finished_at"] = datetime.utcnow().isoformat()
        log_task(task_id, "Agent 執行完成")

    except Exception as e:
        error_msg = f"Agent execution failed: {str(e)}"
        log_task(task_id, f"錯誤: {error_msg}")
        logger.error(f"[{task_id}] {error_msg}\n{traceback.format_exc()}")
        tasks[task_id]["status"] = TaskStatus.FAILED
        tasks[task_id]["error_message"] = error_msg
        tasks[task_id]["finished_at"] = datetime.utcnow().isoformat()


@app.post("/run", response_model=RunResponse)
async def run_agent(request: RunRequest, background_tasks: BackgroundTasks):
    """啟動 Agent 執行（異步模式）

    立即返回 task_id，Agent 在背景執行。
    使用 GET /tasks/{task_id} 查詢執行狀態。
    """
    # 生成唯一 task_id
    task_id = str(uuid.uuid4())

    # 建立任務記錄
    tasks[task_id] = {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "init_prompt": request.init_prompt,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "finished_at": None,
        "error_message": None,
    }

    # 啟動背景任務
    background_tasks.add_task(
        execute_agent,
        task_id=task_id,
        init_prompt=request.init_prompt,
        verbose=request.verbose
    )

    logger.info(f"[{task_id}] 任務已建立，開始背景執行")

    return RunResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Agent 任務已啟動，正在背景執行"
    )


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """查詢任務執行狀態"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    return TaskStatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        created_at=task["created_at"],
        started_at=task.get("started_at"),
        finished_at=task.get("finished_at"),
        error_message=task.get("error_message"),
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/tasks")
async def list_tasks():
    """列出所有任務（調試用）"""
    return {"total": len(tasks), "tasks": list(tasks.values())}


# @app.post("/clone")
# async def clone_repo(request: CloneRequest):
#     """在容器內 clone Git repo"""
#     import subprocess
#     try:
#         log_message = f"開始 clone {request.repo_url} (branch: {request.branch})"
#         logger.info(log_message)

#         # 清空並 clone repo
#         subprocess.run(["rm", "-rf", "/workspace/repo"], check=True)
#         subprocess.run(["mkdir", "-p", "/workspace/repo"], check=True)
#         subprocess.run([
#             "git", "clone",
#             "-b", request.branch,
#             "--depth", "1",
#             request.repo_url,
#             "/workspace/repo"
#         ], check=True, capture_output=True, text=True)

#         logger.info(f"Successfully cloned {request.repo_url}")
#         return {"status": "success", "message": "Repository cloned successfully"}
#     except subprocess.CalledProcessError as e:
#         error_msg = f"Git clone failed: {e.stderr}"
#         logger.error(error_msg)
#         raise HTTPException(status_code=500, detail=error_msg)


@app.get("/tasks/{task_id}/stream")
async def stream_task_logs(task_id: str):
    """SSE 串流任務執行日誌"""
    from sse_starlette.sse import EventSourceResponse
    import asyncio

    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        """生成 SSE events"""
        last_index = 0

        while True:
            # 檢查任務狀態
            task = tasks.get(task_id)
            if not task:
                break

            # 發送新日誌
            if task_id in task_logs:
                current_logs = task_logs[task_id]
                new_logs = current_logs[last_index:]

                for log in new_logs:
                    yield {
                        "event": "log",
                        "data": f"{log['timestamp']} {log['message']}"
                    }
                last_index = len(current_logs)

            # 如果任務完成，發送完成事件並結束
            if task["status"] in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                yield {
                    "event": "status",
                    "data": f"Task {task['status'].lower()}"
                }
                break

            await asyncio.sleep(1)  # 每秒檢查一次

    return EventSourceResponse(event_generator())
