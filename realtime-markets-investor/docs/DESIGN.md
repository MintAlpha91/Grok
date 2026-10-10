# Design

## Purpose

Produce a timestamped research brief of public market quotes for Jason Rogers, in plain structure, with sources on every figure. The job is to show what the feeds returned and to stop there.

The audience is Jarvis (Grok Bot coordinator) and the existing Investor teammate. Investor (`c69f0ddb-1239-44e1-a853-ec23909fbeac`) already researches companies and markets and writes plain-language briefs with sources. This bot does not replace that work.

## How this differs from Investor

| | Investor teammate | This prototype |
|---|---|---|
| Kind | Grok Bot in the Grok Bot app | Code in this repo. A Cursor cloud agent cannot join Grok Bot chats. Jarvis relays. |
| Job | Company and market research, narrative, sources | Repeatable quote snapshot and a factual brief |
| Output | Prose research | The same facts every run: last, reference field, feed percent, age, errors |
| Orders | Not in scope for that teammate | Not implemented. `place_order` raises. |

Jarvis can pass a brief from this tool to Investor when a number needs a company-level write-up. This tool does not invent the write-up.

## Scope

Proposed, not assumed:

1. **Equities.** Start the conversation with ASX names, because the known account context is an Australian SMSF held at Stake. US listings only if Jason adds symbols.
2. **FX.** AUDUSD is the proposed cross. Other pairs only if he adds them. An ECB reference rate from Frankfurter sits beside the Yahoo FX print so the two public sources can be read together. The gap is not a trade.
3. **Crypto.** The format supports a public BTC quote. Whether crypto stays in the research set is open. The example does not imply an SMSF holding or permission.

The example watchlist marks every row `example_not_a_holding`.

## Alert and brief format

There is no alert sender in this build. A brief is the alert. When Jason sets a threshold later, a future change can flag a row. Until then the brief says `Stale threshold: none configured` and does not pretend a limit was breached.

Every brief has:

- Title stating it is research
- Australia/Brisbane generation time
- SMSF sentence: Stake assets are not personal cash
- One section per sleeve
- One block per instrument with role, source, source URL, and fields copied from the response
- Computed percent only from two prices in that same response, with the formula named
- Feed-reported percent under the feed's own field name
- Age in minutes from the feed timestamp
- Risk rules
- Out-of-scope list
- Open decisions

Failed feeds produce `Last: not available` and the error text. They do not produce a zero, a dash that could be read as a price, or a prior cached price.

## Risk rules

1. Research and brief only.
2. Do not treat SMSF assets as personal cash. Do not suggest contributions, pensions, withdrawals, or mixing personal money with the fund.
3. Do not size a position and do not say buy, sell, or hold as an instruction.
4. Do not invent prices, balances, returns, or targets. If a field is absent, say so.
5. Example symbols are not the SMSF portfolio.
6. Two sources can disagree. Show both. Do not pick a "true" price.
7. This is not financial product advice and not SMSF compliance advice.

## Data-source limits

Yahoo's chart host is a public website endpoint, not a contract for realtime data. CoinGecko's unauthenticated simple-price method is rate limited and can lag. Frankfurter publishes ECB reference rates on ECB business days, so its date can differ from the Brisbane calendar day. The brief prints that date.

A licensed realtime feed, a brokerage quote, or a Stake session would be a new decision. They are not wired in.

## What Jason still decides

- Sleeves: equities, FX, crypto, or a subset
- The real symbol list
- Numeric alert and stale limits (all unset)
- Whether any paid feed is worth adding later
- Whether crypto research belongs next to the SMSF workflow
- Any future opt-in to brokerage connectivity, which this repo will not grow on its own
