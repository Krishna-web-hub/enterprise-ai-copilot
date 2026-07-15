import { useState, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import SplashLoader from './components/SplashLoader';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import DatasetsPage from './pages/DatasetsPage';
import DatasetDashboardPage from './pages/DatasetDashboardPage';
import AskDataPage from './pages/AskDataPage';
import DocumentsPage from './pages/DocumentsPage';
import ModelsPage from './pages/ModelsPage';
import ReportsPage from './pages/ReportsPage';
import Layout from './components/Layout';

/**
 * ProtectedRoute - Redirects to login if user is not authenticated.
 * Shows a loading screen while checking auth status.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-robot-dark">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="h-10 w-10 animate-spin rounded-full border-2 border-neon-blue border-t-transparent" />
            <div className="absolute inset-0 rounded-full border border-cyber-400/20 animate-pulse-ring" />
          </div>
          <p className="font-mono text-[10px] text-gray-500 uppercase tracking-wider">Verifying access...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function App() {
  const { isAuthenticated, isLoading } = useAuth();
  const [showSplash, setShowSplash] = useState(() => {
    // Only show splash once per browser session
    const hasSeenSplash = sessionStorage.getItem('splash_shown');
    return !hasSeenSplash;
  });

  const handleSplashComplete = useCallback(() => {
    setShowSplash(false);
    sessionStorage.setItem('splash_shown', 'true');
  }, []);

  // Show splash loader on first visit
  if (showSplash) {
    return <SplashLoader onComplete={handleSplashComplete} />;
  }

  return (
    <Routes>
      {/* Public landing page - root */}
      <Route
        path="/"
        element={
          !isLoading && isAuthenticated
            ? <Navigate to="/app" replace />
            : <LandingPage />
        }
      />

      {/* Auth pages */}
      <Route
        path="/login"
        element={!isLoading && isAuthenticated ? <Navigate to="/app" replace /> : <LoginPage />}
      />
      <Route
        path="/register"
        element={!isLoading && isAuthenticated ? <Navigate to="/app" replace /> : <RegisterPage />}
      />

      {/* Protected app routes - all under /app */}
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="datasets" element={<DatasetsPage />} />
        <Route path="datasets/:id/dashboard" element={<DatasetDashboardPage />} />
        <Route path="ask-data" element={<AskDataPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="models" element={<ModelsPage />} />
        <Route path="reports" element={<ReportsPage />} />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
