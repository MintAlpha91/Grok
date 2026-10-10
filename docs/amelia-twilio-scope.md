# Amelia on the RAS Twilio number

Scope only. Do not build this yet, and do not buy hosting, numbers, or voice minutes from this document.

Amelia is the Rogers App Specialists assistant. On the business Twilio number she may log every inbound SMS and call, draft a reply, and wait. Jason approves, then the service sends. That is the same sequence as her email workflow: draft, Jason approves, send.

One exception is already decided. The immediate missed-call text uses a template Jason has approved in advance, so that one text can go out on its own. Quote follow-ups, replies to what a customer wrote, and anything Amelia wants to say or send after a call stay in the queue.

This pilot is Rogers App Specialists only (Jason Rogers, Gladstone QLD, ABN 19761869101). The public privacy wording already written for the website is the rule for stored customer data: it is stored with Twilio, it may be held overseas, it is not sold, and our copy is deleted when the client cancels.

## What this covers

In scope for the pilot on the RAS number:

- Inbound SMS, logged, then a drafted reply.
- Inbound voice, logged. The first voice behaviour is a missed call plus the template text. The later voice behaviour is a recording or a live assistant, with any follow-up message still drafted.
- Quote follow-ups on day 2 and day 7, created as drafts. They are not sent on a timer.
- Opt-out. `STOP` is honoured immediately.

Out of scope until a later brief: booking from a calendar, review requests, the owner-view list, the 6pm summary, and a second business on the same service. Those features use the same approval rule when they are built. The data model should leave room for a `business_id`, and the only configured business is RAS.

## Architecture

A small HTTPS webhook service. Node with Express, or a serverless HTTP function, is enough. Twilio is the telephone network. Amelia does not send through the Twilio API until a draft is approved, except for the two fixed templates below.

```text
Caller or texter
    -> RAS Twilio number
    -> POST /twilio/voice  or  POST /twilio/sms  or  POST /twilio/status
    -> verify X-Twilio-Signature
    -> store the event (idempotent on CallSid or MessageSid)
    -> missed-call template?  send once, mark auto_sent
    -> STOP?                  suppress the number, send the fixed STOP reply
    -> anything else          write a draft, status = pending
                              email Jason the draft
    -> Jason approves or rejects
    -> only then messages.create (or the voice action that was drafted)
```

Twilio retries webhooks that do not return 2xx, and it expects a voice response within about 15 seconds. Every handler must be idempotent. A repeated `CallSid` must not send a second "sorry we missed you" text.

Suggested layout, when this is built:

- `POST /twilio/sms` returns empty TwiML. It never puts a reply in that HTTP response, because a TwiML `<Message>` would send before approval.
- `POST /twilio/voice` returns TwiML immediately: reject the call for the missed-call path, or speak the disclosure and record for the voicemail path.
- `POST /twilio/status` receives call and message status. The missed-call text is sent from here, after the call has actually failed to connect, and only once.
- `POST /drafts/:id/approve` and `POST /drafts/:id/reject` are the approval actions. They require a signed, expiring, single-use token.
- A daily job creates day-2 and day-7 follow-up drafts. It does not call Twilio.

### Records

Keep a minimal store. SQLite, Cloudflare D1, or Turso are all enough for one number. Twilio remains the system of record for the message and call logs it already holds.

| Record | Purpose |
|---|---|
| `events` | One row per inbound SMS or call: sid, from, to, body or transcript, time |
| `drafts` | Proposed outbound text, kind, status, link to the event |
| `templates` | Missed-call text and STOP confirmation, each with an approved-at time |
| `suppressions` | Numbers that sent STOP. Pending drafts for that number are cancelled |

Draft status is `pending`, `approved`, `rejected`, `sent`, or `failed`. Amelia may edit the body while it is `pending`. Only the transition to `approved` may call the Twilio send API. Store the resulting MessageSid on the draft.

### Hosting

The pilot needs a public HTTPS URL that stays awake. Twilio will not call a sleeping server reliably.

| Option | Fit |
|---|---|
| Cloudflare Workers, free tier | Best fit for SMS, missed-call, and status webhooks. HTTPS on a `workers.dev` hostname. The free request allowance covers one business number. Confirm the current quota before relying on it. |
| Vercel, Hobby | Fine for the same short HTTP webhooks. Cold starts are usually inside Twilio's voice timeout if the function only returns TwiML or enqueues work. A poor place for a live voice socket. |
| Render, free web service | Poor fit. Free instances sleep, and a cold start can miss Twilio's timeout. Use it only if the service is on a paid instance that stays up. |

