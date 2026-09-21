import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Shell from './Shell';
import { Landing, Overview, Placeholder } from './pages';

const queryClient = new QueryClient();

const router = createBrowserRouter([
  { path: '/welcome', element: <Landing /> },
  {
    path: '/',
    element: <Shell />,
    children: [
      { index: true, element: <Overview /> },
      { path: 'workspace', element: <Overview /> },
      { path: 'login', element: <Placeholder title="Login" /> },
      { path: 'register', element: <Placeholder title="Register" /> },
      { path: 'contracts', element: <Placeholder title="Contracts" /> },
      { path: 'contracts/:id', element: <Placeholder title="Contract detail" /> },
      { path: 'obligations', element: <Placeholder title="Obligations" /> },
      { path: 'deadlines', element: <Placeholder title="Deadlines" /> },
      { path: 'risks', element: <Placeholder title="Risk Radar" /> },
      { path: 'search', element: <Placeholder title="Search" /> },
      { path: 'audit', element: <Placeholder title="Audit Log" /> },
      { path: 'settings', element: <Placeholder title="Settings" /> },
      { path: 'architecture', element: <Placeholder title="Architecture" /> },
    ],
  },
]);

export default function App() {
  return (
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </React.StrictMode>
  );
}
