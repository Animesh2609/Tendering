import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, LockKeyhole } from "lucide-react";
import FormField from "./FormField";
import { useAuth } from "../context/AuthContext";

// Public Bidder/Lister login at /login. Staff always use /staff/login.
export default function PublicLoginForm() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const success = location.state?.message;
  const expired = new URLSearchParams(location.search).has("expired");

  async function handleLogin(event) {
    event.preventDefault();
    if (busy) return;
    setError("");
    setBusy(true);
    try {
      const account = await login(form);
      navigate(account?.role === "LISTER" ? "/lister" : "/bidder", {
        replace: true,
      });
    } catch (err) {
      setError(err?.message || "Sign in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {expired && (
        <div
          role="alert"
          className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
        >
          Your session expired. Please sign in again.
        </div>
      )}
      {success && (
        <div
          role="status"
          className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"
        >
          {success}
        </div>
      )}
      {error && (
        <div
          role="alert"
          className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </div>
      )}
      <form onSubmit={handleLogin} className="space-y-4 max-w-3xl">
        <FormField label="Email address" name="public-login-email" required>
          <input
            className="tb-input"
            id="public-login-email"
            type="email"
            autoComplete="username"
            required
            placeholder="you@organization.com"
            value={form.email}
            onChange={(event) =>
              setForm((previous) => ({
                ...previous,
                email: event.target.value,
              }))
            }
          />
        </FormField>
        <FormField label="Password" name="public-login-password" required>
          <div className="relative">
            <input
              className="tb-input pr-11"
              id="public-login-password"
              type={visible ? "text" : "password"}
              autoComplete="current-password"
              required
              placeholder="Enter your password"
              value={form.password}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  password: event.target.value,
                }))
              }
            />
            <button
              type="button"
              onClick={() => setVisible(!visible)}
              aria-label={visible ? "Hide password" : "Show password"}
              className="absolute right-3 top-[17px] text-slate-500 dark:text-slate-400"
            >
              {visible ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </FormField>
        <button type="submit" disabled={busy} className="tb-btn-primary w-full">
          {busy ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <LockKeyhole size={16} />
          )}{" "}
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600 dark:text-slate-300">
        New to TenderBlock?{" "}
        <Link className="tb-link" to="/register">
          Create an account
        </Link>
      </p>
    </>
  );
}
