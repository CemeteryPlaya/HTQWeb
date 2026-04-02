import React from 'react';

export const lazyPages = {
  NotFound: React.lazy(() => import('@/pages/NotFound')),
  RequireAuth: React.lazy(() => import('@/components/RequireAuth')),
  BottomNav: React.lazy(() => import('@/components/BottomNav').then((module) => ({ default: module.BottomNav }))),
  Toaster: React.lazy(() => import('@/components/ui/toaster').then((module) => ({ default: module.Toaster }))),
  Sonner: React.lazy(() => import('@/components/ui/sonner').then((module) => ({ default: module.Toaster }))),

  Projects: React.lazy(() => import('@/pages/Projects')),
  Services: React.lazy(() => import('@/pages/Services')),
  IntegrationDemo: React.lazy(() => import('@/pages/IntegrationDemo')),
  Contacts: React.lazy(() => import('@/pages/Contacts')),
  News: React.lazy(() => import('@/pages/News')),
  NewsDetail: React.lazy(() => import('@/pages/NewsDetail')),
  Login: React.lazy(() => import('@/pages/Login')),
  Register: React.lazy(() => import('@/pages/Register')),
  MyProfile: React.lazy(() => import('@/pages/MyProfile')),
  Messenger: React.lazy(() => import('@/features/messenger/MessengerPage')),

  AdminNews: React.lazy(() => import('@/pages/AdminNews')),
  AdminContacts: React.lazy(() => import('@/pages/AdminContacts')),
  AdminProjects: React.lazy(() => import('@/pages/AdminProjects')),
  AdminUsers: React.lazy(() => import('@/pages/AdminUsers')),
  AdminRegistrations: React.lazy(() => import('@/pages/AdminRegistrations')),
  AdminChats: React.lazy(() => import('@/pages/AdminChats')),

  HREmployees: React.lazy(() => import('@/pages/hr/HREmployees')),
  HRDepartments: React.lazy(() => import('@/pages/hr/HRDepartments')),
  HRTimeTracking: React.lazy(() => import('@/pages/hr/HRTimeTracking')),
  HRRecruitment: React.lazy(() => import('@/pages/hr/HRRecruitment')),
  HRDocuments: React.lazy(() => import('@/pages/hr/HRDocuments')),
  HRLogs: React.lazy(() => import('@/pages/hr/HRLogs')),
  HRProfiles: React.lazy(() => import('@/pages/hr/HRProfiles')),
  HRHistory: React.lazy(() => import('@/pages/hr/HRHistory')),
  HRArchive: React.lazy(() => import('@/pages/hr/HRArchive')),
  HRAccounts: React.lazy(() => import('@/pages/hr/HRAccounts')),
  HRRoadmap: React.lazy(() => import('@/pages/hr/HRRoadmap')),
  HRReports: React.lazy(() => import('@/pages/hr/HRReports')),
  HRCalendar: React.lazy(() => import('@/pages/Calendar')),
  DepartmentFiles: React.lazy(() => import('@/pages/DepartmentFiles')),
  ConferencePage: React.lazy(() => import('@/pages/ConferencePage')),

  TaskRouter: React.lazy(() => import('@/components/tasks/TaskRouter').then((module) => ({ default: module.TaskRouter }))),
  TaskDetailRouter: React.lazy(() => import('@/components/tasks/TaskDetailRouter').then((module) => ({ default: module.TaskDetailRouter }))),

  EmailInbox: React.lazy(() => import('@/pages/Email/EmailInbox')),
  OAuthCallbackPage: React.lazy(() => import('@/pages/Email/OAuthCallbackPage')),
};
