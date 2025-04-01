from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from src.database import get_db
from src.func_db import get_user
from src.config import SECRET, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_EXPIRE_MINUTES = 60


async def verify_password(plain_password, hashed_password):
    """Функция проверки пароля"""
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password):
    """Функция создания хеша пароля"""
    return pwd_context.hash(password)


async def create_access_token(data: dict, expires_delta=None):
    """Функция создания токена авторизации"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """Функция проверки регистрации"""
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = await get_user(db, username)
        if user is None:
            raise credentials_exception
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc
    return user


async def get_current_user_opt(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """Функция проверки регистрации"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
        return await get_user(db, username)
    except jwt.PyJWTError:
        return None
