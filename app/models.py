from sqlalchemy import Date, Column, ForeignKey, Integer, String, DateTime, func , Text , Boolean,UniqueConstraint,JSON
from app.database import base

class User(base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now())
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
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(), default=func.now(),
        onupdate=func.now(),
    )
    
class ActivityLogs(base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True,autoincrement=True)
    user_id = Column(Integer,ForeignKey("users.id"), nullable=False)
    action_name = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())
    
class CompanyGrp(base):
    __tablename__ = "company_grp"
    id = Column(Integer, primary_key=True,autoincrement=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now(), onupdate=func.now())   
    
class PurposeGrp(base):
    __tablename__ = "purpose_grp"
    id = Column(Integer, primary_key=True,autoincrement=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now(), onupdate=func.now())   
    
class Project(base):
     __tablename__ = "projects"
     id = Column(Integer, primary_key=True,autoincrement=True)
     company_id = Column(Integer,ForeignKey("company_grp.id"), nullable=True)
     purpose_id = Column(Integer,ForeignKey("purpose_grp.id"), nullable=True)
     project_name = Column(String(100), nullable=False)
     project_desc = Column(Text, nullable=False)
     is_link = Column(Boolean, nullable=False, default=False)
     url_link = Column(String(255), nullable=True)
     sort_order = Column(Integer, nullable=False, default=0)
     is_published = Column(Boolean, nullable=False, default=True, server_default="true")
     created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())
     updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now(), onupdate=func.now())


class Experience(base):
    __tablename__ = "experience"
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company_grp.id"), nullable=True)
    position = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_published = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now(), onupdate=func.now())


class SkillsGrp(base):
    __tablename__ = "skills_grp"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now(), onupdate=func.now())


class Skill(base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("skills_grp.id"), nullable=False)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now(), onupdate=func.now())


class ProjectSkill(base):
    __tablename__ = "project_skills"
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), primary_key=True)


class TagGrp(base):
    __tablename__ = "tag_grp"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


class ProjectTag(base):
    __tablename__ = "project_tags"
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tag_grp.id"), primary_key=True)


class ExtraText(base):
    __tablename__ = "extra_text"
    __table_args__ = (
        UniqueConstraint("entity", "entity_id", "field", "lang", name="uq_extra_text"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    field = Column(String(50), nullable=False)
    lang = Column(String(5), nullable=False, default="")
    value = Column(Text, nullable=True)
