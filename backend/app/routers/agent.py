"""Agent API - 代理 Container AI Server 的通訊"""
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase
from sse_starlette.sse import EventSourceResponse
import httpx
import logging

from ..database.mongodb import get_database
from ..services.project_service import ProjectService
from ..models.user import User
from ..models.project import ProjectStatus
from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["agent"])
logger = logging.getLogger(__name__)


async def get_project_service(
    db: AsyncDatabase = Depends(get_database),
) -> ProjectService:
    """依賴注入：獲取 ProjectService"""
    return ProjectService(db)


@router.post("/{project_id}/agent/run")
async def run_agent(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    """啟動 AI Agent 執行（異步模式）

    流程：
    1. 驗證專案權限和狀態（必須是 READY）
    2. 呼叫容器內的 AI Server /run endpoint
    3. 立即返回 run_id，Agent 在背景執行
    """
    # 驗證專案存在和權限
    project = await project_service.get_project_by_id(project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="專案不存在或無權限")

    if project.status != ProjectStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"專案狀態必須為 READY，目前為 {project.status}"
        )

    container_name = f"refactor-project-{project_id}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"呼叫容器 AI Server: {container_name}")
            run_response = await client.post(
                f"http://{container_name}:8000/run",
                json={
                    "init_prompt": project.init_prompt,
                    "verbose": True
                }
            )
            run_response.raise_for_status()
            result = run_response.json()

        logger.info(f"Agent 任務已啟動: project={project_id}, task_id={result['task_id']}")

        # 轉換為前端期望格式
        return {
            "run_id": result["task_id"],
            "project_id": project_id,
            "status": "RUNNING",
            "iteration_index": 0,
            "phase": "plan",
            "created_at": result.get("created_at", ""),
            "message": "Agent 任務已啟動，正在背景執行"
        }

    except httpx.HTTPError as e:
        logger.error(f"AI Server 呼叫失敗: {e}")
        raise HTTPException(status_code=503, detail=f"AI Server 錯誤: {str(e)}")


@router.get("/{project_id}/agent/runs")
async def list_agent_runs(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    """列出專案的所有 Agent Runs"""
    # 驗證專案權限
    project = await project_service.get_project_by_id(project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="專案不存在或無權限")

    container_name = f"refactor-project-{project_id}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://{container_name}:8000/tasks"
            )
            response.raise_for_status()
            tasks_data = response.json()

        # 轉換格式
        status_mapping = {
            "pending": "RUNNING",
            "running": "RUNNING",
            "success": "DONE",
            "failed": "FAILED"
        }

        runs = []
        for task in tasks_data.get("tasks", []):
            runs.append({
                "id": task["task_id"],
                "project_id": project_id,
                "iteration_index": 0,
                "phase": "plan",
                "status": status_mapping.get(task["status"], "RUNNING"),
                "created_at": task.get("created_at", ""),
                "updated_at": task.get("started_at", task.get("created_at", "")),
                "finished_at": task.get("finished_at"),
                "error_message": task.get("error_message"),
            })

        return {
            "total": len(runs),
            "runs": runs
        }

    except httpx.HTTPError as e:
        logger.error(f"查詢 Agent Runs 失敗: {e}")
        # 如果容器未啟動，返回空列表
        return {"total": 0, "runs": []}


@router.get("/{project_id}/agent/runs/{run_id}")
async def get_agent_run_detail(
    project_id: str,
    run_id: str,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    """查詢 Agent Run 詳細狀態"""
    # 驗證專案權限
    project = await project_service.get_project_by_id(project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="專案不存在或無權限")

    container_name = f"refactor-project-{project_id}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://{container_name}:8000/tasks/{run_id}"
            )
            response.raise_for_status()
            task_data = response.json()

        # 轉換 AI Server 格式到前端期望格式
        status_mapping = {
            "pending": "RUNNING",
            "running": "RUNNING",
            "success": "DONE",
            "failed": "FAILED"
        }

        return {
            "id": run_id,
            "project_id": project_id,
            "iteration_index": 0,
            "phase": "plan",
            "status": status_mapping.get(task_data["status"], "RUNNING"),
            "created_at": task_data.get("created_at", ""),
            "updated_at": task_data.get("started_at", task_data.get("created_at", "")),
            "finished_at": task_data.get("finished_at"),
            "error_message": task_data.get("error_message"),
        }

    except httpx.HTTPError as e:
        logger.error(f"查詢任務狀態失敗: {e}")
        raise HTTPException(status_code=503, detail="無法查詢任務狀態")


