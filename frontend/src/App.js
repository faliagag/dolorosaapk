import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Toaster } from "sonner";
import "@/App.css";
import { AuthProvider, useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import InstallPrompt from "@/components/InstallPrompt";
import LoginPage from "@/pages/LoginPage";
import Dashboard from "@/pages/Dashboard";
import CarreteDetail from "@/pages/CarreteDetail";
import ProfilePage from "@/pages/ProfilePage";
import PublicPayPage from "@/pages/PublicPayPage";

function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = React.useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;
    const hash = window.location.hash;
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) {
      navigate("/login");
      return;
    }
    const session_id = match[1];
    (async () => {
      try {
        const res = await api.post("/auth/session", { session_id });
        setUser(res.data);
        window.history.replaceState({}, document.title, "/dashboard");
        navigate("/dashboard", { replace: true, state: { user: res.data } });
      } catch (e) {
        navigate("/login");
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-neon-grid">
      <div className="text-white font-display text-xl pulse-neon p-8 rounded-2xl glass">
        Entrando al carrete...
      </div>
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neon-grid">
        <div className="text-white font-display pulse-neon">Cargando...</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/carretes/:id"
        element={
          <ProtectedRoute>
            <CarreteDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route path="/pay/:shareId/:participantId" element={<PublicPayPage />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function AppContent() {
  return (
    <>
      <AppRouter />
      <InstallPrompt />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="App">
          <Toaster position="top-center" theme="dark" richColors />
          <AppContent />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
