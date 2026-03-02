"""BM25 keyword search over the Airees training corpus."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CorpusDocument:
    """A single document from the training corpus."""

    path: Path
    title: str
    category: str
    content: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class CorpusResult:
    """A search result from the corpus."""

    path: Path
    title: str
    category: str
    score: float
    excerpt: str


@dataclass
class CorpusSearchEngine:
    """BM25 keyword search over markdown training files.

    The index is built lazily on the first search call and cached
    for the lifetime of the process.
    """

    corpus_dir: Path
    _index: object | None = field(default=None, init=False, repr=False)
    _documents: list[CorpusDocument] = field(default_factory=list, init=False, repr=False)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def _extract_title(self, content: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return "Untitled"

    def _extract_category(self, path: Path) -> str:
        try:
            rel = path.relative_to(self.corpus_dir)
            parts = rel.parts
            return parts[0] if parts else "unknown"
        except ValueError:
            return "unknown"

    def _build_index(self) -> None:
        from rank_bm25 import BM25Okapi

        self._documents = []

        if not self.corpus_dir.exists():
            self._index = None
            return

        for md_file in sorted(self.corpus_dir.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            title = self._extract_title(content)
            category = self._extract_category(md_file)
            tokens = tuple(self._tokenize(f"{title} {category} {content}"))

            if not tokens:
                continue

            self._documents.append(
                CorpusDocument(
                    path=md_file,
                    title=title,
                    category=category,
                    content=content,
                    tokens=tokens,
                )
            )

        if not self._documents:
            self._index = None
            return

        corpus_tokenized = [list(doc.tokens) for doc in self._documents]
        self._index = BM25Okapi(corpus_tokenized)

    def search(self, query: str, top_k: int = 3) -> list[CorpusResult]:
        if self._index is None and not self._documents:
            self._build_index()

        if self._index is None or not self._documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = self._index.get_scores(query_tokens)

        scored_docs = sorted(
            zip(scores, self._documents),
            key=lambda x: x[0],
            reverse=True,
        )

        results = []
        for score, doc in scored_docs[:top_k]:
            if score <= 0:
                continue
            excerpt = doc.content[:500].strip()
            results.append(
                CorpusResult(
                    path=doc.path,
                    title=doc.title,
                    category=doc.category,
                    score=float(score),
                    excerpt=excerpt,
                )
            )
        return results

    def format_results(self, results: list[CorpusResult]) -> str:
        if not results:
            return "No relevant training material found."

        sections = []
        for r in results:
            sections.append(
                f"### {r.title}\n"
                f"**Category:** {r.category} | **Relevance:** {r.score:.2f}\n\n"
                f"{r.excerpt}\n"
            )
        return "\n---\n\n".join(sections)
