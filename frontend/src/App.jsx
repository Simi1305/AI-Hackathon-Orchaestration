import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import OrganizerDashboard from "./pages/organizer/Dashboard";
import ParticipantDashboard from "./pages/participant/Dashboard";
import MentorDashboard from "./pages/mentor/Dashboard";
import JudgeDashboard from "./pages/judge/Dashboard";

function RootRoute() {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  
  const routes = {
    ORGANIZER: "/admin",
    PARTICIPANT: "/participant",
    MENTOR: "/mentor",
    JUDGE: "/judge"
  };
  return <Navigate to={routes[user?.role] || "/login"} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route path="/admin" element={
            <ProtectedRoute allowedRole="ORGANIZER">
              <OrganizerDashboard />
            </ProtectedRoute>
          } />
          
          <Route path="/participant" element={
            <ProtectedRoute allowedRole="PARTICIPANT">
              <ParticipantDashboard />
            </ProtectedRoute>
          } />
          
          <Route path="/mentor" element={
            <ProtectedRoute allowedRole="MENTOR">
              <MentorDashboard />
            </ProtectedRoute>
          } />
          
          <Route path="/judge" element={
            <ProtectedRoute allowedRole="JUDGE">
              <JudgeDashboard />
            </ProtectedRoute>
          } />
          
          <Route path="/" element={<RootRoute />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
