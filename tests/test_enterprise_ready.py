import unittest
import os
import io
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app as fastapi_app

from app.core.auth import hash_password

class TestEnterpriseReadyPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.core.database import Base, engine, SessionLocal
        import app.core.config
        
        app.core.config.settings.DATABASE_URL = "sqlite:///./test_hiresense.db"
        from sqlalchemy import create_engine
        
        cls.test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../test_hiresense.db"))
        for fpath in [cls.test_db_path, cls.test_db_path + "-shm", cls.test_db_path + "-wal"]:
            if os.path.exists(fpath):
                try: os.unlink(fpath)
                except Exception: pass
                
        cls.test_engine = create_engine(
            app.core.config.settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=cls.test_engine)
        
        from app.core.database import get_db
        from fastapi import Depends
        
        def override_get_db():
            from sqlalchemy.orm import sessionmaker
            TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.test_engine)
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()
                
        fastapi_app.dependency_overrides[get_db] = override_get_db
        
        # Insert a dedicated test user
        cls.test_email = f"test_dev_{uuid.uuid4().hex[:6]}@hiresense.ai"
        hashed = hash_password("test_pass_123")
        
        from app.models.user import User
        db = next(override_get_db())
        user = User(
            email=cls.test_email, 
            password_hash=hashed, 
            role="candidate", 
            name="Test Developer", 
            phone="+15550199", 
            created_at=datetime.now(timezone.utc).isoformat()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        cls.test_user_id = user.id
        db.close()

        # Instantiate TestClient after DB setup
        cls.client = TestClient(fastapi_app)

    @classmethod
    def tearDownClass(cls):
        # Shutdown client context and clean up database files
        for fpath in [cls.test_db_path, cls.test_db_path + "-shm", cls.test_db_path + "-wal"]:
            if os.path.exists(fpath):
                try: os.unlink(fpath)
                except Exception: pass

    def test_01_login_issues_refresh_token(self):
        """Test that logging in successfully returns both access and refresh tokens."""
        res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "test_pass_123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["role"], "candidate")

    def test_02_jwt_refresh_loop(self):
        """Test exchanging a refresh token for a brand new access token."""
        # 1. Login to get refresh token
        login_res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "test_pass_123"
        })
        refresh_token = login_res.json()["refresh_token"]

        # 2. Call refresh endpoint
        refresh_res = self.client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(refresh_res.status_code, 200)
        data = refresh_res.json()
        self.assertIn("access_token", data)
        # Optionally return refresh_token if the endpoint rotates it. The current endpoint only returns access_token.

    def test_03_logout_revokes_token(self):
        """Test that logging out invalidates the specific refresh token in the database."""
        # 1. Login
        login_res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "test_pass_123"
        })
        token_data = login_res.json()
        refresh_token = token_data["refresh_token"]
        access_token = token_data["access_token"]

        # 2. Logout
        logout_res = self.client.post(
            "/api/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(logout_res.status_code, 200)

        # 3. Verify that refresh token is now rejected
        refresh_fail_res = self.client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(refresh_fail_res.status_code, 401)

    def test_04_logout_all_devices(self):
        """Test revoking all active refresh tokens for the current user."""
        # 1. Login twice to simulate two device sessions
        r1 = self.client.post("/api/auth/login", json={"email": self.test_email, "password": "test_pass_123"}).json()
        r2 = self.client.post("/api/auth/login", json={"email": self.test_email, "password": "test_pass_123"}).json()
        
        # 2. Trigger logout from all devices
        logout_all_res = self.client.post(
            "/api/auth/logout/all",
            headers={"Authorization": f"Bearer {r1['access_token']}"}
        )
        self.assertEqual(logout_all_res.status_code, 200)

        # 3. Verify that both refresh tokens are now revoked
        check1 = self.client.post("/api/auth/refresh", json={"refresh_token": r1["refresh_token"]})
        check2 = self.client.post("/api/auth/refresh", json={"refresh_token": r2["refresh_token"]})
        self.assertEqual(check1.status_code, 401)
        self.assertEqual(check2.status_code, 401)

    def test_05_upload_validation_constraints(self):
        """Test that uploads enforce max file size limit and block invalid formats."""
        login_res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "test_pass_123"
        })
        access_token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 1. Test unsupported file formats (e.g. executable .exe)
        exe_file = io.BytesIO(b"MZBinaryData...")
        res_exe = self.client.post(
            "/api/candidates/profile/upload",
            files={"file": ("malware.exe", exe_file, "application/x-msdownload")},
            headers=headers
        )
        self.assertEqual(res_exe.status_code, 400)
        self.assertIn("Only PDF and TXT file formats are permitted", res_exe.json()["detail"])

        # 2. Test mock oversized file (exceeds 5MB)
        oversized_data = b"0" * (6 * 1024 * 1024) # 6MB
        oversized_file = io.BytesIO(oversized_data)
        res_large = self.client.post(
            "/api/candidates/profile/upload",
            files={"file": ("oversized.pdf", oversized_file, "application/pdf")},
            headers=headers
        )
        self.assertEqual(res_large.status_code, 400)
        self.assertIn("File size exceeds the upload limit", res_large.json()["detail"])

    def test_06_health_check(self):
        """Test that health monitoring endpoint is responsive and displays DB connectivity status."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")

if __name__ == "__main__":
    unittest.main()
