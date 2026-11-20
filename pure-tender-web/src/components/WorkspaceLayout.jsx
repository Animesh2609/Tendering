import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, ClipboardList, FilePlus2, FileText, LayoutDashboard, LogOut, Search, UserRound, Menu, X } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { initials } from '../utils/format';
import Brand from './Brand';
import DemoNotice from './DemoNotice';
import ThemeToggle from './ThemeToggle';
import { DEMO_MODE } from '../data/constants';

export default function WorkspaceLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [expanded, setExpanded] = useState(false);
  const bidder = user.role === 'BIDDER';
  const isPending = user.accountStatus === 'PENDING' || (!user.accountStatus && user.verified === false);
  const registrationNotice = location.state?.registrationNotice;
  const prefix = bidder ? '/bidder' : '/lister';
  const nav = bidder ? [
    { label:'Dashboard', path:'/bidder', icon:LayoutDashboard, end:true },
    { label:'Browse tenders', path:'/bidder/tenders', icon:Search },
    { label:'My bids', path:'/bidder/my-bids', icon:ClipboardList },
    { label:'Profile', path:'/profile', icon:UserRound },
  ] : [
    { label:'Dashboard', path:'/lister', icon:LayoutDashboard, end:true },
    { label:'Create tender', path:'/lister/create', icon:FilePlus2 },
    { label:'My tenders', path:'/lister/my-tenders', icon:FileText },
    { label:'Profile', path:'/profile', icon:UserRound },
  ];
  function handleLogout() { logout(); navigate('/login', { replace:true }); }
  return <div className="min-h-screen bg-[#f5f6fc] dark:bg-slate-950">
    <div className="fixed inset-x-0 top-0 z-40 flex h-[72px] items-center justify-between border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 sm:px-6 lg:px-8">
      <div className="flex items-center gap-3"><button type="button" onClick={()=>setExpanded(!expanded)} className="rounded-lg p-2 text-slate-600 dark:text-slate-300 lg:hidden" aria-label="Toggle sidebar">{expanded?<X size={20}/>:<Menu size={20}/>}</button><Brand to={prefix}/></div>
      <div className="flex items-center gap-3"><ThemeToggle/><span className="hidden rounded-full bg-[#eef4f4] dark:bg-slate-800 px-3 py-1 text-xs font-bold text-[#285970] dark:text-slate-200 sm:inline-flex">{bidder?'Bidder workspace':'Lister workspace'}</span><span className="grid h-9 w-9 place-items-center rounded-full bg-[#285970] text-xs font-bold text-white">{initials(user.fullName)}</span><div className="hidden min-w-0 sm:block"><p className="max-w-[195px] truncate text-xs font-semibold text-ink dark:text-slate-100">{user.organizationName || user.fullName}</p><p className="text-xs text-slate-500 dark:text-slate-400">{user.role}</p></div></div>
    </div>
    <aside className={`fixed bottom-0 left-0 top-[72px] z-30 w-[244px] border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-5 transition-transform lg:translate-x-0 ${expanded?'translate-x-0':'-translate-x-full'}`}>
      <div className="mb-4 px-3 text-[11px] font-extrabold uppercase tracking-widest text-slate-400 dark:text-slate-500">Workspace</div>
      <nav className="space-y-1">{nav.map(({label,path,icon:Icon,end})=><NavLink key={path} to={path} end={end} onClick={()=>setExpanded(false)} className={({isActive})=>`flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-semibold transition ${isActive?'bg-[#eef4f4] dark:bg-slate-800 text-[#285970] dark:text-slate-200':'text-slate-600 dark:text-slate-300 hover:bg-slate-50 hover:text-[#285970]'}`}><Icon size={18}/>{label}</NavLink>)}</nav>
      <div className="absolute inset-x-3 bottom-6"><button type="button" onClick={handleLogout} className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-red-50 hover:text-red-700"><LogOut size={18}/> Logout</button></div>
    </aside>
    {expanded && <button type="button" aria-label="Close sidebar" className="fixed inset-0 z-20 bg-slate-900/25 lg:hidden" onClick={()=>setExpanded(false)}/>}
    <main className="px-4 pb-12 pt-[96px] sm:px-7 lg:ml-[244px] lg:px-9"><div className="mx-auto max-w-[1170px]">{DEMO_MODE && <div className="mb-3"><DemoNotice compact/></div>}
      {registrationNotice && <div role="status" className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900 dark:bg-slate-900 dark:text-emerald-200">{registrationNotice}</div>}
      {isPending && <div role="status" className="mb-5 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900 dark:bg-slate-900 dark:text-amber-200">
        <AlertCircle size={19} className="mt-0.5 shrink-0" />
        <div><strong>Account awaiting Admin verification.</strong> {bidder ? 'You can view your dashboard and browse published tenders. Admin verification is required before you can submit bids.' : 'You can view your dashboard and manage your profile. Admin verification is required before you can create tenders.'}
          {user.profileMissing && <> Your organization profile is incomplete. <Link className="underline font-semibold" to="/profile">Complete it under My Profile.</Link></>}
          {!DEMO_MODE && !user.profileMissing && <> After Admin approval, sign out and sign in to refresh your account status.</>}
        </div>
      </div>}
      <Outlet /></div></main>
  </div>;
}
