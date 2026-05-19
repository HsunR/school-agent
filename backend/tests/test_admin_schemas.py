"""Tests for admin Pydantic schemas."""

from pydantic import ValidationError
import pytest
from app.schemas.admin import UploadRequest


def test_upload_request_valid():
    req = UploadRequest(content="some text", category="student_manual")
    assert req.delimiter == "*****SPILIT_BY_HUSNR*****"


def test_upload_request_invalid_category():
    with pytest.raises(ValidationError):
        UploadRequest(content="text", category="invalid_cat")  # type: ignore


def test_upload_request_empty_content():
    with pytest.raises(ValidationError):
        UploadRequest(content="", category="student_manual")
