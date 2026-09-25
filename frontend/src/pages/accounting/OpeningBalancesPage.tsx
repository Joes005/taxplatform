import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Scale } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears, useLedgers, useCustomers, useVendors } from "@/hooks/useAccounting";
import { useOpeningBalances, useCreateOpeningBalance } from "@/hooks/useOpeningBalances";
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
import { formatDate, formatMoney } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "./LedgersPage";
import type { BalanceType, OpeningBalanceAccountType } from "@/types/accounting";

const schema = z.object({
  financial_year_id: z.string().min(1, "Select a financial year"),
  account_type: z.enum(["LEDGER", "CUSTOMER", "VENDOR"] as const),
  account_id: z.string().min(1, "Select an account or party"),
  amount: z.coerce.number().min(0, "Amount must be zero or positive"),
  balance_type: z.enum(["DEBIT", "CREDIT"] as const),
  notes: z.string().max(255).optional(),
});

type FormValues = z.infer<typeof schema>;

export default function OpeningBalancesPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";

  const [selectedFy, setSelectedFy] = useState<string>("");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const { data: financialYears } = useFinancialYears(companyId);
  const { data: ledgers } = useLedgers(companyId);
  const { data: customers } = useCustomers(companyId);
  const { data: vendors } = useVendors(companyId);

  const { data: obData, isLoading } = useOpeningBalances(companyId, {
    financialYearId: selectedFy || undefined,
    accountType: selectedType === "ALL" ? undefined : (selectedType as OpeningBalanceAccountType),
  });

  const createMutation = useCreateOpeningBalance(companyId);

  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      account_type: "LEDGER",
      balance_type: "DEBIT",
      amount: 0,
    },
  });

  const formAccountType = watch("account_type");

  useEffect(() => {
    if (financialYears?.items && financialYears.items.length > 0 && !selectedFy) {
      const current = financialYears.items.find((f) => f.is_current) ?? financialYears.items[0];
      if (current) {
        setSelectedFy(current.id);
        setValue("financial_year_id", current.id);
      }
    }
  }, [financialYears, selectedFy, setValue]);

  if (!activeCompany) return <EmptyCompanyState icon={Scale} />;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        financial_year_id: values.financial_year_id,
        account_type: values.account_type,
        account_id: values.account_id,
        amount: values.amount,
        balance_type: values.balance_type,
        notes: values.notes || null,
      });
      toast({ title: "Opening balance recorded", variant: "success" });
      setOpen(false);
      reset({
        financial_year_id: selectedFy,
        account_type: "LEDGER",
        balance_type: "DEBIT",
        amount: 0,
      });
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  const getAccountLabel = (type: OpeningBalanceAccountType, accountId: string) => {
    if (type === "LEDGER") {
      const ledger = ledgers?.items.find((l) => l.id === accountId);
      return ledger ? `${ledger.name} (${ledger.ledger_type})` : accountId;
    }
    if (type === "CUSTOMER") {
      const cust = customers?.items.find((c) => c.id === accountId);
      return cust ? cust.name : accountId;
    }
    if (type === "VENDOR") {
      const vend = vendors?.items.find((v) => v.id === accountId);
      return vend ? vend.name : accountId;
    }
    return accountId;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Opening Balances</h1>
          <p className="text-sm text-muted-foreground">
            Set and review opening balances for general ledger accounts, debtors, and creditors.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} className="gap-1.5">
          <Plus className="h-4 w-4" /> New Opening Balance
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="w-56">
          <Select value={selectedFy} onValueChange={setSelectedFy}>
            <SelectTrigger>
              <SelectValue placeholder="All Financial Years" />
            </SelectTrigger>
            <SelectContent>
              {(financialYears?.items ?? []).map((fy) => (
                <SelectItem key={fy.id} value={fy.id}>
                  {fy.name} {fy.is_current ? "(Current)" : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-48">
          <Select value={selectedType} onValueChange={setSelectedType}>
            <SelectTrigger>
              <SelectValue placeholder="Account Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Account Types</SelectItem>
              <SelectItem value="LEDGER">General Ledger</SelectItem>
              <SelectItem value="CUSTOMER">Customer (Debtor)</SelectItem>
              <SelectItem value="VENDOR">Vendor (Creditor)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : obData && obData.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Account / Party</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Balance Type</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {obData.items.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="font-medium">
                    {getAccountLabel(row.account_type, row.account_id)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{row.account_type}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={row.balance_type === "DEBIT" ? "secondary" : "default"}>
                      {row.balance_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatMoney(row.amount)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{row.notes ?? "—"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(row.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState
            icon={Scale}
            title="No opening balances recorded"
            hint="Set initial debit or credit balances for your accounts to begin the financial year with correct opening figures."
          />
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add opening balance</DialogTitle>
            <DialogDescription>
              Record an initial ledger, debtor, or creditor balance for the financial year.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && (
              <Alert variant="destructive">
                <AlertDescription>{serverError}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label>Financial Year</Label>
                <Link to="/accounting/financial-years" className="text-xs text-primary hover:underline">
                  Manage FY
                </Link>
              </div>
              <Controller
                control={control}
                name="financial_year_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select financial year" />
                    </SelectTrigger>
                    <SelectContent>
                      {(financialYears?.items ?? []).map((fy) => (
                        <SelectItem key={fy.id} value={fy.id}>
                          {fy.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.financial_year_id && (
                <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Account Category</Label>
                <Controller
                  control={control}
                  name="account_type"
                  render={({ field }) => (
                    <Select
                      onValueChange={(val) => {
                        field.onChange(val);
                        setValue("account_id", "");
                      }}
                      value={field.value}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="LEDGER">General Ledger</SelectItem>
                        <SelectItem value="CUSTOMER">Customer</SelectItem>
                        <SelectItem value="VENDOR">Vendor</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Balance Type</Label>
                <Controller
                  control={control}
                  name="balance_type"
                  render={({ field }) => (
                    <Select
                      onValueChange={(v) => field.onChange(v as BalanceType)}
                      value={field.value}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="DEBIT">Debit (Dr)</SelectItem>
                        <SelectItem value="CREDIT">Credit (Cr)</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>
                {formAccountType === "LEDGER"
                  ? "Ledger Account"
                  : formAccountType === "CUSTOMER"
                  ? "Customer"
                  : "Vendor"}
              </Label>
              <Controller
                control={control}
                name="account_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select target account" />
                    </SelectTrigger>
                    <SelectContent>
                      {formAccountType === "LEDGER" &&
                        (ledgers?.items ?? []).map((l) => (
                          <SelectItem key={l.id} value={l.id}>
                            {l.name} ({l.ledger_type})
                          </SelectItem>
                        ))}
                      {formAccountType === "CUSTOMER" &&
                        (customers?.items ?? []).map((c) => (
                          <SelectItem key={c.id} value={c.id}>
                            {c.name}
                          </SelectItem>
                        ))}
                      {formAccountType === "VENDOR" &&
                        (vendors?.items ?? []).map((v) => (
                          <SelectItem key={v.id} value={v.id}>
                            {v.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.account_id && (
                <p className="text-xs text-destructive">{errors.account_id.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="ob-amount">Amount (₹)</Label>
              <Input
                id="ob-amount"
                type="number"
                step="0.01"
                min="0"
                {...register("amount")}
              />
              {errors.amount && (
                <p className="text-xs text-destructive">{errors.amount.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="ob-notes">Notes (optional)</Label>
              <Input
                id="ob-notes"
                placeholder="Reference or notes"
                {...register("notes")}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Saving…" : "Save Opening Balance"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
