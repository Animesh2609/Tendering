import { Link } from "react-router-dom";
import { ShieldCheck, Layers3, FileCheck2 } from "lucide-react";
import PublicHeader from "./PublicHeader";
import DemoNotice from "./DemoNotice";
export default function AuthLayout({
  title,
  subtitle,
  children,
  narrow = false,
}) {
  return (
    <>
      <PublicHeader />
      <main className={`studio-auth ${narrow ? "studio-auth-narrow" : ""}`}>
        <div className="studio-auth-intro">
          <span className="studio-eyebrow-pill">
            <Layers3 size={15} /> YOUR PLACE IN THE PROCESS
          </span>
          <h1>{title}</h1>
          <p>{subtitle}</p>
          <div className="studio-auth-assurance">
            <span>
              <ShieldCheck size={17} /> A workspace for your role
            </span>
            <span>
              <FileCheck2 size={17} /> Every submission in one place
            </span>
          </div>
        </div>
        <div className="studio-auth-form">
          <div className="tb-card p-6 sm:p-8">{children}</div>
          <div className="studio-auth-footer">
            <DemoNotice compact />
            <Link className="tb-link" to="/">
              Back to home
            </Link>
          </div>
        </div>
      </main>
    </>
  );
}
