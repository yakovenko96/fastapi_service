from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    short_links = relationship("ShortLink", back_populates="owner")


class ShortLink(Base):
    __tablename__ = "short_links"

    short = Column(String, primary_key=True, index=True)
    original = Column(String)
    date_create = Column(DateTime, default=datetime.now())
    id_user = Column(Integer, ForeignKey("users.id_user"))
    expires_at = Column(DateTime, nullable=True)
    view = Column(Integer, default=0)

    owner = relationship("User", back_populates="short_links")
