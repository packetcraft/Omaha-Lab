import hashlib
import json
import re
from pathlib import Path

import chromadb

_CHROMA_DIR = Path(".chroma")
_MANIFEST_FILE = _CHROMA_DIR / "manifest.json"
_COLLECTION_NAME = "omaha_lab_docs"
_EMBED_MODEL = "nomic-embed-text"
_CHUNK_MAX_CHARS = 600


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _load_manifest() -> dict[str, str]:
    if _MANIFEST_FILE.exists():
        return json.loads(_MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: dict[str, str]) -> None:
    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    _MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _chunk_markdown(text: str) -> list[str]:
    """Split markdown into overlapping paragraph-boundary chunks."""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    bucket: list[str] = []
    bucket_len = 0

    for para in paragraphs:
        if bucket_len + len(para) > _CHUNK_MAX_CHARS and bucket:
            chunks.append("\n\n".join(bucket))
            # one-paragraph overlap
            bucket = [bucket[-1], para]
            bucket_len = len(bucket[0]) + len(para)
        else:
            bucket.append(para)
            bucket_len += len(para)

    if bucket:
        chunks.append("\n\n".join(bucket))

    return [c for c in chunks if len(c) > 30]


class RagEmbedder:
    """Manages ChromaDB collection and Ollama embeddings for context_docs/ files."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        docs_dir: str | Path = "context_docs",
    ) -> None:
        self.docs_dir = Path(docs_dir)
        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(_CHROMA_DIR))

        from langchain_ollama import OllamaEmbeddings
        self.embedder = OllamaEmbeddings(model=_EMBED_MODEL, base_url=base_url)

        self.collection = self.client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def sync(self) -> list[str]:
        """Embed any .md files that changed since last run. Returns rebuilt filenames."""
        manifest = _load_manifest()
        rebuilt: list[str] = []

        for md_file in sorted(self.docs_dir.glob("*.md")):
            current_hash = _md5(md_file)
            if manifest.get(md_file.name) == current_hash:
                continue
            self._embed_file(md_file)
            manifest[md_file.name] = current_hash
            rebuilt.append(md_file.name)

        if rebuilt:
            _save_manifest(manifest)
        return rebuilt

    def _embed_file(self, path: Path) -> None:
        source = path.name
        text = path.read_text(encoding="utf-8")
        chunks = _chunk_markdown(text)
        if not chunks:
            return

        # Remove any stale vectors for this source
        existing = self.collection.get(where={"source": source})
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        vectors = self.embedder.embed_documents(chunks)
        self.collection.add(
            ids=[f"{source}::{i}" for i in range(len(chunks))],
            embeddings=vectors,
            documents=chunks,
            metadatas=[{"source": source} for _ in chunks],
        )
