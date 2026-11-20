export const ROLES = Object.freeze({ BIDDER: "BIDDER", LISTER: "LISTER" });
export const SECTORS = [
  "Information Technology",
  "Infrastructure",
  "Construction",
  "Healthcare",
  "Education",
  "Manufacturing",
  "Energy",
  "Transport",
  "Office Supplies",
  "Other",
];
export const ORGANIZATION_TYPES = [
  "Private company",
  "Government department",
  "Educational institution",
  "Non-profit",
  "Individual / sole proprietor",
  "Other",
];
export const TEAM = [
  { name: "Srijan Das", id: "", email: "", phone: "" },
  { name: "Karan Kashyap", id: "", email: "", phone: "" },
  { name: "Animesh Singh", id: "", email: "", phone: "" },
  { name: "Khush Bothra", id: "", email: "", phone: "" },
];
// Ordinary dev/build commands always use Spring Boot. Demo data requires both
// the explicitly selected demo mode and its opt-in flag; a stray flag in a
// production environment cannot enable simulated authentication.
export const DEMO_MODE =
  import.meta.env.MODE === "demo" && import.meta.env.VITE_DEMO_MODE === "true";
// Use 'team' when merging feature/tender-system, or 'integration' for the prior custom overlay.
export const BACKEND_CONTRACT = import.meta.env.VITE_BACKEND_CONTRACT || "team";
const configuredApiUrl = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "/api/v1"
).replace(/\/+$/, "");
export const API_BASE_URL =
  /^https?:\/\//i.test(configuredApiUrl) &&
  !/\/api\/v1$/i.test(configuredApiUrl)
    ? `${configuredApiUrl}/api/v1`
    : configuredApiUrl;
