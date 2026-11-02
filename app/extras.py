from sqlalchemy import delete
from sqlalchemy.orm import Session

from app import models

Extras = dict[int, dict[tuple[str, str], str]]


def loadExtras(db: Session, entity: str) -> Extras:
    result: Extras = {}
    for row in db.query(models.ExtraText).filter(models.ExtraText.entity == entity):
        result.setdefault(row.entity_id, {})[(row.field, row.lang)] = row.value or ""
    return result


def pick(extras: Extras, entity_id: int, field: str, lang: str = "") -> str:
    return extras.get(entity_id, {}).get((field, lang), "")


def saveExtras(db: Session, entity: str, entity_id: int, values: dict[tuple[str, str], str | None]):
    """Upsert each value. An empty value removes the row."""
    existing = {
        (row.field, row.lang): row
        for row in db.query(models.ExtraText).filter(
            models.ExtraText.entity == entity, models.ExtraText.entity_id == entity_id
        )
    }
    for (field, lang), value in values.items():
        row = existing.get((field, lang))
        if not value:
            if row:
                db.delete(row)
        elif row:
            row.value = value
        else:
            db.add(models.ExtraText(entity=entity, entity_id=entity_id, field=field, lang=lang, value=value))


def removeExtras(db: Session, entity: str, entity_id: int):
    db.execute(
        delete(models.ExtraText).where(
            models.ExtraText.entity == entity, models.ExtraText.entity_id == entity_id
        )
    )
