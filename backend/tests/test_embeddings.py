"""Tests for the EmbeddingClient."""

from unittest.mock import MagicMock, patch

import pytest

from app.rag.embeddings import EmbeddingClient


def test_embed_returns_vectors_of_expected_length(settings):
    """EmbeddingClient.embed returns one vector per input text."""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3]),
        MagicMock(embedding=[0.4, 0.5, 0.6]),
    ]

    with patch.object(EmbeddingClient, "__init__", return_value=None):
        client = EmbeddingClient.__new__(EmbeddingClient)
        client.model = "test-embedding-model"
        client.client = MagicMock()
        client.client.embeddings.create.return_value = mock_response

        result = client.embed(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]


def test_embed_raises_on_api_error(settings):
    """EmbeddingClient.embed raises RuntimeError when the API call fails."""
    with patch.object(EmbeddingClient, "__init__", return_value=None):
        client = EmbeddingClient.__new__(EmbeddingClient)
        client.model = "test-embedding-model"
        client.client = MagicMock()
        client.client.embeddings.create.side_effect = Exception("API error")

        with pytest.raises(RuntimeError):
            client.embed(["hello"])
