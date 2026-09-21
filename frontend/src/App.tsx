import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth';
import { Loading } from './components';
import Shell from './Shell';
import Architecture from './pages/Architecture';
import AuditLog from './pages/AuditLog';
import ContractDetail from './pages/ContractDetail';
import Contracts from './pages/Contracts';
import FuturePlaceholder from './pages/FuturePlaceholder';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Obligations from './pages/Obligations';
import Overview from './pages/Overview';
import Register from './pages/Register';
import SearchPage from './pages/SearchPage';
import Settings from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 15_000 } },
});

function Root() {
  const { user, authLoading } = useAuth();
  if (authLoading) return <Loading label="Restoring session…" />;
  if (!user) return <Landing />;
  return <Overview />;
}

function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, authLoading } = useAuth();
  if (authLoading) return <Loading label="Restoring session…" />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

const router = createBrowserRouter([
  { path: '/welcome', element: <Landing /> },
  {
    path: '/',
    element: <Shell />,
    children: [
      { index: true, element: <Root /> },
      { path: 'workspace', element: <Overview /> },
      { path: 'login', element: <GuestOnly><Login /></GuestOnly> },
      { path: 'register', element: <GuestOnly><Register /></GuestOnly> },
      { path: 'contracts', element: <Contracts /> },
      { path: 'contracts/:id', element: <ContractDetail /> },
      { path: 'obligations', element: <Obligations /> },
      { path: 'deadlines', element: <FuturePlaceholder title="Deadlines" /> },
      { path: 'risks', element: <FuturePlaceholder title="Risk Radar" /> },
      { path: 'search', element: <SearchPage /> },
      { path: 'audit', element: <AuditLog /> },
      { path: 'settings', element: <Settings /> },
      { path: 'architecture', element: <Architecture /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);

export default function App() {
  return (
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>
    </React.StrictMode>
  );
}
