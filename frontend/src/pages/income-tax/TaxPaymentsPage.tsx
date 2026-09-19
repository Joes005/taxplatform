import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Wallet } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears } from "@/hooks/useAccounting";
import {
  useAdvanceTaxPayments,
  useCreateAdvanceTaxPayment,
  useCreateCreditEntry,
  useCreateSelfAssessmentTaxPayment,
  useCreditEntries,
  useSelfAssessmentTaxPayments,
} from "@/hooks/useIncomeTaxPayments";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api-client";
import { formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";

const paymentSchema = z.object({
  payment_date: z.string().min(1, "Date is required"),
  amount: z.string().min(1),
  challan_number: z.string().optional(),
});
type PaymentFormValues = z.infer<typeof paymentSchema>;

export default function TaxPaymentsPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={Wallet} />;
  const companyId = activeCompany.company_id;

  const { data: financialYears } = useFinancialYears(companyId);
  const [fyId, setFyId] = useState<string>("");
  const effectiveFyId = fyId || financialYears?.items.find((fy) => fy.is_current)?.id || "";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tax Payments</h1>
          <p className="text-sm text-muted-foreground">Advance tax, self-assessment tax, and TDS/TCS credit received.</p>
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
        <Tabs defaultValue="advance">
          <TabsList>
            <TabsTrigger value="advance">Advance Tax</TabsTrigger>
            <TabsTrigger value="self-assessment">Self-Assessment Tax</TabsTrigger>
            <TabsTrigger value="credits">TDS/TCS Credit</TabsTrigger>
          </TabsList>
          <TabsContent value="advance"><AdvanceTaxTab companyId={companyId} financialYearId={effectiveFyId} /></TabsContent>
          <TabsContent value="self-assessment"><SelfAssessmentTab companyId={companyId} financialYearId={effectiveFyId} /></TabsContent>
          <TabsContent value="credits"><CreditsTab companyId={companyId} financialYearId={effectiveFyId} /></TabsContent>
        </Tabs>
      )}
    </div>
  );
}

function AdvanceTaxTab({ companyId, financialYearId }: { companyId: string; financialYearId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useAdvanceTaxPayments(companyId, financialYearId);
  const createMutation = useCreateAdvanceTaxPayment(companyId);
  const [open, setOpen] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<PaymentFormValues>({ resolver: zodResolver(paymentSchema) });

  const onSubmit = async (values: PaymentFormValues) => {
    try {
      await createMutation.mutateAsync({ financial_year_id: financialYearId, ...values });
      toast({ title: "Advance tax payment recorded", variant: "success" });
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
      <PaymentTable data={data} isLoading={isLoading} />
      <PaymentDialog title="Add advance tax payment" open={open} setOpen={setOpen} onSubmit={handleSubmit(onSubmit)} register={register} isSubmitting={isSubmitting} />
    </div>
  );
}

function SelfAssessmentTab({ companyId, financialYearId }: { companyId: string; financialYearId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useSelfAssessmentTaxPayments(companyId, financialYearId);
  const createMutation = useCreateSelfAssessmentTaxPayment(companyId);
  const [open, setOpen] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<PaymentFormValues>({ resolver: zodResolver(paymentSchema) });

  const onSubmit = async (values: PaymentFormValues) => {
    try {
      await createMutation.mutateAsync({ financial_year_id: financialYearId, ...values });
      toast({ title: "Self-assessment tax payment recorded", variant: "success" });
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
      <PaymentTable data={data} isLoading={isLoading} />
      <PaymentDialog title="Add self-assessment tax payment" open={open} setOpen={setOpen} onSubmit={handleSubmit(onSubmit)} register={register} isSubmitting={isSubmitting} />
    </div>
  );
}

function PaymentTable({ data, isLoading }: { data: { id: string; payment_date: string; amount: string; challan_number: string | null }[] | undefined; isLoading: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-white">
      {isLoading ? (
        <div className="p-6"><Skeleton className="h-10 w-full" /></div>
      ) : (data ?? []).length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Challan No.</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(data ?? []).map((p) => (
              <TableRow key={p.id}>
                <TableCell className="text-muted-foreground">{p.payment_date}</TableCell>
                <TableCell>{p.challan_number ?? "—"}</TableCell>
                <TableCell className="text-right">{formatMoney(p.amount)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <EmptyTableState icon={Wallet} title="No payments recorded" />
      )}
    </div>
  );
}

function PaymentDialog({
  title, open, setOpen, onSubmit, register, isSubmitting,
}: {
  title: string;
  open: boolean;
  setOpen: (v: boolean) => void;
  onSubmit: React.FormEventHandler<HTMLFormElement>;
  register: ReturnType<typeof useForm<PaymentFormValues>>["register"];
  isSubmitting: boolean;
}) {
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1.5"><Label>Payment date</Label><Input type="date" {...register("payment_date")} /></div>
          <div className="space-y-1.5"><Label>Amount</Label><Input type="number" step="0.01" {...register("amount")} /></div>
          <div className="space-y-1.5"><Label>Challan number</Label><Input {...register("challan_number")} /></div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

const creditSchema = z.object({
  deductor_name: z.string().min(1, "Deductor name is required"),
  deductor_tan: z.string().optional(),
  section_code: z.string().optional(),
  amount: z.string().min(1),
  certificate_reference: z.string().optional(),
});
type CreditFormValues = z.infer<typeof creditSchema>;

function CreditsTab({ companyId, financialYearId }: { companyId: string; financialYearId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useCreditEntries(companyId, financialYearId);
  const createMutation = useCreateCreditEntry(companyId);
  const [open, setOpen] = useState(false);
  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<CreditFormValues>({ resolver: zodResolver(creditSchema) });

  const onSubmit = async (values: CreditFormValues) => {
    try {
      await createMutation.mutateAsync({ financial_year_id: financialYearId, ...values });
      toast({ title: "Credit entry recorded", variant: "success" });
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
        {isLoading ? (
          <div className="p-6"><Skeleton className="h-10 w-full" /></div>
        ) : (data ?? []).length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Deductor</TableHead>
                <TableHead>TAN</TableHead>
                <TableHead>Certificate</TableHead>
                <TableHead className="text-right">Amount</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((c) => (
                <TableRow key={c.id}>
                  <TableCell>{c.deductor_name}</TableCell>
                  <TableCell className="text-muted-foreground">{c.deductor_tan ?? "—"}</TableCell>
                  <TableCell className="text-muted-foreground">{c.certificate_reference ?? "—"}</TableCell>
                  <TableCell className="text-right">{formatMoney(c.amount)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Wallet} title="No TDS/TCS credit recorded" />
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add TDS/TCS credit</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div className="space-y-1.5"><Label>Deductor name</Label><Input {...register("deductor_name")} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Deductor TAN</Label><Input {...register("deductor_tan")} /></div>
              <div className="space-y-1.5"><Label>Section code</Label><Input {...register("section_code")} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Amount</Label><Input type="number" step="0.01" {...register("amount")} /></div>
              <div className="space-y-1.5"><Label>Certificate reference</Label><Input {...register("certificate_reference")} /></div>
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
