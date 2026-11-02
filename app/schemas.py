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
    projectShown: bool = True 
    sortOrder: int | None = None
    projectType: str | None = None
    isAvailable: bool | None = None 
    projectNameZh: str | None = None
    projectDescZh: str | None = None
    projectTypeZh: str | None = None


class ProjectUpdateReq(ProjectAddReq):
    id: int


class IdReq(BaseModel):
    id: int


class ExperienceReq(BaseModel):
    role: str
    company: str
    period: str
    description: str | None = ""
    roleZh: str | None = ""
    descriptionZh: str | None = ""
    sortOrder: int | None = None
    isPublished: bool = True


class ExperienceUpdateReq(ExperienceReq):
    id: int


class SkillGroupReq(BaseModel):
    groupTitle: str
    groupDesc: str | None = ""
    groupTitleZh: str | None = ""
    groupIcon: str | None = "code"
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
