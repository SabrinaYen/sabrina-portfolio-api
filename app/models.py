from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func , Text , Boolean,UniqueConstraint,JSON
from app.database import base

class User(base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    
class PrmSetup(base):
    __tablename__ = "prm_setup"
    __table_args__ = (
        UniqueConstraint("locate_at", "param_id", name="uq_prm_setup_locate_param"),
    )
    id = Column(Integer, primary_key=True)
    locate_at = Column(String(50), nullable=False)  
    param_id = Column(String(50), nullable=False)    
    value = Column(Text, nullable=True)             
    is_file = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    
class ActivityLogs(base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True,autoincrement=True)
    user_id = Column(Integer,ForeignKey("users.id"), nullable=False)
    action_name = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
        