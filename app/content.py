
import re
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import encryptPwd, getCurrentUser, verifyPwd
from app.database import get_db
from app.extras import Extras, loadExtras, pick, removeExtras, saveExtras
from app.errors import BadRequest, Duplicate, InUse, InvalidInput, NotFound, commitOr500, getOr404

router = APIRouter()
LINKS = "links"


def logActivity(db: Session, user: models.User, action: str, details: dict | None = None):
    """Stage an activity log row; committed together with the caller's change."""
    db.add(models.ActivityLogs(user_id=user.id, action_name=action, details=details or {}))


def ordered(db: Session, model):
    return db.query(model).order_by(model.sort_order.asc(), model.id.asc())


def nextOrder(db: Session, model, given: int | None) -> int:
    if given is not None:
        return given
    return (db.query(func.max(model.sort_order)).scalar() or 0) + 1


def splitNames(text: str | None) -> list[str]:
    seen, names = set(), []
    for part in (text or "").split(","):
        name = part.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def paramsOf(db: Session, locate_at: str) -> dict:
    rows = db.query(models.PrmSetup).filter(models.PrmSetup.locate_at == locate_at).all()
    return {row.param_id: row.value for row in rows}


# ---------- site content (prm_setup) ----------
@router.post("/save-param")
def SaveParam(
    payload: schemas.SaveParamReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    existing = {
        row.param_id: row
        for row in db.query(models.PrmSetup).filter(
            models.PrmSetup.locate_at == payload.paramType
        )
    }
    for key, value in payload.values.items():
        if key in existing:
            existing[key].value = value
        else:
            db.add(models.PrmSetup(locate_at=payload.paramType, param_id=key, value=value))
    logActivity(db, user, "save-param", {"paramType": payload.paramType, "keys": list(payload.values)})
    commitOr500(db, "Could not save content")
    return paramsOf(db, payload.paramType)


# ---------- projects (tech stack lives in tag_grp / project_tags) ----------
def tagNamesByProject(db: Session, extras: Extras) -> dict[int, list[str]]:
    """Tag names per project, in the order the tags were typed (project_tags has no order column)."""
    result: dict[int, list[str]] = {}
    rows = (
        db.query(models.ProjectTag.project_id, models.TagGrp.name)
        .join(models.TagGrp, models.TagGrp.id == models.ProjectTag.tag_id)
        .order_by(models.TagGrp.id)
        .all()
    )
    for project_id, name in rows:
        result.setdefault(project_id, []).append(name)
    for project_id, names in result.items():
        typed = [n.lower() for n in splitNames(pick(extras, project_id, "tag_order"))]
        names.sort(key=lambda n: typed.index(n.lower()) if n.lower() in typed else len(typed))
    return result


def projectOut(row: models.Project, tags: dict[int, list[str]], extras: Extras) -> dict:
    available = pick(extras, row.id, "available")
    return {
        "id": row.id,
        "projectName": row.project_name,
        "projectNameZh": pick(extras, row.id, "title", "zh"),
        "projectDesc": row.project_desc or "",
        "projectDescZh": pick(extras, row.id, "description", "zh"),
        "projectType": pick(extras, row.id, "type", "en"),
        "projectTypeZh": pick(extras, row.id, "type", "zh"),
        "isAvailable": (available == "true") if available else bool(row.url_link),
        "techStack": ", ".join(tags.get(row.id, [])),
        "linkURL": row.url_link or "",
        "projectShown": bool(row.is_published),
        "companyId": row.company_id,
        "purposeId": row.purpose_id,
        "sortOrder": row.sort_order,
    }


def projectResponse(db: Session, row: models.Project) -> dict:
    extras = loadExtras(db, "project")
    return projectOut(row, tagNamesByProject(db, extras), extras)


def saveProject(db: Session, row: models.Project, p: schemas.ProjectAddReq) -> models.Project:
    """Create or update a project row and sync its tech-stack tags."""
    row.project_name = p.project_name
    row.project_desc = p.projectDesc
    row.company_id = p.company_Id
    row.purpose_id = p.purpose_Id
    row.is_published = p.projectShown
    row.is_link = bool(p.linkURL)
    row.url_link = p.linkURL or None
    if row.id is None:
        row.sort_order = nextOrder(db, models.Project, p.sortOrder)
        db.add(row)
    elif p.sortOrder is not None:
        row.sort_order = p.sortOrder
    db.flush()

    tag_names = splitNames(p.techStack)
    tag_ids = []
    for name in tag_names:
        tag = db.query(models.TagGrp).filter(func.lower(models.TagGrp.name) == name.lower()).first()
        if not tag:
            tag = models.TagGrp(name=name)
            db.add(tag)
            db.flush()
        tag_ids.append(tag.id)
    db.execute(delete(models.ProjectTag).where(models.ProjectTag.project_id == row.id))
    for tag_id in tag_ids:
        db.add(models.ProjectTag(project_id=row.id, tag_id=tag_id))

    saveExtras(db, "project", row.id, {
        ("type", "en"): p.projectType,
        ("type", "zh"): p.projectTypeZh,
        ("title", "zh"): p.projectNameZh,
        ("description", "zh"): p.projectDescZh,
        ("available", ""): None if p.isAvailable is None else str(p.isAvailable).lower(),
        ("tag_order", ""): ", ".join(tag_names),
    })
    return row


@router.get("/get-project-list")
def GetProjectList(db: Session = Depends(get_db), _user: models.User = Depends(getCurrentUser)):
    extras = loadExtras(db, "project")
    tags = tagNamesByProject(db, extras)
    return [projectOut(r, tags, extras) for r in ordered(db, models.Project)]


@router.post("/update-project")
def UpdateProject(
    payload: schemas.ProjectUpdateReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    row = getOr404(db, models.Project, payload.id, "Project")
    saveProject(db, row, payload)
    logActivity(db, user, "update-project", {"id": row.id})
    commitOr500(db, "Could not update project")
    return projectResponse(db, row)


@router.post("/delete-project")
def DeleteProject(
    payload: schemas.IdReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    row = getOr404(db, models.Project, payload.id, "Project")
    db.execute(delete(models.ProjectTag).where(models.ProjectTag.project_id == row.id))
    db.execute(delete(models.ProjectSkill).where(models.ProjectSkill.project_id == row.id))
    removeExtras(db, "project", row.id)
    db.delete(row)
    logActivity(db, user, "delete-project", {"id": payload.id})
    commitOr500(db, "Could not delete project")
    return {"message": "Project deleted"}


# ---------- purposes ----------
@router.post("/add-purpose")
def AddPurpose(
    payload: schemas.AddPurposeReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    if db.query(models.PurposeGrp).filter(models.PurposeGrp.name == payload.purposeName).first():
        raise Duplicate()
    row = models.PurposeGrp(name=payload.purposeName)
    db.add(row)
    logActivity(db, user, "add-purpose", {"name": payload.purposeName})
    commitOr500(db, "Could not add purpose")
    db.refresh(row)
    return {"id": row.id, "name": row.name}


@router.post("/delete-purpose")
def DeletePurpose(
    payload: schemas.DelCompanyPurposeList,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    if db.query(models.Project).filter(models.Project.purpose_id == payload.id).first():
        raise InUse("Purpose")
    result = db.execute(
        delete(models.PurposeGrp).where(
            (models.PurposeGrp.id == payload.id) & (models.PurposeGrp.name == payload.name)
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise NotFound("Purpose")
    logActivity(db, user, "delete-purpose", {"id": payload.id})
    commitOr500(db, "Could not delete purpose")
    return {"message": "Purpose deleted"}


# ---------- experience (portal "period" text <-> start_date / end_date) ----------
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def parseDate(text: str, is_end: bool) -> date | None:
    """"Oct 2024" -> 2024-10-01. A bare year is Jan (start) or Dec (end)."""
    named = re.search(r"([A-Za-z]{3})[A-Za-z]*\.?\s*(\d{4})", text)
    if named and named.group(1).title() in MONTHS:
        return date(int(named.group(2)), MONTHS.index(named.group(1).title()) + 1, 1)
    year = re.search(r"\d{4}", text)
    return date(int(year.group()), 12 if is_end else 1, 1) if year else None


def parsePeriod(period: str) -> tuple[date, date | None]:
    """"Jun 2022 - Oct 2024" or "Oct 2024 — Present" -> (start, end). End is None while ongoing."""
    parts = re.split(r"\s*[—–-]\s*", (period or "").strip(), maxsplit=1)
    start = parseDate(parts[0], is_end=False)
    if not start:
        raise InvalidInput('period must look like "Oct 2024 — Present" or "Jun 2022 - Oct 2024"')
    if len(parts) == 1 or not re.search(r"\d", parts[1]):  # "Present", "now", or nothing
        return start, None
    return start, parseDate(parts[1], is_end=True)


def formatPeriod(start: date, end: date | None) -> str:
    finish = f"{MONTHS[end.month - 1]} {end.year}" if end else "Present"
    return f"{MONTHS[start.month - 1]} {start.year} — {finish}"


def bulletsOf(text: str | None) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def experienceOut(row: models.Experience, companies: dict[int, str], extras: Extras) -> dict:
    return {
        "id": row.id,
        "role": row.position,
        "roleZh": pick(extras, row.id, "role", "zh"),
        "company": companies.get(row.company_id, ""),
        "period": formatPeriod(row.start_date, row.end_date),
        "description": row.description or "",
        "descriptionZh": pick(extras, row.id, "description", "zh"),
        "sortOrder": row.sort_order,
        "isPublished": bool(row.is_published),
    }


def companyNames(db: Session) -> dict[int, str]:
    return {c.id: c.name for c in db.query(models.CompanyGrp).all()}


def saveExperience(db: Session, row: models.Experience, p: schemas.ExperienceReq):
    company = db.query(models.CompanyGrp).filter(models.CompanyGrp.name == p.company).first()
    if not company:
        company = models.CompanyGrp(name=p.company)
        db.add(company)
        db.flush()
    row.company_id = company.id
    row.position = p.role
    row.start_date, row.end_date = parsePeriod(p.period)
    row.description = p.description
    row.is_published = p.isPublished
    if row.id is None:
        row.sort_order = nextOrder(db, models.Experience, p.sortOrder)
        db.add(row)
    elif p.sortOrder is not None:
        row.sort_order = p.sortOrder
    db.flush()
    saveExtras(db, "experience", row.id, {("role", "zh"): p.roleZh, ("description", "zh"): p.descriptionZh})


def experienceResponse(db: Session, row: models.Experience) -> dict:
    return experienceOut(row, companyNames(db), loadExtras(db, "experience"))


@router.get("/get-experience-list")
def GetExperienceList(db: Session = Depends(get_db), _user: models.User = Depends(getCurrentUser)):
    companies, extras = companyNames(db), loadExtras(db, "experience")
    return [experienceOut(r, companies, extras) for r in ordered(db, models.Experience)]


@router.post("/add-experience")
def AddExperience(
    payload: schemas.ExperienceReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    row = models.Experience()
    saveExperience(db, row, payload)
    logActivity(db, user, "add-experience", {"role": payload.role})
    commitOr500(db, "Could not add experience")
    db.refresh(row)
    return experienceResponse(db, row)


@router.post("/update-experience")
def UpdateExperience(
    payload: schemas.ExperienceUpdateReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    row = getOr404(db, models.Experience, payload.id, "Experience")
    saveExperience(db, row, payload)
    logActivity(db, user, "update-experience", {"id": row.id})
    commitOr500(db, "Could not update experience")
    return experienceResponse(db, row)


@router.post("/delete-experience")
def DeleteExperience(
    payload: schemas.IdReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    db.delete(getOr404(db, models.Experience, payload.id, "Experience"))
    removeExtras(db, "experience", payload.id)
    logActivity(db, user, "delete-experience", {"id": payload.id})
    commitOr500(db, "Could not delete experience")
    return {"message": "Experience deleted"}


# ---------- skill groups (skills_grp + skills; groupDesc = comma separated names) ----------
def skillNamesByGroup(db: Session) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for skill in ordered(db, models.Skill):
        result.setdefault(skill.category_id, []).append(skill.name)
    return result


def skillOut(row: models.SkillsGrp, names: dict[int, list[str]], extras: Extras) -> dict:
    return {
        "id": row.id,
        "groupTitle": row.category_name,
        "groupTitleZh": pick(extras, row.id, "category", "zh"),
        "groupIcon": pick(extras, row.id, "icon") or "code",
        "groupDesc": ", ".join(names.get(row.id, [])),
        "sortOrder": row.sort_order,
    }


def skillResponse(db: Session, row: models.SkillsGrp) -> dict:
    return skillOut(row, skillNamesByGroup(db), loadExtras(db, "skill_group"))


def saveSkillGroup(db: Session, row: models.SkillsGrp, p: schemas.SkillGroupReq):
    row.category_name = p.groupTitle
    if row.id is None:
        row.sort_order = nextOrder(db, models.SkillsGrp, p.sortOrder)
        db.add(row)
    elif p.sortOrder is not None:
        row.sort_order = p.sortOrder
    db.flush()
    saveExtras(db, "skill_group", row.id, {("category", "zh"): p.groupTitleZh, ("icon", ""): p.groupIcon})

    wanted = splitNames(p.groupDesc)
    current = db.query(models.Skill).filter(models.Skill.category_id == row.id).all()
    by_name = {s.name.lower(): s for s in current}
    removed = [s.id for s in current if s.name.lower() not in {w.lower() for w in wanted}]
    if removed:
        db.execute(delete(models.ProjectSkill).where(models.ProjectSkill.skill_id.in_(removed)))
        db.execute(delete(models.Skill).where(models.Skill.id.in_(removed)))
    for position, name in enumerate(wanted, start=1):
        skill = by_name.get(name.lower())
        if skill:
            skill.sort_order = position
        else:
            db.add(models.Skill(category_id=row.id, name=name, sort_order=position))


@router.get("/get-skill-list")
def GetSkillList(db: Session = Depends(get_db), _user: models.User = Depends(getCurrentUser)):
    names, extras = skillNamesByGroup(db), loadExtras(db, "skill_group")
    return [skillOut(r, names, extras) for r in ordered(db, models.SkillsGrp)]


@router.post("/add-skill")
def AddSkill(
    payload: schemas.SkillGroupReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    row = models.SkillsGrp()
    saveSkillGroup(db, row, payload)
    logActivity(db, user, "add-skill", {"group": payload.groupTitle})
    commitOr500(db, "Could not add skill group")
    db.refresh(row)
    return skillResponse(db, row)


@router.post("/update-skill")
def UpdateSkill(
    payload: schemas.SkillGroupUpdateReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    row = getOr404(db, models.SkillsGrp, payload.id, "Skill group")
    saveSkillGroup(db, row, payload)
    logActivity(db, user, "update-skill", {"id": row.id})
    commitOr500(db, "Could not update skill group")
    return skillResponse(db, row)


@router.post("/delete-skill")
def DeleteSkill(
    payload: schemas.IdReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    row = getOr404(db, models.SkillsGrp, payload.id, "Skill group")
    ids = [s.id for s in db.query(models.Skill).filter(models.Skill.category_id == row.id)]
    if ids:
        db.execute(delete(models.ProjectSkill).where(models.ProjectSkill.skill_id.in_(ids)))
        db.execute(delete(models.Skill).where(models.Skill.id.in_(ids)))
    removeExtras(db, "skill_group", row.id)
    db.delete(row)
    logActivity(db, user, "delete-skill", {"id": payload.id})
    commitOr500(db, "Could not delete skill group")
    return {"message": "Skill group deleted"}


# ---------- social links (stored in prm_setup, locate_at = "links") ----------
def linkList(db: Session) -> list[dict]:
    rows = (
        db.query(models.PrmSetup)
        .filter(models.PrmSetup.locate_at == LINKS)
        .order_by(models.PrmSetup.id)
        .all()
    )
    return [{"label": r.param_id, "url": r.value or ""} for r in rows]


@router.get("/get-link-list")
def GetLinkList(db: Session = Depends(get_db), _user: models.User = Depends(getCurrentUser)):
    return linkList(db)


@router.post("/add-link")
def AddLink(
    payload: schemas.SocialLinkReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    row = (
        db.query(models.PrmSetup)
        .filter(models.PrmSetup.locate_at == LINKS, models.PrmSetup.param_id == payload.label)
        .first()
    )
    if row:
        row.value = payload.url
    else:
        db.add(models.PrmSetup(locate_at=LINKS, param_id=payload.label, value=payload.url))
    logActivity(db, user, "save-link", {"label": payload.label})
    commitOr500(db, "Could not save link")
    return {"label": payload.label, "url": payload.url}


@router.post("/delete-link")
def DeleteLink(
    payload: schemas.SocialLinkDelReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    result = db.execute(
        delete(models.PrmSetup).where(
            models.PrmSetup.locate_at == LINKS, models.PrmSetup.param_id == payload.label
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise NotFound("Link")
    logActivity(db, user, "delete-link", {"label": payload.label})
    commitOr500(db, "Could not delete link")
    return {"message": "Link deleted"}


# ---------- visitor statistics (counts live in prm_setup, locate_at = "visits") ----------
VISITS = "visits"


def addVisit(db: Session, param_id: str):
    row = (
        db.query(models.PrmSetup)
        .filter(models.PrmSetup.locate_at == VISITS, models.PrmSetup.param_id == param_id)
        .first()
    )
    if row:
        row.value = str(int(row.value or 0) + 1)
    else:
        db.add(models.PrmSetup(locate_at=VISITS, param_id=param_id, value="1"))


@router.post("/public/visit")
def RecordVisit(db: Session = Depends(get_db)):
    """The public site calls this once per visit. No login needed."""
    addVisit(db, "total")
    addVisit(db, date.today().isoformat())
    commitOr500(db, "Could not record visit")
    return {"message": "ok"}


@router.get("/get-visit-stats")
def GetVisitStats(db: Session = Depends(get_db), _user: models.User = Depends(getCurrentUser)):
    counts = paramsOf(db, VISITS)
    today = date.today()
    days = [today - timedelta(days=n) for n in range(6, -1, -1)]  # oldest first
    last7 = [{"date": d.isoformat(), "count": int(counts.get(d.isoformat()) or 0)} for d in days]
    return {
        "total": int(counts.get("total") or 0),
        "today": last7[-1]["count"],
        "last7": last7,
    }


# ---------- account ----------
@router.post("/change-password")
def ChangePassword(
    payload: schemas.ChangePasswordReq,
    db: Session = Depends(get_db),
    user: models.User = Depends(getCurrentUser),
):
    if not verifyPwd(payload.currentPassword, user.hashed_password):
        raise BadRequest("Current password is wrong")
    if len(payload.newPassword) < 8:
        raise BadRequest("New password must be at least 8 characters")
    user.hashed_password = encryptPwd(payload.newPassword)
    logActivity(db, user, "change-password")
    commitOr500(db, "Could not change password")
    return {"message": "Password changed"}
