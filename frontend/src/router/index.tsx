import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppLayout } from "@/layouts/AppLayout";
import { AuthLayout } from "@/layouts/AuthLayout";
import { ProtectedRoute } from "@/router/ProtectedRoute";

import LoginPage from "@/pages/auth/Login";
import RegisterPage from "@/pages/auth/Register";
import DashboardPage from "@/pages/dashboard/Dashboard";
import CompaniesListPage from "@/pages/companies/CompaniesList";
import CompanyDetailsPage from "@/pages/companies/CompanyDetails";
import UsersPage from "@/pages/users/UsersPage";
import AuditLogsPage from "@/pages/audit-logs/AuditLogsPage";
import SettingsPage from "@/pages/settings/SettingsPage";
import ForbiddenPage from "@/pages/errors/Forbidden";
import NotFoundPage from "@/pages/errors/NotFound";

export const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/dashboard", element: <DashboardPage /> },
          { path: "/companies", element: <CompaniesListPage /> },
          { path: "/companies/:companyId", element: <CompanyDetailsPage /> },
          { path: "/users", element: <UsersPage /> },
          { path: "/audit-logs", element: <AuditLogsPage /> },
          { path: "/settings", element: <SettingsPage /> },
        ],
      },
    ],
  },
  { path: "/error/403", element: <ForbiddenPage /> },
  { path: "/error/404", element: <NotFoundPage /> },
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  { path: "*", element: <NotFoundPage /> },
]);
