import { Suspense, type ReactNode, useEffect, useState } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Index from '@/pages/Index';

import { AppErrorBoundary } from '@/app/components/AppErrorBoundary';
import { PageLoader } from '@/app/components/PageLoader';
import { lazyPages } from '@/app/routing/lazyPages';
import { registerRoutePrefetch } from '@/app/routing/prefetch';
import { protectedRoutes, publicRoutes } from '@/app/routing/routeDefinitions';
import type { RouteConfig } from '@/app/routing/types';
import { getAccessToken } from '@/lib/auth/profileStorage';
import { ConferenceNotifier } from '@/components/ConferenceNotifier';

registerRoutePrefetch();

const queryClient = new QueryClient();
const DeferredToaster = lazyPages.Toaster;
const DeferredSonner = lazyPages.Sonner;

const SuspensePage = ({ children }: { children: ReactNode }) => (
  <Suspense fallback={<PageLoader />}>{children}</Suspense>
);

const RouteElement = ({ route }: { route: RouteConfig }) => {
  const Component = route.component;
  const content = <Component />;

  if (!route.requiresAuth) {
    return <SuspensePage>{content}</SuspensePage>;
  }

  const RequireAuth = lazyPages.RequireAuth;
  return (
    <SuspensePage>
      <RequireAuth>{content}</RequireAuth>
    </SuspensePage>
  );
};

const AppRoutes = () => (
  <Routes>
    <Route path="/" element={<Index />} />

    {publicRoutes.map((route) => (
      <Route key={route.path} path={route.path} element={<RouteElement route={route} />} />
    ))}

    {protectedRoutes.map((route) => (
      <Route key={route.path} path={route.path} element={<RouteElement route={route} />} />
    ))}

    <Route path="*" element={<SuspensePage><lazyPages.NotFound /></SuspensePage>} />
  </Routes>
);

const App = () => {
  const hasAccessToken = Boolean(getAccessToken());
  const BottomNav = lazyPages.BottomNav;
  const [showDeferredUi, setShowDeferredUi] = useState(false);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setShowDeferredUi(true);
    }, 1500);

    return () => window.clearTimeout(timeoutId);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {showDeferredUi && (
        <Suspense fallback={null}>
          <DeferredToaster />
          <DeferredSonner />
        </Suspense>
      )}
      <AppErrorBoundary>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AppRoutes />
          {hasAccessToken && (
            <Suspense fallback={null}>
              <BottomNav />
              <ConferenceNotifier />
            </Suspense>
          )}
        </BrowserRouter>
      </AppErrorBoundary>
    </QueryClientProvider>
  );
};

export default App;
