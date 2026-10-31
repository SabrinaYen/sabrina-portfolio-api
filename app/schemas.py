from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class ParamRequest(BaseModel):
    paramType: str


class SaveParamReq(BaseModel):
    paramType: str
    values: dict[str, str | None]


class ActivityLogsReq(BaseModel):
    username: str


class AddCompanyPurposeList(BaseModel):
    companyName: str


class DelCompanyPurposeList(BaseModel):
    id: int
    name: str


class AddPurposeReq(BaseModel):
    purposeName: str


class ProjectAddReq(BaseModel):
    project_name: str
    projectDesc: str
    linkURL: str | None = None
    techStack: str | None = None
    company_Id: int | None = None
    purpose_Id: int | None = None
    projectShown: bool = True  # published flag (checkbox in portal)
    sortOrder: int | None = None
    projectType: str | None = None  # e.g. "E-commerce Experience"
    isAvailable: bool | None = None  # is the live link still working?
    # Chinese versions
    projectNameZh: str | None = None
    projectDescZh: str | None = None
    projectTypeZh: str | None = None


class ProjectUpdateReq(ProjectAddReq):
    id: int


class IdReq(BaseModel):
    id: int


class ExperienceReq(BaseModel):
    role: str
    company: str  # company name; created in company_grp if new
    period: str  # e.g. "Oct 2024 — Present" or "Jun 2022 - Oct 2024"
    description: str | None = ""  # one bullet per line
    roleZh: str | None = ""
    descriptionZh: str | None = ""  # bullets in the same order as the English ones
    sortOrder: int | None = None
    isPublished: bool = True


class ExperienceUpdateReq(ExperienceReq):
    id: int


class SkillGroupReq(BaseModel):
    groupTitle: str
    groupDesc: str | None = ""  # comma separated skill names
    groupTitleZh: str | None = ""
    groupIcon: str | None = "code"  # code, database, cloud or checked
    sortOrder: int | None = None


class SkillGroupUpdateReq(SkillGroupReq):
    id: int


class SocialLinkReq(BaseModel):
    label: str
    url: str


class SocialLinkDelReq(BaseModel):
    label: str


class ChangePasswordReq(BaseModel):
    currentPassword: str
    newPassword: str