Live AI voice is the first feature that needs a long-lived WebSocket (`wss://`). A short HTTP function cannot hold that socket. That path wants Cloudflare Durable Objects (Workers paid plan) or a small always-on Node process. Do not start that host for the pilot.

No domain purchase. The platform hostname is enough for Twilio webhooks.

## Missed-call text-back

Jason pre-approves this template. After that, the service may send it without a per-message approval. Suggested wording, matching the offer sheet:

> Hi, it's Rogers App Specialists. Sorry we missed you! What can we help with?

Rules:

- Send only after the call did not connect. Prefer `<Reject>` as the first voice verb so Twilio does not answer the call, then send from the status callback when the status is no-answer or busy. Do not text on `failed` or `canceled`. A trunk error is not a missed call.
- One text per `CallSid`.
- Send from the RAS Twilio number, not from an alphanumeric sender name. The customer must be able to reply to the same thread.
- Do not add a sales follow-up to this text. The customer's reply is a new inbound SMS and becomes a draft.
- If the number is already suppressed, do not text.
- If the template row has no `approved_at`, do not text. Hold a draft instead.

This is the Starter behaviour: text-back within a minute of a missed call.

## Everything else stays draft-and-approve

| Kind | Who writes it | When it sends |
|---|---|---|
| Missed-call text | Fixed template | Immediately, after the template is pre-approved |
| STOP confirmation | Fixed template | Immediately, so the opt-out is honoured |
| Reply to an inbound SMS | Amelia | After Jason approves that draft |
| Quote follow-up, day 2 and day 7 | Amelia, from the approved follow-up wording | After Jason approves that draft. Stop after day 7 |
| SMS proposed after a voicemail or a live call | Amelia | After Jason approves that draft |
| Spoken AI replies, if live voice is turned on later | A pre-approved persona, not a fresh draft per sentence | See Voice. Outbound texts from the call still wait |

Quote follow-ups name the business and include `Reply STOP to opt out`. They are commercial messages under the Spam Act 2003. A timer may create the draft. It must not send it. A reply, a STOP, or a rejection cancels the remaining follow-ups for that enquiry.

## Voice

Two designs. Build the simpler one first. Live answering is a later decision, not the pilot.

### Pilot: record or miss, then text

Missed call, as above.

If the product needs a message taken, the voice webhook returns TwiML that speaks the disclosure line, then `<Record>` with transcription. Amelia drafts an SMS from the transcript. Jason approves it. Then it sends.

For the RAS pilot, prefer not to keep the audio file. Transcription needs the recording to exist long enough for Twilio to produce the transcript. Delete the recording through the Twilio API once the transcript is stored. The terms note says the simplest pilot keeps the transcript or summary only, and that recording should be checked with Suzanne before any audio is retained. Do not enable transcription until that check is done. Until then, missed-call text-back does not need a recording at all.

### Later: live AI answering

A live call cannot wait for Jason to approve each sentence. Per-utterance approval and a real-time voice agent cannot both be true. If Pro voice is switched on, treat the voice persona the way the missed-call template is treated: Jason approves the disclosure, the system prompt, the topics Amelia may discuss, and the list of actions she must not take (no prices she invents, no booking she confirms, no promise of a Google Play outcome). Spoken replies stay inside that approved persona. Every SMS, quote, or booking that comes out of the call is still a draft.

Two vendor shapes, both using the RAS Twilio number:

