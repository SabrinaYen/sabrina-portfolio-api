"""SQL injection checks. Run with: .venv/bin/python -m unittest discover -s tests -t .

Uses a throwaway in-memory SQLite database, never the real one.
"""
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.auth import encryptPwd
from app.database import base, get_db
from app.main import app

INJECTIONS = ["' OR 1=1 --", "admin'--", "' OR '1'='1", "x'; DROP TABLE users; --"]


class InjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        base.metadata.create_all(engine)
        cls.Session = sessionmaker(bind=engine)

        def override():
            db = cls.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override
        db = cls.Session()
        db.add(models.User(username="admin", hashed_password=encryptPwd("correct-password")))
        db.commit()
        db.close()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def login(self, username, password):
        return self.client.post("/login", json={"username": username, "password": password})

    def test_real_login_works(self):
        self.assertEqual(self.login("admin", "correct-password").status_code, 200)

    def test_injection_in_username_is_rejected(self):
        for payload in INJECTIONS:
            with self.subTest(payload=payload):
                self.assertEqual(self.login(payload, "anything").status_code, 401)

    def test_injection_in_password_is_rejected(self):
        for payload in INJECTIONS:
            with self.subTest(payload=payload):
                self.assertEqual(self.login("admin", payload).status_code, 401)

    def test_users_table_survives(self):
        self.login(INJECTIONS[-1], "x")
        db = self.Session()
        self.assertEqual(db.query(models.User).count(), 1)
        db.close()

    def test_protected_routes_need_a_token(self):
        for path in ["/get-company-list", "/get-project-list", "/get-visit-stats"]:
            with self.subTest(path=path):
                self.assertIn(self.client.get(path).status_code, (401, 403))

    def test_injection_in_content_is_stored_as_plain_text(self):
        token = self.login("admin", "correct-password").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        evil = "x'); DROP TABLE company_grp; --"
        self.assertEqual(self.client.post("/add-company", headers=headers, json={"companyName": evil}).status_code, 200)
        names = [c["name"] for c in self.client.get("/get-company-list", headers=headers).json()]
        self.assertIn(evil, names)  # saved as text, table still there


if __name__ == "__main__":
    unittest.main()
