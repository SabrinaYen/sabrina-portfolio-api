from fastapi import Depends, HTTPException,FastAPI
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import verifyPwd, generateToken

app = FastAPI();

def verifyUsr(payload: schemas.LoginRequest, db: Session) -> models.User | None:
    if not payload.username or not payload.password:
        return None

    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user:
        return None
    if not verifyPwd(payload.password, user.hashed_password):
        return None
    return user


@app.post("/generate-token")
def generate_token(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = verifyUsr(payload, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = generateToken(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}