- **Twilio ConversationRelay.** The voice webhook returns `<Connect><ConversationRelay url="wss://...">`. Twilio does speech-to-text and text-to-speech. Our server receives transcript messages on the socket and streams reply text back. The welcome greeting must include the recording disclosure. Twilio documents an `X-Twilio-Signature` on the WebSocket handshake; verify it. Using ConversationRelay requires accepting Twilio's predictive and generative AI/ML terms in the console. Docs: [ConversationRelay onboarding](https://www.twilio.com/docs/voice/conversationrelay/onboarding).
- **Retell, bridged from Twilio.** Either an Elastic SIP trunk (`sip:sip.retellai.com`) or, with less console setup, a voice webhook that registers the call with Retell and returns `<Dial><Sip>sip:{call_id}@sip.retellai.com`. Retell then runs the agent. Docs: [Retell Twilio trunk](https://docs.retellai.com/deploy/twilio) and [custom telephony](https://docs.retellai.com/deploy/custom-telephony). Same rule: disclosure in the greeting, and no outbound SMS without a draft.

ConversationRelay keeps the call on Twilio and leaves the model in our process, which makes the approval log easier to keep. Retell is faster to a polished voice and moves the conversation onto a second vendor. Either way, a second data processor has to be named in the privacy note before a paying client uses it. The current public line names Twilio only.

Recommendation: ship missed-call text-back and the voicemail-to-draft path first. Do not open a ConversationRelay or Retell account as part of this scope.

## Approval surface

Simplest first. No dashboard in the pilot.

**Email.** Each pending draft is mailed to rogersinc426@gmail.com. The mail shows the customer number, the inbound text or transcript, and Amelia's proposed reply. Two links: Approve and Reject. Each link is an HMAC over the draft id and an expiry, single-use, valid for a short time (a day is enough). Approving sends through Twilio. Rejecting stores the reason and sends nothing.

Editing: Jason replies to the mail with the replacement text, or the same page the link opens has one text box. The edited body is what gets sent, and the stored draft keeps both the original and the edited version.

**SMS to Jason, later.** A "Reply YES to send" text to his own mobile is possible once he nominates that mobile. Do not send approval traffic to the RAS Twilio number. That number is the customer line and would loop back into Amelia.

**Web list, when email gets clumsy.** A single page of pending drafts, a password or a magic link to the same inbox, an edit box, Approve and Reject. Build this when day-2 follow-ups and voicemail drafts make the inbox noisy. It is the same state machine, not a new one.

There is no Amelia email implementation in this repository. The state machine above is the contract to match. Do not invent a parallel queue.

## Compliance

Not legal advice. The terms file already marks the items below as needing Suzanne or an ACMA/OAIC read before the first paying client. The pilot on our own number should still follow them.

**Recording disclosure.** Play this before any recording or any AI voice, every call:

> This call may be recorded and answered by an AI assistant for Rogers App Specialists.

Queensland's Invasion of Privacy Act 1971 lets a party record a call. Callers can be interstate, and an AI assistant is arguably a third party. The terms say to check the federal Telecommunications (Interception and Access) Act position before recording. Missed-call `<Reject>` does not record, so the pilot can launch text-back before that check. Do not turn on `<Record>` or live voice before the check.

**SMS identity and STOP.**

- Send and receive on the Twilio long number so replies and STOP land on the webhook.
- Commercial messages (quote follow-ups, and later review requests) identify Rogers App Specialists and include `Reply STOP to opt out`.
- `STOP` (and the usual Twilio opt-out keywords) suppresses the number immediately and cancels pending drafts. The confirmation text is a second pre-approved template, not a fresh draft. Opt-outs have to be honoured promptly.
- A missed-call text-back to someone who just called is a reply to their enquiry. Later nudges are not.
- Do not text bought lists or numbers scraped from the web.

**Sender ID register.** From 1 July 2026, an unregistered alphanumeric sender ID on Australian SMS is over-stamped `Unverified`. That is a branded header such as `RogersApp`, not the phone number itself. The pilot does not need a branded sender ID. If one is added later, it has to be registered through a participating telco, it has to match the business name on the register, and it is a poor fit here because customers often cannot reply STOP to an alphanumeric sender. ACMA's description: [SMS Sender ID Register](https://www.acma.gov.au/sms-sender-id-register). Confirm with Twilio whether they can lodge an AU sender ID before anyone designs one. The business name also has to be current on the ABR; the terms note that the name registration was still processing.

**Data.** Customer name, number, message, and job details are stored with Twilio and may be held on overseas servers. Our database is a second copy used for the approval queue. Delete our copy when the client cancels. The terms also suggest a 12-month cap on call and text logs. That cap is a check with the accountant and the privacy wording, not a second public promise. Do not write a different retention rule onto the website from this service.

**Website line, unchanged.** Calls may be recorded and answered by AI. We never sell your customers' data.

## Secrets and environment

No secret values belong in the repo, in this doc, or in the client. Set them on the host.

| Variable | Required | Use |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | Yes | Account id. Public-ish, still treat it as a credential |
| `TWILIO_AUTH_TOKEN` | Yes | Webhook signature check, and the API auth for sending. Server only |
| `TWILIO_NUMBER_SID` | Yes | Incoming phone number SID (`PN...`). Used to point the number's SMS and voice URLs at this service |
| `TWILIO_FROM_NUMBER` | Yes | The RAS number in E.164. The `From` on outbound SMS |
| `PUBLIC_BASE_URL` | Yes | The HTTPS origin Twilio calls. Signature validation must use this exact URL |
| `APPROVAL_NOTIFY_EMAIL` | Yes | `rogersinc426@gmail.com` |
| `APPROVAL_LINK_SECRET` | Yes | HMAC key for approve and reject links. Separate from the Twilio token |
| `DATABASE_URL` or a D1 binding | Yes | Drafts, events, suppressions, templates |

Add only when that phase exists:

| Variable | Phase |
|---|---|
| `MISSED_CALL_TEMPLATE` | Can live in the database instead of the environment, once Jason has approved the row |
| `MAIL_PROVIDER` credentials | Emailing drafts. A free transactional tier is enough for one inbox |
| An LLM API key | Drafting replies that are not a fixed template |
| `RETELL_API_KEY`, `RETELL_AGENT_ID` | Live Retell voice, if chosen |
| The ConversationRelay WebSocket host | No extra vendor key if Twilio is doing STT/TTS and our model key is the LLM key above |

Local development can use a tunnel to the same routes. The tunnel URL is not the production `PUBLIC_BASE_URL`.

Operational notes, not extra products: validate `X-Twilio-Signature` on every Twilio request, refuse the request when it fails, and do not log the auth token or the approval secret. Twilio's debugger and request logs will contain message bodies. That is the "stored with Twilio" copy described in the privacy line.

## Build plan

Sizes are relative scope, not a schedule. Small is one webhook path and one send path. Medium adds a queue, a timer, or a second channel. Large is a live media path and a second vendor.

| Phase | What is built | Size | Done when |
|---|---|---|---|
| 1. Receive and log | HTTPS service, signature check, store inbound SMS and voice status, return empty or `<Reject>` TwiML. Send nothing | Small | A real SMS and a real call to the RAS number appear in the log and nothing goes back out |
| 2. Missed-call template | Jason marks the template approved. Status callback sends it once per missed `CallSid`, from the RAS number | Small | One missed call produces one text, and a Twilio retry does not produce a second |
| 3. Draft, approve, send | Draft row, email with signed links, edit, approve sends, reject does not. STOP suppression and the fixed STOP reply | Medium | An inbound SMS sits in email until Jason approves it, and a STOP blocks the next draft |
| 4. Follow-up drafts | Daily job creates day-2 and day-7 drafts from approved wording, with the business name and `Reply STOP`. Cancels them on reply, STOP, or rejection | Medium | A follow-up appears as a draft on the right day and is still unsent until approved |
| 5. Voicemail to draft | Disclosure line, record, transcribe, delete the audio after the transcript is stored, draft the SMS. Blocked on the recording check | Medium | A test call produces a transcript and a pending draft, and the recording is not kept |
| 6. Draft list | One page over the same drafts, magic link to the same email | Medium, optional | Jason can approve from the page without hunting mail |
| 7. Live voice | ConversationRelay or Retell, pre-approved persona, disclosure in the greeting, post-call SMS still drafted. Needs a socket host and a privacy update if a second processor is added | Large | A test call stays inside the approved persona, and no SMS leaves without approval |

Phases 1 to 3 are the pilot. Phases 4 and 5 complete the behaviour described in the offer for text and for "take a message". Phase 7 is Pro voice and is a separate decision.

## Open checks before build

- Suzanne, or a lawyer, on recording and the Telecommunications (Interception and Access) Act, before phase 5 or 7.
- ACMA sender ID path through Twilio, only if a branded header is ever wanted. Not needed for the pilot.
- ABR business name current, before any sender-ID registration.
- Retention: delete our copy on cancel, and whether the suggested 12-month cap is also stored in the service.
- Which mailbox actually sends the approval mail, so drafts do not depend on a personal Gmail session staying open.
