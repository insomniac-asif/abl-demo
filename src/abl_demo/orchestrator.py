"""Wires the bus, the three peers, and the consensus manager into one round.

A round is the whole protocol end to end: one peer proposes, the other two
challenge from their domains, consensus is evaluated (3/3 or escalate), and if
approved the decision is published so Lis can record it.
"""

from __future__ import annotations

import logging

from .agents import Aurora, Borea, Lis
from .bus import PeerBus
from .consensus import ConsensusManager, HumanTiebreaker
from .protocol import AgentID, Decision, Proposal
from .providers import Provider, provider_from_env

logger = logging.getLogger("abl_demo.orchestrator")


class Collective:
    """The ABL triplet operating as peers over a shared bus."""

    def __init__(
        self,
        provider: Provider | None = None,
        tiebreaker: HumanTiebreaker | None = None,
    ) -> None:
        self.bus = PeerBus()
        provider = provider or provider_from_env()
        self.aurora = Aurora(provider, self.bus)
        self.borea = Borea(provider, self.bus)
        self.lis = Lis(provider, self.bus)
        self.consensus = ConsensusManager(tiebreaker=tiebreaker)
        self._agents = {
            AgentID.AURORA: self.aurora,
            AgentID.BOREA: self.borea,
            AgentID.LIS: self.lis,
        }

    def run_round(self, task: str, proposer: AgentID = AgentID.AURORA) -> Decision:
        """Execute one propose -> challenge -> execute cycle.

        All three peers must be present — there is no degraded mode. If a peer
        were missing we would refuse to operate rather than proceed with two.
        """
        if set(self._agents) != {AgentID.AURORA, AgentID.BOREA, AgentID.LIS}:
            raise RuntimeError("all three peers must be online; refusing to operate")

        logger.info("[round] task=%r proposer=%s", task, proposer.value)
        proposal: Proposal = self._agents[proposer].propose(task)

        challenges = [
            self._agents[aid].challenge(proposal)
            for aid in self._agents
            if aid != proposer
        ]

        decision = self.consensus.evaluate(proposal, challenges)
        # Publishing the decision lets Lis persist it (memory is her domain).
        self.bus.publish(proposer, "decisions", decision)
        return decision
