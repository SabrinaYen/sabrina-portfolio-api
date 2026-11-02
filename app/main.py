from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import delete
from app.database import get_db
from app.site_data import router as site_data_router
from app.errors import Duplicate, InUse, NotFound, Unauthorized, commitOr500
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


@app.get("/health")
def health():
    """Used by the host to check the API is up."""
    return {"status": "ok"}


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
    user.last_login_at = datetime.now(timezone.utc)
    commitOr500(db, "Could not complete login")
    return {"access_token": generateToken(data={"sub": user.username}), "token_type": "bearer"}


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


def checkExistedPrjRecord(company_id, purpose_id, project_name, db: Session):
    if not company_id or not purpose_id or not project_name:
        return False
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


@app.get("/get-company-list")
def GetCompanyList(
    db: Session = Depends(get_db), user: models.User = Depends(getCurrentUser)
):
    rows = db.query(models.CompanyGrp).all()
    return [{"id": row.id, "name": row.name} for row in rows]


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

    new_company = models.CompanyGrp(name=payload.companyName)
    db.add(new_company)
    commitOr500(db, "Could not add company")
    db.refresh(new_company)
    return {"id": new_company.id, "name": new_company.name}


@app.post("/delete-company")
def DeleteCompany(
    payload: schemas.DelCompanyPurposeList,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    if db.query(models.Project).filter(models.Project.company_id == payload.id).first():
        raise InUse("Company")
    result = db.execute(
        delete(models.CompanyGrp).where(
            (models.CompanyGrp.name == payload.name) & (models.CompanyGrp.id == payload.id)
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise NotFound("Company")
    commitOr500(db, "Could not delete company")
    return {"message": "Company deleted"}


@app.get("/get-purpose-list")
def GetPurposeList(
    db: Session = Depends(get_db), user: models.User = Depends(getCurrentUser)
):
    rows = db.query(models.PurposeGrp).all()
    return [{"id": row.id, "name": row.name} for row in rows]


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
    commitOr500(db, "Could not add project")
    db.refresh(new_project)
    return projectResponse(db, new_project)
