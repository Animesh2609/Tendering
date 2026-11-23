import { DEMO_MODE } from "../../../data/constants";
import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Download,
  ExternalLink,
  FileText,
  Search,
  Shield,
  Trophy,
  X,
} from "lucide-react";
import { auditorApi } from "../api/auditorApi";
import Empty from "./EmptyState";

const titleCase = (value) =>
  String(value || "UNKNOWN")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
const date = (value) =>
  value
    ? new Date(value).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "—";
function Integrity({ value }) {
  const state = String(value || "UNKNOWN").toLowerCase();
  return <span className={`integrity-pill ${state}`}>{titleCase(value)}</span>;
}
const outcomeClass = (status) =>
  String(status || "").toUpperCase() === "AWARDED" ? "approved" : "pending";

export default function AuditorTenderBrowser({
  mode,
  rows = [],
  reports = [],
  token,
  onBack,
  onClaim,
  onResolve,
  onAward,
}) {
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [pdf, setPdf] = useState(null);
  useEffect(
    () => () => {
      if (pdf?.url) URL.revokeObjectURL(pdf.url);
    },
    [pdf],
  );

  const visible = rows.filter((row) =>
    `${row.tenderTitle || row.title} ${row.authorityName || ""} ${row.tenderId || row.id}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  async function openTender(tender) {
    setSelected(tender);
    setDetail(null);
    setError("");
    setLoading(true);
    try {
      setDetail(
        await auditorApi.auditTender(tender.tenderId || tender.id, token),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    if (selected) openTender(selected);
    // Refresh the selected audit after report actions update the parent list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reports]);
  const previewOpened = useRef(false);
  useEffect(() => {
    if (!DEMO_MODE || previewOpened.current) return;
    const id = new URLSearchParams(window.location.search).get("tender");
    const tender = rows.find((t) => (t.tenderId || t.id) === id);
    if (tender) {
      previewOpened.current = true;
      void openTender(tender);
    }
    // Preview entry only; existing audit refresh behavior remains unchanged.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows]);
  async function openProposal(bid) {
    setError("");
    try {
      const blob = await auditorApi.proposal(bid.bidId, token);
      setPdf({
        url: URL.createObjectURL(blob),
        name: `proposal-${bid.bidId}.pdf`,
      });
    } catch (e) {
      setError(e.message);
    }
  }

  if (selected) {
    const tenderId = selected.tenderId || selected.id;
    const tenderReports =
      detail?.reports ||
      reports.filter((report) => report.tenderId === tenderId);
    const status = detail?.status || selected.status;
    const winningBid = detail?.bids?.find(
      (bid) => String(bid.status).toUpperCase() === "SELECTED",
    );
    const canAward =
      mode === "flagged" &&
      String(status).toUpperCase() === "ON_HOLD" &&
      tenderReports.length > 0 &&
      tenderReports.every((report) =>
        ["RESOLVED", "DISMISSED"].includes(report.status),
      );
    const backLabel =
      mode === "queue"
        ? "Review queue"
        : mode === "completed"
          ? "Completed tenders"
          : "Flagged tenders";
    return (
      <section className="panel auditor-detail">
        <div className="panel-head">
          <div>
            <button
              className="back-link"
              onClick={() => {
                setSelected(null);
                setDetail(null);
                onBack?.();
              }}
            >
              <ArrowLeft size={16} /> {backLabel}
            </button>
            <h2>
              {detail?.tenderTitle || selected.tenderTitle || selected.title}
            </h2>
            <p>
              {detail?.authorityName ||
                selected.authorityName ||
                "Tender issuer"}{" "}
              · {titleCase(status)}
            </p>
          </div>
        </div>
        {error && <p className="alert error">{error}</p>}
        {loading ? (
          <Empty text="Checking tender and bid records against the ledger…" />
        ) : (
          detail && (
            <>
              {detail.verificationMessage && (
                <p
                  className={`alert ${detail.unavailable ? "" : "error"}`}
                  role="status"
                >
                  {detail.verificationMessage}
                </p>
              )}
              <div className="audit-summary">
                {detail.description && <p>{detail.description}</p>}
                {mode !== "completed" && (
                  <span>
                    Database integrity{" "}
                    <Integrity value={detail.databaseIntegrity} />
                  </span>
                )}
                <span>
                  Blockchain integrity{" "}
                  <Integrity value={detail.blockchainIntegrity} />
                </span>
                <span>
                  Submitted bids{" "}
                  <b>{detail.unavailable ? "—" : detail.bids?.length || 0}</b>
                </span>
              </div>
              {mode === "completed" &&
                String(status).toUpperCase() === "AWARDED" && (
                  <section className="completed-award">
                    <div className="completed-award-icon">
                      <Trophy size={20} />
                    </div>
                    <div className="completed-award-copy">
                      <small>AWARD RESULT</small>
                      <h3>
                        {winningBid?.bidderName ||
                          "Winning bid details unavailable"}
                      </h3>
                      <p>
                        {winningBid
                          ? `Winning bid ${new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(winningBid.quotedAmount))} · Bid reference ${winningBid.bidId}`
                          : "The tender is marked awarded, but no selected bid was returned."}
                      </p>
                    </div>
                    <span className={`status ${outcomeClass(status)}`}>
                      {titleCase(status)}
                    </span>
                  </section>
                )}
              {mode === "completed" &&
                String(status).toUpperCase() !== "AWARDED" && (
                  <section className="completed-award">
                    <div className="completed-award-icon">
                      <FileText size={20} />
                    </div>
                    <div className="completed-award-copy">
                      <small>TENDER OUTCOME</small>
                      <h3>{titleCase(status)}</h3>
                      <p>
                        This tender is retained in history with its submitted
                        bids and audit details.
                      </p>
                    </div>
                    <span className="status approved">{titleCase(status)}</span>
                  </section>
                )}
              {tenderReports.length > 0 && (
                <div className="audit-reports">
                  <h3>Integrity reports</h3>
                  {tenderReports.map((report) => (
                    <article className="audit-report" key={report.reportId}>
                      <div>
                        <b>{titleCase(report.type)}</b>
                        <p>{report.description}</p>
                        <small>
                          {titleCase(report.status)} ·{" "}
                          {report.evidenceReference || report.reportId}
                        </small>
                      </div>
                      <div className="audit-report-actions">
                        {report.status === "OPEN" && (
                          <button
                            className="secondary"
                            onClick={() => onClaim?.(report)}
                          >
                            Claim report
                          </button>
                        )}
                        {report.status === "UNDER_REVIEW" && (
                          <button
                            className="secondary"
                            onClick={() => onResolve?.(report)}
                          >
                            Record finding
                          </button>
                        )}
                        {canAward && (
                          <button
                            className="primary"
                            onClick={() => onAward?.(report)}
                          >
                            Award held tender
                          </button>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Bidder</th>
                      <th>Submitted bid</th>
                      <th>Opened at</th>
                      <th>Blockchain integrity</th>
                      {mode !== "completed" && <th>Database integrity</th>}
                      <th>Proposal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(detail.bids || []).map((bid) => (
                      <tr key={bid.bidId}>
                        <td>
                          <b>{bid.bidderName || "Unknown bidder"}</b>
                          <small>{bid.bidderId || bid.bidId}</small>
                        </td>
                        <td>
                          {bid.quotedAmount == null
                            ? "—"
                            : new Intl.NumberFormat("en-IN", {
                                style: "currency",
                                currency: "INR",
                                maximumFractionDigits: 2,
                              }).format(Number(bid.quotedAmount))}
                          <small>{titleCase(bid.status)}</small>
                        </td>
                        <td>{date(bid.openedAt)}</td>
                        <td>
                          <Integrity value={bid.blockchainIntegrity} />
                        </td>
                        {mode !== "completed" && (
                          <td>
                            <Integrity value={bid.databaseIntegrity} />
                          </td>
                        )}
                        <td>
                          {bid.proposalUploaded && mode !== "queue" ? (
                            <button
                              className="document-button"
                              onClick={() => openProposal(bid)}
                            >
                              <FileText size={16} /> View PDF
                            </button>
                          ) : (
                            <span>
                              {bid.proposalUploaded
                                ? "Available after review"
                                : "Not available"}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!detail.bids?.length && !detail.unavailable && (
                  <Empty text="No opened bids were found for this tender." />
                )}
              </div>
            </>
          )
        )}
        {pdf && (
          <div
            className="pdf-backdrop"
            onMouseDown={(e) => e.target === e.currentTarget && setPdf(null)}
          >
            <section className="pdf-viewer">
              <header>
                <b>{pdf.name}</b>
                <div>
                  <a className="secondary" href={pdf.url} download={pdf.name}>
                    <Download size={15} /> Download
                  </a>
                  <button
                    className="icon-button"
                    onClick={() => setPdf(null)}
                    aria-label="Close PDF"
                  >
                    <X size={18} />
                  </button>
                </div>
              </header>
              <iframe title="Bid proposal PDF" src={pdf.url} />
            </section>
          </div>
        )}
      </section>
    );
  }

  const heading =
    mode === "queue"
      ? "Tender review queue"
      : mode === "completed"
        ? "Completed tenders"
        : "Flagged tenders";
  const description =
    mode === "queue"
      ? "Review tenders under evaluation and check their database records against Fabric."
      : mode === "completed"
        ? "History of awarded, rejected, cancelled and voided tenders."
        : "Tenders on hold and referred for auditor review.";
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{heading}</h2>
          <p>{description}</p>
        </div>
        <label className="searchbox">
          <Search size={16} />
          <input
            placeholder="Search tenders"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>
      {error && <p className="alert error">{error}</p>}
      <div className="auditor-tender-list">
        {visible.map((tender) => (
          <button
            className="auditor-tender-row"
            key={tender.tenderId || tender.id}
            onClick={() => openTender(tender)}
          >
            <span className="quick-icon">
              <Shield size={17} />
            </span>
            <span className="quick-copy">
              <b>{tender.tenderTitle || tender.title}</b>
              <small>
                {tender.authorityName || "Tender issuer"} ·{" "}
                {tender.tenderId || tender.id} ·{" "}
                {date(tender.completedAt || tender.flaggedAt)}
              </small>
            </span>
            <span
              className={`status ${mode === "completed" ? outcomeClass(tender.status) : mode === "queue" ? "review" : "pending"}`}
            >
              {titleCase(tender.status)}
            </span>
            <ExternalLink size={17} />
          </button>
        ))}
        {!visible.length && (
          <Empty
            text={
              mode === "queue"
                ? "No tenders are currently under evaluation."
                : "No tenders match this search."
            }
          />
        )}
      </div>
    </section>
  );
}
