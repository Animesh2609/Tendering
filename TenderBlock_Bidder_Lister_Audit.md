# Bidder/Lister audit — uploaded v9

Reviewed on 8 November 2026. Input: `TenderBlock_Bidder_Lister_Updated_v9_2026-11-08.zip`. Target: public repository `srijangdas/TenderBlock`, **backend commit `8b7b5b7e3682ee3f16c60c7bafe87ceca984f092`**. The repository's `feature/bidder-lister` head `09ae6238d3...` contains an older backend; it must not be confused with the target. The v9 ZIP already supports submitted-bid updates, unlike the older frontend previously reviewed.

The shared ChatGPT URL timed out and then returned no readable body. No conclusions depend on its contents. Documents and suggested commands in the ZIP were treated as context rather than instructions; the included legacy backend patch was not applied.

## Execution and scope

- The shipped integration harness compiles the repository's original backend sources directly. All 80 checked source/POM files are byte-identical to the pinned repository commit.
- The harness adds an in-memory H2 database in PostgreSQL compatibility mode, a JWT fixture key, and two verified fixture accounts. It excludes only the normal startup class and the Fabric sample service/controller. Original API security, controllers, DTO validation, services and repositories execute unchanged.
- No backend source or other actors' UI was modified. `StaffWorkspacePage.jsx`, `StaffLoginPage.jsx`, `App.jsx`, `AuthContext.jsx`, and public login component are byte-identical to the supplied v9 base. The Admin/Evaluator/Auditor API adapters in `services.js` are unchanged.
- Shared `http.js` now parses monetary fields without rounding them. Staff UI formatting accepts these decimal strings; no staff UI layout or workflow is changed.
- H2 tests do not certify PostgreSQL storage, concurrency, production deployment, or Fabric transactions. PDF fixtures exercise the signature/MIME rules implemented by BidService; they do not establish full PDF-renderer validation.

## Confirmed frontend mismatches and fixes

Java paths below are relative to `PureTender/src/main/java/icu/telepathystudios/puretender/`. Frontend paths are relative to this project. All endpoints include `/api/v1`.

### F1 — missing-company-profile recovery chose the wrong operation

**Frontend:** `src/api/services.js` (`authApi.login`) and `src/pages/ProfilePage.jsx`.

**Java:** `controller/CompanyProfileController.java`, `service/role_man/CompanyProfileService.java`, `dto/company/CompanyProfileRequest.java`, and `config/SecurityConfig.java`.

| Operation | Expected payload / service behavior | Actual response |
|---|---|---|
| `GET /api/v1/company/profile/me` | No body; missing profile should produce service-level 404 | **403**, empty body |
| Original UI then used `PUT /api/v1/company/profile/me` | CompanyProfileRequest; updates an existing profile only | **403**, empty body; PUT cannot create it |
| `POST /api/v1/company/profile` | CompanyProfileRequest; creates a missing profile | **201**, CompanyProfileResponse |

Example accepted creation payload:

```json
{"companyName":"Integration Company","registrationNumber":null,"gstin":null,"pan":null,"address":"10 Integration Road","contactNumber":"9876543210","website":null}
```

The login adapter assumed only 404 meant missing; an empty 403 set `profileMissing=false`. The profile page then treated an unknown profile as an existing editable profile for a PENDING account and sent PUT. This was reproduced for both CONTRACTOR and AUTHORITY.

**Fix:** non-404 read failures keep existence unknown. The page disables ordinary updates until it has loaded an existing profile, offers retry, and offers an explicit **Create missing company profile** action. Only that explicit choice sends POST. A 403 is never interpreted as proof of absence. Backend uniqueness/authorization still apply; creation cannot overwrite an existing profile. A failed creation remains unconfirmed and does not trigger a blind PUT fallback.

**Regression evidence:** both original-v9 recovery cases failed; both pass with the fix, receiving real POST 201 responses.

### F2 — upload UI promised 10 MB but the default server accepts 1 MB

**Frontend:** `src/components/TeamBidForm.jsx`, `src/api/teamBidClient.js`; new `src/api/proposalValidation.js`.

**Java:** `controller/BidController.java`, `service/BidService.java` (`uploadProposal`, `validatePdf`); Spring Boot multipart defaults, with no committed override.

**HTTP:** `PUT /api/v1/bids/{bidId}/proposal`.

**Payload:** `multipart/form-data` with exactly the field **file**, containing a non-empty PDF with MIME type `application/pdf` and `%PDF-` header. Service upper bound: 10 MiB; transport default per-file bound: 1 MiB.

