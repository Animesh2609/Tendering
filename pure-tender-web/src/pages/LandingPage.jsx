import { Link } from "react-router-dom";
import {
  Building2,
  BriefcaseBusiness,
  ShieldCheck,
  ClipboardCheck,
  ScanLine,
  FileText,
  LockKeyhole,
  Layers3,
  Check,
} from "lucide-react";
import PublicHeader from "../components/PublicHeader";
import HeroIllustration from "../components/HeroIllustration";
import TeamFooter from "../components/TeamFooter";
import { DEMO_MODE } from "../data/constants";
const roles = [
  {
    icon: Building2,
    title: "Lister",
    label: "Publish with clarity",
    copy: "Define requirements, create tenders and follow each request through approval.",
    to: "/register",
  },
  {
    icon: BriefcaseBusiness,
    title: "Bidder",
    label: "Find your next opportunity",
    copy: "Explore published tenders, prepare proposals and track your submissions.",
    to: "/register",
  },
  {
    icon: ShieldCheck,
    title: "Admin",
    label: "Keep the process moving",
    copy: "Verify accounts, review tender requests and assign the right evaluator.",
    to: "/staff/login",
  },
  {
    icon: ClipboardCheck,
    title: "Evaluator",
    label: "Make informed assessments",
    copy: "Review assigned bids and record technical and financial scores.",
    to: "/staff/login",
  },
  {
    icon: ScanLine,
    title: "Auditor",
    label: "Examine the evidence",
    copy: "Investigate flagged records and review tender integrity and outcomes.",
    to: "/staff/login",
  },
];
export default function LandingPage() {
  return (
    <>
      <PublicHeader />
      <main id="home" className="studio-landing">
        <section className="studio-hero">
          <div className="studio-hero-glow" aria-hidden="true" />
          <div className="tb-container">
            <span className="studio-eyebrow-pill">
              <Layers3 size={15} /> A connected procurement workspace
            </span>
            <h1>
              Every tender.
              <br />
              <span>A clearer decision.</span>
            </h1>
            <p className="studio-hero-description">
              From the first requirement to the final award.
              <br className="hidden sm:block" /> Bring people, proposals and
              accountability into one place.
            </p>
            <div className="studio-hero-actions">
              <Link className="tb-btn-primary studio-shimmer" to="/register">
                Create your account
              </Link>
              <a className="tb-btn-outline" href="#features">
                Explore the workspaces
              </a>
            </div>
            <div className="studio-hero-trust">
              <span>
                <LockKeyhole size={15} /> Role-based access
              </span>
              <span>
                <FileText size={15} /> Clear tender stages
              </span>
              <span>
                <ScanLine size={15} /> Integrity review
              </span>
            </div>
            <HeroIllustration />
          </div>
        </section>
        <section id="about" className="studio-section">
          <div className="tb-container studio-about-grid">
            <div>
              <p className="tb-eyebrow">THE BIGGER PICTURE</p>
              <h2 className="studio-heading">
                Less scattered information.
                <br />
                <span>More shared understanding.</span>
              </h2>
            </div>
            <div className="studio-about-copy">
              <p>
                Tendering brings together organizations, bidders and reviewers.
                TenderBlock gives each person a focused workspace, with the
                documents and decisions they need.
              </p>
              <p>
                Approval, evaluation and auditing remain separate
                responsibilities. Spring Boot coordinates the workflow, with
                Hyperledger Fabric supporting evidence records when the backend
                and network are deployed.
              </p>
              <div className="studio-inline-note">
                <ShieldCheck size={20} />
                <span>
                  Designed around accountability, from submission to outcome.
                </span>
              </div>
            </div>
          </div>
        </section>
        <section id="features" className="studio-section">
          <div className="tb-container">
            <div className="studio-section-heading">
              <div>
                <p className="tb-eyebrow">ONE PLATFORM. FIVE PERSPECTIVES.</p>
                <h2 className="studio-heading">
                  The right tools.
                  <br />
                  <span>For your part in the process.</span>
                </h2>
              </div>
              <p>Purposeful workspaces that keep your next action in focus.</p>
            </div>
            <div className="studio-role-grid">
              {roles.map(({ icon: Icon, title, label, copy, to }) => (
                <article className="studio-role-card" key={title}>
                  <div className="studio-icon-tile">
                    <Icon size={23} />
                  </div>
                  <span className="studio-mono">{title.toUpperCase()}</span>
                  <h3>{label}</h3>
                  <p>{copy}</p>
                  <Link
                    to={DEMO_MODE ? `/preview?role=${title.toLowerCase()}` : to}
                  >
                    {DEMO_MODE
                      ? "Preview workspace"
                      : title === "Lister" || title === "Bidder"
                        ? "Get started"
                        : "Staff sign in"}
                  </Link>
                </article>
              ))}
            </div>
          </div>
        </section>
        <section id="process" className="studio-section">
          <div className="tb-container">
            <div className="studio-section-heading">
              <div>
                <p className="tb-eyebrow">A TRACEABLE PATH</p>
                <h2 className="studio-heading">
                  A clear next step.
                  <br />
                  <span>At every stage.</span>
                </h2>
              </div>
            </div>
            <div className="studio-process-grid">
              {[
                [
                  "Create & approve",
                  "A Lister submits the scope and dates. An Admin reviews the tender and assigns an evaluator before publication.",
                ],
                [
                  "Submit & evaluate",
                  "Bidders submit proposals before the deadline. Assigned evaluators assess bids using technical and financial criteria.",
                ],
                [
                  "Check & conclude",
                  "Integrity checks support the award process. Flagged tenders move to the Auditor for investigation and resolution.",
                ],
              ].map(([title, copy]) => (
                <article key={title}>
                  <div className="studio-process-icon">
                    <Check size={20} />
                  </div>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
        <section className="studio-final-cta">
          <div className="tb-container">
            <span className="studio-icon-tile">
              <Layers3 size={24} />
            </span>
            <h2>
              Your next opportunity
              <br />
              starts here.
            </h2>
            <p>Register as a Bidder or Lister to get started.</p>
            <Link className="tb-btn-primary" to="/register">
              Join TenderBlock
            </Link>
            {DEMO_MODE && (
              <Link className="tb-link" to="/preview">
                Browse every page preview
              </Link>
            )}
          </div>
        </section>
      </main>
      <TeamFooter />
    </>
  );
}
