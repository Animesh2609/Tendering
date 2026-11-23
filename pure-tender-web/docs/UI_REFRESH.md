# TenderBlock UI refresh

This update applies the visual direction of [transfer-aware-dupgt](https://github.com/Jrap-bit/transfer-aware-dupgt) to the existing TenderBlock React frontend. It is based on TenderBlock main commit `87a17075fe668e8bb2ecc7b3a0bbe0382284439f`. The reference was reviewed at commit `02f1d6638cc116a008e40ed9adf8c07a8808225c`.

## Design changes

- Near-black surfaces, a fine background grid, violet and amber lighting, translucent navigation and restrained borders.
- Self-hosted Geist Sans and Geist Mono, matching the reference's typography. The font packages retain their own licensing.
- A new landing page, workflow illustration, role cards, shared brand and split authentication layout.
- One visual system for Bidder, Lister, Admin, Evaluator and Auditor workspaces, including tables, metrics, forms, review dialogs and audit details.
- Dark is the default on first use. The existing light-theme preference and theme switch remain supported.
- Responsive rules for narrow screens, visible focus states and reduced-motion preferences.

The visual implementation is adapted for procurement. Movie recommendations, model output and unrelated reference content are not part of TenderBlock.

## Run against the backend

```sh
npm ci
npm run dev
```

The existing backend configuration, session checks, account verification and API adapters are preserved. Standard `dev`, `build` and live commands do not enable demo authentication. No Java or chaincode files were changed. Configure the API URL and backend target using the existing environment configuration for your deployment.

## Explore every changed view

```sh
npm run dev:demo
```

Open `/preview`. The gallery contains 33 page and view entries grouped by public access and the five roles. Every card opens an actual application screen, using a seeded sample account. The gallery includes tender and bid editing, evaluator history and scoring, approval/rejection dialogs, audit details, resolution and award dialogs. A floating **All previews** link returns to the gallery.

The explicit demo build is `npm run build:demo`. `/preview` and preview entry handlers are guarded by the existing `DEMO_MODE` condition. Demo-mode query parameters open nested staff views; they do not bypass live authentication or role authorization.

Sample records persist only in the browser. **Reset sample data** restores the demo state after trying actions. File downloads and actual ledger verification require the live backend; demo integrity indicators are not evidence of a real Fabric transaction. Some existing demo workflows differ from the live backend (for example, editable demo tenders use DRAFT while live tenders use SUBMITTED).

## Verification

- Production and explicit demo builds.
- Existing Java-controller contract comparison for 37 listed operations, using `BACKEND_SOURCE=../PureTender npm run test:contracts`. This is a static route check, not backend integration testing; the older checker still reports two optional GET entries as pending.
- React rendering/navigation checks for all 33 gallery entries in a simulated DOM, including role sign-in, edit forms, three evaluation cards, nested audit details and all four review dialogs.
- Theme switching and role-filtered gallery checks.
- Source whitespace validation.

Browser screenshots, responsive visual rendering and a running Spring Boot/Fabric end-to-end flow were not verified in this environment. The hosted gallery is provided for visual review; run your normal integration tests before replacing a live deployment.

## Review or integrate

Apply the supplied patch to the matching TenderBlock revision, or replace `pure-tender-web` with the supplied source directory. Install dependencies using the updated lockfile. Keep your deployment-specific environment files and secrets outside the delivery package. The UI preview site is a separate demo deployment, not the project's production backend.
