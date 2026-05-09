from __future__ import annotations

import hashlib


class LocalHashEmbedder:
    """Deterministic pseudo-embedder for tests. Not semantically meaningful."""

    def __init__(self, dimension: int = 384) -> None:
        if dimension <= 0:
            raise ValueError('dimension must be positive')
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        values: list[float] = []
        seed = text.encode('utf-8')
        counter = 0
        while len(values) < self.dimension:
            digest = hashlib.sha256(seed + counter.to_bytes(4, 'big')).digest()
            counter += 1
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) >= self.dimension:
                    break
        return values

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embed(query)


class SentenceTransformerEmbedder:
    """Production-quality embedder using sentence-transformers.

    Default model: ``BAAI/bge-small-en-v1.5`` (384-dim, matches pgvector schema).
    Model is lazily loaded on first call.
    """

    def __init__(
        self,
        model_name: str = 'BAAI/bge-small-en-v1.5',
        batch_size: int = 32,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None

    @property
    def dimension(self) -> int:
        model = self._load_model()
        dim = model.get_sentence_embedding_dimension()
        return int(dim) if dim is not None else 384

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    'sentence-transformers is required for SentenceTransformerEmbedder. '
                    'Install with: pip install sentence-transformers'
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
