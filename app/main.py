from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import delete
from app.database import get_db
from app.site_data import router as site_data_router
from app.errors import Duplicate, InUse, NotFound, ServerError, Unauthorized
from app import models, schemas
from app.auth import verifyPwd, generateToken, getCurrentUser
import os
from datetime import datetime, timezone
from app.content import (
    router as content_router,
    logActivity,
    saveProject,
    projectResponse,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(content_router)
app.include_router(site_data_router)


def verifyUsr(payload: schemas.LoginRequest, db: Session) -> models.User | None:
    user = (
        db.query(models.User).filter(models.User.username == payload.username).first()
    )
    if not user or not verifyPwd(payload.password, user.hashed_password):
        return None
    return user


@app.post("/me")
def me(user: models.User = Depends(getCurrentUser)):
    return {"username": user.username}


@app.post("/login")
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = verifyUsr(payload, db)
    if not user:
        raise Unauthorized("Invalid email or password")
    else:
        try:
            user.last_login_at = datetime.now(timezone.utc)
            db.commit()
            token = generateToken(data={"sub": user.username})
            return {"access_token": token, "token_type": "bearer"}
        except SQLAlchemyError:
            db.rollback()
            raise ServerError("Could not complete login")


@app.post("/get-param")
def GetParam(
    payload: schemas.ParamRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    param_rows = (
        db.query(models.PrmSetup)
        .filter(models.PrmSetup.locate_at == payload.paramType)
        .all()
    )
    return {row.param_id: row.value for row in param_rows}


@app.post("/get-activity-logs")
def GetActivityLogs(
    payload: schemas.ActivityLogsReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    logs_rows = (
        db.query(models.ActivityLogs)
        .join(models.User, models.User.id == models.ActivityLogs.user_id)
        .filter(models.User.username == payload.username)
        .order_by(models.ActivityLogs.created_at.desc())
        .all()
    )
    return [
        {
            "action": row.action_name,
            "details": row.details,
            "created_at": row.created_at,
        }
        for row in logs_rows
    ]


# Project API
def checkExistedPrjRecord(company_id, purpose_id, project_name, db: Session):
    if not company_id or not purpose_id or not project_name:
        return False
    else:
        return (
            db.query(models.Project)
            .filter(
                models.Project.company_id == company_id,
                models.Project.purpose_id == purpose_id,
                models.Project.project_name == project_name,
            )
            .first()
            is not None
        )


# Project sub API get company listing
@app.get("/get-company-list")
def GetCompanyList(
    db: Session = Depends(get_db), user: models.User = Depends(getCurrentUser)
):
    logs_rows = db.query(models.CompanyGrp).all()
    if logs_rows:
        return [{"id": row.id, "name": row.name} for row in logs_rows]
    else:
        return []


@app.post("/add-company")
def AddCompany(
    payload: schemas.AddCompanyPurposeList,
    db: Session = Depends(get_db),
    _user: models.User = Depends(getCurrentUser),
):
    isExisted = (
        db.query(models.CompanyGrp)
        .filter(models.CompanyGrp.name == payload.companyName)
        .first()
    )
    if isExisted:
        raise Duplicate()

    try:
        new_company = models.CompanyGrp(name=payload.companyName)
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
    except SQLAlchemyError:
        db.rollback()
        raise ServerError("Could not add company")
    return {"id": new_company.id, "name": new_company.name}


@app.post("/delete-company")
def DeleteCompany(
    payload: schemas.DelCompanyPurposeList,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    if db.query(models.Project).filter(models.Project.company_id == payload.id).first():
        raise InUse("Company")
    try:
        filterReq = (models.CompanyGrp.name == payload.name) & (
            models.CompanyGrp.id == payload.id
        )
        result = db.execute(delete(models.CompanyGrp).where(filterReq))
        if result.rowcount == 0:
            db.rollback()
            raise NotFound("Company")
        db.commit()
        return {"message": "Company deleted"}
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise ServerError("Could not delete company")


# Project sub API get purpose listing
@app.get("/get-purpose-list")
def GetPurposeList(
    db: Session = Depends(get_db), user: models.User = Depends(getCurrentUser)
):
    rows = db.query(models.PurposeGrp).all()
    return [{"id": row.id, "name": row.name} for row in rows]


# Project Add
@app.post("/add-project")
def AddProject(
    payload: schemas.ProjectAddReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    isExisted = checkExistedPrjRecord(
        payload.company_Id, payload.purpose_Id, payload.project_name, db
    )
    if isExisted:
        raise Duplicate()
    new_project = saveProject(db, models.Project(), payload)
    logActivity(db, user, "add-project", {"name": payload.project_name})
    try:
        db.commit()
        db.refresh(new_project)
    except SQLAlchemyError:
        db.rollback()
        raise ServerError("Could not add project")
    return projectResponse(db, new_project)
