import random
import string
from typing import Optional
import json
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from redis.asyncio import Redis
from src.database import get_db
from src.models import User as UserModel, ShortLink as ShortLinkModel
from src.func_db import create_user, get_user, create_short_link

from src.auth.auth import (get_password_hash,
                           verify_password,
                           create_access_token,
                           get_current_user,
                           get_current_user_opt)

from src.links.schemas import (CreateShortRequest,
                               CreateShortResponse,
                               SearchResponse,
                               UpdateResponse,
                               DeleteResponse,
                               User)

router = APIRouter(prefix='/links', tags=["links"])
redis = Redis(host='redis', port=6379, db=0)
TIME_CASH = 10


async def generate_short_code(length: int = 6) -> str:
    """Функция для генерации сокращенных ссылок"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# API endpoints
@router.post("/register", response_model=User)
async def register_user(username: str, password: str, db: AsyncSession = Depends(get_db)):
    """Функция регистрации"""
    user = await get_user(db, username)
    if user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    hashed_password = await get_password_hash(password)
    user = await create_user(db, username, hashed_password)
    return user


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Функция авторизации"""
    user = await get_user(db, form_data.username)
    if not user or not await verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")
    access_token = await create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/shorten", status_code=status.HTTP_201_CREATED, response_model=CreateShortResponse)
async def create_short_code(url_request: CreateShortRequest,
                            db: AsyncSession = Depends(get_db),
                            current_user: Optional[UserModel] = Depends(get_current_user_opt)):
    """Функция для создания сокращенных ссылок для пользователя"""
    print('create_short_code')
    original_url = url_request.original_url
    custom_alias = url_request.custom_alias
    expires_at = url_request.expires_at

    user_id = current_user.id_user if current_user else None

    if custom_alias:
        exe_short_link = await db.execute(select(ShortLinkModel).filter(
            ShortLinkModel.short == custom_alias,
            (ShortLinkModel.id_user == user_id) | (ShortLinkModel.id_user.is_(None))))
        if exe_short_link.scalars().first():
            raise HTTPException(status_code=400, detail="Такая ссылка уже используется")
        short_link = await create_short_link(db,
                                             short=custom_alias,
                                             original=original_url,
                                             id_user=user_id,
                                             expires_at=expires_at)
        return CreateShortResponse(short_code=short_link.short, original_url=original_url)

    short_code = await generate_short_code()
    while True:
        existing_short_link = await db.execute(select(ShortLinkModel).filter(ShortLinkModel.short == short_code))
        if not existing_short_link.scalars().first():
            break
        short_code = await generate_short_code()

    short_link = await create_short_link(db, short=short_code,
                                         original=original_url,
                                         id_user=user_id, expires_at=expires_at)
    return CreateShortResponse(short_code=short_link.short, original_url=original_url)


@router.get("/search", response_model=SearchResponse)
async def search_short_code(original_url: str, db: AsyncSession = Depends(get_db)):
    """Функция для поиска сокращенных ссылок пользователя"""
    short_links_found = await db.execute(select(ShortLinkModel).filter(ShortLinkModel.original == original_url))
    short_links_found = short_links_found.scalars().all()
    if short_links_found:
        return SearchResponse(short_codes=[short.short for short in short_links_found])
    raise HTTPException(status_code=404, detail="Такой ссылки не существует")


@router.get("/my_links", response_model=SearchResponse)
async def get_my_links(db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    """Функция для получения всех сокращенных ссылок пользователя"""
    short_links_found = await db.execute(select(ShortLinkModel).filter(ShortLinkModel.id_user == current_user.id_user))
    short_links_found = short_links_found.scalars().all()
    if short_links_found:
        return SearchResponse(short_codes=[short.short for short in short_links_found])
    return SearchResponse(short_codes=[])


@router.delete("/my_links", response_model=DeleteResponse)
async def delete_all_my_links(db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    """Функция для удаления всех сокращенных ссылок пользователя"""
    all_short_links = delete(ShortLinkModel).where(ShortLinkModel.id_user == current_user.id_user)
    await db.execute(all_short_links)
    await db.commit()
    return DeleteResponse(message="Все ваши сокращенные ссылки удалены")


@router.get("/{short_code}/stats")
async def get_short_link_stats(short_code: str,
                               db: AsyncSession = Depends(get_db),
                               current_user: UserModel = Depends(get_current_user)):
    """Функция для получения статистики по сокращенной ссылке"""
    short_link = await db.execute(select(ShortLinkModel).filter(ShortLinkModel.short == short_code))
    short_link = short_link.scalars().first()
    if short_link:
        return {"short_code": short_code, "original_url": short_link.original, "view": short_link.view}
    raise HTTPException(status_code=404, detail="Такой ссылки не существует")


@router.get("/{short_code}")
async def redirect_to_url(short_code: str, db: AsyncSession = Depends(get_db)):
    """Функция для перенаправления с короткой ссылки на оригинальную"""
    cached_link = await redis.get(short_code)
    if cached_link:
        short_link = json.loads(cached_link)
        return RedirectResponse(short_link['original'])
    else:
        short_link = await db.execute(select(ShortLinkModel).filter(ShortLinkModel.short == short_code))
        short_link = short_link.scalars().first()
        if short_link:
            short_link.view += 1
            short_link_dict = {
                'short': short_link.short,
                'original': short_link.original,
            }
            await redis.set(short_code, json.dumps(short_link_dict), ex=TIME_CASH)
            await db.commit()
            return RedirectResponse(short_link.original)
        raise HTTPException(status_code=404, detail="Такой ссылки не существует")


# pylint: disable=unused-argument
@router.put("/{short_code}", response_model=UpdateResponse)
async def update_short_code(short_code_old: str,
                            db: AsyncSession = Depends(get_db),
                            current_user: UserModel = Depends(get_current_user)):
    """Функция для пересоздания сокращенной ссылки, доступная только зарегистрированным пользователям"""
    short_link = await db.execute(select(ShortLinkModel).filter(ShortLinkModel.short == short_code_old,
                                                                ShortLinkModel.id_user == current_user.id_user))
    if not short_link:
        raise HTTPException(status_code=404, detail="Такой ссылки не существует")
    short_link = short_link.scalars().first()
    await db.delete(short_link)
    await db.commit()
    short_code = await generate_short_code()
    while True:
        existing_short_link = await db.execute(select(ShortLinkModel).filter(ShortLinkModel.short == short_code))
        if not existing_short_link.scalars().first():
            break
        short_code = await generate_short_code()
    new_short_link = ShortLinkModel(short=short_code, original=short_link.original, id_user=current_user.id_user)
    db.add(new_short_link)
    await db.commit()
    await db.refresh(new_short_link)
    return UpdateResponse(short_code=new_short_link.short, original_url=new_short_link.original)


@router.delete("/{short_code}", response_model=DeleteResponse)
async def delete_short_code(short_code: str,
                            db: AsyncSession = Depends(get_db),
                            current_user: UserModel = Depends(get_current_user)):
    """Функция для удаления сокращенной ссылки, доступная только зарегистрированным пользователям"""
    short_link = await db.execute(select(ShortLinkModel).filter(ShortLinkModel.short == short_code,
                                                                ShortLinkModel.id_user == current_user.id_user))
    short_link = short_link.scalars().first()
    if short_link:
        await db.delete(short_link)
        await db.commit()
        return DeleteResponse(message=f"{short_code} удален")
    raise HTTPException(status_code=404, detail="Такой ссылки не существует")
