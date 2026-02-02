"""認證服務"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pymongo.asynchronous.database import AsyncDatabase

from ..models.user import User
from ..config import settings


# bcrypt 加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """認證服務類"""

    def __init__(self, db: AsyncDatabase):
        self.db = db
        self.users_collection = db["users"]

    def hash_password(self, password: str) -> str:
        """使用 bcrypt 加密密碼"""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """驗證密碼"""
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: str, email: str) -> tuple[str, int]:
        """
        生成 JWT access token

        Returns:
            (token, expires_in_seconds)
        """
        expires_delta = timedelta(hours=settings.jwt_access_token_expire_hours)
        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": user_id,  # subject (用戶 ID)
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow()
        }

        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        expires_in_seconds = int(expires_delta.total_seconds())
        return token, expires_in_seconds

    def decode_token(self, token: str) -> dict:
        """
        驗證並解碼 JWT token

        Raises:
            JWTError: Token 無效或已過期
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    async def create_user(self, email: str, username: str, password: str) -> User:
        """
        建立新用戶

        Raises:
            ValueError: Email 或 Username 已存在
        """
        # 檢查 email 是否已存在
        existing_user = await self.users_collection.find_one({"email": email})
        if existing_user:
            raise ValueError("Email already registered")

        # 檢查 username 是否已存在
        existing_username = await self.users_collection.find_one({"username": username})
        if existing_username:
            raise ValueError("Username already taken")

        # 建立用戶
        password_hash = self.hash_password(password)
        user_data = {
            "email": email,
            "username": username,
            "password_hash": password_hash,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await self.users_collection.insert_one(user_data)
        user_data["_id"] = str(result.inserted_id)

        return User(**user_data)

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        驗證用戶登入（使用 username）

        Returns:
            User object if authentication successful, None otherwise
        """
        user_doc = await self.users_collection.find_one({"username": username})
        if not user_doc:
            return None

        # 轉換 _id 為字串
        user_doc["_id"] = str(user_doc["_id"])
        user = User(**user_doc)

        if not self.verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根據 ID 查詢用戶"""
        from bson import ObjectId

        try:
            user_doc = await self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user_doc:
                return None

            user_doc["_id"] = str(user_doc["_id"])
            return User(**user_doc)
        except Exception:
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根據 email 查詢用戶"""
        user_doc = await self.users_collection.find_one({"email": email})
        if not user_doc:
            return None

        user_doc["_id"] = str(user_doc["_id"])
        return User(**user_doc)
