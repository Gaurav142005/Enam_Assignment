# Deploying FINN on Railway

One container runs both halves: the API (FastAPI, internal port 8000) and the web app (Next.js, Railway's public port).
Data lives on a Railway volume. On first boot the volume is seeded from `api/seed/finn.db.gz`, a snapshot of filings,
prices, fundamentals, leadership and finished research with all personal data stripped, so the demo works the moment it's up.
Every push to `main` redeploys automatically.

## Cost

| Plan | Price | Fits FINN? |
|---|---|---|
| Free trial | $0, $5 one-time credit, 30 days, no card | Yes: covers about a month |
| Free | $0, $1/month credit, 0.5 GB RAM cap | Fits in memory, but ~$2/month of usage outruns the $1 credit, so it stops mid-month |
| Hobby | $5/month, includes $5 of usage | Yes: FINN's ~$2–3/month of usage is covered, so $5 flat |

Measured in the production image: ~105 MB idle, ~240 MB once prices or PDFs have been read, ~255 MB peak while deep research
parses a 480-page annual report. At Railway's rates (≈ $10 per GB-month of RAM, $20 per vCPU-month, $0.15 per GB-month of
volume) that is about $2–3 a month. Optional: Settings → Resource limits → memory 512 MB, so a runaway can never bill more.

## Steps

### 1. Put the code on GitHub (once)
Create an empty **public** repository on github.com (the brief asks for a public repo), then:

```bash
git remote add origin https://github.com/<you>/finn.git
git push -u origin main
```

### 2. Create the Railway service (once)
1. Sign in at railway.com with GitHub. The trial needs no card.
2. **New Project → Deploy from GitHub repo →** pick the repo. Railway reads `railway.json` and builds the `Dockerfile`.
3. Open the service → **Variables** and add:

   | Variable | Value | Why |
   |---|---|---|
   | `GEMINI_API_KEY` | your key | Model features (summaries, Q&A, deep research). Without it, everything else still works. |
   | `FINN_PUBLIC_DEMO` | `1` | Visitors can't upload their own LinkedIn export (everyone would see it); they get the sample instead. |
   | `FINN_AUTO_REFRESH_MIN` | `60` | Re-check filings and prices hourly. Keeps model use low on a free Gemini key. |

4. Right-click the service → **Attach volume**, mount path **`/data`**.
5. **Settings → Networking → Generate domain.** That URL is the demo link.

First build takes ~3–4 minutes; health check is `/api/health`.

### 3. Updating
Push to `main`. Railway rebuilds and redeploys; the volume (and anything imported on it) is kept.

## Keeping demo data fresh
- The app re-pulls filings and prices for the portfolio every `FINN_AUTO_REFRESH_MIN` minutes ("Checked Xm ago" on the Brief).
- NSE sometimes blocks cloud IPs. If the Brief stops updating, refresh the snapshot from your laptop instead:
  ```bash
  make ingest-all && make seed     # rebuilds api/seed/finn.db.gz from your local data
  git commit -am "Refresh demo data" && git push
  ```
  then in Railway delete and re-attach the volume (or run `rm /data/finn.db` from the service shell) so the next boot re-seeds.

## Try the image locally
```bash
make docker   # build + run on http://localhost:3200 with a throwaway volume
```

## Notes
- The Gemini free tier allows ~20 requests/day on some models; FINN skips exhausted models and uses the next.
  `Settings → AI usage today` shows what has been spent.
- Your local `.env` is never copied into the image (`.dockerignore`); set secrets only in Railway's Variables.
