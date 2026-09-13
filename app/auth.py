import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import HTTPException,status,Depends
from fastapi.security import OAuth2PasswordBearer

load_dotenv(); # setup env configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # getCurrentUser() func bearer token

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

def getCurrentUser(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decodeToken(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return payload