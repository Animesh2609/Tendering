const tones = {
  PUBLISHED: "success",
  OPEN: "success",
  SELECTED: "success",
  AWARDED: "success",
  SUBMITTED: "info",
  DEMO_SUBMITTED: "info",
  OPENED: "info",
  UNDER_EVALUATION: "review",
  EVALUATED: "review",
  PENDING_APPROVAL: "warning",
  PENDING_VERIFICATION: "warning",
  ON_HOLD: "warning",
  DEMO_ONLY: "warning",
  REJECTED: "danger",
  VOIDED: "danger",
  FAILED: "danger",
  FLAGGED: "danger",
};
export default function StatusBadge({ status }) {
  return (
    <span
      className={`studio-status studio-status-${tones[status] || "neutral"}`}
      data-status={status}
    >
      {String(status || "UNKNOWN").replaceAll("_", " ")}
    </span>
  );
}
