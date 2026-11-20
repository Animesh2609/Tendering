# pure-tender-web

One React application integrating the three supplied TenderBlock frontends. It includes the public site, registration, Bidder and Lister workspaces, company profiles, Admin reviews, Evaluator scoring, and Auditor investigations.

## Run with your Java backend

Requires Node.js 22.12+ (Node.js 24 recommended) and npm.

```bash
npm ci
npm run dev
```

Open http://localhost:5173. Start the existing Java application from `TenderBlock/PureTender` separately. Requests to `/api/v1` are proxied to `http://localhost:8080` by default. The Java backend itself is not included or modified.

For another backend address, create `.env.local` in this directory:

```dotenv
VITE_BACKEND_TARGET=http://localhost:8080
VITE_API_BASE_URL=/api/v1
VITE_BACKEND_CONTRACT=team
```

Use `npm run dev:live` for an explicitly named live mode. For that mode, overrides can also go in `.env.live.local`. Restart Vite after changing settings. Only the current `team` backend contract is supported for this integrated application.

Ordinary `dev` and `build` use the backend. They never switch to fake success or demo authentication when the backend is unavailable.

## Entry points

| Page                                      | URL                                               |
| ----------------------------------------- | ------------------------------------------------- |
| Public landing page                       | `/`                                               |
| Bidder/Lister registration                | `/register`                                       |
| Bidder/Lister login                       | `/login`                                          |
| Staff login: Admin, Evaluator, Auditor    | `/staff/login`                                    |
| Evaluator application                     | `/staff/register/evaluator`                       |
| Role-based staff workspace                | `/staff/workspace`                                |
| Bidder dashboard, opportunities, bids     | `/bidder`, `/bidder/tenders`, `/bidder/my-bids`   |
| Lister dashboard, new tender, own tenders | `/lister`, `/lister/create`, `/lister/my-tenders` |
| Bidder/Lister company profile             | `/profile`                                        |

`/admin`, `/evaluator`, and `/auditor` are convenience aliases to the authenticated user's staff workspace. Access is determined by the backend login response. Java `CONTRACTOR` and `AUTHORITY` map to the UI labels Bidder and Lister. Admin/Auditor accounts must already exist; this app retains the Evaluator registration flow from the supplied evaluator module. New accounts require Admin verification. Sign out and sign in again after approval to refresh account status.

## Browser-only demonstration

```bash
npm run dev:demo
```

All five roles use one local store, one session, and one theme. Demo changes survive a refresh and are visible when switching roles on the same origin. Use the following email addresses with password `Demo@12345`:

- `bidder@demo.test`
- `lister@demo.test`
- `admin@demo.test`
- `evaluator@demo.test`
- `auditor@demo.test`

Demo data includes pending reviews, evaluation assignments, and integrity reports. Demo tenders follow the bidder/lister module's draft → request approval flow; live Java tenders are created as SUBMITTED immediately. Demo proposals store file metadata and hashes, not the original PDF bytes. Download actual submitted files in live mode. Integrity markers and awards in the demo are browser simulations.

To reset the demo, clear `pure_tender_demo_v1` in browser localStorage and sign out. Demo mode requires both `--mode demo` and `VITE_DEMO_MODE=true`; `.env.demo` provides the flag.

## Build and deployment

```bash
npm run build
npm run preview
```

The ZIP includes a live-mode `dist/` build. Rebuild after changing `VITE_API_BASE_URL`; Vite injects public settings at build time. The dev server proxy is not a production deployment configuration.

GitHub Pages builds set `GITHUB_PAGES=true` in the deployment workflow, use `/TenderBlock/` as the app base path, create `dist/404.html` as a copy of `dist/index.html`, and disable Jekyll processing for the uploaded build. Direct links to React routes therefore fall back to the SPA entry point.

Configure the production web server to:

1. Serve `dist/` and fall back to `index.html` for React routes.
2. Reverse proxy `/api/v1/` to Spring Boot, preserving the path and Authorization header.

See `docs/nginx.example.conf`. When calling an absolute backend URL from the browser instead, configure the Java server's CORS policy for your frontend origin. Never place secrets in a `VITE_` variable.

## Validation

```bash
npm run lint
npm run test:contracts
npx playwright install chromium
npm test
```

If Chromium is already installed, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to its executable path. The browser tests start live-mode and demo-mode Vite servers on ports 5173 and 5176. Live-mode tests intercept HTTP calls with contract-shaped fixtures; they do not require a running Java backend. Keep those ports free when running the suite.

For a fresh route check against your local Java checkout:

```bash
BACKEND_SOURCE=/path/to/TenderBlock/PureTender npm run test:contracts
```

See `docs/VALIDATION.md` for the executed checks and their limits, `docs/BACKEND_HANDOFF.md` for the five pending endpoints, and `docs/INTEGRATION_NOTES.md` for the merge structure.
