import type { ComponentType, LazyExoticComponent } from 'react';

export type LazyPage = LazyExoticComponent<ComponentType>;

export interface RouteConfig {
  path: string;
  component: LazyPage;
  requiresAuth?: boolean;
}
