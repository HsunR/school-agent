"""OpenAI-compatible embedding client for RAG."""

import logging
from typing import Any

from openai import OpenAI

from app.core.settings import Settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Client for generating text embeddings via an OpenAI-compatible API.

    Wraps the ``openai`` client to produce embeddings for text chunks.
    The ``base_url``, ``model``, and ``api_key`` are all configurable
    via ``Settings`` so any OpenAI-compatible provider can be used.
    """

    def __init__(self, settings: Settings) -> None:
        self.model = settings.llm_embedding_model
        self.client = OpenAI(
            base_url=settings.llm_embedding_base_url,
            api_key=settings.llm_embedding_api_key,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings and return the resulting vector list.

        Args:
            texts: List of text strings to embed.

        Returns:
            A list of embedding vectors (each a list of floats).

        Raises:
            RuntimeError: If the embedding API call fails.
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.exception("Embedding API call failed")
            raise RuntimeError("Embedding API call failed") from e
