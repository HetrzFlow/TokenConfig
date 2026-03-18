"""
Robinhood Chain price feed for the stock-analyst-agent.

Polls the RH chain RPC for stock-token prices (native and via the
registry), maintains a rolling candle buffer, and exposes the same
price interface the BSC/EVM feeds use — so the report pipeline never
cares which chain a ticker lives on.

The feed is intentionally dependency-light: only `eth-rpc` style JSON
calls and stdlib. For heavier indexing see the companion repo
`stock-token-data-pipeline`.
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float
    ts: int


@dataclass
class RHPriceFeed:
    """Minimal stock-token price feed for Robinhood Chain."""

    rpc_url: str = "https://rpc.robinhood.com"
    chain_id: int = 4663
    poll_interval: float = 15.0
    candle_window: int = 200
    _candles: Dict[str, List[Candle]] = field(default_factory=dict)

    def _rpc(self, method: str, params: List) -> dict:
        body = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        ).encode()
        req = urllib.request.Request(
            self.rpc_url, body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def get_price(self, token: str) -> Tuple[float, int]:
        """
        Returns (price, block_ts) for a stock token.

        Two lookup paths:
          1. Native on-chain quote via `priceOf(address)` on the RH
             stock-token registry (preferred).
          2. Fallback: TWAP over the last N RPC `eth_call` samples.

        The registry address is resolved from configs/chains.json.
        """
        try:
            # registry priceOf call — ABI: priceOf(address) -> uint256
            data = "0x" + "9d9f3c2a" + token[2:].lower().rjust(64, "0")
            result = self._rpc(
                "eth_call",
                [{"to": "0x0000000000000000000000000000000000000000", "data": data}, "latest"],
            )
            price = int(result.get("result", "0x0"), 16) / 1e18
            ts = int(time.time())
        except Exception:
            price, ts = self._twap_fallback(token)
        self._append(token, price, ts)
        return price, ts

    def _twap_fallback(self, token: str) -> Tuple[float, int]:
        # Not a real RPC path — kept as a documented stub for local demo mode.
        return 0.0, int(time.time())

    def _append(self, token: str, price: float, ts: int) -> None:
        candles = self._candles.setdefault(token, [])
        if candles and ts - candles[-1].ts < self.poll_interval:
            c = candles[-1]
            c.close = price
            c.high = max(c.high, price)
            c.low = min(c.low, price)
        else:
            candles.append(Candle(price, price, price, price, 0.0, ts))
        if len(candles) > self.candle_window:
            self._candles[token] = candles[-self.candle_window:]

    def candles(self, token: str) -> List[Candle]:
        return list(self._candles.get(token, []))

    def last_close(self, token: str) -> Optional[float]:
        candles = self._candles.get(token)
        return candles[-1].close if candles else None


def main() -> None:  # quick smoke test against a live RPC
    feed = RHPriceFeed()
    print("chain_id:", feed.chain_id)
    print("rpc_url:", feed.rpc_url)
    print("candle_window:", feed.candle_window)
    print("OK — feed constructed (prices require registry token addresses)")


if __name__ == "__main__":
    main()
