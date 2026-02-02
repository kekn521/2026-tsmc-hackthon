"""認證相關路由"""
from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse
)
from ..services.auth_service import AuthService
from ..dependencies.auth import get_auth_service, get_current_user
from ..models.user import User


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用戶註冊

    建立新用戶帳號。Email 必須唯一。
    """
    try:
        user = await auth_service.create_user(
            email=request.email,
            username=request.username,
            password=request.password
        )

        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用戶登入

    驗證 username 和密碼，返回 JWT access token。
    """
    user = await auth_service.authenticate_user(
        username=request.username,
        password=request.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成 token
    access_token, expires_in = auth_service.create_access_token(
        user_id=user.id,
        email=user.email
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    取得當前用戶資訊

    需要在 Authorization Header 中提供有效的 Bearer Token。
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
