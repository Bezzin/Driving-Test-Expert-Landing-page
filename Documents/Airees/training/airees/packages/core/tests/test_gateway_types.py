"""Tests for gateway message types: Attachment, InboundMessage, OutboundMessage."""
from __future__ import annotations

import time

import pytest

from airees.gateway.types import Attachment, InboundMessage, OutboundMessage


# -- Attachment ---------------------------------------------------------------


def test_attachment_creation():
    att = Attachment(type="image", url="https://example.com/img.png")
    assert att.type == "image"
    assert att.url == "https://example.com/img.png"
    assert att.data is None
    assert att.filename is None
    assert att.mime_type is None


def test_attachment_with_all_fields():
    att = Attachment(
        type="file",
        url=None,
        data=b"hello",
        filename="doc.txt",
        mime_type="text/plain",
    )
    assert att.type == "file"
    assert att.data == b"hello"
    assert att.filename == "doc.txt"
    assert att.mime_type == "text/plain"


def test_attachment_frozen():
    att = Attachment(type="image")
    with pytest.raises(AttributeError):
        att.type = "video"


# -- InboundMessage -----------------------------------------------------------


def test_inbound_message_creation():
    msg = InboundMessage(channel="cli", sender_id="user-1", text="hello")
    assert msg.channel == "cli"
    assert msg.sender_id == "user-1"
    assert msg.text == "hello"
    assert msg.attachments == ()
    assert msg.reply_to is None
    assert msg.metadata == {}


def test_inbound_message_timestamp_default():
    before = time.time()
    msg = InboundMessage(channel="cli", sender_id="u1", text="hi")
    after = time.time()
    assert before <= msg.timestamp <= after


def test_inbound_message_with_attachments():
    att = Attachment(type="image", url="https://example.com/a.png")
    msg = InboundMessage(
        channel="telegram",
        sender_id="user-2",
        text="look at this",
        attachments=(att,),
    )
    assert len(msg.attachments) == 1
    assert msg.attachments[0].url == "https://example.com/a.png"


def test_inbound_message_frozen():
    msg = InboundMessage(channel="cli", sender_id="u", text="t")
    with pytest.raises(AttributeError):
        msg.text = "changed"


def test_inbound_message_with_reply_to():
    msg = InboundMessage(
        channel="cli", sender_id="u1", text="reply", reply_to="msg-42"
    )
    assert msg.reply_to == "msg-42"


def test_inbound_message_with_metadata():
    msg = InboundMessage(
        channel="cli",
        sender_id="u1",
        text="hi",
        metadata={"priority": "high"},
    )
    assert msg.metadata["priority"] == "high"


# -- OutboundMessage ----------------------------------------------------------


def test_outbound_message_creation():
    msg = OutboundMessage(channel="cli", recipient_id="user-1", text="response")
    assert msg.channel == "cli"
    assert msg.recipient_id == "user-1"
    assert msg.text == "response"
    assert msg.attachments == ()
    assert msg.reply_to is None
    assert msg.metadata == {}


def test_outbound_message_with_attachments():
    att = Attachment(type="file", filename="report.pdf")
    msg = OutboundMessage(
        channel="telegram",
        recipient_id="user-2",
        text="here is the report",
        attachments=(att,),
    )
    assert len(msg.attachments) == 1
    assert msg.attachments[0].filename == "report.pdf"


def test_outbound_message_frozen():
    msg = OutboundMessage(channel="cli", recipient_id="u", text="t")
    with pytest.raises(AttributeError):
        msg.text = "changed"


def test_outbound_message_with_reply_to():
    msg = OutboundMessage(
        channel="cli", recipient_id="u1", text="reply", reply_to="msg-99"
    )
    assert msg.reply_to == "msg-99"


def test_outbound_message_with_metadata():
    msg = OutboundMessage(
        channel="cli",
        recipient_id="u1",
        text="hi",
        metadata={"source": "brain"},
    )
    assert msg.metadata["source"] == "brain"
