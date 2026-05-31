import { Navigate } from "react-router-dom";
import { isAuthenticated, getRole } from "../api";

export default function ProtectedRoute({ children, allowedRole }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (allowedRole && getRole() !== allowedRole) {
    const role = getRole();
    const routes = { ORGANIZER: "/admin", PARTICIPANT: "/participant", MENTOR: "/mentor", JUDGE: "/judge" };
    return <Navigate to={routes[role] || "/login"} replace />;
  }
  return children;
}
