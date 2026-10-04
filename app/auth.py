import os
import jwt
import bcrypt

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import HTTPException,status,Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

load_dotenv(); # setup env configuration
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # getCurrentUser() func bearer token
bearer = HTTPBearer()  # reads "Authorization: Bearer <token>"

SECRET_KEY = os.getenv("SECRET_KEY");
ALGORITHM = os.getenv("ALGORITHM");
ACCESS_TOKEN_EXPIRE_HOURS = 24;

def encryptPwd(pwd: str) -> str:
    hashed = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

# this is to verify correct pwd from db;
def verifyPwd(inputPwd: str, hashPwd: str) -> bool:
    return bcrypt.checkpw(inputPwd.encode("utf-8"), hashPwd.encode("utf-8"))

# generate token after login
def generateToken(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decodeToken(access_token:str) -> dict:
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

def getCurrentUser(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decodeToken(creds.credentials);
    except JWTError:
        raise credentials_error
    username = payload.get("sub")
    if username is None:
        raise credentials_error
    user = db.query(models.User).filter(models.User.username == username).first();
    return user;
   

