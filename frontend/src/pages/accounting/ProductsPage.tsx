import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Package, Plus, Search } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCreateProduct, useProducts } from "@/hooks/useAccounting";
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
import { EmptyCompanyState, EmptyTableState } from "./LedgersPage";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  item_type: z.enum(["PRODUCT", "SERVICE"], { message: "Select a type" }),
  hsn_sac: z.string().max(20).optional().or(z.literal("")),
  unit: z.string().max(20).optional().or(z.literal("")),
  tax_rate: z.coerce.number().min(0).max(100).optional(),
});

type FormValues = z.infer<typeof schema>;

export default function ProductsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";
  const [search, setSearch] = useState("");
  const { data, isLoading } = useProducts(companyId, search || undefined);
  const createMutation = useCreateProduct(companyId);
  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!activeCompany) return <EmptyCompanyState icon={Package} />;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createMutation.mutateAsync({
        ...values,
        hsn_sac: values.hsn_sac || null,
        unit: values.unit || null,
        tax_rate: values.tax_rate !== undefined ? String(values.tax_rate) : "0",
      });
      toast({ title: "Item created", variant: "success" });
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
          <h1 className="text-2xl font-semibold tracking-tight">Products &amp; Services</h1>
          <p className="text-sm text-muted-foreground">Items you sell or purchase, with their HSN/SAC and tax rate</p>
        </div>
        <PermissionGate permission="PRODUCT_MANAGE">
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" /> New Item
          </Button>
        </PermissionGate>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search items…" className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>HSN/SAC</TableHead>
                <TableHead>Tax Rate</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell><Badge variant="outline">{p.item_type}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{p.hsn_sac ?? "—"}</TableCell>
                  <TableCell className="text-muted-foreground">{p.tax_rate}%</TableCell>
                  <TableCell><Badge variant={p.is_active ? "success" : "secondary"}>{p.is_active ? "Active" : "Inactive"}</Badge></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyTableState icon={Package} title="No items yet" hint="Add a product or service to use in invoices." />
        )}
      </div>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (o) { reset(); setServerError(null); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New product/service</DialogTitle>
            <DialogDescription>The tax rate here pre-fills invoice line items — Phase 3 does not build a rate engine.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}
            <div className="space-y-1.5">
              <Label htmlFor="prod-name">Name</Label>
              <Input id="prod-name" {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="prod-type">Type</Label>
              <Controller
                control={control}
                name="item_type"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger id="prod-type"><SelectValue placeholder="Select a type" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PRODUCT">Product</SelectItem>
                      <SelectItem value="SERVICE">Service</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.item_type && <p className="text-xs text-destructive">{errors.item_type.message}</p>}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2 space-y-1.5">
                <Label htmlFor="prod-hsn">HSN/SAC</Label>
                <Input id="prod-hsn" {...register("hsn_sac")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-rate">Tax %</Label>
                <Input id="prod-rate" type="number" step="0.01" {...register("tax_rate")} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="prod-unit">Unit</Label>
              <Input id="prod-unit" placeholder="Nos, Kg, Hrs…" {...register("unit")} />
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
