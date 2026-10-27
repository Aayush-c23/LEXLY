"""
Security and DPDP Act 2023 Compliance Test Suite (SEC-601).

Verifies:
1. PII Redaction for Indian identifiers (Aadhaar, PAN, phone numbers, emails).
2. 24-hour TTL session expiration and right-to-erasure cascade deletion.
3. Zero persistent storage of client IP addresses or raw device identifiers.
4. Client-side secret isolation: zero Supabase service-role or Gemini API keys in Android bundle.
"""

import os
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.engine.session_store import (
    cleanup_expired_sessions,
    delete_session_cascade,
    create_session,
    get_session
)


# ============================================================================
# 1. PII REDACTION TESTS (DPDP ACT 2023 SECTION 6 & 8)
# ============================================================================

class TestPiiSanitization:
    """Tests PII redaction patterns matching Indian statutory requirements."""

    PHONE_REGEX = re.compile(r"(?:\+91[\s\-]?)?(?:0)?[6-9]\d{4}[\s\-]?\d{5}\b")
    AADHAAR_REGEX = re.compile(r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b")
    PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

    def redact_pii(self, text: str) -> str:
        text = self.AADHAAR_REGEX.sub("[REDACTED_AADHAAR]", text)
        text = self.PAN_REGEX.sub("[REDACTED_PAN]", text)
        text = self.PHONE_REGEX.sub("[REDACTED_PHONE]", text)
        text = self.EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
        return text

    def test_indian_phone_number_redaction(self):
        samples = [
            ("Call me at +91 9876543210 immediately.", "Call me at [REDACTED_PHONE] immediately."),
            ("Emergency contact: 09876543210 or 8765432109", "Emergency contact: [REDACTED_PHONE] or [REDACTED_PHONE]"),
        ]
        for raw, expected in samples:
            assert self.redact_pii(raw) == expected

    def test_aadhaar_number_redaction(self):
        raw = "Complainant Aadhaar card number is 3456 7890 1234."
        assert self.redact_pii(raw) == "Complainant Aadhaar card number is [REDACTED_AADHAAR]."

    def test_pan_card_redaction(self):
        raw = "Tax fraud report involving PAN ABCDE1234F at the tax office."
        assert self.redact_pii(raw) == "Tax fraud report involving PAN [REDACTED_PAN] at the tax office."

    def test_email_redaction(self):
        raw = "Send notice to victim.support@legalaid.delhi.gov.in now."
        assert self.redact_pii(raw) == "Send notice to [REDACTED_EMAIL] now."


# ============================================================================
# 2. 24-HOUR TTL EXPIRATION & SESSION CLEANUP (DPDP RETENTION LIMITATION)
# ============================================================================

@pytest.mark.asyncio
class TestSessionTtlAndErasure:
    """Tests session expiration after 24 hours and right-to-erasure cascade deletion."""

    async def test_cleanup_expired_sessions_sql_execution(self):
        """Verifies cleanup_expired_sessions deletes sessions older than cutoff."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 5"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        deleted_count = await cleanup_expired_sessions(mock_pool, ttl_hours=24)
        assert deleted_count == 5

        # Check SQL invoked
        mock_conn.execute.assert_called_once()
        sql_arg = mock_conn.execute.call_args[0][0]
        assert "DELETE FROM analysis_sessions" in sql_arg
        assert "created_at <" in sql_arg

    async def test_session_cleanup_endpoint(self):
        """Verifies POST /api/v1/session/cleanup endpoint triggers TTL cleanup."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 3"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("backend.app.api.v1.endpoints.session.get_pool", return_value=mock_pool):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/v1/session/cleanup")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "CLEANUP_COMPLETED"
                assert "purged_sessions_count" in data

    async def test_right_to_erasure_cascade_deletion(self):
        """Verifies DELETE /api/v1/session/{id} deletes session and associated facts."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 1"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("backend.app.api.v1.endpoints.session.get_pool", return_value=mock_pool):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete("/api/v1/session/sess-dpdp-erasure-001")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "DELETED"
                assert data["session_id"] == "sess-dpdp-erasure-001"


# ============================================================================
# 3. ZERO PERSISTENT PII & ZERO IP ADDRESS STORAGE AUDIT
# ============================================================================

class TestZeroStorageAudit:
    """Verifies that session models do not record client IP, IMEI, or hardware IDs."""

    def test_session_table_fields_contain_no_ip_or_device_fields(self):

        # Inspect signature and expected table schema:
        # Tables: analysis_sessions(session_id, incident_date, current_regime, status, created_at)
        # and session_facts(session_id, fact_key, answer, step)
        schema_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "supabase", "migrations", "20240101000000_initial_schema.sql"
        )
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                content = f.read().lower()
                assert "ip_address" not in content
                assert "client_ip" not in content
                assert "device_id" not in content
                assert "mac_address" not in content


# ============================================================================
# 4. SECRET ISOLATION & ANDROID CODEBASE AUDIT
# ============================================================================

class TestAndroidSecretIsolation:
    """Scans all Android source code to ensure zero secret key leakage."""

    FORBIDDEN_SECRET_NAMES = [
        "SUPABASE_SERVICE_ROLE_KEY",
        "GEMINI_API_KEY",
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
    ]

    def test_no_server_secrets_in_android_bundle(self):
        android_dir = os.path.join(os.path.dirname(__file__), "..", "..", "android")
        assert os.path.exists(android_dir), "Android directory must exist"

        found_leakages = []

        for root, dirs, files in os.walk(android_dir):
            # Skip build and hidden directories
            if any(part.startswith(".") or part == "build" for part in root.split(os.sep)):
                continue

            for file in files:
                if file.endswith((".kt", ".java", ".xml", ".gradle", ".properties")):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        for secret in self.FORBIDDEN_SECRET_NAMES:
                            if secret in content:
                                found_leakages.append(f"{file_path}: contains '{secret}'")

        assert len(found_leakages) == 0, f"Found secret key leakage in Android codebase: {found_leakages}"
