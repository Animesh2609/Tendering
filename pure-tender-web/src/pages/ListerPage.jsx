import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, Clock3, FileText, Trophy, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { tenderApi } from "../api/services";
import { BACKEND_CONTRACT, DEMO_MODE } from "../data/constants";
import { canCancelTenderBeforeDeadline } from "../utils/tenderPermissions";
import PaginationControls from "../components/PaginationControls";
import PageTitle from "../components/PageTitle";
import StatusBadge from "../components/StatusBadge";
import { formatDate } from "../utils/format";

// Both Lister screens need the same list, so the loading logic lives in one hook.
function useMyTenders({ paged = false, page = 0 } = {}) {
  const { user, token } = useAuth();
  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pageInfo, setPageInfo] = useState({ totalPages: 1, totalElements: 0 });
  const [refreshNumber, setRefreshNumber] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);

    (paged
      ? tenderApi.minePage(user, token, page, 10)
      : tenderApi.mine(user, token)
    )
      .then((result) => {
        if (!active) return;
        setTenders(paged ? result.items : result);
        if (paged)
          setPageInfo({
            totalPages: result.totalPages,
            totalElements: result.totalElements,
          });
        setError("");
      })
      .catch((err) => {
        if (active) setError(err.message || "Could not load your tenders.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [user, token, refreshNumber, page, paged]);

  return {
    tenders,
    loading,
    error,
    pageInfo,
    refresh: () => setRefreshNumber((number) => number + 1),
  };
}

export default function ListerPage() {
  const { user } = useAuth();
  const { tenders, error, loading } = useMyTenders();
  const teamMode = !DEMO_MODE && BACKEND_CONTRACT === "team";

  const summary = [
    { label: "Total requests", value: tenders.length, icon: FileText },
    {
      label: teamMode ? "Submitted" : "Drafts",
      value: tenders.filter(
        (t) => t.status === (teamMode ? "SUBMITTED" : "DRAFT"),
      ).length,
      icon: ClipboardList,
    },
    {
      label: "Published",
      value: tenders.filter((t) => t.status === "PUBLISHED").length,
      icon: Clock3,
    },
  ];

  return (
    <>
      <PageTitle
        title="Tender overview"
        subtitle={`Hello, ${user.fullName}. Here's where your organization's tender requests stand.`}
      />

      <section
        aria-label="Tender counts"
        className="mb-6 grid gap-4 sm:grid-cols-3"
      >
        {summary.map(({ label, value, icon: Icon }) => (
          <div
            key={label}
            className="tb-card flex items-center justify-between p-5"
          >
            <div>
              <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                {label}
              </p>
              <p className="mt-2 text-3xl font-semibold text-ink dark:text-slate-100">
                {value}
              </p>
            </div>
            <Icon size={21} className="text-[#5a7886] dark:text-slate-300" />
          </div>
        ))}
      </section>

      <div className="space-y-5">
        <section className="tb-card p-5">
          <h2 className="font-semibold text-ink dark:text-slate-100">
            Tender management
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            Track your tender requests below. Use <strong>Create tender</strong>{" "}
            in the left sidebar when you need to submit a new request for Admin
            review. Use <strong>My tenders</strong> to edit or cancel eligible
            tenders.
          </p>
        </section>
        <section className="tb-card self-start overflow-hidden">
          <div className="border-b border-slate-100 p-5 dark:border-slate-700">
            <h2 className="font-semibold text-ink dark:text-slate-100">
              Recent requests
            </h2>
            <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
              The latest tenders created by your account.
            </p>
          </div>

          {loading && (
            <p className="p-5 text-sm text-slate-500 dark:text-slate-400">
              Loading your tenders…
            </p>
          )}
          {!loading && error && (
            <p role="alert" className="p-5 text-sm text-red-700">
              {error}
            </p>
          )}
          {!loading && !error && tenders.length === 0 && (
            <p className="p-5 text-sm text-slate-600 dark:text-slate-300">
              No tender requests yet. Use Create tender in the sidebar to submit
              the first one.
            </p>
          )}
          {!loading &&
            !error &&
            tenders.slice(0, 6).map((tender) => (
              <div
                key={tender.id}
                className="border-b border-slate-100 p-4 dark:border-slate-700"
              >
                <p className="text-sm font-semibold text-ink dark:text-slate-100">
                  {tender.title}
                </p>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Due {formatDate(tender.submissionDeadline)}
                  </span>
                  <StatusBadge status={tender.status} />
                </div>
              </div>
            ))}
          <Link
            to="/lister/my-tenders"
            className="block px-5 py-4 text-sm font-semibold text-[#285970] hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            View all tender requests →
          </Link>
        </section>
      </div>
    </>
  );
}

export function MyTendersPage() {
  const { user, token } = useAuth();
  const [page, setPage] = useState(0);
  const { tenders, error, loading, refresh, pageInfo } = useMyTenders({
    paged: true,
    page,
  });
  const teamMode = !DEMO_MODE && BACKEND_CONTRACT === "team";
  const [workingId, setWorkingId] = useState("");
  const [message, setMessage] = useState("");
  const [cancelId, setCancelId] = useState(null);
  const [reason, setReason] = useState("");
  const [awardDetails, setAwardDetails] = useState(null);
  const [awardLoadingId, setAwardLoadingId] = useState("");
  const [rejectionDetails, setRejectionDetails] = useState(null);

  async function viewAward(tender) {
    setAwardLoadingId(tender.id);
    setAwardDetails(null);
    setRejectionDetails(null);
    setMessage("");
    try {
      const details = await tenderApi.award(user, tender.id, token);
      if (!details?.winningContractorName) {
        throw new Error("The award response did not include the winning contractor.");
      }
      setAwardDetails(details);
    } catch (err) {
      setMessage(err.status === 404 && ["Not Found", "Request failed (404)."].includes(err.message)
        ? "The running backend returned 404 for the award lookup. Rebuild and restart Spring Boot in IntelliJ; if it still fails, check that the tender has a selected winning bid."
        : err.message || "Could not load award details.");
    } finally {
      setAwardLoadingId("");
    }
  }

  async function requestApproval(id) {
    setWorkingId(id);
    setMessage("");

    try {
      await tenderApi.requestApproval(user, id, token);
      setMessage("Tender sent for Admin review. It is not published yet.");
      refresh();
    } catch (err) {
      setMessage(err.message || "Could not request approval.");
    } finally {
      setWorkingId("");
    }
  }

  async function cancelTender(event) {
    event.preventDefault();
    const selected = tenders.find(
      (tender) => String(tender.id) === String(cancelId),
    );
    if (
      !selected ||
      !canCancelTenderBeforeDeadline(selected, {
        verified: user?.verified === true,
        teamMode,
      })
    ) {
      setMessage(
        "Cancellation is available to verified Listers for their published tenders before the submission deadline.",
      );
      setCancelId(null);
      return;
    }
    if (!reason.trim()) return;
    setWorkingId(cancelId);
    setMessage("");
    try {
      await tenderApi.cancel(user, cancelId, reason, token);
      setMessage("Tender cancelled. It is no longer available for new bids.");
      setCancelId(null);
      setReason("");
      refresh();
    } catch (err) {
      setMessage(err.message || "Could not cancel this tender.");
    } finally {
      setWorkingId("");
    }
  }

  return (
    <>
      <PageTitle
        title="My tenders"
        subtitle="Edit eligible requests and follow their status."
      />
      {awardDetails && (
        <section className="tb-card mb-4 max-w-3xl p-5" aria-live="polite">
          <section
            aria-labelledby="award-details-title"
            className="w-full"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="flex items-center gap-2 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                  <Trophy size={17} /> Tender awarded
                </p>
                <h2 id="award-details-title" className="mt-2 text-lg font-semibold text-ink dark:text-slate-100">
                  {awardDetails.tenderTitle}
                </h2>
              </div>
              <button className="tb-btn-outline !p-2" onClick={() => setAwardDetails(null)} aria-label="Close award details">
                <X size={17} />
              </button>
            </div>
            <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
              <div><dt className="text-slate-500 dark:text-slate-400">Awarded to</dt><dd className="mt-1 font-semibold text-ink dark:text-slate-100">{awardDetails.winningContractorName}</dd></div>
              <div><dt className="text-slate-500 dark:text-slate-400">Winning bid amount</dt><dd className="mt-1 font-semibold text-ink dark:text-slate-100">{awardDetails.winningBidAmount == null ? "—" : new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(awardDetails.winningBidAmount))}</dd></div>
              <div><dt className="text-slate-500 dark:text-slate-400">Award date</dt><dd className="mt-1 font-medium text-ink dark:text-slate-100">{formatDate(awardDetails.awardedAt)}</dd></div>
              <div><dt className="text-slate-500 dark:text-slate-400">Winning bid reference</dt><dd className="mt-1 break-all font-mono text-xs text-ink dark:text-slate-100">{awardDetails.winningBidId}</dd></div>
            </dl>
          </section>
        </section>
      )}
      {rejectionDetails && (
        <section className="tb-card mb-4 max-w-3xl border-l-4 border-rose-500 p-5" aria-live="polite">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">Tender rejection reason</p>
              <h2 className="mt-2 font-semibold text-ink dark:text-slate-100">{rejectionDetails.title}</h2>
            </div>
            <button className="tb-btn-outline !p-2" onClick={() => setRejectionDetails(null)} aria-label="Close rejection reason"><X size={17} /></button>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700 dark:text-slate-300">
            {rejectionDetails.rejectionReason || "The backend response did not include a rejection reason. Rebuild and restart Spring Boot in IntelliJ, then refresh this page."}
          </p>
        </section>
      )}
      {message && (
        <p
          role="status"
          className="mb-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
        >
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="mb-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {cancelId && (
        <form onSubmit={cancelTender} className="tb-card mb-4 p-4">
          <h3 className="font-semibold text-ink dark:text-slate-100">
            Cancel tender
          </h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Cancel your published tender before its submission deadline. The
            cancellation reason is required and cannot be changed here
            afterwards.
          </p>
          <label htmlFor="tender-cancel-reason" className="tb-label mt-3 block">
            Reason for cancellation
          </label>
          <textarea
            id="tender-cancel-reason"
            required
            maxLength={2000}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className="tb-input mt-2 min-h-20"
            placeholder="Explain why the tender is being cancelled"
          />
          <div className="mt-3 flex gap-2">
            <button
              type="submit"
              disabled={Boolean(workingId) || !reason.trim()}
              className="tb-btn-primary"
            >
              Confirm cancellation
            </button>
            <button
              type="button"
              className="tb-btn-outline"
              onClick={() => setCancelId(null)}
            >
              Keep tender
            </button>
          </div>
        </form>
      )}
      <div className="tb-card overflow-x-auto">
        <table className="tb-table">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Tender</th>
              <th>Deadline</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {tenders.map((tender) => {
              const cancellable = canCancelTenderBeforeDeadline(tender, {
                verified: user?.verified === true,
                teamMode,
              });
              return (
                <tr key={tender.id}>
                  <td className="text-xs font-medium">{tender.id}</td>
                  <td className="min-w-[210px] font-semibold text-ink dark:text-slate-100">
                    {tender.title}
                  </td>
                  <td>{formatDate(tender.submissionDeadline)}</td>
                  <td>
                    <StatusBadge status={tender.status} />
                  </td>
                  <td>
                    {tender.status === "AWARDED" ? (
                      <button
                        type="button"
                        className="tb-btn-outline inline-flex items-center gap-2"
                        disabled={Boolean(workingId) || awardLoadingId === tender.id}
                        onClick={() => viewAward(tender)}
                      >
                        <Trophy size={15} /> {awardLoadingId === tender.id ? "Loading…" : "View award"}
                      </button>
                    ) : tender.status === "REJECTED" ? (
                      <button
                        type="button"
                        className="tb-btn-outline"
                        onClick={() => {
                          setAwardDetails(null);
                          setRejectionDetails(tender);
                          setMessage("");
                        }}
                      >
                        View rejection reason
                      </button>
                    ) : cancellable ? (
                      <button
                        type="button"
                        className="tb-btn-outline"
                        disabled={Boolean(workingId)}
                        onClick={() => {
                          setCancelId(tender.id);
                          setReason("");
                          setMessage("");
                        }}
                      >
                        Cancel tender
                      </button>
                    ) : (
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        No action available
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {loading && (
          <p className="p-5 text-sm text-slate-500 dark:text-slate-400">
            Loading tenders…
          </p>
        )}
        {!loading && !error && tenders.length === 0 && (
          <p className="p-6 text-sm text-slate-500 dark:text-slate-400">
            No tenders saved yet. Use Create tender from the sidebar.
          </p>
        )}
      </div>
      <PaginationControls
        page={page}
        totalPages={pageInfo.totalPages}
        totalElements={pageInfo.totalElements}
        onPageChange={setPage}
        loading={loading}
      />
    </>
  );
}
