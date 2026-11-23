import { Link } from "react-router-dom";
import { Info, LogIn, UserPlus } from "lucide-react";
import PublicHeader from "../components/PublicHeader";

export default function AccessPage() {
  return (
    <>
      <PublicHeader />
      <main className="studio-access min-h-[calc(100vh-74px)] bg-gradient-to-b from-[#edf5fe] to-[#f8fafc] dark:from-slate-950 dark:to-slate-900 py-16">
        <div className="tb-container max-w-4xl">
          <div className="mb-10 text-center">
            <h1 className="text-3xl font-extrabold tracking-tight text-ink dark:text-slate-100 sm:text-4xl">
              Welcome to{" "}
              <span className="text-blue-700 dark:text-blue-300">
                TenderBlock
              </span>
            </h1>
            <p className="mt-3 text-slate-600 dark:text-slate-300">
              Choose how you want to continue. This public portal is for Bidders
              and Listers.
            </p>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            <Link
              to="/register"
              className="tb-card group flex flex-col items-center p-9 text-center transition hover:-translate-y-1 hover:border-blue-300 hover:shadow-lg"
            >
              <span className="mb-5 grid h-17 w-17 place-items-center rounded-full bg-blue-50 dark:bg-slate-800 text-blue-700 dark:text-blue-300">
                <UserPlus size={33} />
              </span>
              <h2 className="text-xl font-bold text-ink dark:text-slate-100">
                Create account
              </h2>
              <p className="mt-3 max-w-[260px] text-sm leading-7 text-slate-600 dark:text-slate-300">
                New to TenderBlock? Register as exactly one role: Bidder or
                Lister.
              </p>
              <span className="tb-btn-primary mt-7 w-full">Sign up </span>
            </Link>
            <Link
              to="/login"
              className="tb-card group flex flex-col items-center p-9 text-center transition hover:-translate-y-1 hover:border-blue-300 hover:shadow-lg"
            >
              <span className="mb-5 grid h-17 w-17 place-items-center rounded-full bg-blue-50 dark:bg-slate-800 text-blue-700 dark:text-blue-300">
                <LogIn size={33} />
              </span>
              <h2 className="text-xl font-bold text-ink dark:text-slate-100">
                Sign in
              </h2>
              <p className="mt-3 max-w-[260px] text-sm leading-7 text-slate-600 dark:text-slate-300">
                Already registered? Sign in using your email and password to
                continue.
              </p>
              <span className="tb-btn-outline mt-7 w-full">Sign in </span>
            </Link>
          </div>
          <div className="mt-7 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-900">
            <Info size={22} className="mt-0.5 shrink-0" />
            <p>
              <strong>Roles are mutually exclusive.</strong> A Bidder cannot
              simultaneously be a Lister under this workflow. Admin, Evaluator
              and Auditor accounts are managed separately and do not use public
              registration.
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
