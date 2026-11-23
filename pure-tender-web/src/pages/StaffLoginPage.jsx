import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import ThemeToggle from "../components/ThemeToggle";
import { DEMO_MODE } from "../data/constants";

// This is a separate URL with no public landing-page header.
// The real Spring Boot backend must provision and authorize staff accounts.
export default function StaffLoginPage() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { staffLogin, user, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await staffLogin(form);
      navigate("/staff/workspace", { replace: true });
    } catch (err) {
      setError(err?.message || "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  if (user) return <Navigate to="/workspace" replace />;
  return (
    <main className="studio-staff-auth relative flex min-h-screen items-center justify-center bg-slate-100 dark:bg-slate-900 px-4 py-12">
      <div className="absolute right-5 top-5">
        <ThemeToggle />
      </div>
      <div className="studio-staff-card w-full max-w-md rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-7 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <ShieldCheck className="text-blue-700 dark:text-blue-300" size={30} />
          <div>
            <h1 className="text-2xl font-bold text-ink dark:text-slate-100">
              TenderBlock Staff Login
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Admin · Evaluator · Auditor
            </p>
          </div>
        </div>
        <p className="mb-5 text-sm leading-6 text-slate-600 dark:text-slate-300">
          Use your organisation-issued account. Evaluator applicants can
          register below. Admin and Auditor accounts are provisioned by your
          organisation.
        </p>
        {DEMO_MODE && (
          <div className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
            Staff DEMO ONLY: admin@demo.test, evaluator@demo.test or
            auditor@demo.test (password: Demo@12345). These are local simulated
            accounts, NOT genuine staff permissions.
          </div>
        )}
        {location.state?.message && (
          <p
            role="status"
            className="mb-4 text-sm text-emerald-700 dark:text-emerald-300"
          >
            {location.state.message}
          </p>
        )}
        {error && (
          <p
            role="alert"
            className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700"
          >
            {error}
          </p>
        )}
        {sessionExpired && (
          <p role="alert" className="mb-4 text-sm text-amber-700">
            Your session expired. Sign in again.
          </p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <label
            className="block text-sm font-semibold text-slate-700 dark:text-slate-200"
            htmlFor="staffEmail"
          >
            Email address
          </label>
          <input
            id="staffEmail"
            type="email"
            required
            autoComplete="username"
            className="tb-input"
            value={form.email}
            onChange={(event) =>
              setForm((old) => ({ ...old, email: event.target.value }))
            }
          />
          <label
            className="block text-sm font-semibold text-slate-700 dark:text-slate-200"
            htmlFor="staffPassword"
          >
            Password
          </label>
          <div className="relative">
            <input
              id="staffPassword"
              type={showPassword ? "text" : "password"}
              required
              autoComplete="current-password"
              className="tb-input pr-12"
              value={form.password}
              onChange={(event) =>
                setForm((old) => ({ ...old, password: event.target.value }))
              }
            />
            <button
              type="button"
              className="absolute right-3 top-3 text-slate-500 dark:text-slate-400"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword((old) => !old)}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          <button
            type="submit"
            disabled={busy}
            className="tb-btn-primary w-full"
          >
            <LockKeyhole size={17} />
            {busy ? "Signing in..." : "Sign in as staff"}
          </button>
        </form>
        <p className="mt-4 text-sm">
          <Link to="/staff/register/evaluator" className="tb-link">
            Apply for an evaluator account
          </Link>
        </p>
        <Link
          to="/"
          className="mt-5 inline-block text-sm text-brand dark:text-blue-300"
        >
          Back to TenderBlock
        </Link>
      </div>
    </main>
  );
}
