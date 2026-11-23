import { Link } from "react-router-dom";
import { Layers3 } from "lucide-react";
export default function Brand({ to = "/", compact = false }) {
  return (
    <Link to={to} className="studio-brand brand" aria-label="TenderBlock home">
      <span className="studio-brand-mark brand-mark">
        <Layers3 size={22} strokeWidth={1.7} />
      </span>
      {!compact && (
        <span className="studio-brand-word brand-word">
          Tender<span>Block</span>
          <small>PROCUREMENT, CONNECTED.</small>
        </span>
      )}
    </Link>
  );
}
