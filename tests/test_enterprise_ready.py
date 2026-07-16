import unittest
import os
import io
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main import app
from src.database import get_db_connection
from src.auth import hash_password, create_access_token, create_refresh_token

class TestEnterpriseReadyPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import src.database
        
        # Define isolated test database file
        cls.test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../test_hiresense.db"))
        for fpath in [cls.test_db_path, cls.test_db_path + "-shm", cls.test_db_path + "-wal"]:
            if os.path.exists(fpath):
                try: os.unlink(fpath)
                except Exception: pass
                
        src.database.DB_PATH = cls.test_db_path
        
        # Setup clean test schema structures
        from src.database import init_db, get_db_connection
        init_db()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert a dedicated test user
        cls.test_email = f"test_dev_{uuid.uuid4().hex[:6]}@hiresense.ai"
        hashed = hash_password("test_pass_123")
        cursor.execute(
            "INSERT INTO users (email, password_hash, role, name, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (cls.test_email, hashed, "candidate", "Test Developer", "+15550199", datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        
        # Get ID
        cursor.execute("SELECT id FROM users WHERE email = ?", (cls.test_email,))
        cls.test_user_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        # Instantiate TestClient after DB setup
        cls.client = TestClient(app)

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
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": self.test_email,
            "password": "test_pass_123"
        })
        refresh_token = login_res.json()["refresh_token"]

        # 2. Call refresh endpoint
        refresh_res = self.client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(refresh_res.status_code, 200)
        data = refresh_res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["refresh_token"], refresh_token)

    def test_03_logout_revokes_token(self):
        """Test that logging out invalidates the specific refresh token in the database."""
        # 1. Login
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": self.test_email,
            "password": "test_pass_123"
        })
        token_data = login_res.json()
        refresh_token = token_data["refresh_token"]
        access_token = token_data["access_token"]

        # 2. Logout
        logout_res = self.client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        self.assertEqual(logout_res.status_code, 200)

        # 3. Verify that refresh token is now rejected
        refresh_fail_res = self.client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        self.assertEqual(refresh_fail_res.status_code, 401)

    def test_04_logout_all_devices(self):
        """Test revoking all active refresh tokens for the current user."""
        # 1. Login twice to simulate two device sessions
        r1 = self.client.post("/api/v1/auth/login", json={"email": self.test_email, "password": "test_pass_123"}).json()
        r2 = self.client.post("/api/v1/auth/login", json={"email": self.test_email, "password": "test_pass_123"}).json()
        
        # 2. Trigger logout from all devices
        logout_all_res = self.client.post(
            "/api/v1/auth/logout/all",
            headers={"Authorization": f"Bearer {r1['access_token']}"}
        )
        self.assertEqual(logout_all_res.status_code, 200)

        # 3. Verify that both refresh tokens are now revoked
        check1 = self.client.post("/api/v1/auth/refresh", json={"refresh_token": r1["refresh_token"]})
        check2 = self.client.post("/api/v1/auth/refresh", json={"refresh_token": r2["refresh_token"]})
        self.assertEqual(check1.status_code, 401)
        self.assertEqual(check2.status_code, 401)

    def test_05_upload_validation_constraints(self):
        """Test that uploads enforce max file size limit and block invalid formats."""
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": self.test_email,
            "password": "test_pass_123"
        })
        access_token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 1. Test unsupported file formats (e.g. executable .exe)
        exe_file = io.BytesIO(b"MZBinaryData...")
        res_exe = self.client.post(
            "/api/v1/candidates/profile/upload",
            files={"file": ("malware.exe", exe_file, "application/x-msdownload")},
            headers=headers
        )
        self.assertEqual(res_exe.status_code, 400)
        self.assertIn("Only PDF and TXT file formats are permitted", res_exe.json()["detail"])

        # 2. Test mock oversized file (exceeds 5MB)
        oversized_data = b"0" * (6 * 1024 * 1024) # 6MB
        oversized_file = io.BytesIO(oversized_data)
        res_large = self.client.post(
            "/api/v1/candidates/profile/upload",
            files={"file": ("oversized.pdf", oversized_file, "application/pdf")},
            headers=headers
        )
        self.assertEqual(res_large.status_code, 400)
        self.assertIn("exceeds the 5MB upload limit", res_large.json()["detail"])

    def test_06_health_check(self):
        """Test that health monitoring endpoint is responsive and displays DB connectivity status."""
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")

if __name__ == "__main__":
    unittest.main()
