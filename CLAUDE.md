# FartPort — Agent Handoff Document

## What This Is
FartPort (formerly PlugPffft) is a desktop app (Electron) that plays a fart sound when you plug/unplug your laptop charger. It sells for **$4.99 one-time** via Stripe. This repo is the **Electron app**. The landing page is a separate repo.

---

## Repos & Paths

| Repo | GitHub | Local path |
|------|--------|------------|
| Electron app | `eltonoliveira3012-cyber/plugpffft` | `/Users/eltoncostadeoliveirajr/Documents/Playground/plugpffft/` |
| Landing page | `eltonoliveira3012-cyber/pfft-power-sounds` | `/Users/eltoncostadeoliveirajr/Downloads/n8n/pfft-power-sounds/` |

**Git push note:** HTTPS auth is broken due to macOS Keychain interference. Use **GitHub Desktop** to push both repos.

---

## App Name History
- Originally: **PlugPffft**
- Renamed to: **FartPort** (final name, April 2025)
- All references updated: `package.json`, `electron-builder.yml`, landing page components, Stripe product, `index.html`

---

## Infrastructure

### Supabase
- **Project:** `plugpffft`
- **Project ID:** `zqnlohdoagqspoqptcwz`
- **URL:** `https://zqnlohdoagqspoqptcwz.supabase.co`
- **Anon key** (public, safe to commit): hardcoded in `src/lib/config.ts` in the landing page repo

#### Edge Functions (all deployed, `verify_jwt: false`)
| Function | Version | Purpose |
|----------|---------|---------|
| `create-checkout` | v6 | Creates Stripe Checkout session, redirects user to Stripe |
| `stripe-webhook` | deployed | Verifies Stripe signature, inserts into `purchases` table |
| `get-downloads` | deployed | Verifies session_id, returns signed GitHub Release download URLs |

#### Database
- Table: `purchases` — stores completed Stripe payments
  - `stripe_session_id` (unique), `stripe_payment_intent_id`, `customer_email`, `paid_at`, `amount`

#### Supabase Secrets (must be set in Supabase dashboard → Settings → Edge Functions)
| Secret | Value |
|--------|-------|
| `STRIPE_SECRET_KEY` | From Stripe dashboard (live key) |
| `STRIPE_WEBHOOK_SECRET` | From Stripe webhook endpoint |
| `STRIPE_PRICE_ID` | `price_1TICRk43ADtPwwfeaJkVkwKX` |
| `SITE_URL` | Optional — `create-checkout` falls back to request Origin header if not set |

### Stripe
- **Product:** FartPort (`prod_UGjvH6NmgGOa8J`)
- **Price ID:** `price_1TICRk43ADtPwwfeaJkVkwKX` ($4.99 USD, one-time)
- **Webhook endpoint:** `https://zqnlohdoagqspoqptcwz.supabase.co/functions/v1/stripe-webhook`
- **Webhook event:** `checkout.session.completed`

### GitHub Releases (file hosting)
Builds are hosted on GitHub Releases in `eltonoliveira3012-cyber/plugpffft`.
The `get-downloads` Edge Function fetches the latest release via GitHub API and returns download URLs.

Current builds in latest release:
| Platform | Filename | Size |
|----------|----------|------|
| macOS ARM64 | `FartPort-1.0.0-mac-arm64.dmg` | ~91 MB |
| macOS x64 | `FartPort-1.0.0-mac-x64.dmg` | ~97 MB |
| Windows | `FartPort-1.0.0-win-x64.exe` | ~75 MB |

---

## Landing Page Architecture

**Stack:** React + TypeScript + Vite + Tailwind CSS + shadcn/ui + TanStack React Query
**Theme:** Dark background (`220 15% 7%`), electric yellow accent (`54 100% 60%`)
**Deployed via:** Lovable (syncs from GitHub repo automatically on push)

### Key Files
| File | Purpose |
|------|---------|
| `src/lib/config.ts` | Supabase URL + anon key (hardcoded fallbacks) |
| `src/hooks/useCheckout.ts` | Calls `create-checkout`, redirects to Stripe |
| `src/hooks/useDownloads.ts` | Calls `get-downloads` with session_id, returns download links |
| `src/pages/Success.tsx` | Post-payment page — reads `?session_id=`, shows download buttons |
| `src/App.tsx` | Routes: `/` = landing, `/success` = download page |
| `src/components/HeroSection.tsx` | Hero with "Buy for $4.99" CTA |
| `src/components/DownloadSection.tsx` | Second CTA section |
| `src/components/FAQSection.tsx` | Custom accordion FAQ |
| `src/components/FeaturesSection.tsx` | 6-card feature grid |
| `src/components/HowItWorks.tsx` | 3-step numbered cards |
| `src/components/Footer.tsx` | Minimal footer |

### Payment Flow
```
User clicks "Buy for $4.99"
  → useCheckout → POST /functions/v1/create-checkout
      → Stripe Checkout ($4.99)
          → success: /success?session_id=xxx
              → useDownloads → GET /functions/v1/get-downloads?session_id=xxx
                  → verifies payment in purchases table (or direct Stripe API)
                  → returns GitHub Release download URLs
          → Stripe webhook → /functions/v1/stripe-webhook
              → inserts row into purchases table
```

---

## Electron App

**Stack:** Electron + TypeScript (no framework)
**Build tool:** electron-builder
**Output:** `release/` directory
**App behavior:** Runs as a menu bar (macOS) / system tray (Windows) app — no dock icon. Plays fart MP3 on charger connect/disconnect.

### Build Commands
```bash
npm run dist:mac:arm64   # macOS Apple Silicon
npm run dist:mac:x64     # macOS Intel
npm run dist:win         # Windows
```

### GitHub Actions
Workflow: `.github/workflows/build-release.yml`
Trigger: push a tag (`git tag v1.x.x && git push origin v1.x.x`) or manually via `workflow_dispatch`
Builds all 3 platforms and creates a GitHub Release.
**Code signing is disabled** (`CSC_IDENTITY_AUTO_DISCOVERY: false`) — builds are unsigned.

---

## Pending / Known Issues

- **Landing page not yet pushed to GitHub** — redesign + FartPort rename commits exist locally, need to be pushed via GitHub Desktop so Lovable redeploys.
- **Supabase secrets** — `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` must be confirmed set in Supabase dashboard. `STRIPE_PRICE_ID` was previously set to wrong value by accident; correct value is `price_1TICRk43ADtPwwfeaJkVkwKX`.
- **Unsigned builds** — macOS will show a Gatekeeper warning. Users need to right-click → Open to bypass on first launch.
- **No custom domain yet** — site is on Lovable subdomain. When a custom domain is added, set `SITE_URL` secret in Supabase.

---

## Testing Checklist
1. Click "Buy for $4.99" → should redirect to Stripe checkout
2. Use test card `4242 4242 4242 4242`, any future expiry, any CVC
3. After payment → redirected to `/success?session_id=xxx`
4. Download buttons appear for available platforms
5. Check Supabase `purchases` table for new row (webhook working)
6. Visiting `/success?session_id=fake` should show error (not downloads)
