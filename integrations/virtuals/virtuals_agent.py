"""
Virtuals Protocol integration for the stock-analyst-agent.

Deploys an analyst "persona" agent on Virtuals Protocol that can:
  1. Read on-chain stock-token prices (Robinhood Chain / BSC / EVM)
  2. Answer tokenized-equity questions with the same research stack
     used by the x402 seller (indicators, sentiment, thesis).
  3. Post structured verdicts back on-chain via the agent's channel.

The integration follows the Virtuals agent-deployment pattern: a
persona is a configurable brain (model + system prompt + tool
bindings) registered in the Virtuals registry, with a dedicated
on-chain wallet that signs its outputs.

Usage:
    python -m integrations.virtuals.deploy --persona onchain-analyst-v1 \
        --chain robbinhood --tickers TSLA,NVDA,GOOGL
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from stockanalyst.app.agent.prompt_builder import build_system_prompt
from stockanalyst.app.agent.tools import TOOL_REGISTRY


@dataclass
class VirtualsPersona:
    """A deployable analyst persona for Virtuals Protocol."""

    name: str
    model: str = "kimi-k2.6"
    temperature: float = 0.2
    max_tokens: int = 4096
    tickers: List[str] = field(default_factory=list)
    chains: List[str] = field(default_factory=lambda: ["robinhood", "bsc", "evm"])
    system_prompt: str = ""
    tool_bindings: Dict[str, bool] = field(default_factory=dict)

    def to_manifest(self) -> Dict[str, Any]:
        """Serializable deployment manifest for the Virtuals registry."""
        return {
            "schema": "virtuals.persona.v1",
            "name": self.name,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "watchlist": self.tickers,
            "chains": self.chains,
            "system_prompt": self.system_prompt or build_system_prompt(
                watchlist=self.tickers, mode="virtuals"
            ),
            "tools": self.tool_bindings,
        }


PERSONA_PRESETS: Dict[str, VirtualsPersona] = {
    "onchain-analyst-v1": VirtualsPersona(
        name="onchain-analyst-v1",
        tickers=["TSLA", "NVDA", "GOOGL", "MSFT", "SKHYB", "SNDKB"],
        tool_bindings={
            "price_feed": True,
            "indicators": True,
            "onchain_holders": True,
            "news_sentiment": True,
            "thesis_writer": True,
        },
    ),
    "yield-scout-v1": VirtualsPersona(
        name="yield-scout-v1",
        model="kimi-k2.6",
        tickers=["AAPL", "AMZN", "META"],
        tool_bindings={
            "price_feed": True,
            "yield_finder": True,
        },
    ),
}


def _load_manifest(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


async def deploy_persona(persona: VirtualsPersona, dry_run: bool = True) -> Dict[str, Any]:
    """
    Deploy (or simulate) a persona on Virtuals Protocol.

    In dry-run mode this prints the manifest and returns it; with
    ``dry_run=False`` it would call the Virtuals registry endpoint
    (configured via VIRTUALS_REGISTRY_URL) and mint the persona NFT.
    """
    manifest = persona.to_manifest()
    registry_url = os.getenv(
        "VIRTUALS_REGISTRY_URL", "https://app.virtuals.io/api/agents"
    )
    if dry_run:
        print("[dry-run] would POST to", registry_url)
        print(json.dumps(manifest, indent=2))
        return {"status": "dry-run", "manifest": manifest}

    # Real deployment path — requires VIRTUALS_API_KEY.
    # The registry returns an agent_id + persona NFT metadata URL.
    import httpx

    api_key = os.getenv("VIRTUALS_API_KEY")
    if not api_key:
        raise RuntimeError("VIRTUALS_API_KEY not set")
    resp = await httpx.AsyncClient().post(
        registry_url,
        headers={"Authorization": f"Bearer {api_key}"},
        json=manifest,
        timeout=60,
    )
    resp.raise_for_status()
    return {"status": "deployed", "payload": resp.json()}


def _available_tools(persona: VirtualsPersona) -> List[str]:
    return [name for name, enabled in persona.tool_bindings.items() if enabled and name in TOOL_REGISTRY]


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Virtuals stock-analyst persona")
    parser.add_argument("--persona", choices=list(PERSONA_PRESETS), default="onchain-analyst-v1")
    parser.add_argument("--chain", default="robinhood", help="primary chain for price feeds")
    parser.add_argument("--tickers", default="", help="comma-separated ticker override")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--deploy", action="store_true", help="actually deploy (needs API key)")
    args = parser.parse_args()

    persona = PERSONA_PRESETS[args.persona]
    if args.tickers:
        persona.tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    persona.chains.insert(0, args.chain)

    result = asyncio.run(deploy_persona(persona, dry_run=not args.deploy))
    print("\nBound tools:", ", ".join(_available_tools(persona)) or "(none)")
    print("Status:", result["status"])


if __name__ == "__main__":
    main()
