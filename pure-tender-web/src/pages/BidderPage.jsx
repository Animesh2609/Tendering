import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { bidApi, tenderApi, downloadBidPdf } from "../api/services";
import { BACKEND_CONTRACT, DEMO_MODE } from "../data/constants";
import { useAuth } from "../context/AuthContext";
import PageTitle from "../components/PageTitle";
import TenderTable from "../components/TenderTable";
import TenderDetailsPanel from "../components/TenderDetailsPanel";
import PaginationControls from "../components/PaginationControls";
import StatusBadge from "../components/StatusBadge";
import { formatCurrency, formatDate } from "../utils/format";

export default function BidderPage({
  title = "Tender opportunities",
  showAllInitially = false,
}) {
  const { user, token } = useAuth();
  const { tenderId } = useParams();
  const [tenders, setTenders] = useState([]);
  const [ownBids, setOwnBids] = useState([]);
  const [bidWarning, setBidWarning] = useState("");
  const [bidsReady, setBidsReady] = useState(false);
  const [page, setPage] = useState(0);
  const [pageInfo, setPageInfo] = useState({ totalPages: 1, totalElements: 0 });
  const teamMode = !DEMO_MODE && BACKEND_CONTRACT === "team";
  // BidService.getMyBids() requires VERIFIED, even for read-only retrieval.
  const bidHistoryRestricted = teamMode && user?.verified !== true;
  const [selectedId, setSelectedId] = useState(tenderId || null);
  const [directTender, setDirectTender] = useState(null);
  const [directError, setDirectError] = useState("");
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(showAllInitially || Boolean(tenderId));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshNumber, setRefreshNumber] = useState(0);
  const [lastSubmitted, setLastSubmitted] = useState(null);
  const tenderDetailsRef = useRef(null);

  function selectTender(tenderId) {
    setSelectedId(tenderId);
    window.requestAnimationFrame(() => {
      tenderDetailsRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }

  function handleSubmitted(bid) {
    if (!bid?.id) {
      setRefreshNumber((number) => number + 1);
      return;
    }
    // Retain the confirmed server response. Reloading /bids/my here unmounted
    // the success state and could offer a new form if that read was stale.
    setOwnBids((previous) => [
      bid,
      ...previous.filter((item) => item.id !== bid.id),
    ]);
    setLastSubmitted(bid);
  }

  useEffect(() => {
    let active = true;
    setLoading(true);

    tenderApi
      .listPage(token, page, 10)
      .then((result) => {
        if (!active) return;
        setTenders(result.items.filter((t) => t.status === "PUBLISHED"));
        setPageInfo({
          totalPages: result.totalPages,
          totalElements: result.totalElements,
        });
        setError("");
      })
      .catch((err) => {
        if (active)
          setError(err.message || "Could not load published tenders.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token, refreshNumber, page]);

  useEffect(() => {
    if (!teamMode) return;
    let active = true;
    // A pending account can browse published tenders, but /bids/my returns 403.
    // Do not make this forbidden request or misrepresent it as a tender-list error.
    if (bidHistoryRestricted) {
      setOwnBids([]);
      setBidWarning("");
      setBidsReady(true);
      return () => {
        active = false;
      };
    }
    setBidsReady(false);
    bidApi
      .mine(user, token)
      .then((records) => {
        if (active) {
          setOwnBids(records);
          setBidWarning("");
          setBidsReady(true);
        }
      })
      .catch((err) => {
        if (active) {
          setBidWarning(err.message || "Could not load your bid records.");
          setBidsReady(false);
        }
      });
    return () => {
      active = false;
    };
  }, [teamMode, bidHistoryRestricted, user, token, refreshNumber]);

  // A deep-linked tender may live on a different published-tender page.
  // Fetch its exact UUID rather than accidentally displaying page 1's first tender.
  useEffect(() => {
    setSelectedId(tenderId || null);
    setLastSubmitted(null);
    setDirectTender(null);
    setDirectError("");
    if (!tenderId || !token) return;
    let active = true;
    tenderApi
      .detail(tenderId, token)
      .then((item) => {
        if (!active) return;
        if (item.status !== "PUBLISHED")
          throw new Error("This tender is not currently published.");
        setDirectTender(item);
      })
      .catch((err) => {
        if (active)
          setDirectError(err.message || "Could not find the requested tender.");
      });
    return () => {
      active = false;
    };
  }, [tenderId, token]);

  // The current team DTO has no sector. In that case showing all published
  // tenders is more useful than presenting an empty recommendation list.
  const hasSectorData = tenders.some((t) => t.sector);
  const recommended = useMemo(() => {
    if (!user.sector) return [];
    return tenders.filter(
      (t) => t.sector?.toLowerCase() === user.sector.toLowerCase(),
    );
  }, [tenders, user.sector]);

  const useRecommendations = Boolean(user.sector && hasSectorData && !showAll);
  const visible = useRecommendations ? recommended : tenders;
  const selected =
    visible.find((t) => String(t.id) === String(selectedId)) ||
    (String(selectedId) === String(tenderId) ? directTender : null) ||
    (!tenderId || String(selectedId) !== String(tenderId)
      ? visible[0]
      : null) ||
    null;
  const existingBid =
    ownBids.find((b) => String(b.tenderId) === String(selected?.id)) || null;

  return (
    <>
      <PageTitle
        title={title}
        subtitle="Browse published tenders, read the terms and check the deadline before preparing a bid."
        action={
          <button
            type="button"
            onClick={() => {
              setLastSubmitted(null);
              setRefreshNumber((number) => number + 1);
            }}
            className="tb-btn-outline"
          >
            <RefreshCw size={16} /> Refresh
          </button>
        }
      />

      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-5 py-4 dark:border-slate-700 dark:bg-slate-900">
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
          <strong className="text-ink dark:text-slate-100">
            {visible.length}
          </strong>{" "}
          published tender{visible.length === 1 ? "" : "s"} shown on this page.
          {!hasSectorData &&
            tenders.length > 0 &&
            " Sector-based matching is unavailable because the current backend does not return sector data."}
        </p>
        {user.sector && hasSectorData && (
          <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-[#285970] dark:text-slate-200">
            <input
              type="checkbox"
              checked={showAll}
              onChange={(event) => setShowAll(event.target.checked)}
              className="accent-[#285970]"
            />
            Show all published tenders
          </label>
        )}
      </div>

      {directError && (
        <p
          role="alert"
          className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800"
        >
          {directError}
        </p>
      )}
      {bidWarning && (
        <p
          role="alert"
          className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800"
        >
          {bidWarning}
        </p>
      )}
      {loading && (
        <div className="tb-card p-8 text-sm text-slate-500 dark:text-slate-400">
          Loading tender records…
        </div>
      )}
      {error && (
        <div
          role="alert"
          className="mb-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          {error}{" "}
          <button
            type="button"
            className="underline"
            onClick={() => setRefreshNumber((number) => number + 1)}
          >
            Try again
          </button>
        </div>
      )}
      {!loading && !error && (
        <div className="space-y-5">
          <TenderTable
            tenders={visible}
            selectedId={selected?.id}
            onSelect={selectTender}
            search={search}
            setSearch={setSearch}
          />
          <PaginationControls
            page={page}
            totalPages={pageInfo.totalPages}
            totalElements={pageInfo.totalElements}
            onPageChange={setPage}
            loading={loading}
          />
          <div
            ref={tenderDetailsRef}
            id="tender-details"
            className="scroll-mt-6"
          >
            {lastSubmitted &&
              selected &&
              String(lastSubmitted.tenderId) === String(selected.id) && (
                <section role="status" className="tb-card mb-4 p-5">
                  <h3 className="font-semibold text-emerald-700 dark:text-emerald-300">
                    Bid submitted
                  </h3>
                  <p className="mt-2 text-sm">
                    Reference: {lastSubmitted.id}. Your submission has been
                    saved.
                  </p>
                </section>
              )}
            <TenderDetailsPanel
              tender={selected}
              existingBid={existingBid}
              bidsReady={!teamMode || bidsReady}
              onSubmitted={handleSubmitted}
            />
          </div>
        </div>
      )}
    </>
  );
}

export function MyBidsPage() {
  const { user, token } = useAuth();
  const [bids, setBids] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [page, setPage] = useState(0);
  const [pageInfo, setPageInfo] = useState({ totalPages: 1, totalElements: 0 });
  const teamMode = !DEMO_MODE && BACKEND_CONTRACT === "team";
  const bidHistoryRestricted = teamMode && user?.verified !== true;

  useEffect(() => {
    let active = true;
    if (bidHistoryRestricted) {
      setBids([]);
      setPageInfo({ totalPages: 1, totalElements: 0 });
      setError("");
      setLoading(false);
      return () => {
        active = false;
      };
    }
    setLoading(true);
    bidApi
      .minePage(user, token, page, 10)
      .then((response) => {
        if (active) {
          setBids(response.items);
          setPageInfo({
            totalPages: response.totalPages,
            totalElements: response.totalElements,
          });
          setError("");
        }
      })
      .catch((err) => {
        if (active) setError(err.message || "Could not load your bids.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [user, token, refresh, page, bidHistoryRestricted]);

  async function download(bid) {
    try {
      setError("");
      await downloadBidPdf(bid.id, "proposal", token);
    } catch (err) {
      setError(err.message || "Could not download your proposal.");
    }
  }

  return (
    <>
      <PageTitle
        title="My bids"
        subtitle="Track your quotations. Draft and submitted bids can be updated while their tender remains published and before its deadline."
        action={
          <button
            type="button"
            className="tb-btn-outline"
            onClick={() => setRefresh((n) => n + 1)}
          >
            Refresh
          </button>
        }
      />
      {bidHistoryRestricted && (
        <div
          role="status"
          className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-slate-900 dark:text-amber-200"
        >
          <strong>Bid history available after Admin verification.</strong> Your
          account is not yet VERIFIED. You can browse published tenders, but the
          current Spring Boot backend restricts viewing and submitting bids
          until approval. After approval, sign out and sign in again.
        </div>
      )}
      {!bidHistoryRestricted && error && (
        <p
          role="alert"
          className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700"
        >
          {error}
        </p>
      )}
      {!bidHistoryRestricted && (
        <div className="tb-card overflow-x-auto">
          <table className="tb-table">
            <thead>
              <tr>
                <th>Bid reference</th>
                <th>Tender</th>
                <th>Amount</th>
                <th>Submitted</th>
                <th>Proposal</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {bids.map((bid) => {
                const tenderVoided = bid.tenderStatus === "VOIDED";
                const canEdit =
                  !tenderVoided &&
                  (teamMode
                    ? ["DRAFT", "SUBMITTED"].includes(bid.status)
                    : bid.status === "SUBMITTED" &&
                      (!bid.tenderDeadline ||
                        Date.parse(bid.tenderDeadline) > Date.now()));
                return (
                  <tr key={bid.id}>
                    <td className="font-semibold text-ink dark:text-slate-100">
                      {bid.id}
                    </td>
                    <td>{bid.tenderTitle || bid.tenderId}</td>
                    <td>{formatCurrency(bid.amount ?? bid.quotedAmount)}</td>
                    <td>{formatDate(bid.submittedAt)}</td>
                    <td>
                      {teamMode ? (
                        bid.proposalUploaded ? (
                          <button
                            type="button"
                            className="tb-link"
                            onClick={() => download(bid)}
                          >
                            Download PDF
                          </button>
                        ) : (
                          <span className="text-xs text-slate-500">
                            Not uploaded
                          </span>
                        )
                      ) : (
                        "Demo record"
                      )}
                    </td>
                    <td>
                      <StatusBadge
                        status={tenderVoided ? "VOIDED" : bid.status}
                      />
                    </td>
                    <td>
                      {canEdit ? (
                        <Link
                          className="tb-link"
                          to={`/bidder/bids/${bid.id}/edit`}
                        >
                          {teamMode && bid.status === "SUBMITTED"
                            ? "Edit submitted bid"
                            : "Continue draft"}
                        </Link>
                      ) : (
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          Locked
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {loading && (
            <p className="p-6 text-sm text-slate-500">Loading bids…</p>
          )}
          {!loading && !bids.length && !error && (
            <p className="p-8 text-center text-sm text-slate-500 dark:text-slate-400">
              You have no saved bids.{" "}
              <Link className="tb-link" to="/bidder/tenders">
                Browse published tenders{" "}
              </Link>
            </p>
          )}
        </div>
      )}
      {!bidHistoryRestricted && (
        <PaginationControls
          page={page}
          totalPages={pageInfo.totalPages}
          totalElements={pageInfo.totalElements}
          onPageChange={setPage}
          loading={loading}
        />
      )}
    </>
  );
}
