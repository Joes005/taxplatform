import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CalendarRange, Plus, Receipt, ShieldCheck } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import { useCreateGstProfile, useGstProfile } from "@/hooks/useGstProfile";
import { useCreateGstReturnPeriod, useGstReturnPeriods } from "@/hooks/useGstReturnPeriods";
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
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
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

export default function GstDashboardPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={ShieldCheck} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">GST Compliance</h1>
        <p className="text-sm text-muted-foreground">
          GSTR-1 &amp; GSTR-3B preparation, GSTR-2B reconciliation, and ITC review — a local preparation
          workspace for your CA/auditor, not a GST portal filing tool.
        </p>
      </div>

      <GstProfileCard companyId={activeCompany.company_id} />
      <ReturnPeriodsCard companyId={activeCompany.company_id} />
    </div>
  );
}

const registrationTypes = ["REGULAR", "COMPOSITION", "CASUAL", "SEZ", "OTHER"] as const;

const profileSchema = z.object({
  gstin: z.string().length(15, "GSTIN must be exactly 15 characters"),
  legal_name: z.string().min(1, "Legal name is required"),
  trade_name: z.string().optional().or(z.literal("")),
  registration_type: z.enum(registrationTypes),
});
type ProfileFormValues = z.infer<typeof profileSchema>;

function GstProfileCard({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const { data: profile, isLoading, isError } = useGstProfile(companyId);
  const createMutation = useCreateGstProfile(companyId);
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
    defaultValues: { registration_type: "REGULAR" },
  });

  const onSubmit = async (values: ProfileFormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        ...values,
        gstin: values.gstin.toUpperCase(),
        trade_name: values.trade_name || null,
      });
      toast({ title: "GST profile created", variant: "success" });
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
            <p className="text-sm font-medium">No GST profile yet</p>
            <p className="text-xs text-muted-foreground">
              Add your company's GSTIN before preparing GSTR-1/GSTR-3B for any return period.
            </p>
          </div>
          <PermissionGate permission="GST_CREATE">
            <Button onClick={() => setOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" /> Add GST profile
            </Button>
          </PermissionGate>
        </CardContent>

        <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add GST profile</DialogTitle>
              <DialogDescription>
                GSTIN format is checked locally (including its checksum) — this never calls the GST portal.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
              <div className="space-y-1.5">
                <Label htmlFor="gstin">GSTIN</Label>
                <Input id="gstin" maxLength={15} className="uppercase" {...register("gstin")} />
                {errors.gstin && <p className="text-xs text-destructive">{errors.gstin.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="legal-name">Legal name</Label>
                <Input id="legal-name" {...register("legal_name")} />
                {errors.legal_name && <p className="text-xs text-destructive">{errors.legal_name.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="trade-name">Trade name (optional)</Label>
                <Input id="trade-name" {...register("trade_name")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="registration-type">Registration type</Label>
                <Controller
                  control={control}
                  name="registration_type"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger id="registration-type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {registrationTypes.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
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
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">GSTIN</p>
          <p className="font-mono text-sm font-semibold">{profile.gstin}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Legal Name</p>
          <p className="text-sm font-medium">{profile.legal_name}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">State</p>
          <p className="text-sm font-medium">{profile.state_name} ({profile.state_code})</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Registration</p>
          <Badge variant="outline">{profile.registration_type}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}

const periodSchema = z.object({
  financial_year_id: z.string().min(1, "Select a financial year"),
  year: z.coerce.number().int().min(2000).max(2100),
  month: z.coerce.number().int().min(1).max(12),
});
type PeriodFormValues = z.infer<typeof periodSchema>;

function ReturnPeriodsCard({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useGstReturnPeriods(companyId);
  const { data: financialYears } = useFinancialYears(companyId);
  const createMutation = useCreateGstReturnPeriod(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<PeriodFormValues>({
    resolver: zodResolver(periodSchema),
    defaultValues: {
      year: new Date().getFullYear(),
      month: new Date().getMonth() + 1,
    },
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
        <PermissionGate permission="GST_CREATE">
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
                <TableHead>Period</TableHead>
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
                      to={`/gst/return-periods/${period.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {MONTH_NAMES[period.month - 1]} {period.year}
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
          <EmptyTableState icon={Receipt} title="No return periods yet" hint="Create one to start preparing GSTR-1." />
        )}
      </CardContent>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New return period</DialogTitle>
            <DialogDescription>A monthly period to prepare GSTR-1, reconcile GSTR-2B, and prepare GSTR-3B against.</DialogDescription>
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
                <Label htmlFor="period-fy">Financial year</Label>
                <Link to="/accounting/financial-years" className="text-xs text-primary hover:underline">
                  Manage FY
                </Link>
              </div>
              <Controller
                control={control}
                name="financial_year_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="period-fy"><SelectValue placeholder="Select financial year" /></SelectTrigger>
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
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="period-year">Year</Label>
                <Input id="period-year" type="number" {...register("year")} />
                {errors.year && <p className="text-xs text-destructive">{errors.year.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="period-month">Month</Label>
                <Controller
                  control={control}
                  name="month"
                  render={({ field }) => (
                    <Select onValueChange={(v) => field.onChange(Number(v))} value={field.value ? String(field.value) : undefined}>
                      <SelectTrigger id="period-month"><SelectValue placeholder="Month" /></SelectTrigger>
                      <SelectContent>
                        {MONTH_NAMES.map((name, i) => (
                          <SelectItem key={name} value={String(i + 1)}>{name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.month && <p className="text-xs text-destructive">{errors.month.message}</p>}
              </div>
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
