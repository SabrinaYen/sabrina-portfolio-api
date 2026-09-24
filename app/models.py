from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import base

class User(base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
class Setting(base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    site_name = Column(String, unique=True, nullable=False, index=True)
    tagline = Column(String, nullable=True)
    domain =  Column(String, nullable=True)
    meta_title =  Column(String, nullable=True)
    meta_desc =  Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())