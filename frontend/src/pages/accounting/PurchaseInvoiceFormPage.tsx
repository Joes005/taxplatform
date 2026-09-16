import { useMemo, useState } from "react";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useFinancialYears, useVendors } from "@/hooks/useAccounting";
import { useCreatePurchaseInvoice } from "@/hooks/usePurchaseInvoices";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatMoney } from "@/lib/utils";
import { ApiError } from "@/lib/api-client";

const itemSchema = z.object({
  description: z.string().max(500).optional(),
  quantity: z.coerce.number().gt(0, "Required"),
  unit_price: z.coerce.number().min(0),
  discount: z.coerce.number().min(0).optional(),
  cgst_rate: z.coerce.number().min(0).max(100).optional(),
  sgst_rate: z.coerce.number().min(0).max(100).optional(),
  igst_rate: z.coerce.number().min(0).max(100).optional(),
});

const schema = z.object({
  financial_year_id: z.string().min(1, "Select a financial year"),
  vendor_id: z.string().min(1, "Select a vendor"),
  invoice_number: z.string().min(1, "Required").max(50),
  invoice_date: z.string().min(1, "Required"),
  supplier_invoice_number: z.string().max(50).optional(),
  items: z.array(itemSchema).min(1, "Add at least one line item"),
});

type FormValues = z.infer<typeof schema>;

function lineTotal(item: FormValues["items"][number]) {
  const taxable = item.quantity * item.unit_price - (item.discount ?? 0);
  const tax = taxable * ((item.cgst_rate ?? 0) + (item.sgst_rate ?? 0) + (item.igst_rate ?? 0)) / 100;
  return { taxable: Math.max(taxable, 0), total: Math.max(taxable, 0) + Math.max(tax, 0) };
}

export default function PurchaseInvoiceFormPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const companyId = activeCompany?.company_id ?? "";
  const { data: financialYears } = useFinancialYears(companyId);
  const { data: vendors } = useVendors(companyId);
  const createMutation = useCreatePurchaseInvoice(companyId);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { items: [{ quantity: 1, unit_price: 0 }] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "items" });
  const watchedItems = watch("items");

  const totals = useMemo(() => {
    return (watchedItems ?? []).reduce(
      (acc, item) => {
        const { taxable, total } = lineTotal(item);
        return { taxable: acc.taxable + taxable, grandTotal: acc.grandTotal + total };
      },
      { taxable: 0, grandTotal: 0 }
    );
  }, [watchedItems]);

  if (!activeCompany) return null;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      const invoice = await createMutation.mutateAsync({
        ...values,
        items: values.items.map((i) => ({
          ...i,
          discount: i.discount ?? 0,
          cgst_rate: i.cgst_rate ?? 0,
          sgst_rate: i.sgst_rate ?? 0,
          igst_rate: i.igst_rate ?? 0,
        })),
      });
      toast({ title: "Purchase invoice created", variant: "success" });
      navigate(`/accounting/purchase-invoices/${invoice.id}`);
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <Link to="/accounting/purchase-invoices" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to purchase invoices
      </Link>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New purchase invoice</h1>
        <p className="text-sm text-muted-foreground">Totals shown here are a preview — the server recalculates on save.</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {serverError && <Alert variant="destructive"><AlertDescription>{serverError}</AlertDescription></Alert>}

        <Card>
          <CardHeader><CardTitle>Details</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Financial Year</Label>
              <Controller
                control={control}
                name="financial_year_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue placeholder="Select financial year" /></SelectTrigger>
                    <SelectContent>
                      {(financialYears?.items ?? []).map((fy) => <SelectItem key={fy.id} value={fy.id}>{fy.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.financial_year_id && <p className="text-xs text-destructive">{errors.financial_year_id.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label>Vendor</Label>
              <Controller
                control={control}
                name="vendor_id"
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value}>
                    <SelectTrigger><SelectValue placeholder="Select vendor" /></SelectTrigger>
                    <SelectContent>
                      {(vendors?.items ?? []).map((v) => <SelectItem key={v.id} value={v.id}>{v.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.vendor_id && <p className="text-xs text-destructive">{errors.vendor_id.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pinv-number">Invoice Number</Label>
              <Input id="pinv-number" {...register("invoice_number")} />
              {errors.invoice_number && <p className="text-xs text-destructive">{errors.invoice_number.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pinv-date">Invoice Date</Label>
              <Input id="pinv-date" type="date" {...register("invoice_date")} />
              {errors.invoice_date && <p className="text-xs text-destructive">{errors.invoice_date.message}</p>}
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label htmlFor="pinv-supplier-no">Supplier's Invoice Number</Label>
              <Input id="pinv-supplier-no" {...register("supplier_invoice_number")} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Line items</CardTitle>
            <Button type="button" variant="outline" size="sm" onClick={() => append({ quantity: 1, unit_price: 0 })}>
              <Plus className="mr-1 h-3.5 w-3.5" /> Add line
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {fields.map((field, index) => {
              const item = watchedItems?.[index];
              const { taxable, total } = item ? lineTotal(item) : { taxable: 0, total: 0 };
              return (
                <div key={field.id} className="space-y-3 rounded-md border border-border p-3">
                  <div className="flex items-start gap-3">
                    <div className="flex-1 space-y-1.5">
                      <Label className="text-xs">Description</Label>
                      <Input {...register(`items.${index}.description` as const)} />
                    </div>
                    <button type="button" onClick={() => remove(index)} className="mt-6 text-muted-foreground hover:text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="grid grid-cols-6 gap-2">
                    <div className="space-y-1">
                      <Label className="text-xs">Qty</Label>
                      <Input type="number" step="0.001" {...register(`items.${index}.quantity` as const)} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Unit Price</Label>
                      <Input type="number" step="0.01" {...register(`items.${index}.unit_price` as const)} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Discount</Label>
                      <Input type="number" step="0.01" {...register(`items.${index}.discount` as const)} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">CGST %</Label>
                      <Input type="number" step="0.01" {...register(`items.${index}.cgst_rate` as const)} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">SGST %</Label>
                      <Input type="number" step="0.01" {...register(`items.${index}.sgst_rate` as const)} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">IGST %</Label>
                      <Input type="number" step="0.01" {...register(`items.${index}.igst_rate` as const)} />
                    </div>
                  </div>
                  <div className="flex justify-end gap-4 text-xs text-muted-foreground">
                    <span>Taxable: {formatMoney(taxable)}</span>
                    <span className="font-medium text-foreground">Line total: {formatMoney(total)}</span>
                  </div>
                </div>
              );
            })}
            {errors.items && typeof errors.items.message === "string" && (
              <p className="text-xs text-destructive">{errors.items.message}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between pt-6">
            <div className="text-sm text-muted-foreground">Preview total (server recalculates on save)</div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Taxable: {formatMoney(totals.taxable)}</p>
              <p className="text-lg font-semibold">{formatMoney(totals.grandTotal)}</p>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => navigate("/accounting/purchase-invoices")}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save as draft"}</Button>
        </div>
      </form>
    </div>
  );
}
