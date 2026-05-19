"""Tests for ChromaManager."""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from app.rag.chroma_manager import ChromaManager

COLLECTION = "student_manual"


@pytest.fixture
def mock_chroma():
    """Fixture that patches chromadb.PersistentClient to return a mock."""
    with patch("app.rag.chroma_manager.chromadb") as mock_chromadb:
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        yield mock_client, mock_collection


def test_upload_dedup_skips_existing_chunks(settings, mock_chroma):
    """Chunks whose hash already exists are skipped."""
    _, mock_collection = mock_chroma

    existing_hash = hashlib.sha256("existing chunk".encode()).hexdigest()
    new_hash = hashlib.sha256("new chunk".encode()).hexdigest()

    mock_collection.get.return_value = {"ids": [existing_hash]}

    manager = ChromaManager(settings, MagicMock())
    chunks = ["existing chunk", "new chunk"]
    result = manager.upload(COLLECTION, chunks)

    assert result == {"inserted": 1, "skipped": 1}
    assert mock_collection.add.call_count == 1


def test_upload_empty_chunks_skipped(settings, mock_chroma):
    """Empty/whitespace chunks are filtered out."""
    _, mock_collection = mock_chroma
    mock_collection.get.return_value = {"ids": []}

    manager = ChromaManager(settings, MagicMock())
    result = manager.upload(COLLECTION, ["", "   ", "real content"])

    assert result == {"inserted": 1, "skipped": 0}
    assert mock_collection.add.call_count == 1


def test_clear_collection(settings, mock_chroma):
    """Clear deletes the collection."""
    mock_client, _ = mock_chroma

    manager = ChromaManager(settings, MagicMock())
    manager.clear(COLLECTION)

    mock_client.delete_collection.assert_called_once_with(COLLECTION)


def test_clear_all(settings, mock_chroma):
    """Clear with no args deletes all collections."""
    mock_client, _ = mock_chroma

    manager = ChromaManager(settings, MagicMock())
    manager.clear()

    assert mock_client.delete_collection.call_count == 2


def test_get_data_pagination(settings, mock_chroma):
    """Preview returns paginated results."""
    _, mock_collection = mock_chroma
    mock_collection.count.return_value = 2
    mock_collection.get.return_value = {
        "ids": ["h1", "h2"],
        "documents": ["doc1", "doc2"],
        "metadatas": [{"hash": "h1"}, {"hash": "h2"}],
    }

    manager = ChromaManager(settings, MagicMock())
    result = manager.get_data(COLLECTION, page=1, size=2)

    assert len(result["documents"]) == 2
    assert result["documents"][0] == "doc1"


def test_stats_counts(settings, mock_chroma):
    """Stats shows count per collection."""
    _, mock_collection = mock_chroma
    mock_collection.count.return_value = 42

    manager = ChromaManager(settings, MagicMock())
    result = manager.stats(COLLECTION)

    assert result["total_count"] == 42
