import { Calculator } from "lucide-react";

import { useGstr3b } from "@/hooks/useGstr3b";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatMoney } from "@/lib/utils";
import { EmptyTableState } from "@/pages/accounting/LedgersPage";

export function Gstr3bSection({ companyId, periodId }: { companyId: string; periodId: string }) {
  const { data, isLoading } = useGstr3b(companyId, periodId);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!data) return <EmptyTableState icon={Calculator} title="Could not prepare GSTR-3B" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <p className="text-sm text-muted-foreground">
          GSTR-3B Preparation — a summary for review, not a filed return.
        </p>
        {(data.error_count > 0 || data.warning_count > 0) && (
          <div className="flex gap-2">
            {data.error_count > 0 && <Badge variant="destructive">{data.error_count} errors</Badge>}
            {data.warning_count > 0 && <Badge variant="warning">{data.warning_count} warnings</Badge>}
          </div>
        )}
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">3.1 Outward Supplies</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {[
            ["Taxable Value", data.outward_supplies.taxable_value],
            ["CGST", data.outward_supplies.cgst_amount],
            ["SGST", data.outward_supplies.sgst_amount],
            ["IGST", data.outward_supplies.igst_amount],
            ["Cess", data.outward_supplies.cess_amount],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className="mt-1 text-base font-semibold">{formatMoney(value)}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">4. Input Tax Credit</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Matched ITC</p>
            <p className="mt-1 text-base font-semibold">{formatMoney(data.input_tax_credit.itc_matched)}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Approved (claimable)</p>
            <p className="mt-1 text-base font-semibold text-success">{formatMoney(data.input_tax_credit.itc_approved)}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Needs Review</p>
            <p className="mt-1 text-base font-semibold text-warning">{formatMoney(data.input_tax_credit.itc_review_required)}</p>
          </div>
        </CardContent>
      </Card>

      <Card className="border-primary/30 bg-primary/5">
        <CardHeader><CardTitle className="text-base">Net Tax Liability</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {[
            ["Output Tax", data.net_liability.output_tax],
            ["Eligible ITC", data.net_liability.eligible_itc],
            ["CGST", data.net_liability.cgst_net],
            ["SGST", data.net_liability.sgst_net],
            ["IGST", data.net_liability.igst_net],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className="mt-1 text-base font-semibold">{formatMoney(value)}</p>
            </div>
          ))}
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Net Liability</p>
            <p className="mt-1 text-xl font-bold">{formatMoney(data.net_liability.net_liability)}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
