# Stock Analyst Agent

[![ERC-8183](https://img.shields.io/badge/Protocol-ERC--8183-blue)](https://github.com/bnb-chain/BEPs)
[![x402](https://img.shields.io/badge/Payment-x402%20v2-orange)](buyer-client/src/x402-async.ts)
[![B402](https://img.shields.io/badge/Settlement-B402%20HMAC--SHA512-green)](gateway/x402_lambda/)
[![UOMP](https://img.shields.io/badge/Context-UOMP-purple)](https://github.com/0xaicrypto/uomp-core)
[![Robinhood Chain](https://img.shields.io/badge/Chain-Robinhood%20(4663)-lightgrey)](configs/chains.json)
[![BSC](https://img.shields.io/badge/Chain-BSC-yellow)](configs/chains.json)
[![Virtuals](https://img.shields.io/badge/Agent%20Deploy-Virtuals%20Protocol-8A2BE2)](integrations/virtuals/)
[![Python](https://img.shields.io/badge/Seller-Python%203.12-3776AB?logo=python)](stockanalyst/)
[![TypeScript](https://img.shields.io/badge/Buyer-TypeScript-3178C6?logo=typescript)](buyer-client/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

**The agent that reads your portfolio and sells you a thesis — paid via x402 / ERC-8183, with native support for tokenized equities on Robinhood Chain, BSC and any EVM.**

An end-to-end, production-shaped demo of a **personalized AI stock analyst** for the tokenized-equity era. It aggregates five independent data sources, computes ten technical indicators, writes a structured bull/bear thesis with target price, and settles payment three ways — free identity-proof quotes, x402 async jobs, and fully trustless ERC-8183 on-chain escrow.

This is a **hard fork of [bnb-chain/stockanalyst-agent-demo](https://github.com/bnb-chain/stockanalyst-agent-demo)** with a chain-agnostic data layer, a Robinhood Chain price feed, Virtuals Protocol persona deployment, and a stock-token metadata adapter.

---

## Why this exists

Tokenized equities (TSLA/B, NVDA/B, GOOGL, SKHYB, SNDKB and friends) trade on BSC today and are moving to dedicated L2s like Robinhood Chain. Every chain re-implements the same primitives — price feeds, issuer metadata, transfer restrictions, settlement provenance — and every analyst agent re-implements the same research stack. This repo is the reference implementation that ties both sides together:

- **Chain layer**: one adapter (`StockTokenAdapter`) that normalizes stock tokens across RH chain, BSC and EVM.
- **Payment layer**: the x402 + ERC-8183 + B402 stack that lets an agent get paid for analysis without KYC, subscriptions or a credit card.
- **Agent layer**: a seller runtime that can be deployed as a plain service **or** as a Virtuals Protocol persona.

## Features

- 🧠 **Real research stack** — yfinance, FRED macro, SEC EDGAR insider trades, Alpha Vantage AI sentiment, GNews headlines.
- 📈 **10 technical indicators** — RSI, MACD, Bollinger, MA50/200 golden/death cross, ADX, OBV, ATR, VaR 95%.
- 💳 **Three payment tiers** — free 0-U quotes, 1-U x402 async jobs, 1-U ERC-8183 on-chain escrow.
- 🔐 **B402 authenticated settlement** — HMAC-SHA512 signed callbacks so nobody can forge a paid result.
- ⛓️ **Chain-agnostic** — Robinhood Chain (4663), BSC (56), Base (8453), any EVM; configured in `configs/chains.json`.
- 🤖 **Virtuals-ready** — deploy analyst personas on Virtuals Protocol from a manifest.
- 🔒 **UOMP context** — reads your portfolio and cost basis from a local privacy guard, never a cloud API.
- ☁️ **S3 storage** — private report delivery via presigned URLs.
- 🧪 **34+ unit tests** — x402 envelope, signing, job store, report pipeline, competition reporting.

## Architecture

```
  LOCAL (buyer machine)                         CLOUD / CHAIN
  ──────────────────────                        ─────────────

  UOMP Guard (localhost:9374)
  ├─ portfolio: TSLA/B ×50, NVDA/B ×20
  └─ profile:  moderate / 12mo
        │
        │ [1] read context (privacy-preserving)
        ▼
  buyer-client (Node.js / TypeScript)
        │
        ├─── x402 free tier ────────────────► seller agent  :9000
        │    sign 0-U EIP-712 proof           └─ verify sig + rate limit (10/24h)
        │    POST /x402/free                      fetch_quote() — no LLM
        │◄── SSE quick quote ──────────────────── (~1s)
        │
        ├─── x402 paid async ───────────────► seller agent  :9000 / :9001
        │    sign 1-U EIP-712 proof           ├─ Binance Pay facilitator
        │    POST /x402/analyze/async         ├─ kimi-k2.6 background analysis
        │◄── jobId + private token ──────────└─ poll status → presigned S3 URL
        │
        ├─[2]─ A2A negotiate ───────────────► seller agent (platform :9000)
        │      OAuth2 token                    └─ sign quote → 1.0 U
        │◄──────────────────────────────────── signed quote
        │
        ├─[3]─ createJob ───────────────────► BSC Testnet (chain 97)
        │      registerJob / setBudget         AgenticCommerce escrow
        │      approve + fund                  U token locked
        │
        ├─ start relay (localhost:9444) + Cloudflare Tunnel
        │        │
        ├─[4]─ notify_funded ──────────────► seller agent
        │      EIP-712 signed context         ├─ kimi-k2.6 (~5-15 min)
        │                                     ├─[5] submit_result → BSC Testnet
        │                                     └─[6] POST report → tunnel
        │◄────────────────────────────────────────────────────────────┘
        │
        ├─[5]─ poll getJob() ──────────────► BSC Testnet → SUBMITTED
        ├─[6]─ fetch report via tunnel URL
        └─[7]─ settle (after 24h) ─────────► BSC Testnet (escrow released)
```

## Payment channel comparison

| | x402 Free | x402 Paid | ERC-8183 |
|---|---|---|---|
| Cost | 0 U | 1.0 U | 1.0 U |
| Signing | EIP-712 (0-U identity proof) | EIP-712 + EIP-3009 | EIP-191 quote + on-chain txs |
| Settlement | none (identity only) | Binance Pay facilitator | on-chain escrow (trustless) |
| Latency | ~1 s | async (30 s – 2 min) | 5–15 min |
| Privacy | portfolio read locally | private S3 report | private S3 report |
| Replay protection | signed nonce | signed nonce + auth header | chain state |

## Chain support

| Chain | Chain ID | Native | Stock tokens | Feed |
|---|---|---|---|---|
| Robinhood Chain | 4663 | ETH | registry-based | `integrations/robinhood/price_feed.py` |
| BSC | 56 | BNB | TSLAB, NVDAB, MSFTo, GOOGL, … | BSC RPC |
| Base | 8453 | ETH | any ERC-20 | EVM RPC |
| Any EVM | — | — | via `StockTokenAdapter` | EVM RPC |

See `configs/chains.json` for the full network matrix.

## Virtuals Protocol

Deploy the same analyst as a Virtuals persona:

```bash
python -m integrations.virtuals.deploy --persona onchain-analyst-v1 --dry-run
# real deploy (needs VIRTUALS_API_KEY):
python -m integrations.virtuals.deploy --persona onchain-analyst-v1 --deploy
```

Personas ship with a watchlist, tool bindings and a system prompt built
from the same research stack the seller uses. See
`integrations/virtuals/virtuals_agent.py` for the manifest schema.

## Quick start

### Prerequisites

- Python 3.12+ (seller), Node.js 20+ (buyer client)
- `uv` for dependency management
- Access to a BSC Testnet RPC and a funded testnet wallet for ERC-8183 tier

### 1. Seller

```bash
cd stockanalyst
uv sync
uv run uvicorn app.agent.seller_core:app --port 9000
```

### 2. Buyer client

```bash
cd buyer-client
npm install
npm run x402:free     # free quote (~1s)
npm run x402:async    # paid async job (1.0 U)
npm run dev           # ERC-8183 on-chain escrow flow
```

### 3. Gateway (optional, cloud deployment)

```bash
cd gateway/x402_lambda
uv sync
uv run pytest         # run the gateway test suite
```

## Report output

Every paid analysis produces a structured markdown report:

- **Verdict**: BUY / HOLD / SELL with confidence
- **Bull & bear theses** — one paragraph each, sourced
- **Portfolio P&L** vs your actual cost basis (from UOMP)
- **Indicators table**: RSI, MACD, Bollinger, MA50/200 cross, ADX, OBV, ATR, VaR 95%
- **Target price** with horizon (3m / 12m)
- **Risks**: concentration, macro, liquidity of the token wrapper

## Repository layout

```
stockanalyst/            # seller agent (Python 3.12, FastAPI)
├── app/agent/           # agent core: signing, x402, seller, tools, prompts
│   └── tests/           # 34+ unit tests incl. fixture vectors
buyer-client/            # TypeScript buyer (x402 async + ERC-8183 flows)
├── src/                 # x402 client, A2A negotiation
gateway/                 # cloud gateway
├── x402_lambda/         # serverless x402 handler (Python)
contracts/               # Solidity: StockTokenAdapter + escrow interfaces
integrations/            # chain & protocol integrations
├── robinhood/           # RH chain price feed
├── virtuals/            # Virtuals persona deployment
├── binance-pay/         # facilitator adapter
├── s3/                  # private report storage
configs/                 # chains.json, env templates, model configs
docs/                    # architecture, payment flows, deployment
scripts/                 # demo scripts, dev helpers
data/                    # sample portfolios, indicator configs
examples/                # runnable end-to-end examples
benchmarks/              # indicator + latency benchmarks
tests/                   # cross-component integration tests
.github/                 # CI workflows
```

## Development

```bash
# Run the full test suite
cd stockanalyst && uv run pytest

# Lint
uv run ruff check .

# Type-check the buyer client
cd buyer-client && npx tsc --noEmit
```

## Roadmap

- [x] x402 free + paid tiers
- [x] ERC-8183 on-chain escrow flow
- [x] B402 HMAC-SHA512 authenticated settlement
- [x] S3 private report storage
- [x] Robinhood Chain price feed
- [x] Virtuals persona deployment
- [ ] Multi-LLM routing (kimi-k2.6 ↔ deepseek ↔ claude)
- [ ] Options-chain aware thesis generation
- [ ] Cross-chain arb signals (see `stock-token-arbitrage`)

## Related projects

- `stock-token-index` — on-chain registry of tokenized equities
- `rh-stock-token-sdk` — SDK for Robinhood Chain stock tokens
- `virtuals-stock-agents` — more Virtuals analyst personas
- `stock-token-data-pipeline` — the data layer this agent consumes
- `x402-payment-gateway` — self-hosted x402 gateway

## License

Apache-2.0. The original demo is (c) BNB Chain; this fork adds the
chain-agnostic layer, RH chain feed and Virtuals integration.
