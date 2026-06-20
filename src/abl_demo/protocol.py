"""Core message and action types that flow across the peer bus.

ABL has no hierarchy: Aurora, Borea, and Lis are peers. Every action follows the
same protocol — propose -> challenge -> execute — and nothing executes without
unanimous (3/3) consensus. These dataclasses are the vocabulary all three agents
speak on the bus.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentID(str, Enum):
    """The three peers. There is no fourth tier above them — a human operator is
    only ever consulted as a tiebreaker, never as a commander."""

    AURORA = "aurora"  # reasoning & planning
    BOREA = "borea"  # execution & tools
    LIS = "lis"  # memory & observation


ALL_AGENTS: tuple[AgentID, ...] = (AgentID.AURORA, AgentID.BOREA, AgentID.LIS)


class Phase(str, Enum):
    """The three beats of the action protocol."""

    PROPOSE = "propose"
    CHALLENGE = "challenge"
    EXECUTE = "execute"


class Vote(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"  # counts as non-approval; consensus needs all three to APPROVE


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass(frozen=True)
class Proposal:
    """An action one agent wants the collective to take."""

    proposer: AgentID
    summary: str
    rationale: str
    id: str = field(default_factory=_new_id)
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Challenge:
    """A peer's critique of a proposal, from that peer's domain of expertise."""

    proposal_id: str
    challenger: AgentID
    vote: Vote
    reasoning: str
    id: str = field(default_factory=_new_id)
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Decision:
    """The outcome of a consensus round."""

    proposal_id: str
    approved: bool
    votes: dict[AgentID, Vote]
    escalated_to_human: bool
    note: str

    @property
    def unanimous(self) -> bool:
        return all(v is Vote.APPROVE for v in self.votes.values())


@dataclass(frozen=True)
class Message:
    """A single envelope on the peer bus. Everything is traceable: who said what,
    when, about which proposal."""

    sender: AgentID
    topic: str
    payload: Any
    id: str = field(default_factory=_new_id)
    created_at: float = field(default_factory=time.time)
