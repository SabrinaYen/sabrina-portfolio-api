"""Checks that /public/site-data returns the shape of personal-data.js.

Run with: .venv/bin/python -m unittest discover -s tests -t .
"""
import json
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.auth import encryptPwd
from app.content import formatPeriod, parsePeriod
from app.database import base, get_db
from app.main import app


class SiteDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        def override():
            db = Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override
        db = Session()
        db.add(models.User(username="a", hashed_password=encryptPwd("pw")))
        db.commit()
        db.close()
        cls.client = TestClient(app)
        token = cls.client.post("/login", json={"username": "a", "password": "pw"}).json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {token}"}

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def post(self, path, body):
        response = self.client.post(path, headers=self.headers, json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_site_data_shape(self):
        self.post("/save-param", {"paramType": "contents", "values": {
            "name": "Sabrina", "nameZh": "淑冰", "position": "Dev", "email": "a@b.c", "tagline": "hello",
        }})
        self.post("/save-param", {"paramType": "site", "values": {"terminalLines": json.dumps(
            [{"command": "x --a", "en": "one", "zh": "一"}])}})
        self.post("/add-link", {"label": "GitHub", "url": "https://github.com/x"})
        self.post("/add-skill", {"groupTitle": "Cloud", "groupDesc": "AWS, Docker", "groupIcon": "cloud"})
        self.post("/add-project", {"project_name": "Shown", "projectDesc": "d", "techStack": "B, A", "linkURL": "http://x"})
        self.post("/add-project", {"project_name": "Hidden", "projectDesc": "d", "projectShown": False})
        self.post("/add-experience", {
            "role": "Dev", "company": "Acme", "period": "Oct 2024 — Present",
            "description": "First\nSecond", "descriptionZh": "第一",
        })

        data = self.client.get("/public/site-data").json()

        self.assertEqual(set(data), {"uiText", "personalData", "terminalLines", "skills", "projects", "experience"})
        self.assertEqual(data["personalData"]["name"], {"en": "Sabrina", "zh": "淑冰"})
        self.assertEqual(data["personalData"]["curTitle"], {"en": "Dev", "zh": "Dev"})
        self.assertEqual(data["personalData"]["socialLinks"], {"github": "https://github.com/x"})
        self.assertEqual(data["uiText"]["bio"], {"en": "hello", "zh": "hello"})
        self.assertEqual(data["terminalLines"], [{"command": "x --a", "output": {"en": "one", "zh": "一"}}])
        self.assertEqual(data["skills"][0]["items"], ["AWS", "Docker"])
        self.assertEqual(data["skills"][0]["skillsIcon"], "cloud")
        self.assertEqual([(p["title"]["en"], p["isSensitive"]) for p in data["projects"]],
                         [("Shown", False), ("Hidden", True)])
        self.assertEqual(data["projects"][0]["tags"], ["B", "A"])
        self.assertTrue(data["projects"][0]["isAvaliable"])
        self.assertEqual(data["experience"][0]["period"], "Oct 2024 — Present")
        self.assertEqual(data["experience"][0]["summary"], [
            {"en": "First", "zh": "第一"}, {"en": "Second", "zh": "Second"},
        ])

    def test_period_parsing(self):
        for text in ["Oct 2024 — Present", "Jun 2022 - Oct 2024", "Aug 2022 — Oct 2022"]:
            self.assertEqual(formatPeriod(*parsePeriod(text)), text.replace(" - ", " — "))
        start, end = parsePeriod("2022 - now")
        self.assertEqual((start.month, start.year, end), (1, 2022, None))

    def test_bad_period_is_rejected(self):
        response = self.client.post("/add-experience", headers=self.headers,
                                    json={"role": "r", "company": "c", "period": "soon"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
