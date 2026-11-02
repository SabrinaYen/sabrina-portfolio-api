import argparse
import getpass
import json
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:  # this Python may not know the system's certificates, so use the project's own list
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

LIVE_API = "https://sabrina-portfolio-api.onrender.com"
DEFAULT_FILE = Path(__file__).resolve().parents[2] / "sabrina-portfolio/src/assets/data/personal-data.js"


def load_source(path: Path) -> dict:
    """personal-data.js is a JavaScript module, so let node turn it into JSON."""
    script = f"import * as d from {json.dumps(path.as_uri())}; console.log(JSON.stringify(d))"
    result = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Could not read {path}:\n{result.stderr}")
    return json.loads(result.stdout)


# ---------- turn the file into what the API expects ----------
def bilingual(value) -> dict:
    return value if isinstance(value, dict) else {"en": value, "zh": ""}


def content_values(src: dict) -> dict:
    person, ui = src["personalData"], src["uiText"]
    values = {"email": person["email"]}
    texts = {
        "name": person["name"], "position": person["curTitle"], "bio": person["bio"],
        "location": person["location"], "tagline": ui["bio"],
        "aboutHeading": ui["aboutHeading"], "aboutHeadingDesc": ui["aboutHeadingDesc"],
        "contactHeading": ui["contactHeading"], "contactBody": ui["contactBody"],
    }
    for key, text in texts.items():
        values[key], values[key + "Zh"] = text["en"], text["zh"]
    return values


def terminal_json(src: dict) -> str:
    return json.dumps([
        {"command": line["command"], "en": line["output"]["en"], "zh": line["output"]["zh"]}
        for line in src["terminalLines"]
    ])


def link_payloads(src: dict) -> list[dict]:
    names = {"github": "GitHub", "linkedin": "LinkedIn"}
    return [{"label": names.get(key, key.title()), "url": url} for key, url in src["personalData"]["socialLinks"].items()]


def skill_payloads(src: dict) -> list[dict]:
    return [{
        "groupTitle": s["category"]["en"], "groupTitleZh": s["category"]["zh"],
        "groupDesc": ", ".join(s["items"]), "groupIcon": s["skillsIcon"],
    } for s in src["skills"]]


def project_payload(p: dict, company_id: int | None) -> dict:
    title = bilingual(p["title"])
    return {
        "project_name": title["en"], "projectNameZh": title["zh"],
        "projectType": p["type"]["en"], "projectTypeZh": p["type"]["zh"],
        "projectDesc": p["description"]["en"], "projectDescZh": p["description"]["zh"],
        "techStack": ", ".join(p["tags"]), "linkURL": p["link"],
        "isAvailable": p["isAvaliable"],  # (sic) the file's spelling
        "projectShown": not p["isSensitive"],  # sensitive projects stay hidden on the site
        "company_Id": company_id,
    }


def experience_payloads(src: dict) -> list[dict]:
    return [{
        "role": e["role"]["en"], "roleZh": e["role"]["zh"], "company": e["company"], "period": e["period"],
        "description": "\n".join(s["en"] for s in e["summary"]),
        "descriptionZh": "\n".join(s["zh"] for s in e["summary"]),
    } for e in src["experience"]]


# ---------- talking to the API ----------
class Api:
    def __init__(self, base: str):
        self.base, self.token = base.rstrip("/"), None

    def call(self, method: str, path: str, body: dict | None = None):
        request = urllib.request.Request(
            self.base + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {self.token}"} if self.token else {})},
        )
        try:
            with urllib.request.urlopen(request, timeout=120, context=SSL_CONTEXT) as response:  # the free host can take a while to wake
                return json.load(response)
        except urllib.error.HTTPError as error:
            detail = json.loads(error.read() or b"{}").get("detail", "")
            sys.exit(f"{method} {path} failed ({error.code}): {detail}")
        except urllib.error.URLError as error:
            sys.exit(f"Could not reach {self.base}: {error.reason}")

    def login(self, username: str, password: str):
        self.token = self.call("POST", "/login", {"username": username, "password": password})["access_token"]


def do_import(api: Api, src: dict):
    existing = {name: api.call("GET", path) for name, path in
                [("projects", "/get-project-list"), ("experience", "/get-experience-list"), ("skills", "/get-skill-list")]}
    if any(existing.values()):
        counts = ", ".join(f"{len(v)} {k}" for k, v in existing.items())
        sys.exit(f"The API already has content ({counts}). Not importing, to avoid duplicates.")

    print("Saving texts...")
    api.call("POST", "/save-param", {"paramType": "contents", "values": content_values(src)})
    api.call("POST", "/save-param", {"paramType": "site", "values": {"terminalLines": terminal_json(src)}})
    for link in link_payloads(src):
        api.call("POST", "/add-link", link)

    print("Saving skills...")
    for skill in skill_payloads(src):
        api.call("POST", "/add-skill", skill)

    print("Saving projects...")
    companies = {c["name"]: c["id"] for c in api.call("GET", "/get-company-list")}
    for p in src["projects"]:
        name = p.get("company")
        if name and name not in companies:
            companies[name] = api.call("POST", "/add-company", {"companyName": name})["id"]
        api.call("POST", "/add-project", project_payload(p, companies.get(name)))

    print("Saving experience...")
    for item in experience_payloads(src):
        api.call("POST", "/add-experience", item)
    print("Done.")


def do_check(api: Api, src: dict):
    got = api.call("GET", "/public/site-data")
    person = src["personalData"]
    want = {
        "personalData": {**{k: person[k] for k in ["name", "curTitle", "bio", "email", "location"]},
                         "socialLinks": {k.lower(): v for k, v in person["socialLinks"].items()}},
        "terminalLines": src["terminalLines"], "skills": src["skills"], "experience": src["experience"],
        "uiText": {k: src["uiText"][k] for k in ["bio", "aboutHeading", "aboutHeadingDesc", "contactHeading", "contactBody"]},
        "projects": [{**p, "title": bilingual(p["title"]) if isinstance(p["title"], dict) else {"en": p["title"], "zh": p["title"]}}
                     for p in src["projects"]],
    }
    ok = True
    for section, expected in want.items():
        actual = got[section]
        if section == "projects":  # the API sends hidden projects too, marked isSensitive
            actual = [{k: v for k, v in p.items()} for p in actual]
        same = actual == expected
        ok &= same
        print(("OK    " if same else "DIFF  ") + section)
    sys.exit(0 if ok else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default=LIVE_API, help="API address (default: the live API)")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE, help="path to personal-data.js")
    parser.add_argument("--username", help="portal username (asked if left out)")
    parser.add_argument("--dry-run", action="store_true", help="only show what would be sent")
    parser.add_argument("--check", action="store_true", help="compare the API's public data with the file")
    args = parser.parse_args()

    src = load_source(args.file)
    if args.dry_run:
        print(f"Would import from {args.file}:")
        print(f"  texts: {len(content_values(src))} values, {len(src['terminalLines'])} terminal lines, {len(link_payloads(src))} links")
        print(f"  skills: {len(src['skills'])}, projects: {len(src['projects'])} "
              f"({sum(p['isSensitive'] for p in src['projects'])} hidden), experience: {len(src['experience'])}")
        return
    api = Api(args.api)
    if args.check:
        return do_check(api, src)

    api.login(args.username or input("Portal username: "), getpass.getpass("Portal password: "))
    do_import(api, src)


if __name__ == "__main__":
    main()
