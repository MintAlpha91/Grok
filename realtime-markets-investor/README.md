# Realtime Markets Investor Bot (research-only)

Research briefs from public market data. This project does not place orders, move money, or read brokerage balances.

It is a tool for Jarvis to run and hand to Jason Rogers, and for the existing Grok Bot teammate Investor (`c69f0ddb-1239-44e1-a853-ec23909fbeac`) to use as a quote snapshot. It is not that teammate, and it cannot message Grok Bots.

Account context: the Stake portfolio is **SMSF property, not personal cash**. Briefs say that every time. They do not include balances.

Times are shown in **Australia/Brisbane**.

## Run

From this directory, with Python 3.12 and no third-party packages:

```bash
PYTHONPATH=src python3 -m rmi --watchlist watchlist.example.json
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

`--out brief.md` also writes the brief to a file. `briefs/` is gitignored so live quotes are not committed.

The example watchlist is **not a portfolio**. `BHP.AX`, `AUDUSD`, and `BTC-USD` are placeholders so the three proposed sleeves have a shape. Jason replaces them.

## What a brief contains

- Generation time in Australia/Brisbane
- SMSF / Stake wording
- For each symbol: source, source URL, last price, and only the change fields that feed actually returned
- A computed percent only when both `regularMarketPrice` and `chartPreviousClose` were in the same Yahoo response, labeled as arithmetic
- Feed errors as errors, with `Last: not available`
- Risk rules and the open decisions

## Scope proposal

Jason has not locked the market list. The prototype proposes three optional sleeves and does not turn any of them on as a holding:

| Sleeve | Why it is proposed | Example only |
|---|---|---|
| Equities | Australian SMSF context makes ASX the natural first place to look | `BHP.AX` |
| FX | AUD matters for an AUD SMSF | `AUDUSD=X`, plus an ECB reference rate |
| Crypto | The brief format can carry a public crypto quote | `BTC-USD` |

Crypto in the example file does **not** mean the SMSF holds crypto or is allowed to. That decision stays with Jason and his adviser. This tool does not give tax or superannuation advice.

## Data sources in this build

All three are public and unauthenticated. None of them is a licensed realtime feed. Quotes can be delayed. The brief prints each feed's own timestamp and the age in minutes. No stale limit is active, because Jason has not set one.

- **Equities and FX quotes:** Yahoo Finance chart endpoint, `range=1d`. Unofficial. With a one-day range, `chartPreviousClose` is the field used as the reference. `fulldayChangePercent` is reported separately when the payload includes it.
- **FX cross-check:** [Frankfurter](https://www.frankfurter.app/) ECB reference rate. The brief keeps the rate date from the payload. It is not a tradable spot and not a spread to trade.
- **Crypto:** CoinGecko simple price, including `usd_24h_change` and `last_updated_at` only when present.

## Out of scope

These stay off until Jason explicitly opts in. `rmi.policy.place_order` raises and cannot submit anything.

- Brokerage API keys, including Stake
- Live order placement, cancellation, or amendment
- Moving money, contributions, or withdrawals
- Reading SMSF balances
- Paid market-data feeds

## Docs

- [Design](docs/DESIGN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Handoff for Jarvis](docs/HANDOFF-JARVIS.md)
