"""Common errors, so the endpoints can just write `raise NotFound("Company")`.

Each class is an HTTPException with a fixed status code, so FastAPI sends the
right response automatically.
"""
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class Unauthorized(HTTPException):  # 401: bad login or token
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


class BadRequest(HTTPException):  # 400: the request itself is wrong
    def __init__(self, detail: str):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)


class Duplicate(BadRequest):  # 400: the record already exists
    def __init__(self):
        super().__init__("Error: Duplication")


class NotFound(HTTPException):  # 404: e.g. NotFound("Company")
    def __init__(self, what: str):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{what} not found")


class InUse(HTTPException):  # 409: e.g. InUse("Company") when projects still use it
    def __init__(self, what: str):
        super().__init__(status.HTTP_409_CONFLICT, f"{what} is used by existing projects")


class InvalidInput(HTTPException):  # 422: the value has the wrong format
    def __init__(self, detail: str):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)


class ServerError(HTTPException):  # 500: the database failed
    def __init__(self, detail: str):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)


# ---------- small database helpers that raise the errors above ----------
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
