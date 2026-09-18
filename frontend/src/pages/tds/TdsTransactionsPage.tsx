import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Calculator, CheckCircle2, Plus, Receipt, XCircle } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useDeductees } from "@/hooks/useDeductees";
import { useTdsSections } from "@/hooks/useTdsRules";
import {
  useCalculateTdsTransaction,
  useCancelTdsTransaction,
  useCreateTdsTransaction,
  useDeductTdsTransaction,
  useTdsTransactions,
} from "@/hooks/useTdsTransactions";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
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
import type { TDSTransactionStatus } from "@/types/tds";

const STATUS_VARIANT: Record<TDSTransactionStatus, "secondary" | "warning" | "success" | "destructive" | "outline"> = {
  DRAFT: "secondary",
  CALCULATED: "warning",
  DEDUCTED: "success",
  PAID: "success",
  CANCELLED: "outline",
  REVIEW_REQUIRED: "destructive",
};

const schema = z.object({
  deductee_id: z.string().min(1, "Select a deductee"),
  tds_section_id: z.string().min(1, "Select a section"),
  transaction_date: z.string().min(1, "Date is required"),
  gross_amount: z.string().min(1, "Amount is required"),
});
type FormValues = z.infer<typeof schema>;

export default function TdsTransactionsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";

  const { data, isLoading } = useTdsTransactions(companyId);
  const { data: deductees } = useDeductees(companyId, 1);
  const { data: sections } = useTdsSections(companyId);
  const createMutation = useCreateTdsTransaction(companyId);
  const calculateMutation = useCalculateTdsTransaction(companyId);
  const deductMutation = useDeductTdsTransaction(companyId);
  const cancelMutation = useCancelTdsTransaction(companyId);

  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!activeCompany) return <EmptyCompanyState icon={Receipt} />;

  const deducteeName = (id: string) => deductees?.items.find((d) => d.id === id)?.name ?? id.slice(0, 8);
  const sectionCode = (id: string) => sections?.find((s) => s.id === id)?.section_code ?? id.slice(0, 8);

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync(values);
      toast({ title: "TDS transaction created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  const runAction = async (
    action: () => Promise<unknown>,
    successMessage: string
  ) => {
    try {
      await action();
      toast({ title: successMessage, variant: "success" });
    } catch (err) {
      toast({
        title: "Action failed",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">TDS Transactions</h1>
          <p className="text-sm text-muted-foreground">
            Applicability and calculation are run per transaction — nothing is deducted silently.
          </p>
        </div>
        <PermissionGate permission="TDS_TRANSACTION_CREATE">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Transaction
          </Button>
        </PermissionGate>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Deductee</TableHead>
                <TableHead>Section</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Gross</TableHead>
                <TableHead className="text-right">TDS</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((t) => (
                <TableRow key={t.id}>
                  <TableCell className="font-medium">{deducteeName(t.deductee_id)}</TableCell>
                  <TableCell className="text-muted-foreground">{sectionCode(t.tds_section_id)}</TableCell>
                  <TableCell className="text-muted-foreground">{t.transaction_date}</TableCell>
                  <TableCell className="text-right">{formatMoney(t.gross_amount)}</TableCell>
                  <TableCell className="text-right">{formatMoney(t.tds_amount)}</TableCell>
                  <TableCell><Badge variant={STATUS_VARIANT[t.status]}>{t.status}</Badge></TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1.5">
                      {(t.status === "DRAFT" || t.status === "REVIEW_REQUIRED") && (
                        <PermissionGate permission="TDS_TRANSACTION_CALCULATE">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => runAction(() => calculateMutation.mutateAsync(t.id), "Calculated")}
                          >
                            <Calculator className="mr-1 h-3.5 w-3.5" /> Calculate
                          </Button>
                        </PermissionGate>
                      )}
                      {t.status === "CALCULATED" && (
                        <PermissionGate permission="TDS_TRANSACTION_UPDATE">
                          <Button
                            size="sm"
                            onClick={() => runAction(() => deductMutation.mutateAsync(t.id), "Deducted")}
                          >
                            <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Deduct
                          </Button>
                        </PermissionGate>
                      )}
                      {(t.status === "DRAFT" || t.status === "CALCULATED") && (
                        <PermissionGate permission="TDS_TRANSACTION_CANCEL">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:text-destructive"
                            onClick={() => runAction(() => cancelMutation.mutateAsync(t.id), "Cancelled")}
                          >
                            <XCircle className="mr-1 h-3.5 w-3.5" /> Cancel
                          </Button>
                        </PermissionGate>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Receipt} title="No TDS transactions yet" hint="Create one against a deductee and section." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New TDS transaction</DialogTitle>
            <DialogDescription>
              Created as DRAFT — run Calculate to evaluate applicability and the deduction amount.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="txn-deductee">Deductee</Label>
              <Controller
                control={control}
                name="deductee_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="txn-deductee"><SelectValue placeholder="Select deductee" /></SelectTrigger>
                    <SelectContent>
                      {(deductees?.items ?? []).map((d) => (
                        <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.deductee_id && <p className="text-xs text-destructive">{errors.deductee_id.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="txn-section">TDS Section</Label>
              <Controller
                control={control}
                name="tds_section_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="txn-section"><SelectValue placeholder="Select section" /></SelectTrigger>
                    <SelectContent>
                      {(sections ?? []).map((s) => (
                        <SelectItem key={s.id} value={s.id}>{s.section_code} — {s.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.tds_section_id && <p className="text-xs text-destructive">{errors.tds_section_id.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="txn-date">Transaction date</Label>
                <Input id="txn-date" type="date" {...register("transaction_date")} />
                {errors.transaction_date && <p className="text-xs text-destructive">{errors.transaction_date.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="txn-amount">Gross amount</Label>
                <Input id="txn-amount" type="number" step="0.01" {...register("gross_amount")} />
                {errors.gross_amount && <p className="text-xs text-destructive">{errors.gross_amount.message}</p>}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Creating…" : "Create"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
