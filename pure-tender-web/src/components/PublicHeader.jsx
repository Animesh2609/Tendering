import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Brand from './Brand';
import ThemeToggle from './ThemeToggle';
import { useAuth } from '../context/AuthContext';

export default function PublicHeader() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user } = useAuth();
  const dashboard = user?.role === 'LISTER' ? '/lister' : user?.role === 'BIDDER' ? '/bidder' : '/staff/workspace';
  const nav = [
    ['Home', '/#home'], ['About', '/#about'], ['For whom', '/#features'],
    ['Process', '/#process'], ['Team', '/#contact'],
  ];
  return (
    <header className="sticky top-0 z-40 border-b border-[#ececf4] bg-white/95 backdrop-blur-sm dark:border-slate-700 dark:bg-slate-900/95">
      <div className="tb-container flex h-[80px] items-center justify-between gap-3">
        <Brand />
        <nav className="hidden items-center gap-5 lg:flex" aria-label="Main navigation">
          {nav.map(([name, url]) => <a key={name} href={url} className="text-sm font-semibold text-slate-600 transition hover:text-[#5b4bda] dark:text-slate-300 dark:hover:text-violet-300">{name}</a>)}
        </nav>
        <div className="ml-auto flex items-center gap-2 sm:ml-0">
          <ThemeToggle />
          {user
            ? <Link to={dashboard} className="tb-btn-primary hidden sm:inline-flex">My workspace</Link>
            : <>
              <Link to="/staff/login" className="hidden text-sm text-brand dark:text-blue-300 sm:inline-flex">Staff</Link>
              <Link to="/register" className="tb-btn-outline hidden sm:inline-flex">Register</Link>
              <Link to="/login" className="tb-btn-primary">Login</Link>
            </>}
          <button type="button" className="rounded-md p-2 text-slate-700 sm:hidden dark:text-slate-100" aria-label="Toggle menu" aria-expanded={mobileOpen} onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X size={24}/> : <Menu size={24}/>}
          </button>
        </div>
      </div>
      {mobileOpen && <nav className="flex flex-col gap-3 border-t border-slate-200 bg-white px-5 py-5 dark:border-slate-700 dark:bg-slate-900 sm:hidden" aria-label="Mobile navigation">
        {nav.map(([name, url]) => <a onClick={() => setMobileOpen(false)} key={name} href={url} className="text-sm font-semibold text-slate-700 dark:text-slate-200">{name}</a>)}
        {user
          ? <Link onClick={() => setMobileOpen(false)} className="tb-btn-primary" to={dashboard}>My workspace</Link>
          : <>
            <Link onClick={() => setMobileOpen(false)} className="tb-btn-outline" to="/register">Register</Link>
            <Link onClick={() => setMobileOpen(false)} className="tb-btn-outline" to="/staff/login">Staff login</Link>
            <Link onClick={() => setMobileOpen(false)} className="tb-btn-primary" to="/login">Login</Link>
          </>}
      </nav>}
    </header>
  );
}
