"""Peer bus message passing + a full end-to-end round."""

from abl_demo.bus import PeerBus
from abl_demo.orchestrator import Collective
from abl_demo.protocol import AgentID, Vote
from abl_demo.providers import MockProvider


def test_bus_delivers_to_subscribers_but_not_sender():
    bus = PeerBus()
    seen: list[str] = []
    bus.subscribe("t", AgentID.BOREA, lambda m: seen.append(m.payload))
    bus.subscribe("t", AgentID.AURORA, lambda m: seen.append("aurora-should-not-see"))
    bus.publish(AgentID.AURORA, "t", "hello")  # sender is Aurora
    assert seen == ["hello"]  # Borea heard it; Aurora did not echo to itself
    assert len(bus.transcript) == 1


def test_round_executes_on_unanimous_script():
    script = {
        "[aurora|propose] task: ship it": "lgtm",
        "[borea|challenge] proposal: ship it": "no concern",
        "[lis|challenge] proposal: ship it": "consistent, recording it",
    }
    c = Collective(provider=MockProvider(script))
    decision = c.run_round("ship it", proposer=AgentID.AURORA)
    assert decision.approved is True
    assert all(v is Vote.APPROVE for v in decision.votes.values())
    # Lis persisted the decision (memory is her domain).
    assert len(c.lis.memory) == 1


def test_round_withholds_when_a_peer_vetoes():
    script = {
        "[aurora|propose] task: risky": "i'm unsure but proposing",
        "[borea|challenge] proposal: risky": "no concern",
        "[lis|challenge] proposal: risky": "REJECT, contradicts precedent",
    }
    c = Collective(provider=MockProvider(script), tiebreaker=lambda p, v: False)
    decision = c.run_round("risky", proposer=AgentID.AURORA)
    assert decision.approved is False
    assert decision.escalated_to_human is True
    assert decision.votes[AgentID.LIS] is Vote.REJECT