**Actual original-v9 behavior:** selecting a 2 MiB PDF passed client validation, created a DRAFT (POST 201), then upload failed with **403, empty body**. The server logged `MaxUploadSizeExceededException`; error dispatch hid the intended transport error. The UI displayed `Request failed (403). Draft reference: ...`.

**Fix:** default to 1 MiB, with `VITE_PROPOSAL_MAX_MB` allowing a coordinated deployment override up to 10 MiB. Validate size, MIME and the same five-byte header as BidService **before creating/updating the bid**. Update the form label to its actual limit. A large invalid upload cannot leave a new draft merely because the frontend accepted it.

**Regression evidence:** original-v9 size case failed; fixed case rejects locally with the 1 MB message and sends no draft-creation request. Accepted small uploads still return **204** and the downloaded bytes match.

### F3 — BigDecimal values were rounded while parsing API responses

**Frontend:** `src/api/http.js`; new `src/api/parseApiJson.js`. The normalized values reach `src/components/TenderForm.jsx`, `TeamBidForm.jsx`, `TenderDetailsPanel.jsx`, and bid/tender listings.

**Java:** `dto/tender/TenderResponse.java`, `dto/bid/BidResponse.java`, `model/classes/Tender.java`, `model/classes/Bid.java`, `TenderService.java`, `BidService.java`.

**HTTP:** `POST /api/v1/tenders`, `GET /api/v1/tenders/{id}` and paginated tender reads; the same transport issue applies to `quotedAmount` in bid responses.

**Example request fields:** `estimatedValue: "9007199254740993.45"`, along with title, description, submissionDeadline and openingDate. Numeric strings are accepted by the actual Java BigDecimal deserializer.

**Actual response:** success **201/200** with JSON numeric `"estimatedValue":9007199254740993.45`. Original frontend `JSON.parse` produced the JavaScript Number **9007199254740994**, losing the original digits/cents before formatting or editing.

**Fix:** preserve `estimatedValue`, `quotedAmount`, `amount` and `budget` number tokens as decimal strings before JSON.parse. Complete JSON string tokens are consumed so embedded quotation text is not rewritten. Pagination counts remain numbers. Existing string-valued money responses also work. Outgoing DTOs continue to send exact decimal strings.

**Regression evidence:** the original real-API precision case failed; the fixed browser reads exactly `"9007199254740993.45"`. Separate tests cover escaped text, nulls, already-quoted values and malformed JSON.

### F4 — profile's Browse published tenders link opened the dashboard

**Frontend:** `src/pages/ProfilePage.jsx`; route definitions in `src/App.jsx` are unchanged.

**Java:** `controller/TenderController.java` / `TenderService.getPublishedTenders`; no Java change needed.

**HTTP contract for browsing:** `GET /api/v1/tenders/published?page=0&size=10`, no body, Bearer token with CONTRACTOR role; response **200**, Spring Page<TenderResponse>.

**Actual original navigation:** the link went to `/bidder` (dashboard). Its summary requests could return 200, but the user did not reach the searchable browser. V9 intentionally split the dashboard from browsing.

**Fix:** point the link to `/bidder/tenders`. The original navigation regression failed at `/bidder`; fixed navigation reaches `/bidder/tenders`.

## Matched contracts verified against the running backend

