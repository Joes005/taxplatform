import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Landmark, Plus, Trash2 } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import {
  useCreateExemptIncome,
  useCreateHousePropertyIncome,
  useCreateOtherIncome,
  useCreateSalaryIncome,
  useDeleteExemptIncome,
  useDeleteHousePropertyIncome,
  useDeleteOtherIncome,
  useDeleteSalaryIncome,
  useExemptIncome,
  useHousePropertyIncome,
  useOtherIncome,
  useSalaryIncome,
} from "@/hooks/useIncomeTaxIncome";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError } from "@/lib/api-client";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { HousePropertyType } from "@/types/incomeTax";

export default function IncomeTaxIncomePage() {
  const { activeCompany } = useAuth();
  const companyId = activeCompany?.company_id;

  const { data: financialYears } = useFinancialYears(companyId);
  const [fyId, setFyId] = useState<string>("");
  const effectiveFyId = fyId || financialYears?.items.find((fy) => fy.is_current)?.id || "";

  if (!activeCompany || !companyId) return <EmptyCompanyState icon={Landmark} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Income</h1>
          <p className="text-sm text-muted-foreground">Salary, house property, other sources, and exempt income.</p>
        </div>
        <Select value={effectiveFyId} onValueChange={setFyId}>
          <SelectTrigger className="w-48"><SelectValue placeholder="Financial year" /></SelectTrigger>
          <SelectContent>
            {(financialYears?.items ?? []).map((fy) => <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {!effectiveFyId ? (
        <p className="text-sm text-muted-foreground">Select a financial year to continue.</p>
      ) : (
        <Tabs defaultValue="salary">
          <TabsList>
            <TabsTrigger value="salary">Salary</TabsTrigger>
            <TabsTrigger value="house-property">House Property</TabsTrigger>
            <TabsTrigger value="other">Other Sources</TabsTrigger>
            <TabsTrigger value="exempt">Exempt Income</TabsTrigger>
          </TabsList>
          <TabsContent value="salary"><SalaryTab companyId={companyId} financialYearId={effectiveFyId} /></TabsContent>
          <TabsContent value="house-property"><HousePropertyTab companyId={companyId} financialYearId={effectiveFyId} /></TabsContent>
          <TabsContent value="other"><OtherIncomeTab companyId={companyId} financialYearId={effectiveFyId} /></TabsContent>
          <TabsContent value="exempt"><ExemptIncomeTab companyId={companyId} financialYearId={effectiveFyId} /></TabsContent>
        </Tabs>
      )}
    </div>
  );
}

const salarySchema = z.object({
  employer_name: z.string().min(1, "Employer name is required"),
  gross_salary: z.string().min(1),
  allowances: z.string().optional(),
  perquisites: z.string().optional(),
  standard_deduction: z.string().optional(),
  professional_tax: z.string().optional(),
  tds: z.string().optional(),
});
type SalaryFormValues = z.infer<typeof salarySchema>;

function SalaryTab({ companyId, financialYearId }: { companyId: string; financialYearId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useSalaryIncome(companyId, financialYearId);
  const createMutation = useCreateSalaryIncome(companyId);
  const deleteMutation = useDeleteSalaryIncome(companyId);
  const [open, setOpen] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<SalaryFormValues>({
    resolver: zodResolver(salarySchema),
  });

  const onSubmit = async (values: SalaryFormValues) => {
    try {
      await createMutation.mutateAsync({ financial_year_id: financialYearId, ...values });
      toast({ title: "Salary income recorded", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      toast({ title: "Failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="INCOME_TAX_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}><Plus className="mr-1.5 h-3.5 w-3.5" /> Add</Button>
        </PermissionGate>
      </div>
      <div className="rounded-lg border border-border bg-white">
        {isLoading ? <div className="p-6"><Skeleton className="h-10 w-full" /></div> : (data ?? []).length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employer</TableHead>
                <TableHead className="text-right">Gross Salary</TableHead>
                <TableHead className="text-right">TDS</TableHead>
                <TableHead className="text-right">Taxable Amount</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((s) => (
                <TableRow key={s.id}>
                  <TableCell>{s.employer_name}</TableCell>
                  <TableCell className="text-right">{formatMoney(s.gross_salary)}</TableCell>
                  <TableCell className="text-right">{formatMoney(s.tds)}</TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(s.taxable_amount)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => deleteMutation.mutate(s.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <EmptyTableState icon={Landmark} title="No salary income recorded" /> }
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add salary income</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="space-y-1.5">
              <Label>Employer name</Label>
              <Input {...register("employer_name")} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Gross salary</Label><Input type="number" step="0.01" {...register("gross_salary")} /></div>
              <div className="space-y-1.5"><Label>Allowances</Label><Input type="number" step="0.01" {...register("allowances")} /></div>
              <div className="space-y-1.5"><Label>Standard deduction</Label><Input type="number" step="0.01" {...register("standard_deduction")} /></div>
              <div className="space-y-1.5"><Label>Professional tax</Label><Input type="number" step="0.01" {...register("professional_tax")} /></div>
              <div className="space-y-1.5"><Label>TDS deducted</Label><Input type="number" step="0.01" {...register("tds")} /></div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const hpSchema = z.object({
  property_type: z.string().min(1),
  address: z.string().optional(),
  gross_rent: z.string().optional(),
  municipal_tax: z.string().optional(),
  interest_on_home_loan: z.string().optional(),
});
type HpFormValues = z.infer<typeof hpSchema>;

function HousePropertyTab({ companyId, financialYearId }: { companyId: string; financialYearId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useHousePropertyIncome(companyId, financialYearId);
  const createMutation = useCreateHousePropertyIncome(companyId);
  const deleteMutation = useDeleteHousePropertyIncome(companyId);
  const [open, setOpen] = useState(false);
  const { register, control, handleSubmit, reset, formState: { isSubmitting } } = useForm<HpFormValues>({
    resolver: zodResolver(hpSchema),
    defaultValues: { property_type: "LET_OUT" },
  });

  const onSubmit = async (values: HpFormValues) => {
    try {
      await createMutation.mutateAsync({
        financial_year_id: financialYearId,
        ...values,
        property_type: values.property_type as HousePropertyType,
      });
      toast({ title: "House property income recorded", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      toast({ title: "Failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="INCOME_TAX_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}><Plus className="mr-1.5 h-3.5 w-3.5" /> Add</Button>
        </PermissionGate>
      </div>
      <div className="rounded-lg border border-border bg-white">
        {isLoading ? <div className="p-6"><Skeleton className="h-10 w-full" /></div> : (data ?? []).length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">NAV</TableHead>
                <TableHead className="text-right">Std. Deduction</TableHead>
                <TableHead className="text-right">Interest</TableHead>
                <TableHead className="text-right">Income / Loss</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((h) => (
                <TableRow key={h.id}>
                  <TableCell>{h.property_type.replaceAll("_", " ")}</TableCell>
                  <TableCell className="text-right">{formatMoney(h.net_annual_value)}</TableCell>
                  <TableCell className="text-right">{formatMoney(h.standard_deduction)}</TableCell>
                  <TableCell className="text-right">{formatMoney(h.interest_on_home_loan)}</TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(h.income_or_loss)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => deleteMutation.mutate(h.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <EmptyTableState icon={Landmark} title="No house property income recorded" /> }
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add house property income</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="space-y-1.5">
              <Label>Property type</Label>
              <Controller
                control={control}
                name="property_type"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="SELF_OCCUPIED">Self Occupied</SelectItem>
                      <SelectItem value="LET_OUT">Let Out</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
            <div className="space-y-1.5"><Label>Address</Label><Input {...register("address")} /></div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5"><Label>Gross rent</Label><Input type="number" step="0.01" {...register("gross_rent")} /></div>
              <div className="space-y-1.5"><Label>Municipal tax</Label><Input type="number" step="0.01" {...register("municipal_tax")} /></div>
              <div className="space-y-1.5"><Label>Home loan interest</Label><Input type="number" step="0.01" {...register("interest_on_home_loan")} /></div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const otherSchema = z.object({
  income_type: z.string().min(1, "Income type is required"),
  description: z.string().optional(),
  gross_amount: z.string().min(1),
  tds: z.string().optional(),
});
type OtherFormValues = z.infer<typeof otherSchema>;

function OtherIncomeTab({ companyId, financialYearId }: { companyId: string; financialYearId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useOtherIncome(companyId, financialYearId);
  const createMutation = useCreateOtherIncome(companyId);
  const deleteMutation = useDeleteOtherIncome(companyId);
  const [open, setOpen] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<OtherFormValues>({
    resolver: zodResolver(otherSchema),
  });

  const onSubmit = async (values: OtherFormValues) => {
    try {
      await createMutation.mutateAsync({ financial_year_id: financialYearId, ...values });
      toast({ title: "Other income recorded", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      toast({ title: "Failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="INCOME_TAX_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}><Plus className="mr-1.5 h-3.5 w-3.5" /> Add</Button>
        </PermissionGate>
      </div>
      <div className="rounded-lg border border-border bg-white">
        {isLoading ? <div className="p-6"><Skeleton className="h-10 w-full" /></div> : (data ?? []).length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Gross</TableHead>
                <TableHead className="text-right">TDS</TableHead>
                <TableHead className="text-right">Net</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((o) => (
                <TableRow key={o.id}>
                  <TableCell>{o.income_type}</TableCell>
                  <TableCell className="text-right">{formatMoney(o.gross_amount)}</TableCell>
                  <TableCell className="text-right">{formatMoney(o.tds)}</TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(o.net_amount)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => deleteMutation.mutate(o.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <EmptyTableState icon={Landmark} title="No other income recorded" /> }
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add other income</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="space-y-1.5"><Label>Income type</Label><Input placeholder="Interest, Dividend, …" {...register("income_type")} /></div>
            <div className="space-y-1.5"><Label>Description</Label><Input {...register("description")} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Gross amount</Label><Input type="number" step="0.01" {...register("gross_amount")} /></div>
              <div className="space-y-1.5"><Label>TDS deducted</Label><Input type="number" step="0.01" {...register("tds")} /></div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const exemptSchema = z.object({
  section_code: z.string().min(1, "Section code is required"),
  description: z.string().optional(),
  amount: z.string().min(1),
});
type ExemptFormValues = z.infer<typeof exemptSchema>;

function ExemptIncomeTab({ companyId, financialYearId }: { companyId: string; financialYearId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useExemptIncome(companyId, financialYearId);
  const createMutation = useCreateExemptIncome(companyId);
  const deleteMutation = useDeleteExemptIncome(companyId);
  const [open, setOpen] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<ExemptFormValues>({
    resolver: zodResolver(exemptSchema),
  });

  const onSubmit = async (values: ExemptFormValues) => {
    try {
      await createMutation.mutateAsync({ financial_year_id: financialYearId, ...values });
      toast({ title: "Exempt income recorded", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      toast({ title: "Failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="INCOME_TAX_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}><Plus className="mr-1.5 h-3.5 w-3.5" /> Add</Button>
        </PermissionGate>
      </div>
      <div className="rounded-lg border border-border bg-white">
        {isLoading ? <div className="p-6"><Skeleton className="h-10 w-full" /></div> : (data ?? []).length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Section</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((e) => (
                <TableRow key={e.id}>
                  <TableCell>{e.section_code}</TableCell>
                  <TableCell className="text-muted-foreground">{e.description ?? "—"}</TableCell>
                  <TableCell className="text-right">{formatMoney(e.amount)}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => deleteMutation.mutate(e.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <EmptyTableState icon={Landmark} title="No exempt income recorded" /> }
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add exempt income</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="space-y-1.5"><Label>Section code</Label><Input placeholder="10(...)" {...register("section_code")} /></div>
            <div className="space-y-1.5"><Label>Description</Label><Input {...register("description")} /></div>
            <div className="space-y-1.5"><Label>Amount</Label><Input type="number" step="0.01" {...register("amount")} /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
