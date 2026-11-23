import { lazy, Suspense } from "react";
import { DEMO_MODE } from "./data/constants";
import { Navigate, Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import AccessPage from "./pages/AccessPage";
import RegisterPage from "./pages/RegisterPage";
import LoginPage from "./pages/LoginPage";
import EvaluatorRegisterPage from "./pages/EvaluatorRegisterPage";
import StaffLoginPage from "./pages/StaffLoginPage";
import StaffWorkspacePage from "./pages/StaffWorkspacePage";
import ListerPage, { MyTendersPage } from "./pages/ListerPage";
import CreateTenderPage from "./pages/CreateTenderPage";
import BidderPage, { MyBidsPage } from "./pages/BidderPage";
import BidderDashboardPage from "./pages/BidderDashboardPage";
import ProfilePage from "./pages/ProfilePage";
import EditBidPage from "./pages/EditBidPage";
import EditTenderPage from "./pages/EditTenderPage";
import NotFoundPage from "./pages/NotFoundPage";
import WorkspaceLayout from "./components/WorkspaceLayout";
import RequireRole from "./components/RequireRole";
import { useAuth } from "./context/AuthContext";

const PreviewGallery = DEMO_MODE
  ? lazy(() => import("./preview/PreviewGallery"))
  : null;
const PreviewEntry = DEMO_MODE
  ? lazy(() => import("./preview/PreviewEntry"))
  : null;
const PreviewReturn = DEMO_MODE
  ? lazy(() => import("./preview/PreviewReturn"))
  : null;

function PublicLandingEntry() {
  const { user } = useAuth();
  if (["ADMIN", "EVALUATOR", "AUDITOR"].includes(user?.role)) {
    return <Navigate to="/staff/workspace" replace />;
  }
  if (user?.role === "BIDDER") return <Navigate to="/bidder" replace />;
  if (user?.role === "LISTER") return <Navigate to="/lister" replace />;
  return <LandingPage />;
}

function RootRedirect() {
  const { user } = useAuth();
  return (
    <Navigate
      to={
        !user
          ? "/"
          : user.role === "LISTER"
            ? "/lister"
            : user.role === "BIDDER"
              ? "/bidder"
              : "/staff/workspace"
      }
      replace
    />
  );
}

export default function App() {
  return (
    <>
      <Routes>
        {DEMO_MODE && (
          <>
            <Route
              path="/preview"
              element={
                <Suspense fallback={<p className="p-8">Loading previews…</p>}>
                  <PreviewGallery />
                </Suspense>
              }
            />
            <Route
              path="/preview/:view"
              element={
                <Suspense fallback={<p className="p-8">Opening preview…</p>}>
                  <PreviewEntry />
                </Suspense>
              }
            />
          </>
        )}
        <Route path="/" element={<PublicLandingEntry />} />
        <Route path="/access" element={<AccessPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        {["admin", "evaluator", "auditor"].map((role) => (
          <Route
            key={role}
            path={`/${role}/*`}
            element={<Navigate to="/staff/workspace" replace />}
          />
        ))}
        <Route path="/staff" element={<Navigate to="/staff/login" replace />} />
        <Route
          path="/staff/register/evaluator"
          element={<EvaluatorRegisterPage />}
        />
        <Route path="/staff/login" element={<StaffLoginPage />} />
        <Route
          element={<RequireRole roles={["ADMIN", "EVALUATOR", "AUDITOR"]} />}
        >
          <Route path="/staff/workspace" element={<StaffWorkspacePage />} />
        </Route>
        <Route element={<RequireRole role="LISTER" />}>
          <Route element={<WorkspaceLayout />}>
            <Route path="/lister" element={<ListerPage />} />
            <Route path="/lister/create" element={<CreateTenderPage />} />
            <Route path="/lister/my-tenders" element={<MyTendersPage />} />
            <Route
              path="/lister/tenders/:tenderId/edit"
              element={<EditTenderPage />}
            />
          </Route>
        </Route>
        <Route element={<RequireRole role="BIDDER" />}>
          <Route element={<WorkspaceLayout />}>
            <Route path="/bidder" element={<BidderDashboardPage />} />
            <Route
              path="/bidder/tenders"
              element={<BidderPage title="Browse Tenders" showAllInitially />}
            />
            <Route
              path="/bidder/tenders/:tenderId"
              element={<BidderPage title="Tender Details" />}
            />
            <Route path="/bidder/my-bids" element={<MyBidsPage />} />
            <Route path="/bidder/bids/:bidId/edit" element={<EditBidPage />} />
          </Route>
        </Route>
        <Route element={<RequireRole roles={["BIDDER", "LISTER"]} />}>
          <Route element={<WorkspaceLayout />}>
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
        </Route>
        <Route path="/workspace" element={<RootRedirect />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      {DEMO_MODE && (
        <Suspense fallback={null}>
          <PreviewReturn />
        </Suspense>
      )}
    </>
  );
}
