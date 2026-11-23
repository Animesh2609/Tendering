import { Link, useLocation } from "react-router-dom";
import { Layers3 } from "lucide-react";
export default function PreviewReturn() {
  const { pathname } = useLocation();
  if (pathname.startsWith("/preview")) return null;
  return (
    <Link className="preview-return" to="/preview">
      <Layers3 size={16} />
      All previews
    </Link>
  );
}
