import { Link } from 'react-router-dom';
import { Blocks } from 'lucide-react';

export default function Brand({ to = '/', compact = false }) {
  return (
    <Link to={to} className="inline-flex items-center gap-2.5 text-[#20243f] dark:text-slate-100" aria-label="TenderBlock home">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#5b4bda] text-white shadow-[0_6px_15px_rgba(91,75,218,.24)]"><Blocks size={19} strokeWidth={2.2} /></span>
      {!compact && <span className="text-xl font-extrabold tracking-tight">Tender<span className="text-[#5b4bda]">Block</span></span>}
    </Link>
  );
}
