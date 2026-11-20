import { DEMO_MODE, API_BASE_URL, BACKEND_CONTRACT } from "../data/constants";
import {
  TEAM_ROUTES,
  toTeamRegisterRequest,
  toTeamCompanyProfileRequest,
  toTeamTenderRequest,
} from "./contracts";
import { createTeamBidClient, readTeamPages } from "./teamBidClient";
import { http } from "./http";
import { proposalLimitBytes } from "./proposalValidation.js";
import {
  toRegisterRequest,
  toDemoRegisterRequest,
  toLoginRequest,
  toCurrentUser,
  toTenderCreateRequest,
  normalizeTender,
  normalizeTenderList,
  normalizeBid,
} from "./dtos";
import {
  demoRegister,
  demoLogin,
  demoGetTenders,
  demoGetTender,
  demoMyTenders,
  demoTenderAward,
  demoCreateTender,
  demoUpdateTender,
  demoRequestApproval,
  demoCancelTender,
  demoSubmitBid,
  demoUpdateBid,
  demoMyBids,
} from "./demoStore";

//#region Authentication APIs
// Team mode uses the Spring Boot API pinned in docs/BACKEND_SNAPSHOT.json.
// Run npm run dev:live for API mode; the demo store remains a separate simulation.
function parseSession(raw) {
  const token = raw?.accessToken ?? raw?.token;
  if (!token) throw new Error("Login response has no accessToken.");
  // Published AuthResponse is flat: userId, fullName, email, role, accessToken, tokenType.
  const user = toCurrentUser(raw.user ?? raw);
  return { token, user };
}
export const authApi = {
  async register(form) {
    if (DEMO_MODE) return demoRegister(toDemoRegisterRequest(form));
    // The existing Spring Boot Role enum uses CONTRACTOR/AUTHORITY.
    // Frontend labels them BIDDER/LISTER; never allow staff role selection here.
    const role =
      form.role === "BIDDER"
        ? "CONTRACTOR"
        : form.role === "LISTER"
          ? "AUTHORITY"
          : null;
    if (!role) throw new Error("Select Bidder or Lister.");
    if (BACKEND_CONTRACT === "team") {
      // Team RegisterRequest.java has exactly three JSON fields.
      const created = await http(TEAM_ROUTES.register(role), {
        method: "POST",
        body: toTeamRegisterRequest(form),
      });
      if (!created?.accessToken)
        throw new Error(
          "Account created, but registration did not return a token for saving company details.",
        );
      try {
        const companyProfile = await http(TEAM_ROUTES.companyProfile, {
          method: "POST",
          body: toTeamCompanyProfileRequest(form),
          token: created.accessToken,
        });
        return { ...created, profileSaved: true, companyProfile };
      } catch (err) {
        // The user account already exists; never prompt a second registration.
        // The user can sign in and complete the missing profile from /profile.
        return {
          ...created,
          profileSaved: false,
          profileWarning: `Your account was created, but the company profile was not saved (${err.message}). Sign in and complete it from My Profile.`,
        };
      }
    }
    return http(`/auth/register/${role}`, {
      method: "POST",
      body: toRegisterRequest(form),
    });
  },
  async login(form) {
    const raw = DEMO_MODE
      ? await demoLogin(toLoginRequest(form))
      : await http("/auth/login", {
          method: "POST",
          body: toLoginRequest(form),
        });
    const result = parseSession(raw);
    if (!["BIDDER", "LISTER"].includes(result.user.role))
      throw new Error("Staff accounts must sign in at /staff/login.");
    if (!DEMO_MODE && BACKEND_CONTRACT === "team") {
      // Registration and company profile use separate DTOs in the team's branch.
      // A missing profile must not fabricate company information.
      try {
        const profile = await http(TEAM_ROUTES.ownCompanyProfile, {
          token: result.token,
        });
        result.user = {
          ...result.user,
          organizationName: profile.companyName ?? "",
          phoneNumber: profile.contactNumber ?? "",
          companyProfile: profile,
        };
        result.user.profileMissing = false;
      } catch (err) {
        // Profile availability must not turn a successful password login into
        // a failed login. /profile shows the error and supports recovery.
        // An empty 403 from the current server can hide a 404, an expired token,
        // or another failure. Keep that state unknown; never guess that it is missing.
        result.user.profileMissing = err.status === 404 ? true : null;
        if (err.status !== 404) result.user.profileLoadError = err.message;
      }
    }
    return result;
  },
};

