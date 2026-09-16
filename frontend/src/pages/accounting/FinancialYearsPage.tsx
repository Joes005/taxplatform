import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CalendarRange, Plus } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCreateFinancialYear, useFinancialYears, useUpdateFinancialYear } from "@/hooks/useAccounting";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
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
import { formatDate } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";

const schema = z
  .object({
    name: z.string().min(1, "Name is required").max(20),
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string().min(1, "End date is required"),
    is_current: z.boolean(),
  })
  .refine((v) => v.end_date > v.start_date, { message: "End date must be after start date", path: ["end_date"] });

type FormValues = z.infer<typeof schema>;

export default function FinancialYearsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const { data, isLoading } = useFinancialYears(companyId);
  const createMutation = useCreateFinancialYear(companyId);
  const updateMutation = useUpdateFinancialYear(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { is_current: true } });

  if (!activeCompany) {
    return <NoCompanyState />;
  }

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync(values);
      toast({ title: "Financial year created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  const setCurrent = async (id: string) => {
    await updateMutation.mutateAsync({ id, payload: { is_current: true } });
    toast({ title: "Current financial year updated", variant: "success" });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Financial Years</h1>
          <p className="text-sm text-muted-foreground">
            Every transaction belongs to exactly one financial year (Apr–Mar)
          </p>
        </div>
        <PermissionGate permission="ACCOUNTING_CREATE">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Financial Year
          </Button>
        </PermissionGate>
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
                <TableHead>Start</TableHead>
                <TableHead>End</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Current</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((fy) => (
                <TableRow key={fy.id}>
                  <TableCell className="font-medium">{fy.name}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(fy.start_date)}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(fy.end_date)}</TableCell>
                  <TableCell>
                    <Badge variant={fy.status === "OPEN" ? "success" : "secondary"}>{fy.status}</Badge>
                  </TableCell>
                  <TableCell>
                    {fy.is_current ? <Badge variant="default">Current</Badge> : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-right">
                    {!fy.is_current && (
                      <PermissionGate permission="ACCOUNTING_UPDATE">
                        <Button variant="ghost" size="sm" onClick={() => setCurrent(fy.id)}>
                          Set current
                        </Button>
                      </PermissionGate>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
            <CalendarRange className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium">No financial years yet</p>
            <p className="text-xs text-muted-foreground">Create one to start recording transactions.</p>
          </div>
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New financial year</DialogTitle>
            <DialogDescription>E.g. "2025-26" for 1 Apr 2025 – 31 Mar 2026</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && (
              <Alert variant="destructive">
                <AlertDescription>{serverError}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="fy-name">Name</Label>
              <Input id="fy-name" placeholder="2025-26" {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="fy-start">Start date</Label>
                <Input id="fy-start" type="date" {...register("start_date")} />
                {errors.start_date && <p className="text-xs text-destructive">{errors.start_date.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="fy-end">End date</Label>
                <Input id="fy-end" type="date" {...register("end_date")} />
                {errors.end_date && <p className="text-xs text-destructive">{errors.end_date.message}</p>}
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("is_current")} className="h-4 w-4 rounded border-input" />
              Make this the current financial year
            </label>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating…" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function NoCompanyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-24 text-center">
      <CalendarRange className="h-8 w-8 text-muted-foreground" />
      <p className="text-sm font-medium">No active company selected</p>
      <p className="text-xs text-muted-foreground">Choose a company from the switcher above.</p>
    </div>
  );
}
