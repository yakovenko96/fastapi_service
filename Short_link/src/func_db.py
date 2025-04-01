from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import User, ShortLink


async def get_user(db: AsyncSession, username: str):
    """Функция получения пользователя из базы"""
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()


async def create_user(db: AsyncSession, username: str, hashed_password: str):
    """Функция создания пользователя в базе"""
    db_user = User(username=username, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def create_short_link(db: AsyncSession, short: str,
                            original: str, id_user: Optional[int],
                            expires_at: Optional[datetime]):
    """Функция создания сокращенной ссылки в базе"""
    db_short_link = ShortLink(short=short, original=original, id_user=id_user, expires_at=expires_at)
    db.add(db_short_link)
    await db.commit()
    await db.refresh(db_short_link)
    return db_short_link


async def get_short_links(db: AsyncSession, id_user: int):
    """Функция получения всех сокращенных ссылок пользователя"""
    return await db.execute(select(ShortLink).filter(ShortLink.id_user == id_user).all())


async def get_short_link_stats(db: AsyncSession, short_code: str):
    """Получение статистики по сокращенной ссылке."""
    short_link = await db.execute(select(ShortLink).filter(ShortLink.short == short_code))
    short_link = short_link.first()
    if short_link:
        return {
            "short_code": short_link.short,
            "original_url": short_link.original,
            "view": short_link.view
        }
    return None


async def delete_all_short_links(db: AsyncSession, id_user: int):
    """Удаление всех сокращенных ссылок пользователя."""
    await db.execute(select(ShortLink).filter(ShortLink.id_user == id_user).delete())
    await db.commit()
