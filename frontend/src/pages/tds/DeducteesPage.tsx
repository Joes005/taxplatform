import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Search, UserRound } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCreateDeductee, useDeductees } from "@/hooks/useDeductees";
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
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";
import type { DeducteeType, PANStatus } from "@/types/tds";

const PAN_STATUS_VARIANT: Record<PANStatus, "success" | "warning" | "destructive" | "secondary"> = {
  AVAILABLE: "success",
  NOT_AVAILABLE: "warning",
  INVALID: "destructive",
  PENDING_REVIEW: "secondary",
};

const deducteeTypes: DeducteeType[] = ["INDIVIDUAL", "COMPANY", "FIRM", "LLP", "TRUST", "HUF", "OTHER"];

const schema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  pan: z.string().max(10).optional().or(z.literal("")),
  deductee_type: z.enum(deducteeTypes as [DeducteeType, ...DeducteeType[]]),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  phone: z.string().max(20).optional().or(z.literal("")),
  state: z.string().max(100).optional().or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

export default function DeducteesPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const [search, setSearch] = useState("");
  const { data, isLoading } = useDeductees(companyId, 1, search || undefined);
  const createMutation = useCreateDeductee(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { deductee_type: "OTHER" } });

  if (!activeCompany) return <EmptyCompanyState icon={UserRound} />;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        ...values,
        pan: values.pan ? values.pan.toUpperCase() : null,
        email: values.email || null,
        phone: values.phone || null,
        state: values.state || null,
      });
      toast({ title: "Deductee created", variant: "success" });
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
          <h1 className="text-2xl font-semibold tracking-tight">Deductees</h1>
          <p className="text-sm text-muted-foreground">People/entities TDS is deducted from when you pay them</p>
        </div>
        <PermissionGate permission="TDS_DEDUCTEE_MANAGE">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Deductee
          </Button>
        </PermissionGate>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search deductees…" className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>PAN</TableHead>
                <TableHead>PAN Status</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="font-medium">{d.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{d.pan ?? "—"}</TableCell>
                  <TableCell><Badge variant={PAN_STATUS_VARIANT[d.pan_status]}>{d.pan_status}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{d.deductee_type}</TableCell>
                  <TableCell><Badge variant={d.is_active ? "success" : "secondary"}>{d.is_active ? "Active" : "Inactive"}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={UserRound} title="No deductees yet" hint="Add a deductee to start recording TDS transactions." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New deductee</DialogTitle>
            <DialogDescription>
              PAN is validated structurally only — no government lookup. Leaving PAN blank marks it
              NOT_AVAILABLE, which uses the higher no-PAN TDS rate.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="ded-name">Name</Label>
              <Input id="ded-name" {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ded-pan">PAN</Label>
                <Input id="ded-pan" className="uppercase" maxLength={10} {...register("pan")} />
                {errors.pan && <p className="text-xs text-destructive">{errors.pan.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ded-type">Type</Label>
                <Controller
                  control={control}
                  name="deductee_type"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger id="ded-type"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {deducteeTypes.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ded-email">Email</Label>
                <Input id="ded-email" type="email" {...register("email")} />
                {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ded-phone">Phone</Label>
                <Input id="ded-phone" {...register("phone")} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ded-state">State</Label>
              <Input id="ded-state" {...register("state")} />
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
