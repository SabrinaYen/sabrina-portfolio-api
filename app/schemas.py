from pydantic import BaseModel 
class LoginRequest(BaseModel):
    username:str
    password:str
class ParamRequest(BaseModel):
    paramType: str
    
class ActivityLogsReq(BaseModel):
    username: str