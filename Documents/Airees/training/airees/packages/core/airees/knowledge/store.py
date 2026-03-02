"""KnowledgeStore — ChromaDB wrapper for personal document search."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_CHUNK_SIZE = 500  # characters per chunk
_CHUNK_OVERLAP = 50


@dataclass(frozen=True)
class KnowledgeResult:
    """A search result from the knowledge store."""

    text: str
    source: str
    score: float


@dataclass
class KnowledgeStore:
    """ChromaDB-backed semantic search over personal documents.

    Attributes:
        data_dir: Directory for ChromaDB persistence.
    """

    data_dir: Path
    _collection: Any = field(default=None, init=False, repr=False)

    def _get_collection(self) -> Any:
        """Lazy-init ChromaDB collection."""
        if self._collection is None:
            import chromadb

            self.data_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.data_dir))
            self._collection = client.get_or_create_collection(
                name="personal_knowledge",
            )
            log.info("ChromaDB collection initialized at %s", self.data_dir)
        return self._collection

    def ingest(self, path: Path) -> int:
        """Ingest a file into the knowledge store.

        Supports: .txt, .md, .pdf

        Returns:
            Number of chunks ingested.
        """
        text = self._extract_text(path)
        if not text.strip():
            log.warning("No text extracted from %s", path)
            return 0

        chunks = self._chunk_text(text)
        collection = self._get_collection()

        ids = [f"{path}::chunk-{i}" for i in range(len(chunks))]
        metadatas = [{"source": str(path), "chunk_index": i} for i in range(len(chunks))]

        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas,
        )
        log.info("Ingested %d chunks from %s", len(chunks), path)
        return len(chunks)

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeResult]:
        """Semantic search over ingested documents."""
        collection = self._get_collection()
        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
        )

        output = []
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i] if results["distances"] else 0.0
            source = results["metadatas"][0][i].get("source", "unknown")
            output.append(
                KnowledgeResult(
                    text=doc,
                    source=source,
                    score=1.0 / (1.0 + distance),  # Convert distance to similarity
                )
            )
        return output

    def delete(self, source: str) -> int:
        """Delete all chunks from a specific source. Returns count deleted."""
        collection = self._get_collection()
        # Get all IDs matching this source
        results = collection.get(where={"source": source})
        if not results["ids"]:
            return 0
        collection.delete(ids=results["ids"])
        log.info("Deleted %d chunks from source %s", len(results["ids"]), source)
        return len(results["ids"])

    def stats(self) -> dict[str, Any]:
        """Return collection statistics."""
        collection = self._get_collection()
        return {
            "document_count": collection.count(),
            "data_dir": str(self.data_dir),
        }

    def _extract_text(self, path: Path) -> str:
        """Extract text from a file based on extension."""
        suffix = path.suffix.lower()
        if suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8")
        elif suffix == ".pdf":
            return self._extract_pdf(path)
        else:
            log.warning("Unsupported file type: %s", suffix)
            return path.read_text(encoding="utf-8", errors="ignore")

    def _extract_pdf(self, path: Path) -> str:
        """Extract text from a PDF file."""
        try:
            import pymupdf
            doc = pymupdf.open(str(path))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            log.error("pymupdf not installed — cannot extract PDF")
            return ""

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + _CHUNK_SIZE
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - _CHUNK_OVERLAP
        return chunks
