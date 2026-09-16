import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ShieldCheck } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useGstReturnPeriod } from "@/hooks/useGstReturnPeriods";
import { useGstr1Overview } from "@/hooks/useGstr1";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState } from "@/pages/accounting/LedgersPage";
import { Gstr1Section } from "@/pages/gst/Gstr1Section";
import { Gstr2bSection } from "@/pages/gst/Gstr2bSection";
import { Gstr3bSection } from "@/pages/gst/Gstr3bSection";
import { ItcSection } from "@/pages/gst/ItcSection";
import { ReconciliationSection } from "@/pages/gst/ReconciliationSection";
import type { GSTReturnPeriodStatus } from "@/types/gst";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const PERIOD_STATUS_VARIANT: Record<GSTReturnPeriodStatus, "secondary" | "warning" | "success" | "outline"> = {
  OPEN: "secondary",
  UNDER_REVIEW: "warning",
  FINALIZED: "success",
  ARCHIVED: "outline",
};

export default function GstReturnPeriodDetailPage() {
  const { periodId } = useParams<{ periodId: string }>();
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={ShieldCheck} />;

  const companyId = activeCompany.company_id;
  const { data: period, isLoading } = useGstReturnPeriod(companyId, periodId);

  if (isLoading || !period || !periodId) {
    return <Skeleton className="h-64 w-full" />;
  }

  return (
    <div className="space-y-6">
      <Link to="/gst" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to GST
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {MONTH_NAMES[period.month - 1]} {period.year}
          </h1>
          <p className="text-sm text-muted-foreground">{period.period_start} to {period.period_end}</p>
        </div>
        <Badge variant={PERIOD_STATUS_VARIANT[period.status]} className="text-sm">{period.status}</Badge>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="gstr1">GSTR-1</TabsTrigger>
          <TabsTrigger value="gstr2b">GSTR-2B</TabsTrigger>
          <TabsTrigger value="reconciliation">Reconciliation</TabsTrigger>
          <TabsTrigger value="itc">ITC</TabsTrigger>
          <TabsTrigger value="gstr3b">GSTR-3B</TabsTrigger>
        </TabsList>

        <TabsContent value="overview"><OverviewTab companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="gstr1"><Gstr1Section companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="gstr2b"><Gstr2bSection companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="reconciliation"><ReconciliationSection companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="itc"><ItcSection companyId={companyId} periodId={periodId} /></TabsContent>
        <TabsContent value="gstr3b"><Gstr3bSection companyId={companyId} periodId={periodId} /></TabsContent>
      </Tabs>
    </div>
  );
}

function OverviewTab({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr1Overview(companyId, periodId);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data) return null;

  const cards: [string, string | number][] = [
    ["B2B Invoices", data.b2b_invoice_count],
    ["B2C Invoices", data.b2c_large_invoice_count + data.b2c_others_invoice_count],
    ["Credit Notes", data.credit_note_count],
    ["Debit Notes", data.debit_note_count],
    ["Taxable Value", formatMoney(data.taxable_value)],
    ["CGST", formatMoney(data.cgst_amount)],
    ["SGST", formatMoney(data.sgst_amount)],
    ["IGST", formatMoney(data.igst_amount)],
    ["Errors", data.error_count],
    ["Warnings", data.warning_count],
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {cards.map(([label, value]) => (
        <Card key={label}>
          <CardContent className="pt-6">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className="mt-1 text-lg font-semibold">{value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
