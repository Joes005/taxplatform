import { useNavigate } from "react-router-dom";
import {
  FileText,
  PlusCircle,
  Receipt,
  ShoppingCart,
  Wallet,
  GitMerge,
  Calculator,
  Banknote,
  ClipboardCheck,
  UploadCloud,
  CalendarClock,
  Building2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface RoleQuickActionsProps {
  role?: string;
}

export function RoleQuickActions({ role }: RoleQuickActionsProps) {
  const navigate = useNavigate();

  // All actions with authorized roles
  const allActions = [
    {
      label: "Create Sales Invoice",
      icon: Receipt,
      to: "/accounting/sales-invoices/new",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT"],
      description: "Bill a customer with GST",
    },
    {
      label: "Create Purchase Invoice",
      icon: ShoppingCart,
      to: "/accounting/purchase-invoices/new",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT"],
      description: "Record vendor purchase & ITC",
    },
    {
      label: "Record Payment / Receipt",
      icon: Wallet,
      to: "/accounting/transactions",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT"],
      description: "Post double-entry journal/cash flow",
    },
    {
      label: "Import Accounting Data",
      icon: UploadCloud,
      to: "/accounting/imports/new",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT"],
      description: "Tally XML / Excel ingestion",
    },
    {
      label: "Import Bank Statement",
      icon: FileText,
      to: "/bank/statements",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT"],
      description: "Upload CSV statement for recon",
    },
    {
      label: "Upload Document",
      icon: PlusCircle,
      to: "/documents",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT", "AUDITOR", "VIEWER"],
      description: "OCR & document archive",
    },
    {
      label: "GST Reconciliation",
      icon: GitMerge,
      to: "/gst",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT"],
      description: "Match GSTR-2B vs Purchase",
    },
    {
      label: "Create TDS Challan",
      icon: Calculator,
      to: "/tds/challans",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT"],
      description: "Deposit TDS & allocate lines",
    },
    {
      label: "Income Tax Computation",
      icon: Banknote,
      to: "/income-tax/computations",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT"],
      description: "Compute slab tax & prepare ITR",
    },
    {
      label: "Audit Engagement",
      icon: ClipboardCheck,
      to: "/audits/engagements",
      roles: ["COMPANY_ADMIN", "AUDITOR"],
      description: "Start checklist & findings",
    },
    {
      label: "Compliance Calendar",
      icon: CalendarClock,
      to: "/compliance/calendar",
      roles: ["COMPANY_ADMIN", "ACCOUNTANT", "AUDITOR", "VIEWER"],
      description: "Statutory deadlines & tracking",
    },
    {
      label: "Company Settings",
      icon: Building2,
      to: "/settings",
      roles: ["COMPANY_ADMIN"],
      description: "Organization profiles & users",
    },
  ];

  // Filter actions for current role if role is specified, otherwise fallback to standard subset
  const filtered = role
    ? allActions.filter((a) => a.roles.includes(role))
    : allActions.slice(0, 8);

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Quick Action Hub</CardTitle>
        <CardDescription className="text-xs">
          Role-tailored shortcuts for frequent workflows (Role: {role ?? "Member"})
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {filtered.map((action) => {
            const Icon = action.icon;
            return (
              <Button
                key={action.label}
                variant="outline"
                onClick={() => navigate(action.to)}
                className="h-auto justify-start p-3 text-left hover:border-primary/50 hover:bg-primary/5 transition-all"
              >
                <div className="flex items-start gap-2.5">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-foreground truncate">{action.label}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{action.description}</p>
                  </div>
                </div>
              </Button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
