import { useState } from "react";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { BookOpenCheck, Plus, Trash2 } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCustomers, useFinancialYears, useLedgers } from "@/hooks/useAccounting";
import {
  useCreateJournalEntry,
  useCreatePayment,
  useCreateReceipt,
  useJournalEntries,
  usePayments,
  usePostJournalEntry,
  useReceipts,
} from "@/hooks/usePaymentsReceipts";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatMoney } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";
import { EmptyCompanyState, EmptyTableState } from "./LedgersPage";

const PAYMENT_MODES = ["CASH", "BANK", "UPI", "CHEQUE", "CARD", "OTHER"];

export default function OtherTransactionsPage() {
  const { activeCompany } = useAuth();
  if (!activeCompany) return <EmptyCompanyState icon={BookOpenCheck} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Payments, Receipts &amp; Journals</h1>
        <p className="text-sm text-muted-foreground">Cash movements and general journal entries</p>
      </div>
      <Tabs defaultValue="payments">
        <TabsList>
          <TabsTrigger value="payments">Payments</TabsTrigger>
          <TabsTrigger value="receipts">Receipts</TabsTrigger>
          <TabsTrigger value="journals">Journal Entries</TabsTrigger>
        </TabsList>
        <TabsContent value="payments"><PaymentsTab companyId={activeCompany.company_id} /></TabsContent>
        <TabsContent value="receipts"><ReceiptsTab companyId={activeCompany.company_id} /></TabsContent>
        <TabsContent value="journals"><JournalsTab companyId={activeCompany.company_id} /></TabsContent>
      </Tabs>
    </div>
  );
}

const paymentSchema = z.object({
  financial_year_id: z.string().min(1, "Required"),
  payment_date: z.string().min(1, "Required"),
  payment_number: z.string().min(1, "Required").max(50),
  ledger_id: z.string().min(1, "Required"),
  amount: z.coerce.number().gt(0, "Must be greater than zero"),
  payment_mode: z.enum(PAYMENT_MODES as [string, ...string[]]),
});
type PaymentFormValues = z.infer<typeof paymentSchema>;

function PaymentsTab({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = usePayments(companyId);
  const { data: financialYears } = useFinancialYears(companyId);
  const { data: ledgers } = useLedgers(companyId);
  const createMutation = useCreatePayment(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, control, handleSubmit, reset, formState: { errors, isSubmitting } } =
    useForm<PaymentFormValues>({ resolver: zodResolver(paymentSchema) });

  const onSubmit = async (values: PaymentFormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync(values);
      toast({ title: "Payment recorded", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="PAYMENT_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}><Plus className="mr-1.5 h-4 w-4" /> Record Payment</Button>
        </PermissionGate>
      </div>
      <div className="rounded-lg border border-border bg-white">
        {isLoading ? <div className="p-6"><Skeleton className="h-10 w-full" /></div> : data && data.items.length > 0 ? (
          <Table>
            <TableHeader><TableRow><TableHead>Number</TableHead><TableHead>Date</TableHead><TableHead>Mode</TableHead><TableHead className="text-right">Amount</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.items.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{p.payment_number}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(p.payment_date)}</TableCell>
                  <TableCell><Badge variant="outline">{p.payment_mode}</Badge></TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(p.amount)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <EmptyTableState icon={BookOpenCheck} title="No payments recorded yet" />}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Record payment</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label>Financial Year</Label>
              <Controller control={control} name="financial_year_id" render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value}>
                  <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>{(financialYears?.items ?? []).map((fy) => <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>)}</SelectContent>
                </Select>
              )} />
              {errors.financial_year_id && <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Payment Number</Label><Input {...register("payment_number")} />{errors.payment_number && <p className="text-xs text-destructive">{errors.payment_number.message}</p>}</div>
              <div className="space-y-1.5"><Label>Date</Label><Input type="date" {...register("payment_date")} />{errors.payment_date && <p className="text-xs text-destructive">{errors.payment_date.message}</p>}</div>
            </div>
            <div className="space-y-1.5">
              <Label>Ledger</Label>
              <Controller control={control} name="ledger_id" render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value}>
                  <SelectTrigger><SelectValue placeholder="Select ledger" /></SelectTrigger>
                  <SelectContent>{(ledgers?.items ?? []).map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}</SelectContent>
                </Select>
              )} />
              {errors.ledger_id && <p className="text-xs text-destructive">{errors.ledger_id.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Amount</Label><Input type="number" step="0.01" {...register("amount")} />{errors.amount && <p className="text-xs text-destructive">{errors.amount.message}</p>}</div>
              <div className="space-y-1.5">
                <Label>Mode</Label>
                <Controller control={control} name="payment_mode" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>{PAYMENT_MODES.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                  </Select>
                )} />
                {errors.payment_mode && <p className="text-xs text-destructive">{errors.payment_mode.message}</p>}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Record"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const receiptSchema = z.object({
  financial_year_id: z.string().min(1, "Required"),
  receipt_date: z.string().min(1, "Required"),
  receipt_number: z.string().min(1, "Required").max(50),
  customer_id: z.string().min(1, "Required"),
  ledger_id: z.string().min(1, "Required"),
  amount: z.coerce.number().gt(0, "Must be greater than zero"),
  payment_mode: z.enum(PAYMENT_MODES as [string, ...string[]]),
});
type ReceiptFormValues = z.infer<typeof receiptSchema>;

