"""Bounded SHA-256 work that overlaps native hashing with document I/O.

There is at most one hashing thread and two outstanding payloads per active
pipeline. Small payloads stay synchronous to avoid thread/future scheduling costs.
No digest is optional: every result is awaited before verification/commit succeeds.
"""

import hashlib
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from types import TracebackType

from .errors import ImageDecodeError


def stream_digest(data: bytes) -> str:
    """Hash the exact compressed PDF stream without decoding or changing it."""
    return hashlib.sha256(data).hexdigest()


def image_stream_digest(data: bytes) -> str:
    """Hash JPEG bytes or concatenated PNG IDAT bytes in their embedded order."""
    if data.startswith(b"\xff\xd8"):
        return stream_digest(data)
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ImageDecodeError("direct stream digest requires JPEG or PNG")
    digest = hashlib.sha256()
    offset = 8
    view = memoryview(data)
    while offset + 12 <= len(data):
        length = int.from_bytes(view[offset:offset + 4], "big")
        kind = view[offset + 4:offset + 8]
        if offset + length + 12 > len(data):
            raise ImageDecodeError("invalid PNG chunk extent")
        if kind == b"IDAT":
            digest.update(view[offset + 8:offset + 8 + length])
        offset += length + 12
    return digest.hexdigest()


class DigestPipeline:
    """Own optional native hash work; backpressure bounds retained input payloads."""

    minimum_async_bytes = 256 * 1024

    def __init__(self) -> None:
        self._executor: ThreadPoolExecutor | None = None
        self._pending: deque[Future[str]] = deque()

    def _submit(self, operation: Callable[[bytes], str], data: bytes) -> Future[str]:
        if len(data) < self.minimum_async_bytes:
            future: Future[str] = Future()
            future.set_result(operation(data))
            return future
        if len(self._pending) >= 2:
            self._pending.popleft().result()
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cb2pdf-sha256")
        future = self._executor.submit(operation, data)
        self._pending.append(future)
        return future

    def image(self, data: bytes) -> Future[str]:
        """Schedule the expected embedded stream digest for a prepared image."""
        return self._submit(image_stream_digest, data)

    def stream(self, data: bytes) -> Future[str]:
        """Schedule an independent digest of an already serialized PDF stream."""
        return self._submit(stream_digest, data)

    def finish(self) -> None:
        """Propagate every outstanding failure before the stage can succeed."""
        while self._pending:
            self._pending.popleft().result()

    def __enter__(self) -> "DigestPipeline":
        return self

    def __exit__(
        self, exception_type: type[BaseException] | None,
        exception: BaseException | None, traceback: TracebackType | None,
    ) -> None:
        try:
            if exception_type is None:
                self.finish()
        finally:
            if self._executor is not None:
                self._executor.shutdown(wait=True, cancel_futures=True)
