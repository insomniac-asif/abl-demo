"""abl-demo — a small, self-contained showcase of the ABL architecture.

Public surface: the peer bus, the propose -> challenge -> execute protocol with
3/3 consensus (human as sole tiebreaker), and three agents with distinct
personalities. This is a clean-room demo — it mirrors the design, not the
private implementation.
"""

from .bus import PeerBus
from .consensus import ConsensusManager
from .orchestrator import Collective
from .protocol import (
    ALL_AGENTS,
    AgentID,
    Challenge,
    Decision,
    Phase,
    Proposal,
    Vote,
)

__all__ = [
    "PeerBus",
    "ConsensusManager",
    "Collective",
    "ALL_AGENTS",
    "AgentID",
    "Challenge",
    "Decision",
    "Phase",
    "Proposal",
    "Vote",
]

__version__ = "0.1.0"
