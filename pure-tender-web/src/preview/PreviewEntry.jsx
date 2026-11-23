import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { PREVIEW_PAGES } from "./catalog";
import { ensurePreviewFixtures } from "./fixtures";
import { DEMO_PASSWORD } from "../api/demoStore";
export default function PreviewEntry() {
  const { view } = useParams();
  const navigate = useNavigate();
  const { login, staffLogin, logout } = useAuth();
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const page = PREVIEW_PAGES.find((p) => p.id === view);
    if (!page) {
      setError("This preview does not exist.");
      return;
    }
    async function open() {
      try {
        ensurePreviewFixtures();
        if (page.role === "public") logout();
        else {
          const signIn = ["bidder", "lister"].includes(page.role)
            ? login
            : staffLogin;
          await signIn({
            email: `${page.role}@demo.test`,
            password: DEMO_PASSWORD,
          });
        }
        if (active) navigate(page.path, { replace: true });
      } catch (e) {
        if (active) setError(e.message);
      }
    }
    void open();
    return () => {
      active = false;
    }; // One navigation per selected preview, not on session changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);
  return (
    <main className="preview-page">
      <h1 className="text-2xl">
        {error ? "Unable to open preview" : "Opening your preview…"}
      </h1>
      {error && (
        <p role="alert" className="my-4">
          {error}
        </p>
      )}
      <Link className="tb-link" to="/preview">
        Back to all previews
      </Link>
    </main>
  );
}
