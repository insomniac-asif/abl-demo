"""The peer bus.

All inter-agent communication flows through one shared bus — no agent calls
another directly, because direct calls are how hierarchies sneak in. The bus is
a simple synchronous pub/sub with a full, ordered transcript so every decision
is auditable after the fact (observability is non-negotiable in a multi-agent
system).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .protocol import AgentID, Message

logger = logging.getLogger("abl_demo.bus")

Handler = Callable[[Message], None]


class PeerBus:
    """A shared, observable message bus.

    Subscribers register interest in a topic and receive every message published
    to it. The bus keeps an append-only transcript so the whole conversation can
    be replayed — this is the demo's stand-in for ABL's persisted bus log.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[tuple[AgentID, Handler]]] = {}
        self._transcript: list[Message] = []

    def subscribe(self, topic: str, agent: AgentID, handler: Handler) -> None:
        self._subscribers.setdefault(topic, []).append((agent, handler))
        logger.debug("%s subscribed to %s", agent.value, topic)

    def publish(self, sender: AgentID, topic: str, payload: Any) -> Message:
        msg = Message(sender=sender, topic=topic, payload=payload)
        self._transcript.append(msg)
        logger.info("[bus] %s -> %s", sender.value, topic)
        for agent, handler in self._subscribers.get(topic, []):
            if agent == sender:
                continue  # an agent doesn't react to its own broadcast
            handler(msg)
        return msg

    @property
    def transcript(self) -> list[Message]:
        """The full ordered history of everything said on the bus."""
        return list(self._transcript)

    def replay(self) -> str:
        """Human-readable transcript — the audit trail."""
        lines = []
        for m in self._transcript:
            lines.append(f"{m.created_at:.3f}  {m.sender.value:>6}  {m.topic}")
        return "\n".join(lines)
