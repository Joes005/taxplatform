import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CalendarRange, Landmark, Plus, Receipt } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useCreateTdsProfile, useTdsProfile } from "@/hooks/useTdsProfile";
import { useCreateTdsReturnPeriod, useTdsReturnPeriods } from "@/hooks/useTdsReturnPeriods";
import { useTdsPayableSummary } from "@/hooks/useTdsTransactions";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/lib/api-client";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { DeductorType, TDSQuarter, TDSReturnPeriodStatus } from "@/types/tds";

const PERIOD_STATUS_VARIANT: Record<TDSReturnPeriodStatus, "secondary" | "warning" | "success" | "outline"> = {
  OPEN: "secondary",
  UNDER_REVIEW: "warning",
  APPROVED: "warning",
  FINALIZED: "success",
  ARCHIVED: "outline",
};

export default function TdsDashboardPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={Landmark} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">TDS Compliance</h1>
        <p className="text-sm text-muted-foreground">
          TDS applicability, calculation, challan tracking, and quarterly return preparation — a local
          preparation workspace for your CA/auditor, not a TRACES/Income Tax portal filing tool.
        </p>
      </div>

      <TdsProfileCard companyId={activeCompany.company_id} />
      <PayableSummaryCards companyId={activeCompany.company_id} />
      <ReturnPeriodsCard companyId={activeCompany.company_id} />
    </div>
  );
}

const deductorTypes: DeductorType[] = ["COMPANY", "INDIVIDUAL", "HUF", "FIRM", "LLP", "GOVERNMENT", "TRUST", "OTHER"];

const profileSchema = z.object({
  tan: z.string().length(10, "TAN must be exactly 10 characters"),
  pan: z.string().length(10, "PAN must be exactly 10 characters"),
  legal_name: z.string().min(1, "Legal name is required"),
  trade_name: z.string().optional().or(z.literal("")),
  deductor_type: z.enum(deductorTypes as [DeductorType, ...DeductorType[]]),
});
type ProfileFormValues = z.infer<typeof profileSchema>;

