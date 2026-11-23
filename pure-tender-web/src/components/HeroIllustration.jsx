import {
  Building2,
  FileCheck2,
  Fingerprint,
  ShieldCheck,
  CircleCheck,
  FileText,
  LockKeyhole,
  Scale,
} from "lucide-react";
const stages = [
  ["Published", FileText],
  ["Bids received", LockKeyhole],
  ["Evaluation", Scale],
  ["Awarded", FileCheck2],
];
export default function HeroIllustration() {
  return (
    <div
      className="studio-hero-board"
      aria-label="Illustrative tender workflow"
    >
      <div className="studio-board-top">
        <span>
          <span className="studio-window-dot" />
          <span className="studio-window-dot" />
          <span className="studio-window-dot" />
        </span>
        <span>WORKFLOW PREVIEW</span>
        <ShieldCheck size={16} />
      </div>
      <div className="studio-board-content">
        <div className="studio-board-heading">
          <div className="studio-icon-tile">
            <Building2 size={24} />
          </div>
          <div>
            <span className="studio-mono">PUBLIC INFRASTRUCTURE</span>
            <h3>A better process. From the start.</h3>
          </div>
          <span className="studio-mini-badge">Illustration</span>
        </div>
        <div className="studio-workflow-track">
          {stages.map(([name, Icon], i) => (
            <div key={name} className={i === 2 ? "current" : ""}>
              <span>
                <Icon size={21} />
              </span>
              <b>{name}</b>
              <small>
                {
                  [
                    "Open for proposals",
                    "Submission deadline",
                    "Independent scoring",
                    "Recorded decision",
                  ][i]
                }
              </small>
            </div>
          ))}
        </div>
        <div className="studio-board-bottom">
          <span>
            <Fingerprint size={20} />
            <span>
              Evidence at every step
              <small>Document integrity and a traceable process</small>
            </span>
          </span>
          <CircleCheck size={22} />
        </div>
      </div>
    </div>
  );
}
