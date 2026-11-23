import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  BriefcaseBusiness,
  Check,
  CircleAlert,
  FileText,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { DEMO } from "../api/authApi";
import { evaluatorApi } from "../api/evaluatorApi";
import AppHeader from "../components/AppHeader";
import WorkspaceSidebar from "../components/WorkspaceSidebar";
import MetricCard from "../components/MetricCard";
import TenderAssignment from "../components/TenderAssignment";
import BidEvaluationCard from "../components/BidEvaluationCard";
import EmptyState from "../components/EmptyState";
import Alert from "../components/Alert";

const date = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-IN", {
        weekday: "long",
        day: "numeric",
        month: "long",
      })
    : "";
const prettyDate = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "—";
const titleCase = (value) =>
  String(value || "")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
const prettyDateTime = (value) =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZone: "Asia/Kolkata",
        timeZoneName: "short",
      }).format(new Date(value))
    : "—";
const HISTORY_STATUSES = new Set([
  "CANCELLED",
  "AWARDED",
  "VOIDED",
  "REJECTED",
  "COMPLETED",
  "FINALIZED",
]);

export default function WorkspacePage() {
  const { session, user, logout } = useAuth();
  const [tenders, setTenders] = useState([]);
  const [selected, setSelected] = useState(null);
  const [bids, setBids] = useState([]);
  const [scores, setScores] = useState({});
  const [opened, setOpened] = useState({});
  const [saved, setSaved] = useState({});
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState(() =>
    DEMO && new URLSearchParams(window.location.search).get("tab") === "history"
      ? "history"
      : "assigned",
  );
  const wrongRole = user?.role !== "EVALUATOR";
  const requestVersion = useRef(0);
  const [award, setAward] = useState(null);
  useEffect(
    () => () => {
      requestVersion.current += 1;
    },
    [],
  );

  const loadTenders = useCallback(async () => {
    if (!session || wrongRole) return;
    setLoading(true);
    setError("");
    try {
      setTenders(await evaluatorApi.tenders(session.token));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [session, wrongRole]);
  useEffect(() => {
    loadTenders();
  }, [loadTenders]);
  const assignedTenders = useMemo(
    () => tenders.filter((t) => !HISTORY_STATUSES.has(t.status)),
    [tenders],
  );
  const historyTenders = useMemo(
    () => tenders.filter((t) => HISTORY_STATUSES.has(t.status)),
    [tenders],
  );
  const tabTenders = activeTab === "history" ? historyTenders : assignedTenders;
  const filtered = useMemo(
    () =>
      tabTenders.filter((t) =>
        `${t.title} ${t.status}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [tabTenders, query],
  );
  async function loadBids(tenderId) {
    const version = ++requestVersion.current;
    setLoading(true);
    setError("");
    try {
      const list = await evaluatorApi.bids(tenderId, session.token);
      const results = await Promise.all(
        list.map(async (bid) => {
          try {
            return [
              bid.bidId,
              await evaluatorApi.getEvaluation(bid.bidId, session.token),
            ];
          } catch (err) {
            if (err.status === 404) return [bid.bidId, null];
            throw err;
          }
        }),
      );
      if (version !== requestVersion.current) return;
      setBids(list);
      const loaded = Object.fromEntries(
        results.filter(([, evaluation]) => evaluation),
      );
      setScores(loaded);
      setSaved(
        Object.fromEntries(
          Object.entries(loaded).map(([id, ev]) => [id, ev.status === "DRAFT"]),
        ),
      );
    } catch (err) {
      if (version === requestVersion.current) setError(err.message);
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }
  async function selectTender(tender) {
    requestVersion.current += 1;
    setSelected(tender);
    setAward(null);
    setScores({});
    setSaved({});
    setBids([]);
    setError("");
    setNotice("");
    if (
      ["BIDS_OPENED", "EVALUATING", "UNDER_EVALUATION", "AWARDED"].includes(
        tender.status,
      ) ||
      opened[tender.tenderId]
    )
      await loadBids(tender.tenderId);
  }
  const previewOpened = useRef(false);
  useEffect(() => {
    if (!DEMO || previewOpened.current) return;
    const id = new URLSearchParams(window.location.search).get("tender");
    const tender = tenders.find((t) => t.tenderId === id);
    if (tender) {
      previewOpened.current = true;
      void selectTender(tender);
    }
    // Selection is requested once after the assignment list arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenders]);
  async function openBids() {
    setBusy("open");
    setError("");
    setNotice("");
    try {
      await evaluatorApi.openBids(selected.tenderId, session.token);
      setOpened((old) => ({ ...old, [selected.tenderId]: true }));
      setNotice("Submitted bids are open for evaluation.");
      await loadBids(selected.tenderId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  function saveEvaluation(bid, scoresToSave) {
    if (
      String(scoresToSave.technicalScore).trim() === "" ||
      String(scoresToSave.financialScore).trim() === ""
    ) {
      setError("Enter both scores before saving.");
      return;
    }
    const technical = Number(scoresToSave.technicalScore);
    const financial = Number(scoresToSave.financialScore);
    if (
      !Number.isFinite(technical) ||
      technical < 0 ||
      technical > 100 ||
      !Number.isFinite(financial) ||
      financial < 0 ||
      financial > 100 ||
      !/^\d+(\.\d{1,2})?$/.test(String(scoresToSave.technicalScore)) ||
      !/^\d+(\.\d{1,2})?$/.test(String(scoresToSave.financialScore))
    ) {
      setError("Enter scores from 0 to 100 with at most two decimal places.");
      return;
    }
    setBusy("save");
    setError("");
    setNotice("");
    evaluatorApi
      .saveEvaluation(
        bid.bidId,
        {
          technicalScore: technical,
          financialScore: financial,
          remarks: scoresToSave.remarks || "",
        },
        session.token,
      )
      .then((result) => {
        setScores((old) => ({ ...old, [bid.bidId]: result }));
        setSaved((old) => ({ ...old, [bid.bidId]: true }));
        setNotice(`Evaluation saved for ${bid.contractorName}.`);
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(""));
  }
  async function finalizeEvaluation(bid) {
    setBusy("finalize");
    setError("");
    try {
      const result = await evaluatorApi.finalizeEvaluation(
        bid.bidId,
        session.token,
      );
      setScores((old) => ({ ...old, [bid.bidId]: result }));
      setSaved((old) => ({ ...old, [bid.bidId]: false }));
      setNotice(`Evaluation submitted for ${bid.contractorName}.`);
      if (!DEMO) {
        try {
          setAward(await evaluatorApi.award(selected.tenderId, session.token));
        } catch (err) {
          if (![404, 409].includes(err.status)) setError(err.message);
        }
      }
      await loadTenders();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  async function downloadProposal(bid) {
    if (DEMO) {
      setNotice("Proposal downloads are unavailable in local demo mode.");
      return;
    }
    setBusy("download");
    setError("");
    try {
      const blob = await evaluatorApi.downloadProposal(
        bid.bidId,
        session.token,
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `tender-${selected.tenderId}-bid-${bid.bidId}-proposal.pdf`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  if (wrongRole)
    return (
      <main className="role-denied">
        <h1>Evaluator access required</h1>
        <p>
          This account has the role <b>{titleCase(user?.role)}</b>. Sign out,
          then use an Evaluator account.
        </p>
        <button className="tb-btn-primary" onClick={logout}>
          Sign out
        </button>
      </main>
    );
  const pending = assignedTenders.filter(
    (t) => !["COMPLETED", "AWARDED", "FINALIZED"].includes(t.status),
  ).length;
  const canOpen =
    selected?.status === "PUBLISHED" && !opened[selected.tenderId];
  const closedHistory =
    selected && ["CANCELLED", "VOIDED", "REJECTED"].includes(selected.status);

  return (
    <div className="workspace-shell">
      <AppHeader user={user} />
      <div className="workspace-layout">
        <WorkspaceSidebar
          count={assignedTenders.length}
          active={selected ? "detail" : "overview"}
          onHome={() => {
            requestVersion.current += 1;
            setSelected(null);
            setError("");
            setNotice("");
          }}
          onLogout={logout}
        />
        <main className="workspace-main">
          <div className="workspace-content">
            {error && <Alert onClose={() => setError("")}>{error}</Alert>}
            {notice && (
              <Alert type="success" onClose={() => setNotice("")}>
                {notice}
              </Alert>
            )}
            {!selected ? (
              <>
                <div className="page-heading">
                  <div>
                    <p className="eyebrow">
                      EVALUATOR WORKSPACE <span>·</span> {date(Date.now())}
                    </p>
                    <h1>
                      {activeTab === "history"
                        ? "Tender history"
                        : "Assigned to you"}
                      <span>.</span>
                    </h1>
                    <p className="description">
                      {activeTab === "history"
                        ? "Review past assignments, including cancelled tenders."
                        : "Review active assignments, examine submitted bids, and record your assessment."}
                    </p>
                  </div>
                  <button
                    className="secondary refresh-button"
                    onClick={loadTenders}
                  >
                    ↻ &nbsp;Refresh
                  </button>
                </div>
                <div className="metrics-grid">
                  <MetricCard
                    icon={BriefcaseBusiness}
                    name="Assigned tenders"
                    value={assignedTenders.length}
                    detail="In your evaluation queue"
                  />
                  <MetricCard
                    icon={FileText}
                    name="Awaiting evaluation"
                    value={pending}
                    detail="Tenders with work remaining"
                  />
                </div>
                <section className="content-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>
                        {activeTab === "history"
                          ? "Tender history"
                          : "Your tender assignments"}
                      </h2>
                      <p>
                        {activeTab === "history"
                          ? "Past assignments, including cancelled tenders."
                          : "Open a tender to view its submitted bids and score each proposal."}
                      </p>
                    </div>
                    <label className="search-field">
                      <Search size={16} />
                      <input
                        aria-label="Search assignments"
                        placeholder="Search tenders"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                    </label>
                  </div>
                  <div
                    className="evaluator-tabs"
                    role="tablist"
                    aria-label="Tender assignments"
                  >
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeTab === "assigned"}
                      className={activeTab === "assigned" ? "active" : ""}
                      onClick={() => setActiveTab("assigned")}
                    >
                      Assigned <span>{assignedTenders.length}</span>
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeTab === "history"}
                      className={activeTab === "history" ? "active" : ""}
                      onClick={() => setActiveTab("history")}
                    >
                      History <span>{historyTenders.length}</span>
                    </button>
                  </div>
                  <div className="assignment-list">
                    {filtered.map((tender) => (
                      <TenderAssignment
                        key={tender.tenderId}
                        tender={tender}
                        onOpen={selectTender}
                      />
                    ))}
                    {!filtered.length && (
                      <EmptyState>
                        {loading
                          ? "Loading your assignments…"
                          : activeTab === "history"
                            ? "No tender history yet."
                            : "No assigned tenders match your search."}
                      </EmptyState>
                    )}
                  </div>
                </section>
                <div className="accountability-note">
                  <ShieldCheck size={18} />
                  <span>
                    <b>Independent assessment</b>
                    <small>
                      Your individual scores and remarks are saved against each
                      submitted bid.
                    </small>
                  </span>
                </div>
              </>
            ) : (
              <>
                <button
                  className="back-link"
                  onClick={() => {
                    requestVersion.current += 1;
                    setSelected(null);
                    setError("");
                    setNotice("");
                  }}
                >
                  <ArrowLeft size={15} /> All assigned tenders
                </button>
                <div className="detail-heading">
                  <div>
                    <p className="eyebrow">
                      {HISTORY_STATUSES.has(selected.status)
                        ? "TENDER HISTORY"
                        : "ASSIGNED TENDER"}{" "}
                      <span>·</span> {titleCase(selected.status)}
                    </p>
                    <h1>{selected.title}</h1>
                    <p className="description">
                      Bid opening {prettyDateTime(selected.openingDate)}{" "}
                      <span>·</span> Submission deadline{" "}
                      {prettyDateTime(selected.submissionDeadline)}{" "}
                      <span>·</span> {selected.submittedBidCount ?? bids.length}{" "}
                      bids submitted
                    </p>
                  </div>
                  <button
                    className="secondary refresh-button"
                    onClick={() => loadBids(selected.tenderId)}
                  >
                    ↻ &nbsp;Refresh
                  </button>
                </div>
                {canOpen ? (
                  <section className="sealed-card">
                    <div className="sealed-icon">⌑</div>
                    <div>
                      <h2>Submitted bids are sealed</h2>
                      <p>
                        Open the bid submissions to begin your evaluation. The
                        backend enforces the tender opening rules.
                      </p>
                    </div>
                    <button
                      className="tb-btn-primary"
                      disabled={busy === "open"}
                      onClick={openBids}
                    >
                      {busy === "open"
                        ? "Opening…"
                        : "Open submitted bids"}{" "}
                    </button>
                  </section>
                ) : closedHistory ? (
                  <section className="sealed-card">
                    <div className="sealed-icon">
                      <FileText size={20} />
                    </div>
                    <div>
                      <h2>This tender is in history</h2>
                      <p>
                        Its status is {titleCase(selected.status)}. Bid
                        evaluation is no longer available.
                      </p>
                    </div>
                  </section>
                ) : (
                  <>
                    {award && (
                      <section className="accountability-note">
                        <ShieldCheck size={18} />
                        <span>
                          <b>Award recorded: {award.winningContractorName}</b>
                          <small>
                            Winning bid {award.winningBidId} · Total score{" "}
                            {award.totalScore}
                          </small>
                        </span>
                      </section>
                    )}
                    <div className="bid-section-heading">
                      <div>
                        <h2>Submitted proposals</h2>
                        <p>
                          Score each bid using the technical and financial
                          criteria.
                        </p>
                      </div>
                      <span className="bid-count">
                        {bids.length} {bids.length === 1 ? "bid" : "bids"}
                      </span>
                    </div>
                    <div className="bid-list">
                      {bids.map((bid, index) => (
                        <BidEvaluationCard
                          key={bid.bidId}
                          bid={bid}
                          index={index}
                          initialEvaluation={scores[bid.bidId]}
                          isSaved={saved[bid.bidId]}
                          busy={busy}
                          onSave={saveEvaluation}
                          onFinalize={finalizeEvaluation}
                          onDownload={downloadProposal}
                        />
                      ))}
                      {!bids.length && (
                        <EmptyState>
                          {loading
                            ? "Loading submitted bids…"
                            : "No submitted bids are available for this tender."}
                        </EmptyState>
                      )}
                    </div>
                  </>
                )}
              </>
            )}
            <footer className="page-footer">
              <span>© 2026 TenderBlock</span>
              <span>Protected procurement workspace</span>
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
}
