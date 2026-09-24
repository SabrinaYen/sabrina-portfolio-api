from fastapi import Depends, HTTPException, FastAPI,status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import verifyPwd, generateToken,getCurrentUser
from datetime import datetime,timezone

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
        except Exception:
            db.rollback();
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not complete login");
        
        
@app.post("/get-setting")
def GetSetting(db: Session = Depends(get_db),user: models.User = Depends(getCurrentUser)):
    try:
        setting = db.query(models.Setting).first()
        return setting;
    except:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,"Error: No Rows");


    

 
        
    