//#endregion

//#region Company profile API
export const companyProfileApi = {
  async mine(token) {
    if (DEMO_MODE) return null;
    if (BACKEND_CONTRACT !== "team")
      throw new Error("Company profile API requires the team backend.");
    return http(TEAM_ROUTES.ownCompanyProfile, { token });
  },
  async create(form, token) {
    if (DEMO_MODE || BACKEND_CONTRACT !== "team")
      throw new Error(
        "Real company profile creation requires the team backend.",
      );
    return http(TEAM_ROUTES.companyProfile, {
      method: "POST",
      body: toTeamCompanyProfileRequest(form),
      token,
    });
  },
  async update(form, token) {
    if (DEMO_MODE || BACKEND_CONTRACT !== "team")
      throw new Error("Real company profile updates require the team backend.");
    return http(TEAM_ROUTES.ownCompanyProfile, {
      method: "PUT",
      body: toTeamCompanyProfileRequest(form),
      token,
    });
  },
};

//#endregion

//#region Staff authentication API
export const staffAuthApi = {
  async login(form) {
    const raw = DEMO_MODE
      ? await demoLogin(toLoginRequest(form))
      : await http("/auth/login", {
          method: "POST",
          body: toLoginRequest(form),
        });
    const result = parseSession(raw);
    if (!["ADMIN", "EVALUATOR", "AUDITOR"].includes(result.user.role))
      throw new Error("Only assigned staff accounts may use this portal.");
    return result;
  },
};

//#endregion

//#region Pagination helpers
// Page<T> response from Spring Data. Search in the visible table is local to
// the fetched page because the backend does not expose a tender keyword filter.
async function teamPage(
  path,
  token,
  page = 0,
  size = 10,
  normalizeItem = (value) => value,
) {
  if (
    !Number.isInteger(page) ||
    page < 0 ||
    !Number.isInteger(size) ||
    size < 1 ||
    size > 100
  ) {
    throw new Error("Invalid pagination request.");
  }
  const response = await http(`${path}?page=${page}&size=${size}`, { token });
  if (!Array.isArray(response?.content))
    throw new Error("Expected a Spring Page response.");
  return {
    items: response.content.map(normalizeItem),
    page: response.number ?? page,
    size: response.size ?? size,
    totalPages: Math.max(1, response.totalPages ?? 1),
    totalElements: response.totalElements ?? response.content.length,
  };
}
const pageFromArray = (list, page, size) => ({
  items: list.slice(page * size, (page + 1) * size),
  page,
  size,
  totalPages: Math.max(1, Math.ceil(list.length / size)),
  totalElements: list.length,
});

//#endregion

