import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X, ShieldCheck, Layers3 } from "lucide-react";
import Brand from "./Brand";
import ThemeToggle from "./ThemeToggle";
import { useAuth } from "../context/AuthContext";
import { DEMO_MODE } from "../data/constants";

export default function PublicHeader() {
  const [open, setOpen] = useState(false);
  const { user } = useAuth();
  const dashboard =
    user?.role === "LISTER"
      ? "/lister"
      : user?.role === "BIDDER"
        ? "/bidder"
        : "/staff/workspace";
  const links = [
    ["Overview", "/#about"],
    ["Workspaces", "/#features"],
    ["How it works", "/#process"],
  ];
  return (
    <header className="studio-header">
      <div className="studio-header-inner">
        <Brand />
        <nav className="studio-public-nav" aria-label="Main navigation">
          {links.map(([label, to]) => (
            <a key={to} href={to}>
              {label}
            </a>
          ))}
        </nav>
        <div className="studio-header-actions">
          <ThemeToggle />
          {DEMO_MODE && (
            <Link className="studio-preview-link" to="/preview">
              <Layers3 size={16} /> All previews
            </Link>
          )}
          {user ? (
            <Link className="tb-btn-primary" to={dashboard}>
              My workspace
            </Link>
          ) : (
            <>
              <Link className="studio-staff-link" to="/staff/login">
                <ShieldCheck size={16} /> Staff
              </Link>
              <Link className="tb-btn-primary" to="/login">
                Sign in
              </Link>
            </>
          )}
          <button
            type="button"
            className="studio-menu-button"
            aria-label="Toggle navigation"
            aria-expanded={open}
            aria-controls="public-mobile-nav"
            onClick={() => setOpen(!open)}
          >
            {open ? <X size={21} /> : <Menu size={21} />}
          </button>
        </div>
      </div>
      {open && (
        <nav
          id="public-mobile-nav"
          className="studio-mobile-nav"
          aria-label="Mobile navigation"
        >
          {links.map(([label, to]) => (
            <a key={to} href={to} onClick={() => setOpen(false)}>
              {label}
            </a>
          ))}
          <Link to="/register">Create account</Link>
          <Link to="/staff/login">Staff sign in</Link>
          {DEMO_MODE && <Link to="/preview">All page previews</Link>}
        </nav>
      )}
    </header>
  );
}
