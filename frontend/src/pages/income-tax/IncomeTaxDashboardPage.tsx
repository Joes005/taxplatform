import { useState } from "react";
import { Link } from "react-router-dom";
import { Landmark, Receipt } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useIncomeTaxProfile } from "@/hooks/useIncomeTaxProfile";
import { useTaxComputations } from "@/hooks/useTaxComputations";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { TaxComputationStatus } from "@/types/incomeTax";

const STATUS_VARIANT: Record<TaxComputationStatus, "secondary" | "warning" | "success" | "outline"> = {
  DRAFT: "outline",
  CALCULATED: "secondary",
  REVIEW_REQUIRED: "warning",
  READY_FOR_REVIEW: "warning",
  APPROVED: "success",
  LOCKED: "success",
  CANCELLED: "outline",
};

export default function IncomeTaxDashboardPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={Landmark} />;
  const companyId = activeCompany.company_id;

  const { data: financialYears } = useFinancialYears(companyId);
  const { data: profile } = useIncomeTaxProfile(companyId);
  const { data: computations, isLoading } = useTaxComputations(companyId);
  const [fyFilter, setFyFilter] = useState<string>("all");

  const currentFy = financialYears?.items.find((fy) => fy.is_current);

  const filtered = (computations?.items ?? []).filter(
    (c) => fyFilter === "all" || c.financial_year_id === fyFilter
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Income Tax</h1>
          <p className="text-sm text-muted-foreground">
            Internal Income Tax preparation and computation — not a government filing system.
          </p>
        </div>
        {!profile && (
          <Link to="/income-tax/profile" className="text-sm font-medium text-primary hover:underline">
            Set up Income Tax profile →
          </Link>
        )}
      </div>

      {profile && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">PAN</p>
              <p className="mt-1 text-lg font-semibold">{profile.pan}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Taxpayer Type</p>
              <p className="mt-1 text-lg font-semibold">{profile.taxpayer_type}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Current FY</p>
              <p className="mt-1 text-lg font-semibold">{currentFy?.name ?? "—"}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Computations</p>
              <p className="mt-1 text-lg font-semibold">{computations?.pagination.total ?? 0}</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <Receipt className="h-4 w-4" /> Tax Computations
            </h2>
            <div className="flex items-center gap-2">
              <Select value={fyFilter} onValueChange={setFyFilter}>
                <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All years</SelectItem>
                  {(financialYears?.items ?? []).map((fy) => (
                    <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Link to="/income-tax/computations" className="text-xs font-medium text-primary hover:underline">
                View all
              </Link>
            </div>
          </div>
          {isLoading ? (
            <div className="p-6"><Skeleton className="h-10 w-full" /></div>
          ) : filtered.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Assessment Year</TableHead>
                  <TableHead>Regime</TableHead>
                  <TableHead className="text-right">Taxable Income</TableHead>
                  <TableHead className="text-right">Gross Tax Liability</TableHead>
                  <TableHead className="text-right">Balance</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <Link to={`/income-tax/computations/${c.id}`} className="font-medium text-primary hover:underline">
                        AY {c.assessment_year}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{c.tax_regime.replaceAll("_", " ")}</TableCell>
                    <TableCell className="text-right">{formatMoney(c.taxable_income)}</TableCell>
                    <TableCell className="text-right">{formatMoney(c.gross_tax_liability)}</TableCell>
                    <TableCell className="text-right">{formatMoney(c.balance_payable_or_refund)}</TableCell>
                    <TableCell><Badge variant={STATUS_VARIANT[c.status]}>{c.status.replaceAll("_", " ")}</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyTableState icon={Receipt} title="No tax computations yet" hint="Create one from the Computations page." />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