//#region Tender API
export const tenderApi = {
  async listPage(token, page = 0, size = 10) {
    if (!DEMO_MODE && BACKEND_CONTRACT === "team")
      return teamPage(
        TEAM_ROUTES.publishedTenders,
        token,
        page,
        size,
        normalizeTender,
      );
    const all = await this.list(token);
    return pageFromArray(all, page, size);
  },
  async minePage(user, token, page = 0, size = 10) {
    if (!DEMO_MODE && BACKEND_CONTRACT === "team")
      return teamPage(
        TEAM_ROUTES.myTenders,
        token,
        page,
        size,
        normalizeTender,
      );
    const all = await this.mine(user, token);
    return pageFromArray(all, page, size);
  },
  async list(token) {
    return DEMO_MODE
      ? demoGetTenders()
      : normalizeTenderList(
          BACKEND_CONTRACT === "team"
            ? await readTeamPages(TEAM_ROUTES.publishedTenders, token, http)
            : await http("/tenders", { token }),
        );
  },
  async detail(id, token) {
    return DEMO_MODE
      ? demoGetTender(id)
      : normalizeTender(
          await http(`/tenders/${encodeURIComponent(id)}`, { token }),
        );
  },
  async award(user, id, token) {
    return DEMO_MODE
      ? demoTenderAward(user, id)
      : http(`/tenders/${encodeURIComponent(id)}/award`, { token });
  },
  async mine(user, token) {
    return DEMO_MODE
      ? demoMyTenders(user)
      : normalizeTenderList(
          BACKEND_CONTRACT === "team"
            ? await readTeamPages(TEAM_ROUTES.myTenders, token, http)
            : await http("/tenders/mine", { token }),
        );
  },
  async create(user, form, token) {
    const dto =
      DEMO_MODE || BACKEND_CONTRACT !== "team"
        ? toTenderCreateRequest(form)
        : toTeamTenderRequest(form);
    const response = DEMO_MODE
      ? await demoCreateTender(user, dto)
      : await http("/tenders", { method: "POST", body: dto, token });
    return normalizeTender(response);
  },
  async update(user, id, form, token) {
    const dto =
      DEMO_MODE || BACKEND_CONTRACT !== "team"
        ? toTenderCreateRequest(form)
        : toTeamTenderRequest(form);
    const response = DEMO_MODE
      ? await demoUpdateTender(user, id, dto)
      : await http(`/tenders/${encodeURIComponent(id)}`, {
          method: BACKEND_CONTRACT === "team" ? "PUT" : "PATCH",
          body: dto,
          token,
        });
    return normalizeTender(response);
  },
  async cancel(user, id, reason, token) {
    if (DEMO_MODE) return demoCancelTender(user, id, String(reason ?? ""));
    if (BACKEND_CONTRACT !== "team")
      throw new Error("Tender cancellation requires the team backend.");
    if (!String(reason || "").trim() || String(reason).length > 2000)
      throw new Error("Enter a cancellation reason of 1–2000 characters.");
    return http(TEAM_ROUTES.cancelTender(id), {
      method: "PATCH",
      body: { reason: String(reason).trim() },
      token,
    });
  },
  async requestApproval(user, id, token) {
    if (DEMO_MODE) return demoRequestApproval(user, id);
    if (BACKEND_CONTRACT === "team")
      throw new Error(
        "The team backend creates tenders as SUBMITTED and has no request-approval endpoint.",
      );
    return http(`/tenders/${encodeURIComponent(id)}/request-approval`, {
      method: "POST",
      token,
    });
  },
};

//#endregion

