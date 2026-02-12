import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import React, { Component, ErrorInfo, ReactNode, Suspense } from "react";
import Index from "./pages/Index";
import Projects from "./pages/Projects";
import Services from "./pages/Services";
import IntegrationDemo from "./pages/IntegrationDemo";
import NotFound from "./pages/NotFound";
import Contacts from "./pages/Contacts";
import News from "./pages/News";
import NewsDetail from "./pages/NewsDetail";
import AdminNews from "./pages/AdminNews";
import AdminContacts from "./pages/AdminContacts";
import AdminProjects from "./pages/AdminProjects";
import Login from "./pages/Login";
import Register from "./pages/Register";
import MyProfile from "./pages/MyProfile";
import AdminUsers from "./pages/AdminUsers";
import RequireAuth from "./components/RequireAuth";
import HREmployees from "./pages/hr/HREmployees";
import HRDepartments from "./pages/hr/HRDepartments";
import HRPositions from "./pages/hr/HRPositions";
import HRTimeTracking from "./pages/hr/HRTimeTracking";
import HRVacancies from "./pages/hr/HRVacancies";
import HRApplications from "./pages/hr/HRApplications";
import HRDocuments from "./pages/hr/HRDocuments";
import HRLogs from "./pages/hr/HRLogs";

const queryClient = new QueryClient();

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean, error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-red-50 p-4">
          <div className="max-w-md w-full bg-white p-8 rounded-lg shadow-lg border border-red-200">
            <h1 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h1>
            <p className="text-gray-700 mb-4">The application crashed while rendering this page.</p>
            <pre className="bg-gray-100 p-4 rounded text-xs overflow-auto max-h-40 mb-4">
              {this.state.error?.toString()}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="w-full py-2 px-4 bg-red-600 text-white rounded hover:bg-red-700 transition"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <ErrorBoundary>
        <BrowserRouter>
          <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading Application...</div>}>
            <Routes>
              <Route path="/" element={<Index />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/services" element={<Services />} />
              <Route path="/news" element={<News />} />
              <Route path="/news/:slug" element={<NewsDetail />} />
              <Route path="/manage/news" element={<AdminNews />} />
              <Route path="/manage/contacts" element={
                <RequireAuth>
                  <AdminContacts />
                </RequireAuth>
              } />
              <Route path="/manage/projects" element={
                <RequireAuth>
                  <AdminProjects />
                </RequireAuth>
              } />
              <Route path="/contacts" element={<Contacts />} />
              <Route path="/demo" element={<IntegrationDemo />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/myprofile" element={
                <RequireAuth>
                  <MyProfile />
                </RequireAuth>
              } />
              <Route path="/admin/users" element={
                <RequireAuth>
                  <AdminUsers />
                </RequireAuth>
              } />
              {/* HR Routes */}
              <Route path="/hr/employees" element={
                <RequireAuth>
                  <HREmployees />
                </RequireAuth>
              } />
              <Route path="/hr/departments" element={
                <RequireAuth>
                  <HRDepartments />
                </RequireAuth>
              } />
              <Route path="/hr/positions" element={
                <RequireAuth>
                  <HRPositions />
                </RequireAuth>
              } />
              <Route path="/hr/time-tracking" element={
                <RequireAuth>
                  <HRTimeTracking />
                </RequireAuth>
              } />
              <Route path="/hr/vacancies" element={
                <RequireAuth>
                  <HRVacancies />
                </RequireAuth>
              } />
              <Route path="/hr/applications" element={
                <RequireAuth>
                  <HRApplications />
                </RequireAuth>
              } />
              <Route path="/hr/documents" element={
                <RequireAuth>
                  <HRDocuments />
                </RequireAuth>
              } />
              <Route path="/hr/logs" element={
                <RequireAuth>
                  <HRLogs />
                </RequireAuth>
              } />
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ErrorBoundary>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
