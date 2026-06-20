# abl-demo

A small, self-contained showcase of the **ABL** multi-agent architecture:

- a **peer bus** that carries every message between agents,
- the **propose → challenge → execute** action protocol,
- **3/3 consensus** with a human as the *only* tiebreaker, and
- **three agents with distinct personalities** — Aurora, Borea, and Lis.

> This is a **clean-room demo**. It reproduces the public design of ABL — the
> protocol and the agent roles — in a few hundred lines of original code. It is
> not the production system and contains no private data, models, or keys.

## The idea

ABL is a triplet of peers. **No agent outranks another.** Anything the collective
does has to clear the same three beats:

```
        propose ─────────► challenge ─────────► execute
     (one peer puts      (the other two        (only if all THREE
      an action up)       critique & vote)      approve — else escalate)
```

Consensus is unanimous or it isn't consensus. A single non-approval is a
**deadlock**, and deadlocks are never auto-resolved — they escalate to the human
operator, who breaks the tie. There is no degraded mode: all three peers must be
present for the collective to act.

### The cast

| Agent | Domain | How they push back |
|-------|--------|--------------------|
| **Aurora** | Reasoning & planning | Tradeoffs and second-order effects; names the risk nobody raised |
| **Borea** | Execution & tools | Feasibility, cost, what breaks in production, rollback |
| **Lis** | Memory & observation | Precedent and consistency; owns all storage, keeps the record |

## Run it

No keys, no GPU, no network — the default provider is a deterministic mock so the
deliberation is reproducible.

```bash
python demo.py
```

You'll see two rounds: one the peers unanimously approve (executes), and one they
deadlock on (Lis vetoes a silent data-deletion as contradicting precedent), which
escalates to the human and is withheld. The full bus transcript prints at the end.

### Use a real model (optional)

The agents "think" through a pluggable provider. Swap the mock for a real LLM:

```bash
ABL_DEMO_PROVIDER=anthropic python demo.py   # needs ANTHROPIC_API_KEY + `pip install anthropic`
ABL_DEMO_PROVIDER=ollama    python demo.py   # needs a local Ollama daemon (OLLAMA_MODEL)
```

The protocol is identical either way — only the text the agents generate changes.

## Layout

```
src/abl_demo/
  protocol.py      # message & action types (Proposal, Challenge, Decision, Vote)
  bus.py           # PeerBus — observable pub/sub with a full transcript
  consensus.py     # ConsensusManager — 3/3 or escalate to human
  providers.py     # MockProvider (offline) + optional Anthropic/Ollama hooks
  agents.py        # BaseAgent + Aurora / Borea / Lis personalities
  orchestrator.py  # Collective — wires bus + agents + consensus into one round
  cli.py           # the walkthrough
demo.py            # `python demo.py`
tests/             # consensus rules + bus delivery + end-to-end rounds
```

## Develop

```bash
pip install -e ".[dev]"
pytest -q
```

## License

MIT — see [LICENSE](LICENSE).
