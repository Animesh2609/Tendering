# Test case catalogue

This catalogue reflects the current Java test suite: 49 focused service/unit tests and the existing Spring application context smoke test. Each row maps to one JUnit `@Test` method; multiple assertions within a method remain one test case.

| Test ID | Trace | Operation | Expected outcome |
|---|---|---|---|
| TC-01 | AuthServiceTest | Register with mixed-case email and padded name | Email is normalized, name is trimmed, password is encoded, and an auth response with token is returned. |
| TC-02 | AuthServiceTest | Register duplicate email | HTTP 409; no account is saved. |
| TC-03 | AuthServiceTest | Register with ADMIN role | HTTP 403; no account is saved. |
| TC-04 | AuthServiceTest | Log in with valid credentials for a pending user | Auth response includes bearer token and PENDING account status. |
| TC-05 | AuthServiceTest | Log in with unknown email | HTTP 401. |
| TC-06 | AuthServiceTest | Log in with incorrect password | HTTP 401. |
| TC-07 | AuthServiceTest | Log in with rejected account | HTTP 403. |
| TC-08 | AuthServiceTest | Log in with disabled account | HTTP 403. |
| TC-09 | AuthServiceTest | Read account status using mixed-case email | Email lookup is normalized and VERIFIED status is returned. |
| TC-10 | AuthServiceTest | Read status for unknown user | HTTP 404. |
| TC-11 | TenderBidServiceTest | Create tender as verified authority | SUBMITTED tender response is returned and blockchain record creation is requested. |
| TC-12 | TenderBidServiceTest | Create tender with past submission deadline | HTTP 400; tender is not saved. |
| TC-13 | TenderBidServiceTest | Update a published tender | HTTP 400; tender is not saved. |
| TC-14 | TenderBidServiceTest | Read another authority's private tender | HTTP 403. |
| TC-15 | TenderBidServiceTest | Cancel published tender with padded reason | Tender becomes CANCELLED; reason is trimmed and tender is saved. |
| TC-16 | TenderBidServiceTest | Create bid as verified contractor | DRAFT bid is saved with quoted amount. |
| TC-17 | TenderBidServiceTest | Create a second bid for same tender and contractor | HTTP 409; bid is not saved. |
| TC-18 | TenderBidServiceTest | Submit draft bid without proposal | HTTP 400; bid is not saved. |
| TC-19 | TenderBidServiceTest | Submit draft bid with proposal before deadline | Bid becomes SUBMITTED, submission time is set, and blockchain record creation is requested. |
| TC-20 | TenderBidServiceTest | Update an evaluated bid | HTTP 400. |
| TC-21 | AdminCompanyServiceTest | Verify pending user | User becomes VERIFIED and is saved. |
| TC-22 | AdminCompanyServiceTest | Verify user who is not pending | HTTP 409. |
| TC-23 | AdminCompanyServiceTest | Disable an admin account | HTTP 403. |
| TC-24 | AdminCompanyServiceTest | Enable disabled account | User becomes VERIFIED. |
| TC-25 | AdminCompanyServiceTest | Approve submitted tender with verified evaluator | Tender becomes PUBLISHED and evaluator assignment is saved. |
| TC-26 | AdminCompanyServiceTest | Reject submitted tender | Tender becomes REJECTED and rejection reason is stored. |
| TC-27 | AdminCompanyServiceTest | Create profile for contractor | Profile is saved and response is linked to the user. |
| TC-28 | AdminCompanyServiceTest | Create duplicate company profile | HTTP 409. |
| TC-29 | AdminCompanyServiceTest | Update profile after user verification | HTTP 403. |
| TC-30 | EvaluationAuditServiceTest | Assigned evaluator opens bids after opening time | Submitted bid becomes OPENED; tender becomes UNDER_EVALUATION. |
| TC-31 | EvaluationAuditServiceTest | Open bids for non-published tender | HTTP 409. |
| TC-32 | EvaluationAuditServiceTest | Open bids before opening time | HTTP 403. |
| TC-33 | EvaluationAuditServiceTest | Open tender with no submitted bids | HTTP 409. |
| TC-34 | EvaluationAuditServiceTest | Unassigned evaluator opens bids | HTTP 403. |
| TC-35 | EvaluationAuditServiceTest | Unverified evaluator opens bids | HTTP 403. |
| TC-36 | EvaluationAuditServiceTest | Auditor claims open integrity report | Report becomes UNDER_REVIEW and is assigned to the auditor. |
| TC-37 | EvaluationAuditServiceTest | Claim report already assigned to an auditor | HTTP 409. |
| TC-38 | EvaluationAuditServiceTest | Claim report that is already resolved | HTTP 409. |
| TC-39 | EvaluationAuditServiceTest | Audit tender outside auditable statuses | HTTP 403; no blockchain read is requested. |
| TC-40 | BlockchainServicesTest | Hash known content `abc` | Standard SHA-256 digest is returned. |
| TC-41 | BlockchainServicesTest | Verify content against its correct hash | Match returns true. |
| TC-42 | BlockchainServicesTest | Verify using whitespace-padded uppercase hash | Match returns true. |
| TC-43 | BlockchainServicesTest | Verify null content, null hash, or incorrect hash | Each invalid input returns false. |
| TC-44 | BlockchainServicesTest | Create tender integrity record | Fabric create is requested with `TENDER:<id>` and TENDER type. |
| TC-45 | BlockchainServicesTest | Update tender integrity record | Fabric update is requested with `TENDER:<id>` and a payload hash. |
| TC-46 | BlockchainServicesTest | Hash unchanged tender data twice | Both hashes are equal. |
| TC-47 | BlockchainServicesTest | Read record existence and record contents | Both calls delegate to FabricService and return its results. |
| TC-48 | BlockchainServicesTest | Create bid integrity record from stored proposal | Stored document hash is checked and Fabric create is requested with bid and parent tender IDs. |
| TC-49 | BlockchainServicesTest | Update bid using document with invalid hash | HTTP 500; no Fabric write is requested. |
| TC-50 | PureTenderApplicationTests | Load Spring application context | Application context starts successfully. |

## Scope note

These are the current unit/service and context-startup tests. They do not include live Fabric transaction tests, API-level HTTP tests, mobile layout checks, or end-to-end tests against PostgreSQL and Fabric. In particular, the blockchain tests mock `FabricService`; passing them does not establish that a Fabric peer is available.
