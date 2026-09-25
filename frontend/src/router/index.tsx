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
import ActionCenterPage from "@/pages/action-center/ActionCenterPage";
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

import TdsDashboardPage from "@/pages/tds/TdsDashboardPage";
import DeducteesPage from "@/pages/tds/DeducteesPage";
import TdsTransactionsPage from "@/pages/tds/TdsTransactionsPage";
import TdsChallansPage from "@/pages/tds/TdsChallansPage";
import TdsReturnPeriodDetailPage from "@/pages/tds/TdsReturnPeriodDetailPage";

import BankDashboardPage from "@/pages/bank/BankDashboardPage";
import BankAccountsPage from "@/pages/bank/BankAccountsPage";
import BankStatementsPage from "@/pages/bank/BankStatementsPage";
import BankTransactionsPage from "@/pages/bank/BankTransactionsPage";
import BankReconciliationsPage from "@/pages/bank/BankReconciliationsPage";
import BankReconciliationDetailPage from "@/pages/bank/BankReconciliationDetailPage";

import AuditDashboardPage from "@/pages/audit/AuditDashboardPage";
import AuditEngagementsPage from "@/pages/audit/AuditEngagementsPage";
import AuditEngagementDetailPage from "@/pages/audit/AuditEngagementDetailPage";
import AuditFindingDetailPage from "@/pages/audit/AuditFindingDetailPage";

import IncomeTaxDashboardPage from "@/pages/income-tax/IncomeTaxDashboardPage";
import IncomeTaxProfilePage from "@/pages/income-tax/IncomeTaxProfilePage";
import IncomeTaxIncomePage from "@/pages/income-tax/IncomeTaxIncomePage";
import CapitalGainsPage from "@/pages/income-tax/CapitalGainsPage";
import DeductionsPage from "@/pages/income-tax/DeductionsPage";
import TaxPaymentsPage from "@/pages/income-tax/TaxPaymentsPage";
import TaxComputationsPage from "@/pages/income-tax/TaxComputationsPage";
import TaxComputationDetailPage from "@/pages/income-tax/TaxComputationDetailPage";

import ComplianceDashboardPage from "@/pages/compliance/ComplianceDashboardPage";
import ComplianceCalendarPage from "@/pages/compliance/ComplianceCalendarPage";
import ComplianceTasksPage from "@/pages/compliance/ComplianceTasksPage";
import ComplianceTaskDetailPage from "@/pages/compliance/ComplianceTaskDetailPage";
import ComplianceObligationsPage from "@/pages/compliance/ComplianceObligationsPage";
import NotificationsPage from "@/pages/compliance/NotificationsPage";
import OpeningBalancesPage from "@/pages/accounting/OpeningBalancesPage";

import ReportCenterPage from "@/pages/reports/ReportCenterPage";
import ManagementDashboardPage from "@/pages/reports/ManagementDashboardPage";
import FinancialReportsPage from "@/pages/reports/FinancialReportsPage";
import GeneralLedgerPage from "@/pages/reports/GeneralLedgerPage";
import TaxComplianceReportsPage from "@/pages/reports/TaxComplianceReportsPage";
import BankingReportsPage from "@/pages/reports/BankingReportsPage";

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
          { path: "/action-center", element: <ActionCenterPage /> },
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
          { path: "/accounting/opening-balances", element: <OpeningBalancesPage /> },
          { path: "/accounting/imports", element: <ImportsPage /> },
          { path: "/accounting/imports/new", element: <ImportWizardPage /> },
          { path: "/accounting/imports/:jobId", element: <ImportDetailPage /> },
          { path: "/accounting/reports", element: <ReportsPage /> },
          { path: "/accounting/dashboard", element: <AccountingDashboardPage /> },
          { path: "/gst", element: <GstDashboardPage /> },
          { path: "/gst/return-periods/:periodId", element: <GstReturnPeriodDetailPage /> },
          { path: "/tds", element: <TdsDashboardPage /> },
          { path: "/tds/deductees", element: <DeducteesPage /> },
          { path: "/tds/transactions", element: <TdsTransactionsPage /> },
          { path: "/tds/challans", element: <TdsChallansPage /> },
          { path: "/tds/return-periods/:periodId", element: <TdsReturnPeriodDetailPage /> },
          { path: "/bank", element: <BankDashboardPage /> },
          { path: "/bank/accounts", element: <BankAccountsPage /> },
          { path: "/bank/statements", element: <BankStatementsPage /> },
          { path: "/bank/transactions", element: <BankTransactionsPage /> },
          { path: "/bank/reconciliations", element: <BankReconciliationsPage /> },
          { path: "/bank/reconciliations/:reconciliationId", element: <BankReconciliationDetailPage /> },
          { path: "/audits", element: <AuditDashboardPage /> },
          { path: "/audits/engagements", element: <AuditEngagementsPage /> },
          { path: "/audits/engagements/:engagementId", element: <AuditEngagementDetailPage /> },
          { path: "/audits/findings/:findingId", element: <AuditFindingDetailPage /> },
          { path: "/income-tax", element: <IncomeTaxDashboardPage /> },
          { path: "/income-tax/profile", element: <IncomeTaxProfilePage /> },
          { path: "/income-tax/income", element: <IncomeTaxIncomePage /> },
          { path: "/income-tax/capital-gains", element: <CapitalGainsPage /> },
          { path: "/income-tax/deductions", element: <DeductionsPage /> },
          { path: "/income-tax/payments", element: <TaxPaymentsPage /> },
          { path: "/income-tax/computations", element: <TaxComputationsPage /> },
          { path: "/income-tax/computations/:computationId", element: <TaxComputationDetailPage /> },
          { path: "/compliance", element: <ComplianceDashboardPage /> },
          { path: "/compliance/calendar", element: <ComplianceCalendarPage /> },
          { path: "/compliance/tasks", element: <ComplianceTasksPage /> },
          { path: "/compliance/tasks/:taskId", element: <ComplianceTaskDetailPage /> },
          { path: "/compliance/obligations", element: <ComplianceObligationsPage /> },
          { path: "/notifications", element: <NotificationsPage /> },
          { path: "/reports", element: <ReportCenterPage /> },
          { path: "/reports/management", element: <ManagementDashboardPage /> },
          { path: "/reports/financial", element: <FinancialReportsPage /> },
          { path: "/reports/general-ledger", element: <GeneralLedgerPage /> },
          { path: "/reports/tax", element: <TaxComplianceReportsPage /> },
          { path: "/reports/banking", element: <BankingReportsPage /> },
          { path: "/reports/audit", element: <TaxComplianceReportsPage /> },
          { path: "/reports/compliance", element: <TaxComplianceReportsPage /> },
        ],
      },
    ],
  },
  { path: "/error/403", element: <ForbiddenPage /> },
  { path: "/error/404", element: <NotFoundPage /> },
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  { path: "*", element: <NotFoundPage /> },
]);
