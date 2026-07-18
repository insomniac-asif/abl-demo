# abl-demo

A small, self-contained demo of a three-peer multi-agent architecture where no
agent outranks another, every action must clear a `propose → challenge → execute`
protocol, and a decision only stands with unanimous (3/3) consensus — otherwise
it escalates to a human. It reproduces the public design of ABL in a few hundred
lines of standard-library Python, with no private data, models, or keys.

## What it does

`abl-demo` runs a scripted deliberation between three peer agents — Aurora,
Borea, and Lis — over a shared message bus. Each proposed action is critiqued and
voted on by the peers; it executes only if all three approve, and any
non-approval is a deadlock that is withheld and escalated to a human tiebreaker
rather than auto-resolved. The default run (`python demo.py`) walks through two
rounds — one the peers unanimously approve and execute, and one they deadlock on
(Lis vetoes a silent data-deletion as contradicting precedent), which escalates
and is withheld — and prints the full bus transcript at the end.

## Why

Multi-agent setups often quietly resolve disagreement — a lead agent overrides
peers, a majority outvotes a dissenter, or a timeout lets an action through. That
hides exactly the moments a human should see. This demo takes the opposite stance
as a concrete, readable artifact: consensus is unanimous or it is not consensus,
silence counts as abstain (not consent), there is no degraded or fast path, and a
single objection surfaces to a person instead of being smoothed over. It is a
minimal reference for what "the collective doesn't act unless all peers agree"
looks like in code.

## Install

The demo has **no runtime dependencies** — it runs on the Python standard library
(requires Python >= 3.10). You can run it straight from a clone:

```bash
git clone https://github.com/insomniac-asif/abl-demo
cd abl-demo
python demo.py
```

Optional extras (only if you want them):

```bash
pip install -e ".[dev]"        # dev: pytest, for running the test suite
pip install anthropic          # only needed for the real-model (anthropic) provider
```

## Quickstart

Run the offline walkthrough — deterministic, no keys, no network, no GPU (the
default provider is a mock):

```bash
python demo.py
```

Installing the package also exposes an equivalent console script (both call
`abl_demo.cli:main`):

```bash
pip install -e .
abl-demo
```

### Use a real model (optional)

The agents' reasoning text comes from a pluggable provider. The protocol is
identical whichever provider is selected — only the generated text changes:

```bash
ABL_DEMO_PROVIDER=anthropic python demo.py   # needs ANTHROPIC_API_KEY and `pip install anthropic`
ABL_DEMO_PROVIDER=ollama    python demo.py   # needs a local Ollama daemon; set OLLAMA_MODEL (default llama3)
```

Provider selection is via the `ABL_DEMO_PROVIDER` environment variable
(`mock` | `anthropic` | `ollama`); see `.env.example` for the full set of keys.

## How it works

Three peer agents communicate only through a shared bus, and each round runs the
same three beats:

```
    propose ─────────► challenge ─────────► execute
 (one peer puts       (the other two        (only if all THREE
  an action up)        critique & vote)      approve — else escalate)
```

Consensus rules (`consensus.py`): the proposer implicitly approves its own
proposal; an action executes only if all three peers vote `APPROVE`; an agent
that does not vote is recorded as `ABSTAIN`, which blocks the action because
unanimity is required ("silence is not consent"). A non-unanimous outcome is
logged as a deadlock and escalated to a human operator, who is the only
tiebreaker; with no human available the action is withheld. There is no degraded
mode and no fast path that skips a vote.

The agents have distinct roles and push back differently:

| Agent  | Domain                  | How they push back                                        |
|--------|-------------------------|-----------------------------------------------------------|
| Aurora | Reasoning & planning    | Tradeoffs and second-order effects; names the unraised risk |
| Borea  | Execution & tools       | Feasibility, cost, what breaks in production, rollback    |
| Lis    | Memory & observation    | Precedent and consistency; owns storage, keeps the record |

Layout — the package lives in `src/abl_demo/`, with a thin entry point and the
test suite at the repo root:

```
src/abl_demo/
  protocol.py      # message & action types (Proposal, Challenge, Decision, Vote)
  bus.py           # PeerBus — observable pub/sub with a full transcript
  consensus.py     # ConsensusManager — 3/3 or escalate to human
  providers.py     # MockProvider (offline) + optional Anthropic/Ollama hooks
  agents.py        # BaseAgent + Aurora / Borea / Lis personalities
  orchestrator.py  # Collective — wires bus + agents + consensus into one round
  cli.py           # the walkthrough
demo.py            # (repo root) thin entry point → abl_demo.cli:main
tests/             # (repo root) consensus rules + bus delivery + end-to-end rounds
```

## Status / limitations

Experimental demo, not the production system. It is a **clean-room
reproduction** of ABL's public design — the peer bus, the propose/challenge/
execute protocol, and 3/3-or-escalate consensus — in a few hundred lines of
original code; it ships no private data, trained models, or credentials. The
default deliberation is a scripted, deterministic walkthrough rather than an
open-ended agent runtime, and the real-model providers (Anthropic, Ollama)
change only the reasoning text, not the protocol. MIT licensed.

Run the tests with:

```bash
pip install -e ".[dev]"
pytest -q
```

---

*Part of a set of repositories exploring agent reliability, honesty, and
calibration. `abl-demo` is the public, self-contained slice of the larger
(private) ABL multi-agent system.*
