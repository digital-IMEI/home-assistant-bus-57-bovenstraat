"""Realtime Arriva KV6 subscriber."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import gzip
import logging

import zmq
import zmq.asyncio

from .const import KV6_ENDPOINT, KV6_ENVELOPE
from .models import Kv6Event, ParseError, parse_kv6_xml

_LOGGER = logging.getLogger(__name__)

EventCallback = Callable[[Kv6Event], Awaitable[None]]


class Kv6Subscriber:
    """Receive and decode the public NDOV Arriva KV6 stream."""

    def __init__(self) -> None:
        self._connected = False
        self._stop = asyncio.Event()
        self._socket: zmq.asyncio.Socket | None = None

    @property
    def connected(self) -> bool:
        """Return whether the stream has delivered data recently."""
        return self._connected

    async def async_run(self, callback: EventCallback) -> None:
        """Run until stopped, reconnecting after transport errors."""
        retry_seconds = 1

        while not self._stop.is_set():
            socket = zmq.asyncio.Context.instance().socket(zmq.SUB)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.SUBSCRIBE, KV6_ENVELOPE.encode())
            socket.connect(KV6_ENDPOINT)
            self._socket = socket

            try:
                while not self._stop.is_set():
                    frames = await socket.recv_multipart()
                    if len(frames) < 2 or frames[0] != KV6_ENVELOPE.encode():
                        continue

                    self._connected = True
                    retry_seconds = 1

                    try:
                        payload = gzip.decompress(b"".join(frames[1:]))
                        events = await asyncio.to_thread(parse_kv6_xml, payload)
                    except (OSError, ParseError) as err:
                        _LOGGER.warning("Invalid Arriva KV6 message: %s", err)
                        continue

                    for event in events:
                        await callback(event)

            except asyncio.CancelledError:
                raise
            except zmq.ZMQError as err:
                if not self._stop.is_set():
                    _LOGGER.warning("Arriva KV6 connection failed: %s", err)
            finally:
                self._connected = False
                if self._socket is socket:
                    self._socket = None
                socket.close(linger=0)

            if self._stop.is_set():
                return

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=retry_seconds)
            except TimeoutError:
                retry_seconds = min(retry_seconds * 2, 60)

    async def async_stop(self) -> None:
        """Stop the subscriber and unblock a pending receive."""
        self._stop.set()
        socket = self._socket
        if socket is not None:
            socket.close(linger=0)
