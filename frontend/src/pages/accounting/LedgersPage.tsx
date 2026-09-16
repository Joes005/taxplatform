import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { BookOpen, Plus, Search } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCreateLedger, useLedgers } from "@/hooks/useAccounting";
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
import { formatMoney } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";

const LEDGER_TYPES = ["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE", "RECEIVABLE", "PAYABLE", "BANK", "CASH", "TAX"];

const schema = z.object({
  name: z.string().min(1, "Name is required").max(150),
  code: z.string().max(50).optional().or(z.literal("")),
  ledger_type: z.enum(LEDGER_TYPES as [string, ...string[]], { message: "Select a ledger type" }),
  parent_ledger_id: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function LedgersPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const [search, setSearch] = useState("");
  const { data, isLoading } = useLedgers(companyId, search || undefined);
  const createMutation = useCreateLedger(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!activeCompany) return <EmptyCompanyState icon={BookOpen} />;

  const ledgersByName = new Map((data?.items ?? []).map((l) => [l.id, l.name]));

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        ...values,
        code: values.code || null,
        parent_ledger_id: values.parent_ledger_id || null,
      });
      toast({ title: "Ledger created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Ledgers</h1>
          <p className="text-sm text-muted-foreground">Chart of accounts for {activeCompany.company_name}</p>
        </div>
        <PermissionGate permission="LEDGER_MANAGE">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Ledger
          </Button>
        </PermissionGate>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search ledgers…" className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Parent</TableHead>
                <TableHead>Opening Balance</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((ledger) => (
                <TableRow key={ledger.id}>
                  <TableCell className="font-medium">{ledger.name}</TableCell>
                  <TableCell><Badge variant="outline">{ledger.ledger_type}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">
                    {ledger.parent_ledger_id ? ledgersByName.get(ledger.parent_ledger_id) ?? "—" : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatMoney(ledger.opening_balance)} {ledger.opening_balance_type}
                  </TableCell>
                  <TableCell>
                    <Badge variant={ledger.is_active ? "success" : "secondary"}>
                      {ledger.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={BookOpen} title="No ledgers yet" />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New ledger</DialogTitle>
            <DialogDescription>An accounting account, e.g. "Rent Expense" or "Bank".</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="ledger-name">Name</Label>
              <Input id="ledger-name" {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ledger-type">Type</Label>
              <Controller
                control={control}
                name="ledger_type"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="ledger-type"><SelectValue placeholder="Select a type" /></SelectTrigger>
                    <SelectContent>
                      {LEDGER_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.ledger_type && <p className="text-xs text-destructive">{errors.ledger_type.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ledger-parent">Parent ledger (optional)</Label>
              <Controller
                control={control}
                name="parent_ledger_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="ledger-parent"><SelectValue placeholder="None" /></SelectTrigger>
                    <SelectContent>
                      {(data?.items ?? []).map((l) => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              />
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

export function EmptyCompanyState({ icon: Icon }: { icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-24 text-center">
      <Icon className="h-8 w-8 text-muted-foreground" />
      <p className="text-sm font-medium">No active company selected</p>
      <p className="text-xs text-muted-foreground">Choose a company from the switcher above.</p>
    </div>
  );
}

export function EmptyTableState({
  icon: Icon,
  title,
  hint,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <Icon className="h-8 w-8 text-muted-foreground" />
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
