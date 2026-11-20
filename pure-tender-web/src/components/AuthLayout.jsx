import { Link } from "react-router-dom";
import { CheckCircle2, ShieldCheck } from "lucide-react";
import PublicHeader from "./PublicHeader";
import DemoNotice from "./DemoNotice";
import { DEMO_MODE } from "../data/constants";

export default function AuthLayout({
  title,
  subtitle,
  children,
  narrow = false,
}) {
  return (
    <>
      <PublicHeader />
      <main className="flex min-h-[calc(100vh-74px)] items-center bg-[#f3f7fc] py-8 dark:bg-slate-950 sm:py-10">
        <div
          className={`tb-container ${narrow ? "max-w-[460px]" : "max-w-[990px]"}`}
        >
          <div className="mb-7 text-center">
            <h1 className="text-2xl font-extrabold text-ink dark:text-slate-100 sm:text-3xl">
              {title}
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {subtitle}
            </p>
          </div>
          <div className="tb-card p-5 sm:p-8">{children}</div>
          {DEMO_MODE && (
            <div className="mt-5">
              <DemoNotice compact />
            </div>
          )}
          <div className="mt-5 flex flex-wrap justify-center gap-x-6 gap-y-2 text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1">
              <ShieldCheck size={15} /> Role-based access
            </span>
            <span className="flex items-center gap-1">
              <CheckCircle2 size={15} /> Clear tender workflows
            </span>
            <Link to="/" className="tb-link">
              Back to home
            </Link>
          </div>
        </div>
      </main>
    </>
  );
}
