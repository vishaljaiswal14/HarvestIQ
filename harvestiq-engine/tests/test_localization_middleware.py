import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

import app.core.database as db_module
from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())

@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    fastapi_app = create_app()

    async def fake_user():
        return {
            "_id": ObjectId(USER_ID),
            "preferred_lang": "hi",
            "role": "FARMER",
        }

    # Mock DB query for localization dictionary lookup
    mock_db = MagicMock()
    
    # We define a helper class for mock cursor
    class MockCursor:
        def __init__(self, data):
            self.data = data
            self.index = 0
        def __aiter__(self):
            return self
        async def __anext__(self):
            if self.index < len(self.data):
                res = self.data[self.index]
                self.index += 1
                return res
            raise StopAsyncIteration

    def fake_find(query, *args, **kwargs):
        lang = query.get("lang")
        if lang == "hi":
            return MockCursor([
                {"key": "Query is required", "value": "प्रश्न आवश्यक है", "lang": "hi"},
                {"key": "HIGH_STRESS", "value": "उच्च तनाव", "lang": "hi"},
            ])
        elif lang == "en":
            return MockCursor([
                {"key": "Query is required", "value": "Query is required", "lang": "en"},
                {"key": "HIGH_STRESS", "value": "HIGH_STRESS", "lang": "en"},
            ])
        return MockCursor([])

    mock_db.localization_dictionary.find = fake_find

    fastapi_app.dependency_overrides[get_current_user] = fake_user
    fastapi_app.dependency_overrides[get_database] = lambda: mock_db

    # Set the global database reference so the middleware's get_database call succeeds
    monkeypatch.setattr(db_module, "_db", mock_db)

    # Clear the local cache to ensure it reads from our mocked database find
    from app.middleware.localization import _LOCALIZATION_CACHE
    _LOCALIZATION_CACHE.clear()

    @fastapi_app.get("/test-html")
    def get_html():
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<html><body>Hello</body></html>")

    @fastapi_app.post("/test-204")
    def get_204():
        from fastapi.responses import Response
        return Response(status_code=204)

    with TestClient(fastapi_app, raise_server_exceptions=False) as test_client:
        yield test_client

def test_middleware_translates_error_to_hindi(client: TestClient) -> None:
    # Query is whitespace only -> raises 422 with detail "Query is required"
    # The middleware should intercept and translate "Query is required" to "प्रश्न आवश्यक है"
    response = client.post(
        "/api/v1/advisory/ask",
        json={"farm_id": FARM_ID, "query": "   "},
        headers={"Accept-Language": "hi"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "प्रश्न आवश्यक है"

def test_middleware_falls_back_to_english(client: TestClient) -> None:
    response = client.post(
        "/api/v1/advisory/ask",
        json={"farm_id": FARM_ID, "query": "   "},
        headers={"Accept-Language": "en"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Query is required"

def test_middleware_bypasses_html_responses(client: TestClient) -> None:
    response = client.get("/test-html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert response.text == "<html><body>Hello</body></html>"

def test_middleware_bypasses_204_responses(client: TestClient) -> None:
    response = client.post("/test-204")
    assert response.status_code == 204
    assert response.text == ""

