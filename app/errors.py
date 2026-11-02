from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class Unauthorized(HTTPException): 
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


class BadRequest(HTTPException): 
    def __init__(self, detail: str):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)


class Duplicate(BadRequest):
    def __init__(self):
        super().__init__("Error: Duplication")


class NotFound(HTTPException):
    def __init__(self, what: str):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{what} not found")


class InUse(HTTPException):
    def __init__(self, what: str):
        super().__init__(status.HTTP_409_CONFLICT, f"{what} is used by existing projects")


class InvalidInput(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)


class ServerError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)


def getOr404(db: Session, model, id: int, label: str):
    row = db.get(model, id)
    if not row:
        raise NotFound(label)
    return row


def commitOr500(db: Session, message: str):
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise ServerError(message)
