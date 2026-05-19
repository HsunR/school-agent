"""ChromaDB wrapper for knowledge base storage and retrieval."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import chromadb

from app.core.settings import Settings
from app.rag.embeddings import EmbeddingClient

logger = logging.getLogger(__name__)

# ChromaDB collection names
COLLECTION_MANUAL = "student_manual"
COLLECTION_FORUM = "school_forum"
ALL_COLLECTIONS = [COLLECTION_MANUAL, COLLECTION_FORUM]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ChromaManager:
    """Manages ChromaDB collections for the two knowledge bases.

    Provides upload (with dedup), preview, clear, stats, and retrieval.
    All embeddings are generated via the injected ``EmbeddingClient``.
    """

    def __init__(self, settings: Settings, embedding_client: EmbeddingClient) -> None:
        self.persist_dir = settings.chroma_persist_dir
        self.top_k = settings.rag_top_k
        self.embedding_client = embedding_client
        self._client = chromadb.PersistentClient(path=self.persist_dir)

    def _collection(self, name: str):
        """Get or create a ChromaDB collection by name."""
        return self._client.get_or_create_collection(name)

    def upload(
        self, category: str, chunks: list[str]
    ) -> dict[str, int]:
        """Upload chunks to a collection, skipping duplicates.

        Args:
            category: Collection name (``student_manual`` or ``school_forum``).
            chunks: List of text chunks to upload.

        Returns:
            ``{"inserted": int, "skipped": int}``.
        """
        collection = self._collection(category)
        inserted = 0
        skipped = 0

        # Filter empty chunks
        non_empty = [c for c in chunks if c.strip()]
        if not non_empty:
            return {"inserted": 0, "skipped": 0}

        # Compute hashes and check existing
        hashes = [_sha256(c) for c in non_empty]
        existing = collection.get(ids=hashes)
        existing_ids: set[str] = set(existing.get("ids", []) or [])

        new_chunks: list[str] = []
        new_hashes: list[str] = []
        for chunk, h in zip(non_empty, hashes):
            if h in existing_ids:
                skipped += 1
            else:
                new_chunks.append(chunk)
                new_hashes.append(h)
                inserted += 1

        if not new_chunks:
            return {"inserted": 0, "skipped": skipped}

        # Embed and add
        embeddings = self.embedding_client.embed(new_chunks)
        now = datetime.now(timezone.utc).isoformat()
        metadatas = [
            {"hash": h, "category": category, "created_at": now}
            for h in new_hashes
        ]
        collection.add(
            ids=new_hashes,
            embeddings=embeddings,
            documents=new_chunks,
            metadatas=metadatas,
        )

        logger.info(
            "Uploaded %d chunks to '%s' (%d skipped)",
            inserted, category, skipped,
        )
        return {"inserted": inserted, "skipped": skipped}

    def retrieve(self, category: str, query: str) -> list[str]:
        """Retrieve top-K text chunks from a collection by semantic similarity.

        Args:
            category: Collection name.
            query: The user's question or query text.

        Returns:
            A list of chunk text strings, ordered by relevance.
        """
        collection = self._collection(category)
        query_embedding = self.embedding_client.embed([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k,
        )
        documents = results.get("documents", [[]])[0] or []
        return list(documents)

    def get_data(
        self, category: str, page: int = 1, size: int = 20
    ) -> dict[str, Any]:
        """Paginated preview of stored chunks.

        Args:
            category: Collection name.
            page: 1-indexed page number.
            size: Items per page.

        Returns:
            ``{"ids": [...], "documents": [...], "metadatas": [...], "total": int}``.
        """
        collection = self._collection(category)
        offset = (page - 1) * size
        total = collection.count()
        result = collection.get(limit=size, offset=offset)
        return {
            "ids": result.get("ids", []),
            "documents": result.get("documents", []),
            "metadatas": result.get("metadatas", []),
            "total": total,
        }

    def clear(self, category: str | None = None) -> None:
        """Delete all data from one or both collections.

        Args:
            category: If provided, clear only that collection.
            If ``None``, clear all.
        """
        targets = [category] if category else ALL_COLLECTIONS
        for cat in targets:
            try:
                self._client.delete_collection(cat)
                logger.info("Cleared collection '%s'", cat)
            except Exception:
                logger.warning("Collection '%s' not found, skipping", cat)

    def stats(self, category: str) -> dict[str, Any]:
        """Get statistics for a collection.

        Args:
            category: Collection name.

        Returns:
            ``{"total_count": int, "category": str}``.
        """
        collection = self._collection(category)
        return {
            "total_count": collection.count(),
            "category": category,
        }
