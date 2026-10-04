from fastapi import Depends, HTTPException, FastAPI,status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import verifyPwd, generateToken,getCurrentUser
from datetime import datetime,timezone

app = FastAPI();

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verifyUsr(payload: schemas.LoginRequest, db: Session) -> models.User | None:
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verifyPwd(payload.password, user.hashed_password):
        return None
    return user

@app.post("/me")
def me(user: models.User = Depends(getCurrentUser)):
    return {"username": user.username};
    
@app.post("/login")
def login(payload: schemas.LoginRequest , db: Session = Depends(get_db)):
    user = verifyUsr(payload, db);
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password");
    else:
        try:
            user.last_login_at = datetime.now(timezone.utc);
            db.commit();
            token = generateToken(data={"sub": user.username})
            return {"access_token": token, "token_type": "bearer"}
        except SQLAlchemyError:
            db.rollback();
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not complete login");
        
        
@app.post("/get-param")
def GetParam(payload: schemas.ParamRequest,db: Session = Depends(get_db),user: models.User = Depends(getCurrentUser)):
        param_rows = db.query(models.PrmSetup).filter(models.PrmSetup.locate_at == payload.paramType).all();
        return {row.param_id: row.value for row in param_rows}


@app.post("/get-activity-logs")
def GetActivityLogs(payload: schemas.ActivityLogsReq,db: Session = Depends(get_db),user: models.User = Depends(getCurrentUser)):
    logs_rows = db.query(models.ActivityLogs).filter(models.ActivityLogs.username == payload.username).all();
    if logs_rows:
        return [
            {"action": row.action_name, "details": row.details, "created_at": row.created_at}
            for row in logs_rows
        ]
    else:   
        raise HTTPException(status.HTTP_400_BAD_REQUEST,"Error: No Rows");

        
    