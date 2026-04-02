import { lazyPages } from './lazyPages';
import type { RouteConfig } from './types';

export const publicRoutes: RouteConfig[] = [
  { path: '/projects', component: lazyPages.Projects },
  { path: '/services', component: lazyPages.Services },
  { path: '/news', component: lazyPages.News },
  { path: '/news/:slug', component: lazyPages.NewsDetail },
  { path: '/contacts', component: lazyPages.Contacts },
  { path: '/demo', component: lazyPages.IntegrationDemo },
  { path: '/login', component: lazyPages.Login },
  { path: '/register', component: lazyPages.Register },
  { path: '/manage/news', component: lazyPages.AdminNews },
];

export const protectedRoutes: RouteConfig[] = [
  { path: '/manage/contacts', component: lazyPages.AdminContacts, requiresAuth: true },
  { path: '/manage/projects', component: lazyPages.AdminProjects, requiresAuth: true },
  { path: '/myprofile', component: lazyPages.MyProfile, requiresAuth: true },
  { path: '/messenger', component: lazyPages.Messenger, requiresAuth: true },
  { path: '/admin/users', component: lazyPages.AdminUsers, requiresAuth: true },
  { path: '/admin/chats', component: lazyPages.AdminChats, requiresAuth: true },
  { path: '/admin/registrations', component: lazyPages.AdminRegistrations, requiresAuth: true },
  { path: '/hr/employees', component: lazyPages.HREmployees, requiresAuth: true },
  { path: '/hr/departments', component: lazyPages.HRDepartments, requiresAuth: true },
  { path: '/hr/time-tracking', component: lazyPages.HRTimeTracking, requiresAuth: true },
  { path: '/hr/recruitment', component: lazyPages.HRRecruitment, requiresAuth: true },
  { path: '/hr/documents', component: lazyPages.HRDocuments, requiresAuth: true },
  { path: '/hr/logs', component: lazyPages.HRLogs, requiresAuth: true },
  { path: '/hr/profiles', component: lazyPages.HRProfiles, requiresAuth: true },
  { path: '/hr/history', component: lazyPages.HRHistory, requiresAuth: true },
  { path: '/hr/archive', component: lazyPages.HRArchive, requiresAuth: true },
  { path: '/hr/accounts', component: lazyPages.HRAccounts, requiresAuth: true },
  { path: '/calendar', component: lazyPages.HRCalendar, requiresAuth: true },
  { path: '/files', component: lazyPages.DepartmentFiles, requiresAuth: true },
  { path: '/conference', component: lazyPages.ConferencePage, requiresAuth: true },
  { path: '/room/:roomId', component: lazyPages.ConferencePage, requiresAuth: true },
  { path: '/tasks', component: lazyPages.TaskRouter, requiresAuth: true },
  { path: '/tasks/:id', component: lazyPages.TaskDetailRouter, requiresAuth: true },
  { path: '/tasks/roadmap', component: lazyPages.HRRoadmap, requiresAuth: true },
  { path: '/tasks/reports', component: lazyPages.HRReports, requiresAuth: true },
  { path: '/email', component: lazyPages.EmailInbox, requiresAuth: true },
  { path: '/email/oauth/callback', component: lazyPages.OAuthCallbackPage, requiresAuth: true },
];