function TdsProfileCard({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const { data: profile, isLoading, isError } = useTdsProfile(companyId);
  const createMutation = useCreateTdsProfile(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { deductor_type: "COMPANY" },
  });

  const onSubmit = async (values: ProfileFormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        ...values,
        tan: values.tan.toUpperCase(),
        pan: values.pan.toUpperCase(),
        trade_name: values.trade_name || null,
      });
      toast({ title: "TDS profile created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6"><Skeleton className="h-16 w-full" /></CardContent>
      </Card>
    );
  }

  if (isError || !profile) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex items-center justify-between gap-4 pt-6">
          <div>
            <p className="text-sm font-medium">No TDS profile yet</p>
            <p className="text-xs text-muted-foreground">
              Add your company's TAN before recording TDS transactions or preparing a return.
            </p>
          </div>
          <PermissionGate permission="TDS_CREATE">
            <Button onClick={() => setOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" /> Add TDS profile
            </Button>
          </PermissionGate>
        </CardContent>

        <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add TDS profile</DialogTitle>
              <DialogDescription>
                TAN/PAN format is checked locally only — this never calls the Income Tax e-filing portal.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
              <div className="space-y-1.5">
                <Label htmlFor="tan">TAN</Label>
                <Input id="tan" maxLength={10} className="uppercase" {...register("tan")} />
                {errors.tan && <p className="text-xs text-destructive">{errors.tan.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tds-pan">PAN</Label>
                <Input id="tds-pan" maxLength={10} className="uppercase" {...register("pan")} />
                {errors.pan && <p className="text-xs text-destructive">{errors.pan.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tds-legal-name">Legal name</Label>
                <Input id="tds-legal-name" {...register("legal_name")} />
                {errors.legal_name && <p className="text-xs text-destructive">{errors.legal_name.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tds-trade-name">Trade name (optional)</Label>
                <Input id="tds-trade-name" {...register("trade_name")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="deductor-type">Deductor type</Label>
                <Controller
                  control={control}
                  name="deductor_type"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger id="deductor-type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {deductorTypes.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save"}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-2 pt-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">TAN</p>
          <p className="font-mono text-sm font-semibold">{profile.tan}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">PAN</p>
          <p className="font-mono text-sm font-semibold">{profile.pan}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Legal Name</p>
          <p className="text-sm font-medium">{profile.legal_name}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Deductor Type</p>
          <Badge variant="outline">{profile.deductor_type}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function PayableSummaryCards({ companyId }: { companyId: string }) {
  const { data, isLoading } = useTdsPayableSummary(companyId);
  if (isLoading) return <Skeleton className="h-20 w-full" />;
  if (!data) return null;

  const cards: [string, string][] = [
    ["TDS Deducted", formatMoney(data.tds_deducted)],
    ["TDS Paid", formatMoney(data.tds_paid)],
    ["TDS Outstanding", formatMoney(data.tds_outstanding)],
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
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

const quarters: TDSQuarter[] = ["Q1", "Q2", "Q3", "Q4"];
const periodSchema = z.object({
  financial_year_id: z.string().min(1, "Select a financial year"),
  quarter: z.enum(quarters as [TDSQuarter, ...TDSQuarter[]]),
});
type PeriodFormValues = z.infer<typeof periodSchema>;

function ReturnPeriodsCard({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useTdsReturnPeriods(companyId);
  const { data: financialYears } = useFinancialYears(companyId);
  const createMutation = useCreateTdsReturnPeriod(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<PeriodFormValues>({
    resolver: zodResolver(periodSchema),
    defaultValues: { quarter: "Q1" },
  });

  useEffect(() => {
    if (financialYears?.items && financialYears.items.length > 0) {
      const current = financialYears.items.find((f) => f.is_current) ?? financialYears.items[0];
      if (current && !watch("financial_year_id")) {
        setValue("financial_year_id", current.id);
      }
    }
  }, [financialYears, setValue, watch]);

  const onSubmit = async (values: PeriodFormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync(values);
      toast({ title: "Return period created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarRange className="h-4 w-4" /> Return Periods
        </CardTitle>
        <PermissionGate permission="TDS_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New period
          </Button>
        </PermissionGate>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-6"><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quarter</TableHead>
                <TableHead>Start</TableHead>
                <TableHead>End</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((period) => (
                <TableRow key={period.id}>
                  <TableCell>
                    <Link
                      to={`/tds/return-periods/${period.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {period.quarter}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{period.period_start}</TableCell>
                  <TableCell className="text-muted-foreground">{period.period_end}</TableCell>
                  <TableCell>
                    <Badge variant={PERIOD_STATUS_VARIANT[period.status]}>{period.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Receipt} title="No return periods yet" hint="Create one to start preparing a TDS return." />
        )}
      </CardContent>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New TDS return period</DialogTitle>
            <DialogDescription>A quarterly period to prepare TDS return data against.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            {financialYears?.items?.length === 0 && (
              <Alert variant="warning">
                <AlertDescription>
                  No Financial Year found. <Link to="/accounting/financial-years" className="font-semibold underline">Create a Financial Year</Link> first.
                </AlertDescription>
              </Alert>
            )}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="tds-period-fy">Financial year</Label>
                <Link to="/accounting/financial-years" className="text-xs text-primary hover:underline">
                  Manage FY
                </Link>
              </div>
              <Controller
                control={control}
                name="financial_year_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="tds-period-fy"><SelectValue placeholder="Select financial year" /></SelectTrigger>
                    <SelectContent>
                      {(financialYears?.items ?? []).map((fy) => (
                        <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.financial_year_id && <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tds-period-quarter">Quarter</Label>
              <Controller
                control={control}
                name="quarter"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="tds-period-quarter"><SelectValue placeholder="Quarter" /></SelectTrigger>
                    <SelectContent>
                      {quarters.map((q) => <SelectItem key={q} value={q}>{q}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.quarter && <p className="text-xs text-destructive">{errors.quarter.message}</p>}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Creating…" : "Create"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
