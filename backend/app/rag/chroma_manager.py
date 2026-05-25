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
        self.top_k_manual = settings.rag_top_k_manual
        self.top_k_forum = settings.rag_top_k_forum
        self.embedding_client = embedding_client
        self._client = chromadb.PersistentClient(path=self.persist_dir)

    def _collection(self, name: str):
        """Get or create a ChromaDB collection by name, with health check."""
        collection = self._client.get_or_create_collection(name)
        # Guard: verify collection is usable (not dim=None with missing segment dir)
        try:
            collection.count()
        except Exception:
            logger.warning("Collection '%s' is corrupted, resetting...", name)
            try:
                self._client.delete_collection(name)
            except Exception:
                pass
            collection = self._client.get_or_create_collection(name)
        return collection

    UPLOAD_BATCH_SIZE = 50

    def upload(
        self, category: str, chunks: list[str]
    ) -> dict[str, int]:
        """Upload chunks to a collection, skipping duplicates.

        Processes chunks in batches of ``UPLOAD_BATCH_SIZE`` to avoid
        embedding huge payloads in a single API call.

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

        if not new_chunks:
            return {"inserted": 0, "skipped": skipped}

        # Process in batches: embed → add → repeat
        now = datetime.now(timezone.utc).isoformat()
        for i in range(0, len(new_chunks), self.UPLOAD_BATCH_SIZE):
            batch_chunks = new_chunks[i : i + self.UPLOAD_BATCH_SIZE]
            batch_hashes = new_hashes[i : i + self.UPLOAD_BATCH_SIZE]
            embeddings = self.embedding_client.embed(batch_chunks)
            metadatas = [
                {"hash": h, "category": category, "created_at": now}
                for h in batch_hashes
            ]
            collection.add(
                ids=batch_hashes,
                embeddings=embeddings,
                documents=batch_chunks,
                metadatas=metadatas,
            )
            inserted += len(batch_chunks)
            logger.debug(
                "Uploaded batch %d/%d to '%s'",
                i // self.UPLOAD_BATCH_SIZE + 1,
                (len(new_chunks) + self.UPLOAD_BATCH_SIZE - 1) // self.UPLOAD_BATCH_SIZE,
                category,
            )

        logger.info(
            "Uploaded %d chunks to '%s' (%d skipped)",
            inserted, category, skipped,
        )
        return {"inserted": inserted, "skipped": skipped}

    def warmup(self) -> None:
        """Pre-load collections and vector index to avoid cold-start latency."""
        for name in ALL_COLLECTIONS:
            try:
                collection = self._collection(name)
                count = collection.count()
                logger.info("Warmup: collection '%s' loaded (%d documents)", name, count)
            except Exception:
                logger.warning("Warmup: collection '%s' failed to load", name)

    def retrieve(self, category: str, query: str, top_k: int | None = None) -> list[str]:
        """Retrieve top-K text chunks from a collection by semantic similarity.

        Args:
            category: Collection name.
            query: The user's question or query text.
            top_k: Override the default result count. If ``None``, uses the
                configured default for the collection.

        Returns:
            A list of chunk text strings, ordered by relevance.
        """
        collection = self._collection(category)
        query_embedding = self.embedding_client.embed([query])[0]
        if top_k is not None:
            n_results = top_k
        else:
            n_results = self.top_k_manual if category == "student_manual" else self.top_k_forum
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
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

    def delete_by_id(self, category: str, ids: list[str]) -> int:
        """Delete specific documents from a collection by their IDs.

        Args:
            category: Collection name.
            ids: List of document IDs (SHA256 hashes) to delete.

        Returns:
            Number of documents deleted.
        """
        if not ids:
            return 0
        collection = self._collection(category)
        # Verify IDs exist before deletion
        existing = collection.get(ids=ids)
        existing_ids = existing.get("ids", []) or []
        if not existing_ids:
            return 0
        collection.delete(ids=existing_ids)
        logger.info("Deleted %d docs from '%s'", len(existing_ids), category)
        return len(existing_ids)

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
