"""專案 API Schema"""
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional, Dict, Any
from ..models.project import ProjectStatus


class CreateProjectRequest(BaseModel):
    """建立專案請求"""

    repo_url: str = Field(..., description="Git repository URL")
    branch: str = Field(default="main", description="Git branch")
    init_prompt: str = Field(..., description="初始提示")

    class Config:
        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/user/repo.git",
                "branch": "main",
                "init_prompt": "重構專案以提升可維護性",
            }
        }


class UpdateProjectRequest(BaseModel):
    """更新專案請求"""

    repo_url: Optional[str] = None
    branch: Optional[str] = None
    init_prompt: Optional[str] = None
    status: Optional[ProjectStatus] = None
    container_id: Optional[str] = None


class ProjectResponse(BaseModel):
    """專案回應"""

    id: str = Field(..., description="專案 ID")
    repo_url: str = Field(..., description="Git repository URL")
    branch: str = Field(..., description="Git branch")
    init_prompt: str = Field(..., description="初始提示")
    status: ProjectStatus = Field(..., description="專案狀態")
    container_id: Optional[str] = Field(None, description="Docker 容器 ID")
    created_at: datetime = Field(..., description="建立時間")
    updated_at: datetime = Field(..., description="更新時間")
    last_error: Optional[str] = Field(None, description="最後錯誤訊息")
    docker_status: Optional[Dict[str, Any]] = Field(
        None, description="Docker 容器狀態（包含實時狀態和一致性檢查）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "repo_url": "https://github.com/user/repo.git",
                "branch": "main",
                "init_prompt": "重構專案以提升可維護性",
                "status": "CREATED",
                "container_id": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_error": None,
            }
        }


class ProjectListResponse(BaseModel):
    """專案列表回應"""

    total: int = Field(..., description="總數")
    projects: list[ProjectResponse] = Field(..., description="專案列表")
