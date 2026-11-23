import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ClipboardList,
  FileSearch,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { bidApi, tenderApi } from "../api/services";
import { BACKEND_CONTRACT, DEMO_MODE } from "../data/constants";
import PageTitle from "../components/PageTitle";
import StatusBadge from "../components/StatusBadge";
import { formatDate } from "../utils/format";

export default function BidderDashboardPage() {
  const { user, token } = useAuth();
  const teamMode = !DEMO_MODE && BACKEND_CONTRACT === "team";
  const bidHistoryRestricted = teamMode && user?.verified !== true;
  const [published, setPublished] = useState({ items: [], totalElements: 0 });
  const [bidCount, setBidCount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const loadPublished = tenderApi.listPage(token, 0, 5);
    const loadMyBids = bidHistoryRestricted
      ? Promise.resolve(null)
      : bidApi.minePage(user, token, 0, 1);
    Promise.allSettled([loadPublished, loadMyBids]).then(
      ([opportunities, bids]) => {
        if (!active) return;
        if (opportunities.status === "fulfilled")
          setPublished(opportunities.value);
        else
          setError(
            opportunities.reason?.message ||
              "Could not load published tenders.",
          );
        if (bids.status === "fulfilled")
          setBidCount(bids.value?.totalElements ?? null);
        else setBidCount(null);
        setLoading(false);
      },
    );
    return () => {
      active = false;
    };
  }, [token, user, bidHistoryRestricted, refresh]);

  const stats = [
    {
      label: "Published opportunities",
      value: loading ? "…" : published.totalElements,
      icon: FileSearch,
    },
    {
      label: "My bids",
      value: bidHistoryRestricted ? "Awaiting verification" : (bidCount ?? "—"),
      icon: ClipboardList,
    },
    {
      label: "Account status",
      value: user?.accountStatus || (user?.verified ? "VERIFIED" : "PENDING"),
      icon: ShieldCheck,
    },
  ];

  return (
    <>
      <PageTitle
        title="Bidder dashboard"
        subtitle={`Welcome, ${user?.fullName || "Bidder"}. A quick overview of your account and opportunities.`}
        action={
          <button
            type="button"
            className="tb-btn-outline"
            onClick={() => setRefresh((v) => v + 1)}
          >
            <RefreshCw size={16} /> Refresh
          </button>
        }
      />
      <section
        aria-label="Bidder summary"
        className="grid gap-4 sm:grid-cols-3"
      >
        {stats.map(({ label, value, icon: Icon }) => (
          <div className="tb-card p-5" key={label}>
            <Icon size={22} className="text-[#285970] dark:text-slate-300" />
            <p className="mt-4 text-xs font-semibold text-slate-500 dark:text-slate-400">
              {label}
            </p>
            <p className="mt-2 text-xl font-bold text-ink dark:text-slate-100">
              {value}
            </p>
          </div>
        ))}
      </section>
      {error && (
        <p
          role="alert"
          className="mt-5 rounded-md bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </p>
      )}
      <section className="tb-card mt-6 p-6">
        <h2 className="text-lg font-semibold text-ink dark:text-slate-100">
          Find your next opportunity
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
          The searchable tender list, filters and proposal details are available
          under Browse Tenders. The dashboard is an overview, not a second copy
          of that screen.
        </p>
        <Link to="/bidder/tenders" className="tb-btn-primary mt-4 inline-flex">
          <FileSearch size={16} /> Browse published tenders{" "}
        </Link>
      </section>
      <section className="tb-card mt-6 overflow-hidden">
        <div className="border-b border-slate-100 p-5 dark:border-slate-700">
          <h2 className="font-semibold text-ink dark:text-slate-100">
            Recently published
          </h2>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Latest opportunities. Open Browse Tenders to search and submit
            proposals.
          </p>
        </div>
        {loading && <p className="p-5 text-sm text-slate-500">Loading…</p>}
        {!loading && published.items.length === 0 && (
          <p className="p-5 text-sm text-slate-500">
            No published tenders on the first page.
          </p>
        )}
        {!loading &&
          published.items.map((tender) => (
            <div
              key={tender.id}
              className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-700"
            >
              <div>
                <p className="text-sm font-semibold text-ink dark:text-slate-100">
                  {tender.title}
                </p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Deadline: {formatDate(tender.submissionDeadline)}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={tender.status} />
                <Link className="tb-link" to={`/bidder/tenders/${tender.id}`}>
                  Details{" "}
                </Link>
              </div>
            </div>
          ))}
      </section>
    </>
  );
}
