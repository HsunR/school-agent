"""Tests for admin Pydantic schemas."""

from pydantic import ValidationError
import pytest
from app.schemas.admin import QueueClearResponse, QueueStatusResponse, UploadRequest


def test_upload_request_valid():
    req = UploadRequest(content="some text", category="student_manual")
    assert req.delimiter == "*****SPILIT_BY_HUSNR*****"


def test_upload_request_invalid_category():
    with pytest.raises(ValidationError):
        UploadRequest(content="text", category="invalid_cat")  # type: ignore


def test_upload_request_empty_content():
    with pytest.raises(ValidationError):
        UploadRequest(content="", category="student_manual")


def test_queue_status_response():
    r = QueueStatusResponse(busy=True, pending=2, current_task="doc.txt", progress=30, total=50)
    assert r.busy is True
    assert r.pending == 2
    assert r.current_task == "doc.txt"
    assert r.progress == 30
    assert r.total == 50


def test_queue_status_response_defaults():
    r = QueueStatusResponse(busy=False)
    assert r.pending == 0
    assert r.current_task is None
    assert r.progress == 0
    assert r.total == 0


def test_queue_clear_response():
    r = QueueClearResponse(message="cleared")
    assert r.message == "cleared"
