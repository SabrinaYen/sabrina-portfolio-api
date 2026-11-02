"""GET /public/site-data: everything the portfolio site needs, in the same shape
as src/assets/data/personal-data.js (so the site can swap its import for a fetch).

Text that has two languages is {"en": ..., "zh": ...}. A missing Chinese text
falls back to the English one.
"""
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.content import (
    LINKS, bulletsOf, companyNames, formatPeriod, ordered, paramsOf,
    skillNamesByGroup, tagNamesByProject,
)
from app.database import get_db
from app.extras import loadExtras, pick

router = APIRouter()

UI_TEXT_KEYS = {
    "tagline": "bio",
    "aboutHeading": "aboutHeading",
    "aboutHeadingDesc": "aboutHeadingDesc",
    "contactHeading": "contactHeading",
    "contactBody": "contactBody",
}


def bilingual(en: str | None, zh: str | None) -> dict:
    en = en or ""
    return {"en": en, "zh": zh or en}


def contentBilingual(content: dict, key: str) -> dict:
    return bilingual(content.get(key), content.get(key + "Zh"))


def buildPersonalData(content: dict, db: Session) -> dict:
    links = {row["label"].lower(): row["url"] for row in linkRows(db)}
    return {
        "name": contentBilingual(content, "name"),
        "curTitle": contentBilingual(content, "position"),
        "bio": contentBilingual(content, "bio"),
        "email": content.get("email") or "",
        "location": contentBilingual(content, "location"),
        "socialLinks": links,
    }


def linkRows(db: Session) -> list[dict]:
    rows = db.query(models.PrmSetup).filter(models.PrmSetup.locate_at == LINKS).order_by(models.PrmSetup.id)
    return [{"label": r.param_id, "url": r.value or ""} for r in rows]


def buildTerminalLines(db: Session) -> list[dict]:
    raw = paramsOf(db, "site").get("terminalLines")
    try:
        lines = json.loads(raw) if raw else []
    except ValueError:
        lines = []
    return [
        {"command": line.get("command", ""), "output": bilingual(line.get("en"), line.get("zh"))}
        for line in lines
    ]


def buildSkills(db: Session) -> list[dict]:
    names, extras = skillNamesByGroup(db), loadExtras(db, "skill_group")
    return [
        {
            "category": bilingual(row.category_name, pick(extras, row.id, "category", "zh")),
            "items": names.get(row.id, []),
            "skillsIcon": pick(extras, row.id, "icon") or "code",
        }
        for row in ordered(db, models.SkillsGrp)
    ]


def buildProjects(db: Session) -> list[dict]:
    extras, companies = loadExtras(db, "project"), companyNames(db)
    tags = tagNamesByProject(db, extras)
    projects = []
    for row in ordered(db, models.Project):
        available = pick(extras, row.id, "available")
        project = {
            "title": bilingual(row.project_name, pick(extras, row.id, "title", "zh")),
            "type": bilingual(pick(extras, row.id, "type", "en"), pick(extras, row.id, "type", "zh")),
            "isCompanyProject": row.company_id is not None,
            "description": bilingual(row.project_desc, pick(extras, row.id, "description", "zh")),
            "tags": tags.get(row.id, []),
            "link": row.url_link or "",
            "isAvaliable": (available == "true") if available else bool(row.url_link),
            "isSensitive": not row.is_published,
        }
        if row.company_id is not None:
            project["company"] = companies.get(row.company_id, "")
        projects.append(project)
    return projects


def buildExperience(db: Session) -> list[dict]:
    companies, extras = companyNames(db), loadExtras(db, "experience")
    rows = ordered(db, models.Experience).filter(models.Experience.is_published.is_(True))
    result = []
    for row in rows:
        en = bulletsOf(row.description)
        zh = bulletsOf(pick(extras, row.id, "description", "zh"))
        result.append({
            "role": bilingual(row.position, pick(extras, row.id, "role", "zh")),
            "company": companies.get(row.company_id, ""),
            "period": formatPeriod(row.start_date, row.end_date),
            "summary": [bilingual(text, zh[i] if i < len(zh) else "") for i, text in enumerate(en)],
        })
    return result


@router.get("/public/site-data")
def SiteData(db: Session = Depends(get_db)):
    content = paramsOf(db, "contents")
    ui_text = {
        site_key: contentBilingual(content, key)
        for key, site_key in UI_TEXT_KEYS.items()
        if content.get(key)
    }
    return {
        "uiText": ui_text,
        "personalData": buildPersonalData(content, db),
        "terminalLines": buildTerminalLines(db),
        "skills": buildSkills(db),
        "projects": buildProjects(db),
        "experience": buildExperience(db),
    }
