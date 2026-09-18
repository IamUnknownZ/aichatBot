from __future__ import annotations

import time
from collections.abc import Iterable

import numpy as np
from google import genai
from google.genai import types
from google.genai.errors import APIError


class GeminiEmbedder:
    def __init__(
        self,
        *,
        api_key: str,
        text_model: str,
        multimodal_model: str,
        output_dimensionality: int = 768,
        batch_size: int = 16,
        max_retries: int = 4,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.client = genai.Client(api_key=api_key)
        self.text_model = text_model
        self.multimodal_model = multimodal_model
        self.output_dimensionality = output_dimensionality
        self.batch_size = max(1, batch_size)
        self.max_retries = max(0, max_retries)

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        arr = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(arr))
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    def _text_config(self, task_type: str) -> types.EmbedContentConfig:
        kwargs: dict[str, object] = {
            "output_dimensionality": self.output_dimensionality
        }
        if self.text_model.endswith("embedding-001"):
            kwargs["task_type"] = task_type
        return types.EmbedContentConfig(**kwargs)

    def _embed_with_retry(
        self,
        *,
        model: str,
        contents,
        config: types.EmbedContentConfig,
    ):
        for attempt in range(self.max_retries + 1):
            try:
                return self.client.models.embed_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            except APIError as exc:
                status = getattr(exc, "code", None) or getattr(
                    exc, "status_code", None
                )
                retryable = status == 429 or (
                    isinstance(status, int) and 500 <= status < 600
                )
                if not retryable or attempt >= self.max_retries:
                    raise

                # Bounded exponential backoff. Indexing is an offline/setup task;
                # normal user queries should usually need only one embedding call.
                time.sleep(min(2 ** attempt, 8))

        raise RuntimeError("Embedding retry loop ended unexpectedly")

    def embed_texts(
        self,
        texts: Iterable[str],
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        items = [text for text in texts if text and text.strip()]
        vectors: list[list[float]] = []

        for start in range(0, len(items), self.batch_size):
            batch = items[start : start + self.batch_size]
            response = self._embed_with_retry(
                model=self.text_model,
                contents=batch,
                config=self._text_config(task_type),
            )
            vectors.extend(
                self._normalize(embedding.values)
                for embedding in (response.embeddings or [])
            )

        if len(vectors) != len(items):
            raise RuntimeError(
                f"Embedding count mismatch: expected {len(items)}, got {len(vectors)}"
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_texts([text], task_type="RETRIEVAL_QUERY")
        return vectors[0]

    def embed_image(self, image_bytes: bytes, mime_type: str) -> list[float]:
        response = self._embed_with_retry(
            model=self.multimodal_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            ],
            config=types.EmbedContentConfig(
                output_dimensionality=self.output_dimensionality
            ),
        )
        if not response.embeddings:
            raise RuntimeError("Gemini returned no image embedding")
        return self._normalize(response.embeddings[0].values)