| Frontend / Java files | Method and endpoint | Request payload | Actual response and authorization |
|---|---|---|---|
| RegisterPage, services, contracts / AuthController, AuthService, RegisterRequest | POST `/api/v1/auth/register/{CONTRACTOR\|AUTHORITY}` | `{fullName,email,password}` only | 201; flat AuthResponse, real JWT and PENDING status. Role is mapped from the URL, not an added company/role JSON field. |
| RegisterPage/ProfilePage, contracts / CompanyProfileController, CompanyProfileService, CompanyProfileRequest | POST `/api/v1/company/profile` | Seven profile fields listed above | 201 even while PENDING; profile creation is separate from account creation. |
| PublicLoginForm, services, dtos / AuthController, AuthService, LoginRequest, AuthResponse | POST `/api/v1/auth/login` | `{email,password}` | 200 for PENDING accounts; maps CONTRACTOR to BIDDER and AUTHORITY to LISTER. A missing profile does not turn a successful credential login into failure. |
| ProfilePage / CompanyProfileController and CompanyProfileService | GET/PUT `/api/v1/company/profile/me` | No body for GET; CompanyProfileRequest for PUT | 200 with existing profile; pending profile updates succeed. Existing verified profiles are read-only in UI. |
| BidderPage, tenderApi / TenderController, TenderService, TenderResponse | GET `/api/v1/tenders/published?page=0&size=10` | No body | 200 for pending CONTRACTOR; paginated response is correctly adapted. |
| BidderDashboardPage/BidderPage / BidController, BidService.getVerifiedContractor | GET `/api/v1/bids/my`; POST `/api/v1/bids/tender/{id}` | No body / `{quotedAmount:"100"}` | 403 while PENDING. UI avoids restricted history requests and blocks bidding. No frontend verification bypass was added. |
| TenderForm, contracts / TenderController, TenderService.getAuthority, CreateTenderRequest | POST `/api/v1/tenders` | `{title,description,estimatedValue,submissionDeadline,openingDate}` | Pending AUTHORITY: 403. VERIFIED AUTHORITY: 201, status SUBMITTED. It is not immediately published. |
| TenderForm, EditTenderPage / TenderController, TenderService.updateTender, UpdateTenderRequest | PUT `/api/v1/tenders/{id}` | Same five tender fields | 200 for own SUBMITTED tender in the verified workflow. ISO instants reflect IST input correctly. |
| TeamBidForm, teamBidClient / BidController, BidService, CreateBidRequest | POST `/api/v1/bids/tender/{id}` | `{quotedAmount:"2000.25"}` | 201 DRAFT for verified CONTRACTOR and published unexpired tender. |
| TeamBidForm, teamBidClient / BidController, BidService.uploadProposal | PUT `/api/v1/bids/{id}/proposal` | Multipart **file** | 204; no response JSON is required. |
| TeamBidForm, teamBidClient / BidController, BidService.submitBid | POST `/api/v1/bids/{id}/submit` | No body | 200 SUBMITTED after PDF upload. Missing-PDF attempt is blocked locally; direct server request is refused with 403 due to error masking. |
| MyBidsPage, downloadBidPdf / BidController, BidService.downloadProposal | GET `/api/v1/bids/{id}/proposal` | No body; Bearer header | 200 application/pdf; downloaded bytes match the uploaded fixture. |
| EditBidPage, TeamBidForm / BidController, BidService.updateBid/uploadProposal | PUT `/api/v1/bids/{id}` and optional PUT `/proposal` | `{quotedAmount:"1900.50"}` and optional multipart file | 200/204 for SUBMITTED before deadline. No second POST `/submit` occurs. V9 already supported this and it was preserved. |

## Backend defects / policy differences left unchanged

1. **Error dispatch hides useful errors.** `SecurityConfig` secures `/error`; `JwtFilter` does not restore normal request authentication during error dispatch. Wrong-password login (intended 401), duplicate registration (409), missing profile (404), validation failures (400), and multipart rejection become empty 403 responses. The audit never reclassifies every 403 as missing profile or an expired session. Generic errors cannot be made specific reliably solely in the frontend.
2. **Optional Fabric startup is not implemented.** Normal application startup still requires datasource/JWT/Fabric configuration and certificates. The test harness is not a production startup fix, and no Fabric transaction was verified.
3. **Cancellation policy intentionally differs.** V9 documentation describes a before-deadline PUBLISHED-only UI rule. Current `TenderService.cancelTender` also accepts UNDER_EVALUATION and has no deadline check. The existing stricter frontend policy was preserved; widening cancellation was not necessary for the requested registration/bidding fixes. The team must choose the server-enforced policy.
4. **Some service checks are uneven.** `TenderService.updateTender` checks owner, SUBMITTED state and dates, but does not call the verified-authority helper used by createTender. The frontend retains its verified-account guard rather than weakening it to exploit this difference.
5. **Status refresh requires re-login.** AuthResponse carries accountStatus, while the JWT carries email/role and no current-status endpoint is provided for public actors. The existing UI tells users to sign out/in after approval. Integration tests follow that actual contract.
6. **Staff UI and legacy overlay adapters remain outside scope.** Their previously reported route differences were not repaired or included in the successful Bidder/Lister verdict.

## Evidence and final verification

- Original v9: four targeted cases failed (two actor recovery cases, precision, upload limit); the separate profile navigation case also failed.
- Fixed source: **nine real browser integration scenarios passed** against the shipped standalone Spring Boot/H2 harness.
- The submitted quotation/PDF replacement workflow was rerun after adding the replacement assertion and passed, without a re-submit request.
- ESLint, both production build modes, the original eight test scripts, and new response/PDF validation checks passed. Older script names such as `live-v7.test.mjs` remain contract tests; they are not counted as live integration.
- See `README_INTEGRATION.md` for exact reproduction commands. `audit-evidence/` holds redacted baseline/fixed results, observed backend probe responses, source-integrity data and the change-scope manifest.

The core Bidder/Lister success flows are compatible with the pinned Java backend in the tested configuration. The backend-only limitations above remain material for running the normal application and for production deployment.
