"""Gateway message types for channel-agnostic communication.

All types are frozen dataclasses to guarantee immutability across the
pipeline: adapter -> gateway -> brain -> adapter.
"""
from __future__ import annotations

import time
import types as _types
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Attachment:
    """A file or media item attached to a message.

    Attributes:
        type: Kind of attachment (e.g. ``"image"``, ``"file"``, ``"audio"``).
        url: Remote URL if the attachment is hosted externally.
        data: Raw bytes when the attachment is inline.
        filename: Original filename, if known.
        mime_type: MIME type (e.g. ``"text/plain"``), if known.
    """

    type: str
    url: str | None = None
    data: bytes | None = None
    filename: str | None = None
    mime_type: str | None = None


@dataclass(frozen=True)
class InboundMessage:
    """A message arriving from an external channel.

    Attributes:
        channel: Name of the originating channel (e.g. ``"cli"``,
            ``"telegram"``).
        sender_id: Identifier for the message author within that channel.
        text: The textual content of the message.
        attachments: Zero or more :class:`Attachment` objects.  Stored as a
            tuple to preserve frozen immutability.
        reply_to: Optional identifier of the message being replied to.
        timestamp: Unix epoch float; defaults to the current time.
        metadata: Arbitrary channel-specific key/value pairs.
    """

    channel: str
    sender_id: str
    text: str
    attachments: tuple[Attachment, ...] = ()
    reply_to: str | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Wrap mutable dict in a read-only proxy
        object.__setattr__(self, "metadata", _types.MappingProxyType(self.metadata))


@dataclass(frozen=True)
class OutboundMessage:
    """A message to be delivered to an external channel.

    Attributes:
        channel: Target channel name.
        recipient_id: Identifier for the intended recipient.
        text: The textual content to send.
        attachments: Zero or more :class:`Attachment` objects.
        reply_to: Optional identifier of the message being replied to.
        metadata: Arbitrary channel-specific key/value pairs.
    """

    channel: str
    recipient_id: str
    text: str
    attachments: tuple[Attachment, ...] = ()
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Wrap mutable dict in a read-only proxy
        object.__setattr__(self, "metadata", _types.MappingProxyType(self.metadata))
