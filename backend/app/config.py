"""應用程式配置管理"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """應用程式設定"""

    # API 設定
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    debug: bool = False

    # MongoDB 設定
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "refactor_agent"

    # Docker 設定
    docker_base_image: str = "refactor-base:latest"
    docker_network: str = "refactor-network"
    docker_volume_prefix: str = "/tmp/refactor-workspaces"

    # 開發模式配置
    dev_mode: bool = False
    agent_host_path: Optional[str] = None  # 本機 agent 目錄路徑

    # 容器資源限制
    container_cpu_limit: float = 2.0
    container_memory_limit: str = "2g"

    # Git 設定
    git_clone_timeout: int = 300
    git_depth: int = 1

    # Log 設定
    log_level: str = "INFO"

    # JWT 認證設定
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_hours: int = 24

    # LLM 設定 - Anthropic (已棄用，保留以便向後相容)
    llm_provider: str = "vertex"  # "anthropic" or "vertex"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Vertex AI 設定
    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    vertex_ai_model: str = "gemini-2.5-pro"
    google_application_credentials: Optional[str] = None

    @field_validator('agent_host_path')
    @classmethod
    def validate_agent_path(cls, v: Optional[str]) -> Optional[str]:
        """驗證 agent_host_path 在 dev_mode 啟用時必須存在"""
        if not v:
            return v

        # 檢查目錄存在
        import os
        if not os.path.isdir(v):
            raise ValueError(f"AGENT_HOST_PATH 目錄不存在: {v}")

        # 檢查必要檔案
        ai_server = os.path.join(v, "ai_server.py")
        if not os.path.isfile(ai_server):
            raise ValueError(
                f"AGENT_HOST_PATH '{v}' 缺少 ai_server.py 檔案"
            )

        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全域設定實例
settings = Settings()
