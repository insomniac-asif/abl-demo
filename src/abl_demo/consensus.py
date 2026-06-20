"""Consensus protocol.

The rule is deliberately strict: an action executes only if all three peers vote
APPROVE. Anything less is a deadlock, and deadlocks are not auto-resolved — they
escalate to the human operator, who is the *only* tiebreaker. There is no
degraded mode and no fast path that skips a vote; the entire point is that all
three agents agree before the collective acts.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from .protocol import (
    ALL_AGENTS,
    AgentID,
    Challenge,
    Decision,
    Proposal,
    Vote,
)

logger = logging.getLogger("abl_demo.consensus")

# A tiebreaker is asked a yes/no question and returns True (approve) / False.
HumanTiebreaker = Callable[[Proposal, dict[AgentID, Vote]], bool]


class ConsensusManager:
    """Collects votes for a proposal and renders a Decision.

    Requires 3/3 APPROVE to pass. On any non-unanimous outcome it escalates to
    the supplied human tiebreaker rather than guessing.
    """

    def __init__(self, tiebreaker: HumanTiebreaker | None = None) -> None:
        self._tiebreaker = tiebreaker

    def evaluate(
        self, proposal: Proposal, challenges: list[Challenge]
    ) -> Decision:
        votes = self._collect_votes(proposal, challenges)

        if all(v is Vote.APPROVE for v in votes.values()):
            logger.info("[consensus] 3/3 APPROVE on %s", proposal.id)
            return Decision(
                proposal_id=proposal.id,
                approved=True,
                votes=votes,
                escalated_to_human=False,
                note="unanimous approval",
            )

        # Not unanimous -> deadlock. Do not auto-resolve; escalate to the human.
        logger.info(
            "[consensus] deadlock on %s (%s) -> escalating to human",
            proposal.id,
            self._vote_summary(votes),
        )
        if self._tiebreaker is None:
            return Decision(
                proposal_id=proposal.id,
                approved=False,
                votes=votes,
                escalated_to_human=True,
                note="deadlock; no tiebreaker available -> action withheld",
            )

        human_approved = self._tiebreaker(proposal, votes)
        return Decision(
            proposal_id=proposal.id,
            approved=human_approved,
            votes=votes,
            escalated_to_human=True,
            note=(
                "human tiebreaker approved"
                if human_approved
                else "human tiebreaker rejected"
            ),
        )

    @staticmethod
    def _collect_votes(
        proposal: Proposal, challenges: list[Challenge]
    ) -> dict[AgentID, Vote]:
        """Map each peer to its vote.

        The proposer implicitly approves its own proposal. Any peer that never
        weighed in is treated as ABSTAIN — which, because we demand unanimity,
        is enough to withhold the action (silence is not consent)."""
        votes: dict[AgentID, Vote] = {a: Vote.ABSTAIN for a in ALL_AGENTS}
        votes[proposal.proposer] = Vote.APPROVE
        for ch in challenges:
            if ch.challenger == proposal.proposer:
                continue
            votes[ch.challenger] = ch.vote
        return votes

    @staticmethod
    def _vote_summary(votes: dict[AgentID, Vote]) -> str:
        return ", ".join(f"{a.value}={v.value}" for a, v in votes.items())
