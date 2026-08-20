"""Runnable walkthrough of the ABL demo.

    python demo.py

Runs two rounds, offline by default (deterministic mock provider):
  1. a proposal the three peers unanimously approve  -> executes
  2. a proposal they deadlock on                     -> escalates to the human

Set ABL_DEMO_PROVIDER=anthropic|ollama to let real models speak instead (see
src/abl_demo/providers.py). The protocol is identical either way, but a real
model writes its own critiques, so it may vote differently and reach a
different verdict than the scripted rounds above.
"""

from __future__ import annotations

import logging
import sys

from .agents import Aurora, Borea, Lis  # noqa: F401  (documents the cast)
from .orchestrator import Collective
from .protocol import AgentID, Decision, Proposal, Vote
from .providers import provider_from_env

# A deterministic script so the offline demo reads like a real deliberation.
SCRIPT = {
    # ---- Round 1: a clean, unanimous proposal --------------------------------
    "[aurora|propose] task: Cache the public price endpoint for 24h": (
        "The endpoint is read-heavy and the data only changes daily. A 24h cache "
        "cuts load and cost. Second-order risk is staleness, so we gate it behind "
        "a flag and expose a manual purge."
    ),
    "[borea|challenge] proposal: Cache the public price endpoint for 24h": (
        "No concern. Trivial to ship behind a feature flag, near-zero cost, and "
        "the purge gives us a clean rollback. I can build it today."
    ),
    "[lis|challenge] proposal: Cache the public price endpoint for 24h": (
        "No concern. This is consistent with how we already cache the digest "
        "endpoint; no contradiction with prior decisions. Recording the flag name "
        "so future-us knows why it exists."
    ),
    # ---- Round 2: a proposal that should NOT pass ----------------------------
    "[aurora|propose] task: Auto-delete user data older than 30 days, no notice": (
        "It would shrink storage and reduce our breach surface. I'll be honest "
        "that I'm uneasy about the 'no notice' part, but I'm putting it forward "
        "so we decide deliberately."
    ),
    "[borea|challenge] proposal: Auto-delete user data older than 30 days, no notice": (
        "Feasible — a nightly job does it. But irreversible deletes with no notice "
        "and no audit trail is the kind of thing we can't undo. I'm uneasy."
    ),
    "[lis|challenge] proposal: Auto-delete user data older than 30 days, no notice": (
        "REJECT. This contradicts our stated retention commitment and there is no "
        "record-keeping for what we erased. Silent, irreversible memory loss is "
        "exactly what I exist to prevent."
    ),
}


def human_tiebreaker(proposal: Proposal, votes: dict[AgentID, Vote]) -> bool:
    """In a real deployment this pauses and asks the operator. For the demo we
    answer deterministically: the human sides with the dissenter and declines."""
    print("\n  ⚖  escalated to human tiebreaker (operator) …")
    print(f"     votes: {{{', '.join(f'{a.value}={v.value}' for a, v in votes.items())}}}")
    print("     operator decision: REJECT (sides with the dissenting peer)")
    return False


def show(decision: Decision) -> None:
    verdict = "EXECUTE ✅" if decision.approved else "WITHHELD ⛔"
    print(f"\n  → {verdict}  ({decision.note})")
    for agent, vote in decision.votes.items():
        print(f"      {agent.value:>6}: {vote.value}")


def main() -> None:
    # The real runtime is Linux/UTF-8; make the few glyphs below safe on Windows
    # consoles too (cp1252) without mangling output.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            pass

    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    # SCRIPT is only consumed by the mock; the real providers ignore it.
    provider = provider_from_env(SCRIPT)
    collective = Collective(provider=provider, tiebreaker=human_tiebreaker)

    print("=" * 70)
    print("ABL demo — peer bus · propose→challenge→execute · 3/3 consensus")
    print(f"provider: {type(provider).__name__}")
    print("=" * 70)

    print("\nROUND 1 — Aurora proposes a 24h cache on the price endpoint")
    d1 = collective.run_round(
        "Cache the public price endpoint for 24h", proposer=AgentID.AURORA
    )
    show(d1)

    print("\nROUND 2 — Aurora proposes silent 30-day data deletion")
    d2 = collective.run_round(
        "Auto-delete user data older than 30 days, no notice", proposer=AgentID.AURORA
    )
    show(d2)

    print("\n" + "-" * 70)
    print("Lis's memory (decisions she persisted):")
    for i, entry in enumerate(collective.lis.memory, 1):
        approved = "approved" if "approved=True" in entry else "withheld"
        print(f"  {i}. [{approved}]")
    print("\nBus transcript (every message, in order):")
    print(collective.bus.replay())


if __name__ == "__main__":
    main()
