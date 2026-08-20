"""ABL_DEMO_PROVIDER selection, and the wiring that actually honors it.

The provider_from_env() unit tests below are coverage; the two main() tests are
the regression guard. main() once hardcoded MockProvider(SCRIPT), so the env var
had no effect on `python demo.py` even though provider_from_env() itself was
correct — testing the selector alone would not have caught that.
"""

import sys
from types import SimpleNamespace

import pytest

from abl_demo import cli
from abl_demo.orchestrator import Collective
from abl_demo.providers import MockProvider, OllamaProvider, provider_from_env


def _veto(self, system: str, prompt: str) -> str:
    """Stand in for a real backend without a daemon; 'REJECT' makes peers veto."""
    return "REJECT - stub veto"


def test_main_routes_the_env_var_to_the_selected_provider(monkeypatch, capsys):
    monkeypatch.setenv("ABL_DEMO_PROVIDER", "ollama")
    monkeypatch.setattr(OllamaProvider, "complete", _veto)

    cli.main()
    out = capsys.readouterr().out

    assert "provider: OllamaProvider" in out
    # Behavioral, not cosmetic: a vetoing backend cannot reach a 3/3 round, so
    # the scripted round 1 stops executing. Hardcoding the mock fails this.
    assert out.count("WITHHELD") == 2


def test_main_defaults_to_the_offline_mock(monkeypatch, capsys):
    # delenv so the suite is correct even for a developer who exports the var.
    monkeypatch.delenv("ABL_DEMO_PROVIDER", raising=False)

    cli.main()
    out = capsys.readouterr().out

    assert "provider: MockProvider" in out
    assert out.count("EXECUTE") == 1  # the scripted unanimous round still runs


def test_main_passes_the_demo_script_to_the_mock(monkeypatch, capsys):
    """cli does `from .providers import provider_from_env`, so cli holds its own
    binding — patching abl_demo.providers here would silently miss."""
    seen = []
    monkeypatch.setattr(
        cli, "provider_from_env", lambda script=None: seen.append(script) or MockProvider(script)
    )

    cli.main()
    capsys.readouterr()

    assert seen == [cli.SCRIPT]


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, MockProvider),
        ("mock", MockProvider),
        ("ollama", OllamaProvider),
        ("OLLAMA", OllamaProvider),  # choice is lowercased before matching
        ("nonsense", MockProvider),  # unknown values fall back, never crash
    ],
)
def test_provider_from_env_selects(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("ABL_DEMO_PROVIDER", raising=False)
    else:
        monkeypatch.setenv("ABL_DEMO_PROVIDER", value)

    # Constructing OllamaProvider must not touch the network — only .complete() does.
    assert isinstance(provider_from_env(), expected)


def test_provider_from_env_threads_the_script_into_the_mock(monkeypatch):
    monkeypatch.delenv("ABL_DEMO_PROVIDER", raising=False)

    provider = provider_from_env({"[aurora|propose]": "scripted line"})

    assert provider.complete("sys", "[aurora|propose] task: x") == "scripted line"


def test_anthropic_branch_requires_the_sdk(monkeypatch):
    """Selected but unusable should explain itself, not raise a bare ImportError."""
    monkeypatch.setenv("ABL_DEMO_PROVIDER", "anthropic")
    # A None entry makes `import anthropic` fail whether or not the SDK is
    # installed, so this asserts the same thing on every machine.
    monkeypatch.setitem(sys.modules, "anthropic", None)

    with pytest.raises(RuntimeError, match="pip install anthropic"):
        provider_from_env()


def test_anthropic_branch_requires_an_api_key(monkeypatch):
    monkeypatch.setenv("ABL_DEMO_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setitem(
        sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda api_key: None)
    )

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        provider_from_env()


def test_collective_without_a_provider_also_routes(monkeypatch):
    """Collective(provider=None) calls provider_from_env() on its own path."""
    monkeypatch.setenv("ABL_DEMO_PROVIDER", "ollama")
    monkeypatch.setattr(OllamaProvider, "complete", _veto)

    decision = Collective().run_round("anything")

    assert decision.approved is False
    assert decision.escalated_to_human is True