//#region Bid API and proposal upload
function buildBidBody(form, partial = false) {
  const body = new FormData();
  body.append("amount", String(form.amount));
  body.append("proposalSummary", form.proposalSummary);
  body.append("remarks", form.remarks || "");
  if (form.evidence) body.append("eligibilityProof", form.evidence);
  if (form.proposal) body.append("proposalDocument", form.proposal);
  if (!partial && (!form.evidence || !form.proposal))
    throw new Error("Both PDF files are required for a new bid.");
  return body;
}
export const PROPOSAL_MAX_BYTES = proposalLimitBytes(
  import.meta.env.VITE_PROPOSAL_MAX_MB,
);
const teamBid = createTeamBidClient(http, {
  proposalMaxBytes: PROPOSAL_MAX_BYTES,
});
export const bidApi = {
  async minePage(user, token, page = 0, size = 10) {
    if (!DEMO_MODE && BACKEND_CONTRACT === "team")
      return teamPage(TEAM_ROUTES.myBids, token, page, size, normalizeBid);
    const all = await this.mine(user, token);
    return pageFromArray(all, page, size);
  },
  // The team's backend requires draft -> PDF upload -> submit. Keep these steps
  // explicit so an interrupted upload does not silently create a second bid.
  async createDraft(user, tenderId, amount, token) {
    if (DEMO_MODE || BACKEND_CONTRACT !== "team")
      throw new Error("Draft API is only available with the team backend.");
    return teamBid.createDraft(tenderId, amount, token);
  },
  async updateDraft(user, bidId, amount, token) {
    if (DEMO_MODE || BACKEND_CONTRACT !== "team")
      throw new Error("Draft API is only available with the team backend.");
    return teamBid.updateDraft(bidId, amount, token);
  },
  async uploadProposal(user, bidId, file, token) {
    if (DEMO_MODE || BACKEND_CONTRACT !== "team")
      throw new Error("Proposal upload requires the team backend.");
    return teamBid.uploadProposal(bidId, file, token);
  },
  async finalizeDraft(user, bidId, token) {
    if (DEMO_MODE || BACKEND_CONTRACT !== "team")
      throw new Error("Bid finalization requires the team backend.");
    return teamBid.submitDraft(bidId, token);
  },
  async detail(user, bidId, token) {
    if (DEMO_MODE)
      return demoMyBids(user).find((b) => String(b.id) === String(bidId));
    if (BACKEND_CONTRACT === "team") return teamBid.detail(bidId, token);
    return http(`/bids/${encodeURIComponent(bidId)}`, { token });
  },
  async submit(user, tenderId, form, token) {
    if (DEMO_MODE) return demoSubmitBid(user, tenderId, form);
    if (BACKEND_CONTRACT === "team")
      throw new Error(
        "Use draft creation, proposal upload and bid submission in team mode.",
      );
    return http(`/tenders/${encodeURIComponent(tenderId)}/bids`, {
      method: "POST",
      body: buildBidBody(form),
      token,
    });
  },
  async update(user, bidId, form, token) {
    if (DEMO_MODE) return demoUpdateBid(user, bidId, form);
    if (BACKEND_CONTRACT === "team")
      return teamBid.updateDraft(bidId, form.amount, token);
    return http(`/bids/${encodeURIComponent(bidId)}`, {
      method: "PATCH",
      body: buildBidBody(form, true),
      token,
    });
  },
  async mine(user, token) {
    if (DEMO_MODE) return demoMyBids(user);
    if (BACKEND_CONTRACT === "team") return teamBid.mine(token);
    const result = await http("/bids/me", { token });
    return Array.isArray(result) ? result : (result?.content ?? []);
  },
};

//#endregion

//#region Authorized proposal downloads
// Authorized PDF download: NEVER put a JWT token in the URL/query string.
export async function downloadBidPdf(bidId, kind, token) {
  if (DEMO_MODE) throw new Error("Demo mode does not store downloadable PDFs.");
  if (!token) throw new Error("Sign in to download your proposal.");
  const path =
    BACKEND_CONTRACT === "team"
      ? TEAM_ROUTES.downloadProposal(bidId)
      : `/bids/${encodeURIComponent(bidId)}/files/${encodeURIComponent(kind)}`;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok)
    throw new Error(`PDF download failed (${response.status}).`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  const disposition = response.headers.get("Content-Disposition") || "";
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  let suggested = `tenderblock-proposal-${bidId}.pdf`;
  try {
    const rawName = utf8
      ? decodeURIComponent(utf8[1].trim())
      : plain?.[1]?.trim();
    if (rawName) suggested = rawName;
  } catch {
    /* invalid filename encoding: use fallback */
  }
  link.download = [...suggested]
    .map((character) => {
      const code = character.charCodeAt(0);
      return code < 32 || character === "/" || character === "\\"
        ? "_"
        : character;
    })
    .join("");
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}
//#endregion
