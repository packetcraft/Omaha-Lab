_TOP_K = 3


class RagRetriever:
    """Queries the ChromaDB collection and returns the top-k most relevant chunks."""

    def __init__(self, collection, embedder) -> None:
        self.collection = collection
        self._embedder = embedder

    def retrieve(self, query: str) -> list[dict]:
        """Return up to TOP_K chunks as list of {text, source, distance} dicts."""
        total = self.collection.count()
        if total == 0:
            return []

        query_vector = self._embedder.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=min(_TOP_K, total),
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "distance": round(float(dist), 4),
                }
            )
        return chunks
