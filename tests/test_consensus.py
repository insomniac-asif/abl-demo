"""Consensus protocol: the core guarantee of the system."""

from abl_demo.consensus import ConsensusManager
from abl_demo.protocol import AgentID, Challenge, Proposal, Vote


def _proposal() -> Proposal:
    return Proposal(proposer=AgentID.AURORA, summary="do a thing", rationale="because")


def test_unanimous_approval_executes():
    p = _proposal()
    challenges = [
        Challenge(p.id, AgentID.BOREA, Vote.APPROVE, "fine"),
        Challenge(p.id, AgentID.LIS, Vote.APPROVE, "consistent"),
    ]
    decision = ConsensusManager().evaluate(p, challenges)
    assert decision.approved is True
    assert decision.unanimous is True
    assert decision.escalated_to_human is False


def test_single_reject_deadlocks_and_withholds_without_tiebreaker():
    p = _proposal()
    challenges = [
        Challenge(p.id, AgentID.BOREA, Vote.APPROVE, "fine"),
        Challenge(p.id, AgentID.LIS, Vote.REJECT, "contradicts precedent"),
    ]
    decision = ConsensusManager(tiebreaker=None).evaluate(p, challenges)
    assert decision.approved is False
    assert decision.escalated_to_human is True


def test_abstain_is_not_consent():
    p = _proposal()
    # Borea never weighs in -> stays ABSTAIN -> not unanimous.
    challenges = [Challenge(p.id, AgentID.LIS, Vote.APPROVE, "ok")]
    decision = ConsensusManager(tiebreaker=None).evaluate(p, challenges)
    assert decision.votes[AgentID.BOREA] is Vote.ABSTAIN
    assert decision.approved is False


def test_human_tiebreaker_can_break_deadlock():
    p = _proposal()
    challenges = [
        Challenge(p.id, AgentID.BOREA, Vote.APPROVE, "fine"),
        Challenge(p.id, AgentID.LIS, Vote.REJECT, "no"),
    ]
    # Operator overrides in favor of executing.
    decision = ConsensusManager(tiebreaker=lambda prop, votes: True).evaluate(
        p, challenges
    )
    assert decision.approved is True
    assert decision.escalated_to_human is True


def test_proposer_implicitly_approves():
    p = _proposal()
    decision = ConsensusManager(tiebreaker=None).evaluate(p, [])
    assert decision.votes[AgentID.AURORA] is Vote.APPROVE