@router.get("/{project_id}/agent/runs/{run_id}/stream")
async def stream_agent_logs(
    project_id: str,
    run_id: str,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    """SSE 串流 Agent 執行日誌（轉發容器的 stream）"""
    # 驗證專案權限
    project = await project_service.get_project_by_id(project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="專案不存在或無權限")

    container_name = f"refactor-project-{project_id}"

    async def event_generator():
        """轉發容器的 SSE stream"""
        try:
            url = f"http://{container_name}:8000/tasks/{run_id}/stream"
            logger.info(f"🔗 開始串流 AI Server 日誌: {url}")
            print(f"🔗 [DEBUG] 開始連線到: {url}", flush=True)

            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as response:
                    logger.info(f"✅ SSE 連線已建立，狀態碼: {response.status_code}")
                    print(f"✅ [DEBUG] SSE 連線已建立，狀態碼: {response.status_code}", flush=True)

                    line_count = 0
                    async for line in response.aiter_lines():
                        if line:
                            line_count += 1
                            logger.debug(f"[SSE #{line_count}] {line}")
                            print(f"📨 [DEBUG] 收到 SSE 訊息 #{line_count}: {line[:100]}", flush=True)
                            yield line + "\n"

            logger.info(f"✅ SSE 串流正常結束: run_id={run_id}, 共 {line_count} 行")
            print(f"✅ [DEBUG] SSE 串流正常結束: {line_count} 行", flush=True)

        except httpx.HTTPError as e:
            error_msg = f"HTTP 錯誤: {str(e)}"
            logger.error(f"❌ {error_msg}")
            print(f"❌ [DEBUG] {error_msg}", flush=True)
            yield f"event: error\ndata: {error_msg}\n\n"
        except Exception as e:
            error_msg = f"Stream 轉發失敗: {str(e)}"
            logger.error(f"❌ {error_msg}")
            print(f"❌ [DEBUG] {error_msg}", flush=True)
            yield f"event: error\ndata: {error_msg}\n\n"

    return EventSourceResponse(event_generator())


@router.post("/{project_id}/agent/runs/{run_id}/stop")
async def stop_agent_run(
    project_id: str,
    run_id: str,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    """停止執行中的 Agent Run"""
    # 驗證專案權限
    project = await project_service.get_project_by_id(project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="專案不存在或無權限")

    container_name = f"refactor-project-{project_id}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{container_name}:8000/tasks/{run_id}/stop"
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"Agent Run 已停止: project={project_id}, run_id={run_id}")
        return result

    except httpx.HTTPError as e:
        logger.error(f"停止 Agent Run 失敗: {e}")
        raise HTTPException(status_code=503, detail=f"AI Server 錯誤: {str(e)}")


@router.post("/{project_id}/agent/runs/{run_id}/resume")
async def resume_agent_run(
    project_id: str,
    run_id: str,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user),
):
    """繼續執行已停止的 Agent Run

    會使用原始 init_prompt 重新啟動一個新的任務。
    """
    # 驗證專案權限
    project = await project_service.get_project_by_id(project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="專案不存在或無權限")

    container_name = f"refactor-project-{project_id}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://{container_name}:8000/tasks/{run_id}/resume"
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"Agent Run 已恢復: project={project_id}, old_run_id={run_id}, new_run_id={result['task_id']}")

        # 轉換為前端期望格式
        return {
            "run_id": result["task_id"],
            "old_run_id": result["old_task_id"],
            "project_id": project_id,
            "status": "RUNNING",
            "iteration_index": 0,
            "phase": "plan",
            "created_at": "",
            "message": "Agent 任務已恢復，正在背景執行"
        }

    except httpx.HTTPError as e:
        logger.error(f"恢復 Agent Run 失敗: {e}")
        raise HTTPException(status_code=503, detail=f"AI Server 錯誤: {str(e)}")
