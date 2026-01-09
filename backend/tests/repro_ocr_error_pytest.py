import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
import httpx

# Mocks
@pytest.fixture
def mock_ocr_service_down():
    """Simulate OCR service returning 502 Bad Gateway"""
    with patch("httpx.AsyncClient.post") as mock_post:
        # Create a mock response with 502 status
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="502 Bad Gateway", 
            request=MagicMock(), 
            response=mock_response
        )
        mock_post.return_value = mock_response
        yield mock_post

@pytest.fixture
def mock_ocr_connection_error():
    """Simulate network connection failure"""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        yield mock_post

@pytest.mark.asyncio
async def test_ocr_service_unavailable_repro(mock_ocr_service_down, client_authenticated):
    """
    Reproduction of 'OCR service unavailable' error.
    Scenario: Upstream OCR service returns 5xx error.
    Expected: API returns 502 with detail 'OCR service unavailable'.
    """
    # Create dummy image file
    files = {'file': ('test.jpg', b'fake-image-content', 'image/jpeg')}
    
    response = client_authenticated.post("/api/v1/ocr/tesseract", files=files)
    
    assert response.status_code == 502
    assert response.json()["detail"] == "OCR service unavailable"
    print("\n[SUCCESS] Reproduced 'OCR service unavailable' error as expected.")

@pytest.mark.asyncio
async def test_ocr_processing_failed_repro(mock_ocr_connection_error, client_authenticated):
    """
    Reproduction of generic 'OCR processing failed' error.
    Scenario: Network level failure (connection refused/timeout).
    Expected: API returns 500 with detail starting with 'OCR processing failed'.
    """
    files = {'file': ('test.jpg', b'fake-image-content', 'image/jpeg')}
    
    response = client_authenticated.post("/api/v1/ocr/tesseract", files=files)
    
    assert response.status_code == 500
    assert "OCR processing failed" in response.json()["detail"]
    print("\n[SUCCESS] Reproduced 'OCR processing failed' error as expected.")
