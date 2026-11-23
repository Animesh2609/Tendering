import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Layers3,
  Globe2,
  Building2,
  BriefcaseBusiness,
  ShieldCheck,
  ClipboardCheck,
  ScanLine,
  RotateCcw,
} from "lucide-react";
import PublicHeader from "../components/PublicHeader";
import { PREVIEW_PAGES, PREVIEW_ROLES } from "./catalog";
import { demoReset } from "../api/demoStore";
import { ensurePreviewFixtures } from "./fixtures";
const icons = {
  public: Globe2,
  bidder: BriefcaseBusiness,
  lister: Building2,
  admin: ShieldCheck,
  evaluator: ClipboardCheck,
  auditor: ScanLine,
};
export default function PreviewGallery() {
  const [params, setParams] = useSearchParams();
  const role = PREVIEW_ROLES.includes(params.get("role"))
    ? params.get("role")
    : "all";
  const [notice, setNotice] = useState("");
  const pages = PREVIEW_PAGES.filter((p) => role === "all" || p.role === role);
  return (
    <>
      <PublicHeader />
      <main className="preview-page">
        <div className="preview-heading">
          <span className="studio-eyebrow-pill">
            <Layers3 size={15} /> INTERACTIVE DESIGN PREVIEW
          </span>
          <h1>
            Every role.
            <br />
            Every part of the experience.
          </h1>
          <p>
            Explore all {PREVIEW_PAGES.length} pages and key views in the
            refreshed TenderBlock interface. Choose a card to open the actual
            screen with a sample account. Use “All previews” to return here.
          </p>
          <p className="mt-4">
            Sample data stays in this browser. This preview does not connect to
            Spring Boot or Hyperledger Fabric, and document downloads require
            the live backend.
          </p>
        </div>
        <div className="preview-filters" aria-label="Filter previews by role">
          {["all", ...PREVIEW_ROLES].map((r) => (
            <button
              key={r}
              aria-pressed={role === r}
              onClick={() => setParams(r === "all" ? {} : { role: r })}
            >
              {r === "all"
                ? "All views"
                : r === "public"
                  ? "Public pages"
                  : r[0].toUpperCase() + r.slice(1)}
            </button>
          ))}
          <button
            onClick={() => {
              demoReset();
              ensurePreviewFixtures();
              setNotice(
                "Sample data reset. You can explore the original review states again.",
              );
            }}
          >
            <RotateCcw size={14} className="inline mr-2" />
            Reset sample data
          </button>
        </div>
        {notice && (
          <p role="status" className="mb-5 text-sm">
            {notice}
          </p>
        )}
        <div className="preview-grid">
          {pages.map((page) => {
            const Icon = icons[page.role];
            return (
              <article key={page.id} className="preview-card">
                <div className="preview-card-top">
                  <span className="studio-icon-tile">
                    <Icon size={21} />
                  </span>
                  <div>
                    <small>
                      {page.role[0].toUpperCase() + page.role.slice(1)}
                    </small>
                    <h2>{page.title}</h2>
                  </div>
                </div>
                <div className="preview-card-content">
                  <p>{page.description}</p>
                  <Link className="tb-btn-outline" to={`/preview/${page.id}`}>
                    Open preview
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
      </main>
    </>
  );
}
