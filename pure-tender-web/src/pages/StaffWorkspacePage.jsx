import { lazy, Suspense } from "react";
import { useAuth } from "../context/AuthContext";
import { DEMO_MODE } from "../data/constants";

const EvaluatorWorkspace = lazy(
  () => import("../modules/evaluator/pages/WorkspacePage"),
);
const OperationsWorkspace = lazy(
  () => import("../modules/operations/pages/OperationsWorkspacePage"),
);

export default function StaffWorkspacePage() {
  const { user, logout } = useAuth();
  const evaluator = user.role === "EVALUATOR";
  if (user.accountStatus && user.accountStatus !== "VERIFIED") {
    return (
      <main className="mx-auto max-w-xl p-8">
        <h1 className="text-2xl font-bold">Account verification required</h1>
        <p className="my-4">
          Your account status is {user.accountStatus}. An Admin must verify your
          account before staff actions are available. Sign in again after
          approval to refresh your status.
        </p>
        <button className="tb-btn-primary" onClick={logout}>
          Sign out
        </button>
      </main>
    );
  }
  return (
    <div className={evaluator ? "evaluator-portal" : "operations-portal"}>
      {DEMO_MODE && (
        <div className="studio-demo-banner" role="status">
          Demo mode · Changes are stored in this browser only.
        </div>
      )}
      <Suspense
        fallback={
          <p className="p-8" role="status">
            Loading your workspace…
          </p>
        }
      >
        {evaluator ? <EvaluatorWorkspace /> : <OperationsWorkspace />}
      </Suspense>
    </div>
  );
}
