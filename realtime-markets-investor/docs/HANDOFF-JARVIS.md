# Handoff for Jarvis

Direct Grok Bot linking is not available from a Cursor cloud agent. This note is for you to relay to Jason. Do not ask him for brokerage tokens.

## What this is

A research-only brief command in the Grok repo, branch `cursor/realtime-markets-investor-9dd1`, directory `realtime-markets-investor/`.

It does not trade. `place_order` raises. The Stake portfolio is SMSF property, not personal cash. The tool does not read it.

Investor (`c69f0ddb-1239-44e1-a853-ec23909fbeac`) still owns narrative company and market research. This command only pulls public quotes and prints a sourced brief you can hand to Investor.

## How to run

```bash
cd realtime-markets-investor
PYTHONPATH=src python3 -m rmi --watchlist watchlist.example.json
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Python 3.12. No packages to install. Optional `--out brief.md`.

The example symbols are not Jason's holdings.

## What Jason still needs to decide

1. Sleeves: ASX equities, AUD FX, crypto, or a subset. Crypto in the example is not an SMSF holding and is not advice that the fund may hold it.
2. The real symbol list to replace `watchlist.example.json`.
3. Alert and stale limits. None are set. The brief only reports quote age.
4. Whether any paid data feed is wanted later.

Brokerage API keys and live order placement stay out of scope until he explicitly opts in. Do not collect a Stake key, a brokerage key, or a market-data key for this prototype.

## Repo location

This VM had no Origin session, so a new private Origin repo was not created. GitHub repository creation with the cloud-agent credential was also rejected. The project is committed on the branch above in `MintAlpha91/Grok`.
