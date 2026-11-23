import { DEMO_MODE } from "../../../data/constants";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BadgeCheck,
  Banknote,
  Building2,
  Check,
  CircleAlert,
  ClipboardCheck,
  FileCheck2,
  FileText,
  Search,
  Shield,
  ShieldCheck,
  X,
  Users,
  Download,
} from "lucide-react";
import { adminApi } from "../api/adminApi";
import { auditorApi } from "../api/auditorApi";
import { useAuth } from "../context/AuthContext";
import Brand from "../components/Brand";
import WorkspaceHeader from "../components/WorkspaceHeader";
import WorkspaceSidebar from "../components/WorkspaceSidebar";
import Metric from "../components/MetricCard";
import Empty from "../components/EmptyState";
import ActionModals from "../components/ActionModals";
import AuditorTenderBrowser from "../components/AuditorTenderBrowser";

const money = (value) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
const date = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "—";
const label = (value) =>
  String(value || "")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
const accountType = (role) =>
  role === "AUTHORITY"
    ? "Lister"
    : role === "CONTRACTOR"
      ? "Bidder"
      : label(role);

export default function OperationsWorkspacePage() {
  const { session, user, logout } = useAuth();
  const [tab, setTab] = useState(() => {
    const value = DEMO_MODE
      ? new URLSearchParams(window.location.search).get("tab")
      : "";
    return ["users", "tenders", "flagged", "completed"].includes(value)
      ? value
      : "overview";
  });
  const [users, setUsers] = useState([]);
  const [tenders, setTenders] = useState([]);
  const [reports, setReports] = useState([]);
  const [flaggedTenders, setFlaggedTenders] = useState([]);
  const [completedTenders, setCompletedTenders] = useState([]);
  const [evaluators, setEvaluators] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [modal, setModal] = useState(null);
  const [busyId, setBusyId] = useState("");
  const [documentPreview, setDocumentPreview] = useState(null);
  const previewOpened = useRef(false);
  useEffect(() => {
    if (!DEMO_MODE || previewOpened.current) return;
    const kind = new URLSearchParams(window.location.search).get("review");
    if (["approve", "rejectTender"].includes(kind) && tenders.length) {
      previewOpened.current = true;
      setModal({ type: kind, tender: tenders[0] });
    } else if (["resolve", "award"].includes(kind) && reports.length) {
      const report = reports.find((r) =>
        kind === "resolve"
          ? r.status === "UNDER_REVIEW"
          : r.reportId === "RPT-UI-AWARD",
      );
      if (report) {
        previewOpened.current = true;
        setModal({ type: kind, report });
      }
    }
  }, [tenders, reports]);
  const role = session?.user?.role;
  const isAdmin = role === "ADMIN";
  const filteredUsers = useMemo(
    () =>
      users.filter((u) =>
        `${u.fullName} ${u.email} ${accountType(u.role)} ${u.status}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [users, query],
  );
  const filteredTenders = useMemo(
    () =>
      tenders.filter((t) =>
        `${t.title} ${t.authorityName}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [tenders, query],
  );

  const refresh = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setError("");
    try {
      if (isAdmin) {
        const [u, t] = await Promise.all([
          adminApi.users(session.token, true),
          adminApi.tenders(session.token),
        ]);
        setUsers(u);
        setTenders(t);
        {
          const all = await adminApi.users(session.token);
          setEvaluators(
            all.filter(
              (x) => x.role === "EVALUATOR" && x.status === "VERIFIED",
            ),
          );
        }
      } else {
        const [reportsResult, flaggedResult, completedResult] =
          await Promise.allSettled([
            auditorApi.reports(session.token),
            auditorApi.flaggedTenders(session.token),
            auditorApi.completedTenders(session.token),
          ]);
        const list =
          reportsResult.status === "fulfilled" ? reportsResult.value : [];
        setReports(list);
        const fallback = [
          ...new Map(
            list.map((r) => [
              r.tenderId,
              {
                tenderId: r.tenderId,
                tenderTitle: r.tenderTitle,
                status: "UNKNOWN",
                flaggedAt: r.createdAt,
                reportCount: list.filter((x) => x.tenderId === r.tenderId)
                  .length,
              },
            ]),
          ).values(),
        ];
        setFlaggedTenders(
          flaggedResult.status === "fulfilled" ? flaggedResult.value : fallback,
        );
        setCompletedTenders(
          completedResult.status === "fulfilled" ? completedResult.value : [],
        );
        const unique = [
          ...new Set(list.map((r) => r.tenderId).filter(Boolean)),
        ];
        const states = await Promise.all(
          unique.map(async (id) => {
            try {
              const tender = await auditorApi.tender(id, session.token);
              return [id, tender.status];
            } catch {
              return [id, "UNKNOWN"];
            }
          }),
        );
        if (flaggedResult.status === "rejected")
          setFlaggedTenders(
            fallback.map((t) => ({
              ...t,
              status: Object.fromEntries(states)[t.tenderId] || "UNKNOWN",
            })),
          );
        if (
          flaggedResult.status === "rejected" ||
          completedResult.status === "rejected"
        )
          setError(
            "Some tender lists are unavailable. Reports remain available for investigation, and related flagged tenders are shown below.",
          );
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [session, isAdmin]);
  useEffect(() => {
    refresh();
  }, [refresh]);

  async function act(id, operation) {
    setBusyId(id);
    setError("");
    try {
      await operation();
      await refresh();
      setModal(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId("");
    }
  }
  async function viewTenderDocument(tender) {
    try {
      const blob = await adminApi.tenderDocument(tender.id, session.token);
      setDocumentPreview({
        url: URL.createObjectURL(blob),
        title: tender.title,
      });
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(
    () => () => {
      if (documentPreview?.url) URL.revokeObjectURL(documentPreview.url);
    },
    [documentPreview],
  );
  if (!["ADMIN", "AUDITOR"].includes(role))
    return (
      <main className="denied">
        <Brand />
        <div>
          <CircleAlert size={25} />
          <h1>This portal is for Admin and Auditor accounts</h1>
          <p>
            Your signed-in backend role is <b>{role}</b>. Sign out and use the
            correct portal.
          </p>
          <button className="primary" onClick={logout}>
            Sign out
          </button>
        </div>
      </main>
    );
  return (
    <div className="app-shell">
      <WorkspaceHeader user={user} />
      <div className="body-layout">
        <WorkspaceSidebar
          role={role}
          tab={tab}
          setTab={setTab}
          onLogout={logout}
        />
        <main className="main-content">
          <div className="content-wrap">
            <div className="page-heading">
              <div>
                <p className="eyebrow">
                  {isAdmin ? "ADMINISTRATION" : "INDEPENDENT OVERSIGHT"}{" "}
                  <span className="heading-dot">·</span>{" "}
                  {new Date().toLocaleDateString("en-IN", {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                  })}
                </p>
                <h1>
                  {tab === "overview"
                    ? isAdmin
                      ? "Welcome back"
                      : "Audit overview"
                    : tab === "users"
                      ? "Account reviews"
                      : tab === "tenders"
                        ? "Tender approvals"
                        : tab === "flagged"
                          ? "Flagged tenders"
                          : "Completed tenders"}
                  {tab === "overview" && (
                    <span>, {session.user.fullName.split(" ")[0]}.</span>
                  )}
                </h1>
                <p className="description">
                  {isAdmin
                    ? "Review registrations and route submitted tenders to the right experts."
                    : tab === "completed"
                      ? "Review completed tender outcomes and their submitted bids."
                      : "Review flagged procurement records and document your findings."}
                </p>
              </div>
              <button
                className="secondary refresh"
                disabled={loading}
                onClick={refresh}
              >
                <span className={loading ? "spin" : ""}>↻</span> Refresh
              </button>
            </div>
            {error && (
              <div role="alert" className="alert error">
                <CircleAlert size={17} />
                {error}
                <button onClick={() => setError("")}>
                  <X size={15} />
                </button>
              </div>
            )}
            {tab === "overview" && (
              <>
                <div className="metrics-grid">
                  {isAdmin ? (
                    <>
                      <Metric
                        icon={Users}
                        name="Pending accounts"
                        value={users.length}
                        detail="Awaiting account review"
                      />
                      <Metric
                        icon={FileCheck2}
                        name="Tenders to review"
                        value={tenders.length}
                        detail="Submitted for approval"
                      />
                      <Metric
                        icon={BadgeCheck}
                        name="Active evaluators"
                        value={evaluators.length}
                        detail="Available for assignment"
                      />
                    </>
                  ) : (
                    <>
                      <Metric
                        icon={CircleAlert}
                        name="Open reports"
                        value={
                          reports.filter((x) => x.status === "OPEN").length
                        }
                        detail="Require initial review"
                      />
                      <Metric
                        icon={ClipboardCheck}
                        name="Under review"
                        value={
                          reports.filter((x) => x.status === "UNDER_REVIEW")
                            .length
                        }
                        detail="Assigned investigations"
                      />
                      <Metric
                        icon={BadgeCheck}
                        name="Resolved"
                        value={
                          reports.filter(
                            (x) =>
                              x.status === "RESOLVED" ||
                              x.status === "DISMISSED",
                          ).length
                        }
                        detail="Closed with findings"
                      />
                    </>
                  )}
                </div>
                <section className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>
                        {isAdmin
                          ? "Needs your attention"
                          : "Reports needing attention"}
                      </h2>
                      <p>
                        {isAdmin
                          ? "The next steps in the operations queue."
                          : "Your open and active investigations."}
                      </p>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => setTab(isAdmin ? "tenders" : "flagged")}
                    >
                      View all
                    </button>
                  </div>
                  {isAdmin ? (
                    <div className="quick-list">
                      {tenders.slice(0, 3).map((t) => (
                        <div className="quick-row" key={t.id}>
                          <span className="quick-icon">
                            <FileText size={17} />
                          </span>
                          <span className="quick-copy">
                            <b>{t.title}</b>
                            <small>
                              {t.authorityName || "Tender issuer"} · submitted{" "}
                              {date(t.createdAt)}
                            </small>
                          </span>
                          <span className="status pending">Needs review</span>
                          <button
                            className="row-arrow"
                            onClick={() => setTab("tenders")}
                          ></button>
                        </div>
                      ))}
                      {!tenders.length && (
                        <Empty
                          text={
                            loading
                              ? "Loading your queue…"
                              : "No submitted tenders are waiting for approval."
                          }
                        />
                      )}
                    </div>
                  ) : (
                    <div className="quick-list">
                      {reports
                        .filter((r) =>
                          ["OPEN", "UNDER_REVIEW"].includes(r.status),
                        )
                        .slice(0, 3)
                        .map((r) => (
                          <div className="quick-row" key={r.reportId}>
                            <span className="quick-icon alert-icon">
                              <Shield size={17} />
                            </span>
                            <span className="quick-copy">
                              <b>
                                {r.tenderTitle || "Tender integrity report"}
                              </b>
                              <small>
                                {label(r.type)} · opened {date(r.createdAt)}
                              </small>
                            </span>
                            <span
                              className={`status ${r.status === "OPEN" ? "pending" : "review"}`}
                            >
                              {label(r.status)}
                            </span>
                            <button
                              className="row-arrow"
                              onClick={() => setTab("flagged")}
                            ></button>
                          </div>
                        ))}
                      {!reports.length && (
                        <Empty
                          text={
                            loading
                              ? "Loading reports…"
                              : "No integrity reports are assigned to you."
                          }
                        />
                      )}
                    </div>
                  )}
                </section>
                {isAdmin && (
                  <div className="notice">
                    <ShieldCheck size={18} />
                    <span>
                      <b>Accountability by design</b>
                      <small>
                        Every approval, rejection, and resolution is associated
                        with an authenticated staff account.
                      </small>
                    </span>
                    <span className="notice-mark">TB</span>
                  </div>
                )}
              </>
            )}
            {tab === "users" && isAdmin && (
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Account review queue</h2>
                    <p>Verify or reject new Lister and Bidder accounts.</p>
                  </div>
                  <div className="searchbox">
                    <Search size={16} />
                    <input
                      placeholder="Search accounts"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Applicant</th>
                        <th>Account type</th>
                        <th>Submitted</th>
                        <th>Status</th>
                        <th>Review</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredUsers.map((u) => (
                        <tr key={u.id}>
                          <td>
                            <b>{u.fullName}</b>
                            <small>{u.email}</small>
                          </td>
                          <td>{accountType(u.role)}</td>
                          <td>{date(u.createdAt)}</td>
                          <td>
                            <span
                              className={`status ${u.status === "PENDING" ? "pending" : "approved"}`}
                            >
                              {label(u.status)}
                            </span>
                          </td>
                          <td>
                            <div className="row-actions">
                              <button
                                disabled={busyId === u.id}
                                className="mini-approve"
                                onClick={() =>
                                  act(
                                    u.id,
                                    () =>
                                      adminApi.verifyUser(u.id, session.token),
                                    () =>
                                      setUsers((xs) =>
                                        xs.filter((x) => x.id !== u.id),
                                      ),
                                  )
                                }
                              >
                                <Check size={14} /> Verify
                              </button>
                              <button
                                disabled={busyId === u.id}
                                className="mini-reject"
                                onClick={() =>
                                  act(
                                    u.id,
                                    () =>
                                      adminApi.rejectUser(u.id, session.token),
                                    () =>
                                      setUsers((xs) =>
                                        xs.filter((x) => x.id !== u.id),
                                      ),
                                  )
                                }
                              >
                                <X size={14} /> Reject
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!filteredUsers.length && (
                    <Empty
                      text={
                        loading
                          ? "Loading accounts…"
                          : "No accounts match this search."
                      }
                    />
                  )}
                </div>
              </section>
            )}
            {tab === "tenders" && isAdmin && (
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2>Tender approval queue</h2>
                    <p>Review tender details and assign an evaluator.</p>
                  </div>
                  <div className="searchbox">
                    <Search size={16} />
                    <input
                      placeholder="Search tenders"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                </div>
                <div className="tender-list">
                  {filteredTenders.map((t) => (
                    <article className="tender-card" key={t.id}>
                      <div className="tender-card-top">
                        <span className="tender-symbol">
                          <Building2 size={19} />
                        </span>
                        <span className="status pending">Submitted</span>
                      </div>
                      <h3>{t.title}</h3>
                      <p className="tender-org">
                        {t.authorityName || "Tender issuer"}
                      </p>
                      <p className="tender-description">
                        {t.description || "No description supplied."}
                      </p>
                      <div className="tender-meta">
                        <span>
                          <Banknote size={15} />
                          {money(t.estimatedValue)}
                        </span>
                        <span>
                          <FileText size={15} />
                          Deadline {date(t.submissionDeadline)}
                        </span>
                      </div>
                      <div className="tender-actions">
                        <button
                          className="primary"
                          onClick={() =>
                            setModal({ type: "approve", tender: t })
                          }
                        >
                          <Check size={15} /> Approve & assign
                        </button>
                        <button
                          className="primary"
                          onClick={() =>
                            setModal({ type: "rejectTender", tender: t })
                          }
                        >
                          <X size={15} /> Reject tender
                        </button>
                      </div>
                    </article>
                  ))}
                  {!filteredTenders.length && (
                    <Empty
                      text={
                        loading
                          ? "Loading tenders…"
                          : "No tenders match this search."
                      }
                    />
                  )}
                </div>
              </section>
            )}
            {!isAdmin && tab === "flagged" && (
              <AuditorTenderBrowser
                mode="flagged"
                rows={flaggedTenders}
                reports={reports}
                token={session.token}
                onBack={refresh}
                onClaim={(report) =>
                  act(
                    report.reportId,
                    () => auditorApi.claim(report.reportId, session.token),
                    () =>
                      setReports((xs) =>
                        xs.map((x) =>
                          x.reportId === report.reportId
                            ? { ...x, status: "UNDER_REVIEW" }
                            : x,
                        ),
                      ),
                  )
                }
                onResolve={(report) => setModal({ type: "resolve", report })}
                onAward={(report) => setModal({ type: "award", report })}
              />
            )}
            {!isAdmin && tab === "completed" && (
              <AuditorTenderBrowser
                mode="completed"
                rows={completedTenders}
                reports={reports}
                token={session.token}
                onBack={refresh}
              />
            )}
            <footer className="footer">
              <span>© 2026 TenderBlock</span>
              <span>Protected procurement workspace</span>
            </footer>
          </div>
        </main>
      </div>
      <ActionModals
        busy={Boolean(busyId)}
        error={error}
        modal={modal}
        onClose={() => {
          if (!busyId) {
            setModal(null);
            setError("");
          }
        }}
        evaluators={evaluators}
        onApprove={(id) =>
          act(
            modal.tender.id,
            () => adminApi.approveTender(modal.tender.id, id, session.token),
            () =>
              setTenders((xs) => xs.filter((x) => x.id !== modal.tender.id)),
          )
        }
        onRejectTender={(reason) =>
          act(
            modal.tender.id,
            () => adminApi.rejectTender(modal.tender.id, reason, session.token),
            () =>
              setTenders((xs) => xs.filter((x) => x.id !== modal.tender.id)),
          )
        }
        onResolve={(confirmed, notes) =>
          act(
            modal.report.reportId,
            () =>
              auditorApi.resolve(
                modal.report.reportId,
                confirmed,
                notes,
                session.token,
              ),
            () => {
              setReports((xs) =>
                xs.map((x) =>
                  x.reportId === modal.report.reportId
                    ? {
                        ...x,
                        status: confirmed ? "RESOLVED" : "DISMISSED",
                        resolutionNotes: notes,
                      }
                    : x,
                ),
              );
            },
          )
        }
        onAward={(bidId, remarks) =>
          act(
            modal.report.tenderId,
            () =>
              auditorApi.award(
                modal.report.tenderId,
                bidId,
                remarks,
                session.token,
              ),
            () => {
              setReports((xs) =>
                xs.map((x) =>
                  x.tenderId === modal.report.tenderId
                    ? {
                        ...x,
                        status: "RESOLVED",
                        resolutionNotes: remarks || "Tender award confirmed",
                      }
                    : x,
                ),
              );
            },
          )
        }
      />
      {documentPreview && (
        <div
          className="pdf-backdrop"
          onMouseDown={(e) =>
            e.target === e.currentTarget && setDocumentPreview(null)
          }
        >
          <section className="pdf-viewer">
            <header>
              <b>{documentPreview.title} · Tender document</b>
              <div>
                <a
                  className="secondary"
                  href={documentPreview.url}
                  download="tender-document"
                >
                  <Download size={15} /> Download
                </a>
                <button
                  className="icon-button"
                  onClick={() => setDocumentPreview(null)}
                  aria-label="Close document"
                >
                  <X size={18} />
                </button>
              </div>
            </header>
            <iframe title="Tender document" src={documentPreview.url} />
          </section>
        </div>
      )}
    </div>
  );
}
