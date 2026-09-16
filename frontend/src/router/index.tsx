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
import DocumentsPage from "@/pages/documents/DocumentsPage";
import AuditLogsPage from "@/pages/audit-logs/AuditLogsPage";
import SettingsPage from "@/pages/settings/SettingsPage";
import ForbiddenPage from "@/pages/errors/Forbidden";
import NotFoundPage from "@/pages/errors/NotFound";

import FinancialYearsPage from "@/pages/accounting/FinancialYearsPage";
import LedgersPage from "@/pages/accounting/LedgersPage";
import CustomersPage from "@/pages/accounting/CustomersPage";
import VendorsPage from "@/pages/accounting/VendorsPage";
import ProductsPage from "@/pages/accounting/ProductsPage";
import SalesInvoicesPage from "@/pages/accounting/SalesInvoicesPage";
import SalesInvoiceFormPage from "@/pages/accounting/SalesInvoiceFormPage";
import SalesInvoiceDetailPage from "@/pages/accounting/SalesInvoiceDetailPage";
import PurchaseInvoicesPage from "@/pages/accounting/PurchaseInvoicesPage";
import PurchaseInvoiceFormPage from "@/pages/accounting/PurchaseInvoiceFormPage";
import PurchaseInvoiceDetailPage from "@/pages/accounting/PurchaseInvoiceDetailPage";
import OtherTransactionsPage from "@/pages/accounting/OtherTransactionsPage";
import ImportsPage from "@/pages/accounting/ImportsPage";
import ImportWizardPage from "@/pages/accounting/ImportWizardPage";
import ImportDetailPage from "@/pages/accounting/ImportDetailPage";
import ReportsPage from "@/pages/accounting/ReportsPage";
import AccountingDashboardPage from "@/pages/accounting/AccountingDashboardPage";

import GstDashboardPage from "@/pages/gst/GstDashboardPage";
import GstReturnPeriodDetailPage from "@/pages/gst/GstReturnPeriodDetailPage";

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
          { path: "/documents", element: <DocumentsPage /> },
          { path: "/audit-logs", element: <AuditLogsPage /> },
          { path: "/settings", element: <SettingsPage /> },
          { path: "/accounting/financial-years", element: <FinancialYearsPage /> },
          { path: "/accounting/ledgers", element: <LedgersPage /> },
          { path: "/accounting/customers", element: <CustomersPage /> },
          { path: "/accounting/vendors", element: <VendorsPage /> },
          { path: "/accounting/products", element: <ProductsPage /> },
          { path: "/accounting/sales-invoices", element: <SalesInvoicesPage /> },
          { path: "/accounting/sales-invoices/new", element: <SalesInvoiceFormPage /> },
          { path: "/accounting/sales-invoices/:invoiceId", element: <SalesInvoiceDetailPage /> },
          { path: "/accounting/purchase-invoices", element: <PurchaseInvoicesPage /> },
          { path: "/accounting/purchase-invoices/new", element: <PurchaseInvoiceFormPage /> },
          { path: "/accounting/purchase-invoices/:invoiceId", element: <PurchaseInvoiceDetailPage /> },
          { path: "/accounting/transactions", element: <OtherTransactionsPage /> },
          { path: "/accounting/imports", element: <ImportsPage /> },
          { path: "/accounting/imports/new", element: <ImportWizardPage /> },
          { path: "/accounting/imports/:jobId", element: <ImportDetailPage /> },
          { path: "/accounting/reports", element: <ReportsPage /> },
          { path: "/accounting/dashboard", element: <AccountingDashboardPage /> },
          { path: "/gst", element: <GstDashboardPage /> },
          { path: "/gst/return-periods/:periodId", element: <GstReturnPeriodDetailPage /> },
        ],
      },
    ],
  },
  { path: "/error/403", element: <ForbiddenPage /> },
  { path: "/error/404", element: <NotFoundPage /> },
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  { path: "*", element: <NotFoundPage /> },
]);
