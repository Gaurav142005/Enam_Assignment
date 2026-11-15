# AI build history

FINN was built in one Claude Code session (Claude Opus, with a short stretch on Claude Fable; in VS Code) between 8 and 15 November 2026.
The full transcript is in [claude-code-session.md](claude-code-session.md): every prompt I wrote, every reply, and one line
per tool call. Command output is left out for length, and my email and local paths are redacted. The commit history
(`git log`) is the other half of the record: each commit is one step I reviewed.

## How I worked

- **Layer by layer, not all at once.** Skeleton and contract first (Pydantic models mirrored in TypeScript), then the data
  pipeline, then Push, Pull and Network, then deployment, then design. Each step ended with tests passing and a working app
  before the next began.
- **I set direction and judged output; the agent did the typing.** Most of my prompts are product calls ("only show
  headlines that can actually move the price", "when I open a card, show the info in the card"), not implementation
  instructions. The agent proposed options; I picked.
- **Verify on screen, not in the diff.** The agent drove a headless Chrome after UI changes and I reviewed the screenshots.
  Before submitting, I asked it to use the app as an investor and report what was broken. That found real bugs the tests
  didn't (below).
- **Cost as a constraint from day one.** Free-tier Gemini only. That pushed the design toward rules and arithmetic first,
  with the model last, and toward caching every call.

## Where I course-corrected

| Moment | What went wrong / what I changed | Transcript |
|---|---|---|
| Hosting | Started on Vercel; moved to one Railway container because deep research and the 15-minute watcher need a long-lived process and a disk | prompts 7–8, 11 |
| Deep research cost | It re-ran automatically when a report was a few days old. I had it open the last report instantly and re-run only on Refresh | (summarised section) |
| "No AI slop" | Reports ended with model-sounding wrap-up text. Removed, and the prompts now forbid it | prompt 12 |
| Design | My first pass looked too much like a reference app I'd shared. Asked for our own identity: new font, palette, logo, then a warmer light mode | prompts 15–18 |
| Notifications | I asked whether push notifications actually worked. They didn't: the library rejected the key format, and nothing had tested a real send. Fixed, verified with a real push (HTTP 201), and a test now runs the real library | prompt 19 |
| Signal vs noise | The Brief headlined an Infosys science-prize press release as price-moving. I asked for only headlines that can move the price; this became `materiality.py` (rules, then the market reaction) | prompt 20 |
| Wrong numbers | A business update filed a week after quarter end was showing that quarter's results before they were public. Added a 9-day rule | (summarised section) |
| Investor walkthrough | Asked the agent to use the app as an investor. Found: an empty results card (HAL), fake pages for made-up tickers, a chart axis mixing "1.0L" and "50K", an empty Brief on Sundays, news full of bank-holiday notices, and price-sensitivity crediting market-wide moves to unrelated filings. All fixed the same day | prompts 23–24 |

## What I accepted vs rewrote

- **Accepted:** pipeline plumbing, parsers, the chart and component code, tests.
- **Pushed back on:** anything that put a model where a rule would do (ranking, results numbers, network matching stay
  deterministic), anything that spent model calls without the investor asking, and copy that read as generated.
- **Decided myself:** the product shape (a briefing, not a chat), what counts as price-sensitive, what the network may and
  may not send to a model, and what to leave out.
