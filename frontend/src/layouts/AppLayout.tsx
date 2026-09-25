import { useState, useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  BarChart3,
  Building2,
  CalendarRange,
  ClipboardCheck,
  FileText,
  Gauge,
  LayoutDashboard,
  LogOut,
  Receipt,
  ScrollText,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Users,
  UsersRound,
  Landmark,
  Layers,
  Package,
  Truck,
  UploadCloud,
  Wallet,
  UserRound,
  GitMerge,
  Banknote,
  CalendarClock,
  Bell,
  Scale,
  Search,
  ShieldAlert,
} from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { cn, initials } from "@/lib/utils";
import { CompanySwitcher } from "@/components/CompanySwitcher";
import { NotificationBell } from "@/components/NotificationBell";
import { GlobalSearchDialog } from "@/components/GlobalSearchDialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/action-center", label: "Action Center", icon: ShieldAlert },
  { to: "/reports", label: "Report Center", icon: BarChart3 },
  { to: "/companies", label: "Companies", icon: Building2 },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/users", label: "Users", icon: Users },
  { to: "/audit-logs", label: "Audit Logs", icon: ScrollText },
  { to: "/settings", label: "Settings", icon: Settings },
];

const ACCOUNTING_NAV_ITEMS = [
  { to: "/accounting/dashboard", label: "Dashboard", icon: Gauge },
  { to: "/accounting/financial-years", label: "Financial Years", icon: CalendarRange },
  { to: "/accounting/ledgers", label: "Ledgers", icon: Layers },
  { to: "/accounting/opening-balances", label: "Opening Balances", icon: Scale },
  { to: "/accounting/customers", label: "Customers", icon: UsersRound },
  { to: "/accounting/vendors", label: "Vendors", icon: Truck },
  { to: "/accounting/products", label: "Products", icon: Package },
  { to: "/accounting/sales-invoices", label: "Sales Invoices", icon: Receipt },
  { to: "/accounting/purchase-invoices", label: "Purchase Invoices", icon: ShoppingCart },
  { to: "/accounting/transactions", label: "Payments & Journals", icon: Wallet },
  { to: "/accounting/imports", label: "Imports", icon: UploadCloud },
  { to: "/accounting/reports", label: "Reports", icon: BarChart3 },
];

const GST_NAV_ITEMS = [
  { to: "/gst", label: "GST", icon: ShieldCheck },
];

const TDS_NAV_ITEMS = [
  { to: "/tds", label: "Dashboard", icon: Landmark },
  { to: "/tds/deductees", label: "Deductees", icon: UserRound },
  { to: "/tds/transactions", label: "Transactions", icon: Receipt },
  { to: "/tds/challans", label: "Challans", icon: Wallet },
];

const BANK_NAV_ITEMS = [
  { to: "/bank", label: "Dashboard", icon: Landmark },
  { to: "/bank/accounts", label: "Bank Accounts", icon: Landmark },
  { to: "/bank/statements", label: "Statements", icon: ScrollText },
  { to: "/bank/transactions", label: "Transactions", icon: Receipt },
  { to: "/bank/reconciliations", label: "Reconciliation", icon: GitMerge },
];

const AUDIT_NAV_ITEMS = [
  { to: "/audits", label: "Dashboard", icon: ClipboardCheck },
  { to: "/audits/engagements", label: "Engagements", icon: ClipboardCheck },
];

const INCOME_TAX_NAV_ITEMS = [
  { to: "/income-tax", label: "Dashboard", icon: Banknote },
  { to: "/income-tax/profile", label: "Tax Profile", icon: Banknote },
  { to: "/income-tax/income", label: "Income", icon: Wallet },
  { to: "/income-tax/capital-gains", label: "Capital Gains", icon: Receipt },
  { to: "/income-tax/deductions", label: "Deductions", icon: Layers },
  { to: "/income-tax/payments", label: "Tax Payments", icon: Wallet },
  { to: "/income-tax/computations", label: "Computations", icon: Receipt },
];

const COMPLIANCE_NAV_ITEMS = [
  { to: "/compliance", label: "Dashboard", icon: CalendarClock },
  { to: "/compliance/calendar", label: "Calendar", icon: CalendarClock },
  { to: "/compliance/tasks", label: "Tasks", icon: CalendarClock },
  { to: "/compliance/obligations", label: "Obligations & Rules", icon: ShieldCheck },
  { to: "/notifications", label: "Notifications", icon: Bell },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setSearchOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-white">
        <div className="flex h-14 items-center gap-2 border-b border-border px-5">
          <Landmark className="h-5 w-5 text-primary" />
          <span className="text-sm font-semibold tracking-tight">TaxCompliance</span>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}

          <p className="px-3 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Accounting
          </p>
          {ACCOUNTING_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}

          <p className="px-3 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            GST Compliance
          </p>
          {GST_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}

          <p className="px-3 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            TDS Compliance
          </p>
          {TDS_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}

          <p className="px-3 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Bank Reconciliation
          </p>
          {BANK_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/bank"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
          <p className="px-3 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Audit Workflow
          </p>
          {AUDIT_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/audits"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}

          <p className="px-3 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Income Tax
          </p>
          {INCOME_TAX_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/income-tax"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
          <p className="px-3 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Compliance
          </p>
          {COMPLIANCE_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/compliance"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-border p-3 text-xs text-muted-foreground">
          Phase 10 · Business Workflow &amp; UX Intelligence
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-white px-6">
          <div className="flex items-center gap-4">
            <CompanySwitcher />
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="hidden md:flex items-center gap-2 rounded-md border border-input bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <Search className="h-3.5 w-3.5" />
              <span>Search company records...</span>
              <kbd className="pointer-events-none inline-flex h-4 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
                <span className="text-xs">⌘</span>K
              </kbd>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="flex md:hidden p-2 rounded-md hover:bg-accent text-muted-foreground"
              title="Search records"
            >
              <Search className="h-4 w-4" />
            </button>
            <NotificationBell />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                    {user ? initials(user.first_name, user.last_name) : ""}
                  </span>
                  <span className="hidden sm:inline">{user?.first_name} {user?.last_name}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col">
                    <span className="font-medium">{user?.first_name} {user?.last_name}</span>
                    <span className="text-xs font-normal text-muted-foreground">{user?.email}</span>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => logout()} className="text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>

      <GlobalSearchDialog open={searchOpen} onOpenChange={setSearchOpen} />
    </div>
  );
}
