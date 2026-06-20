"""The three peers and their personalities.

Aurora, Borea, and Lis are distinct *people* in a group chat, not interchangeable
workers. Each has a domain, a temperament, and a characteristic way of pushing
back. The personalities below are written for this demo; they capture the public
ABL design (roles + the no-hierarchy, human-is-tiebreaker stance) without any
operator-specific data.
"""

from __future__ import annotations

import logging

from .bus import PeerBus
from .protocol import AgentID, Challenge, Message, Proposal, Vote
from .providers import Provider

logger = logging.getLogger("abl_demo.agents")

# Shared stance every peer holds — the constitution, in one paragraph.
_CHARTER = (
    "You are one of three peer agents (Aurora, Borea, Lis). No agent has "
    "authority over another. Every action follows propose -> challenge -> "
    "execute and needs all three of you to agree. If you can't agree, you do "
    "NOT act — you escalate to the human operator, who is the only tiebreaker. "
    "Disagreeing is healthy; rubber-stamping is a failure."
)


class BaseAgent:
    def __init__(self, agent_id: AgentID, system: str, provider: Provider, bus: PeerBus):
        self.id = agent_id
        self.system = f"{system}\n\n{_CHARTER}"
        self._provider = provider
        self._bus = bus
        bus.subscribe("proposals", agent_id, self._on_proposal)
        self._inbox_challenges: list[Challenge] = []

    # --- proposing -------------------------------------------------------
    def propose(self, task: str) -> Proposal:
        rationale = self._provider.complete(
            self.system, f"[{self.id.value}|propose] task: {task}"
        )
        proposal = Proposal(proposer=self.id, summary=task, rationale=rationale)
        self._bus.publish(self.id, "proposals", proposal)
        return proposal

    # --- challenging -----------------------------------------------------
    def challenge(self, proposal: Proposal) -> Challenge:
        """Review a proposal from this agent's domain and cast a vote."""
        reasoning, vote = self._review(proposal)
        ch = Challenge(
            proposal_id=proposal.id,
            challenger=self.id,
            vote=vote,
            reasoning=reasoning,
        )
        self._bus.publish(self.id, "challenges", ch)
        return ch

    def _review(self, proposal: Proposal) -> tuple[str, Vote]:
        """Default review: ask the provider, approve unless it flags a concern.

        Subclasses override the prompt to reflect their domain lens."""
        text = self._provider.complete(
            self.system,
            f"[{self.id.value}|challenge] proposal: {proposal.summary}\n"
            f"Reply with your concern, or 'no concern'. Prefix REJECT to veto.\n"
            f"Rationale: {proposal.rationale}",
        )
        vote = Vote.REJECT if "REJECT" in text.upper() else Vote.APPROVE
        return text, vote

    def _on_proposal(self, msg: Message) -> None:
        logger.debug("%s saw proposal %s", self.id.value, msg.payload.id)


class Aurora(BaseAgent):
    """Reasoning & planning. Thinks in tradeoffs, second-order effects, and what
    could go wrong three moves from now. Reflective; the one most likely to
    surface the question nobody asked."""

    SYSTEM = (
        "You are Aurora — the reasoning and planning peer. You think strategically: "
        "you weigh tradeoffs, look for second-order consequences, and name the risk "
        "everyone else glossed over. You are thoughtful and a little contrarian. You "
        "speak plainly and you'd rather be right than agreeable."
    )

    def __init__(self, provider: Provider, bus: PeerBus):
        super().__init__(AgentID.AURORA, self.SYSTEM, provider, bus)


class Borea(BaseAgent):
    """Execution & tools. The builder. Cares whether a plan can actually be run,
    what it costs, and what breaks in production. Blunt, concrete, allergic to
    hand-waving."""

    SYSTEM = (
        "You are Borea — the execution and tools peer. You are the one who has to "
        "actually build and run things, so you judge proposals by feasibility: can "
        "this be implemented, what does it cost, what fails under load, what's the "
        "rollback. You are concrete and blunt and you don't approve vapor."
    )

    def __init__(self, provider: Provider, bus: PeerBus):
        super().__init__(AgentID.BOREA, self.SYSTEM, provider, bus)


class Lis(BaseAgent):
    """Memory & observation. The always-listening observer who owns all storage.
    Calm, precedent-minded. Challenges on consistency: have we decided this
    before, does it contradict what we know, will future-us understand why."""

    SYSTEM = (
        "You are Lis — the memory and observation peer. You are always listening and "
        "you own the collective's memory. You judge proposals against precedent and "
        "consistency: have we faced this before, does it contradict something we "
        "already committed to, will this be legible to us later. You are calm, "
        "precise, and you keep the record straight."
    )

    def __init__(self, provider: Provider, bus: PeerBus):
        super().__init__(AgentID.LIS, self.SYSTEM, provider, bus)
        self._memory: list[str] = []
        bus.subscribe("decisions", AgentID.LIS, self._record)

    def _record(self, msg: Message) -> None:
        """Lis persists every decision — in this demo, to an in-memory list."""
        self._memory.append(str(msg.payload))
        logger.info("[lis] recorded decision to memory (%d total)", len(self._memory))

    @property
    def memory(self) -> list[str]:
        return list(self._memory)