function ReceiptsTab({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useReceipts(companyId);
  const { data: financialYears } = useFinancialYears(companyId);
  const { data: customers } = useCustomers(companyId);
  const { data: ledgers } = useLedgers(companyId);
  const createMutation = useCreateReceipt(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, control, handleSubmit, reset, formState: { errors, isSubmitting } } =
    useForm<ReceiptFormValues>({ resolver: zodResolver(receiptSchema) });

  const onSubmit = async (values: ReceiptFormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync(values);
      toast({ title: "Receipt recorded", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="RECEIPT_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}><Plus className="mr-1.5 h-4 w-4" /> Record Receipt</Button>
        </PermissionGate>
      </div>
      <div className="rounded-lg border border-border bg-white">
        {isLoading ? <div className="p-6"><Skeleton className="h-10 w-full" /></div> : data && data.items.length > 0 ? (
          <Table>
            <TableHeader><TableRow><TableHead>Number</TableHead><TableHead>Date</TableHead><TableHead>Mode</TableHead><TableHead className="text-right">Amount</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.receipt_number}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(r.receipt_date)}</TableCell>
                  <TableCell><Badge variant="outline">{r.payment_mode}</Badge></TableCell>
                  <TableCell className="text-right font-medium">{formatMoney(r.amount)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <EmptyTableState icon={BookOpenCheck} title="No receipts recorded yet" />}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Record receipt</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label>Financial Year</Label>
              <Controller control={control} name="financial_year_id" render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value}>
                  <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>{(financialYears?.items ?? []).map((fy) => <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>)}</SelectContent>
                </Select>
              )} />
              {errors.financial_year_id && <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Receipt Number</Label><Input {...register("receipt_number")} />{errors.receipt_number && <p className="text-xs text-destructive">{errors.receipt_number.message}</p>}</div>
              <div className="space-y-1.5"><Label>Date</Label><Input type="date" {...register("receipt_date")} />{errors.receipt_date && <p className="text-xs text-destructive">{errors.receipt_date.message}</p>}</div>
            </div>
            <div className="space-y-1.5">
              <Label>Customer</Label>
              <Controller control={control} name="customer_id" render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value}>
                  <SelectTrigger><SelectValue placeholder="Select customer" /></SelectTrigger>
                  <SelectContent>{(customers?.items ?? []).map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
                </Select>
              )} />
              {errors.customer_id && <p className="text-xs text-destructive">{errors.customer_id.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Ledger</Label>
              <Controller control={control} name="ledger_id" render={({ field }) => (
                <Select onValueChange={field.onChange} value={field.value}>
                  <SelectTrigger><SelectValue placeholder="Select ledger" /></SelectTrigger>
                  <SelectContent>{(ledgers?.items ?? []).map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}</SelectContent>
                </Select>
              )} />
              {errors.ledger_id && <p className="text-xs text-destructive">{errors.ledger_id.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Amount</Label><Input type="number" step="0.01" {...register("amount")} />{errors.amount && <p className="text-xs text-destructive">{errors.amount.message}</p>}</div>
              <div className="space-y-1.5">
                <Label>Mode</Label>
                <Controller control={control} name="payment_mode" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>{PAYMENT_MODES.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                  </Select>
                )} />
                {errors.payment_mode && <p className="text-xs text-destructive">{errors.payment_mode.message}</p>}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Record"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const journalLineSchema = z.object({
  ledger_id: z.string().min(1, "Required"),
  debit_amount: z.coerce.number().min(0).optional(),
  credit_amount: z.coerce.number().min(0).optional(),
});
const journalSchema = z.object({
  financial_year_id: z.string().min(1, "Required"),
  journal_number: z.string().min(1, "Required").max(50),
  journal_date: z.string().min(1, "Required"),
  narration: z.string().max(500).optional(),
  lines: z.array(journalLineSchema).min(2, "At least two lines are required"),
});
type JournalFormValues = z.infer<typeof journalSchema>;

function JournalsTab({ companyId }: { companyId: string }) {
  const { toast } = useToast();
  const { data, isLoading } = useJournalEntries(companyId);
  const { data: financialYears } = useFinancialYears(companyId);
  const { data: ledgers } = useLedgers(companyId);
  const createMutation = useCreateJournalEntry(companyId);
  const postMutation = usePostJournalEntry(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, control, handleSubmit, watch, reset, formState: { errors, isSubmitting } } =
    useForm<JournalFormValues>({ resolver: zodResolver(journalSchema), defaultValues: { lines: [{ ledger_id: "" }, { ledger_id: "" }] } });
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });
  const watchedLines = watch("lines");

  const totalDebit = (watchedLines ?? []).reduce((sum, l) => sum + (l?.debit_amount ?? 0), 0);
  const totalCredit = (watchedLines ?? []).reduce((sum, l) => sum + (l?.credit_amount ?? 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01 && totalDebit > 0;

  const onSubmit = async (values: JournalFormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync(values);
      toast({ title: "Journal entry created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  const handlePost = async (id: string) => {
    try {
      await postMutation.mutateAsync(id);
      toast({ title: "Journal entry posted", variant: "success" });
    } catch (err) {
      toast({ title: "Could not post", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <PermissionGate permission="JOURNAL_CREATE">
          <Button size="sm" onClick={() => setOpen(true)}><Plus className="mr-1.5 h-4 w-4" /> New Journal Entry</Button>
        </PermissionGate>
      </div>
      <div className="rounded-lg border border-border bg-white">
        {isLoading ? <div className="p-6"><Skeleton className="h-10 w-full" /></div> : data && data.items.length > 0 ? (
          <Table>
            <TableHeader><TableRow><TableHead>Number</TableHead><TableHead>Date</TableHead><TableHead>Narration</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.items.map((j) => (
                <TableRow key={j.id}>
                  <TableCell className="font-medium">{j.journal_number}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(j.journal_date)}</TableCell>
                  <TableCell className="text-muted-foreground">{j.narration ?? "—"}</TableCell>
                  <TableCell><Badge variant={j.status === "POSTED" ? "success" : "secondary"}>{j.status}</Badge></TableCell>
                  <TableCell className="text-right">
                    {j.status === "DRAFT" && (
                      <PermissionGate permission="JOURNAL_POST">
                        <Button variant="ghost" size="sm" onClick={() => handlePost(j.id)}>Post</Button>
                      </PermissionGate>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : <EmptyTableState icon={BookOpenCheck} title="No journal entries yet" />}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset({ lines: [{ ledger_id: "" }, { ledger_id: "" }] }); setServerError(null); } }}>
        <DialogContent className="max-w-xl">
          <DialogHeader><DialogTitle>New journal entry</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Financial Year</Label>
                <Controller control={control} name="financial_year_id" render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>{(financialYears?.items ?? []).map((fy) => <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>)}</SelectContent>
                  </Select>
                )} />
                {errors.financial_year_id && <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>}
              </div>
              <div className="space-y-1.5"><Label>Date</Label><Input type="date" {...register("journal_date")} />{errors.journal_date && <p className="text-xs text-destructive">{errors.journal_date.message}</p>}</div>
            </div>
            <div className="space-y-1.5"><Label>Journal Number</Label><Input {...register("journal_number")} />{errors.journal_number && <p className="text-xs text-destructive">{errors.journal_number.message}</p>}</div>
            <div className="space-y-1.5"><Label>Narration</Label><Input {...register("narration")} /></div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Lines (debits must equal credits)</Label>
                <Button type="button" variant="outline" size="sm" onClick={() => append({ ledger_id: "" })}><Plus className="mr-1 h-3 w-3" /> Add line</Button>
              </div>
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-end gap-2">
                  <div className="flex-1 space-y-1">
                    <Controller control={control} name={`lines.${index}.ledger_id`} render={({ field: f }) => (
                      <Select onValueChange={f.onChange} value={f.value}>
                        <SelectTrigger><SelectValue placeholder="Ledger" /></SelectTrigger>
                        <SelectContent>{(ledgers?.items ?? []).map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}</SelectContent>
                      </Select>
                    )} />
                  </div>
                  <div className="w-28 space-y-1">
                    <Input type="number" step="0.01" placeholder="Debit" {...register(`lines.${index}.debit_amount` as const)} />
                  </div>
                  <div className="w-28 space-y-1">
                    <Input type="number" step="0.01" placeholder="Credit" {...register(`lines.${index}.credit_amount` as const)} />
                  </div>
                  <button type="button" onClick={() => remove(index)} className="mb-2 text-muted-foreground hover:text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              {errors.lines && typeof errors.lines.message === "string" && (
                <p className="text-xs text-destructive">{errors.lines.message}</p>
              )}
              <div className={`flex justify-between text-xs ${isBalanced ? "text-success" : "text-muted-foreground"}`}>
                <span>Total Debit: {formatMoney(totalDebit)}</span>
                <span>Total Credit: {formatMoney(totalCredit)}</span>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Create"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
