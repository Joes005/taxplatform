import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { companySchema, type CompanyFormValues } from "./companySchema";
import { ApiError } from "@/lib/api-client";
import { useState } from "react";

interface CompanyFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  defaultValues?: Partial<CompanyFormValues>;
  onSubmit: (values: CompanyFormValues) => Promise<void>;
  submitLabel: string;
}

export function CompanyFormDialog({
  open,
  onOpenChange,
  title,
  description,
  defaultValues,
  onSubmit,
  submitLabel,
}: CompanyFormDialogProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CompanyFormValues>({
    resolver: zodResolver(companySchema),
    defaultValues: defaultValues ?? {},
  });

  const handleOpenChange = (next: boolean) => {
    if (next) reset(defaultValues ?? {});
    setServerError(null);
    onOpenChange(next);
  };

  const submit = async (values: CompanyFormValues) => {
    setServerError(null);
    try {
      await onSubmit(values);
      onOpenChange(false);
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(submit)} className="space-y-4">
          {serverError && (
            <Alert variant="destructive">
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 space-y-1.5">
              <Label htmlFor="legal_name">Legal name *</Label>
              <Input id="legal_name" {...register("legal_name")} />
              {errors.legal_name && (
                <p className="text-xs text-destructive">{errors.legal_name.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="trade_name">Trade name</Label>
              <Input id="trade_name" {...register("trade_name")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="business_type">Business type</Label>
              <Input id="business_type" placeholder="Pvt Ltd, LLP, Proprietorship…" {...register("business_type")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="pan">PAN</Label>
              <Input id="pan" placeholder="ABCDE1234F" className="uppercase" {...register("pan")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="gstin">GSTIN</Label>
              <Input id="gstin" placeholder="Optional for Phase 1" className="uppercase" {...register("gstin")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tan">TAN</Label>
              <Input id="tan" placeholder="Optional for Phase 1" className="uppercase" {...register("tan")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="financial_year_start">Financial year start</Label>
              <Input id="financial_year_start" type="date" {...register("financial_year_start")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="state">State</Label>
              <Input id="state" {...register("state")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="city">City</Label>
              <Input id="city" {...register("city")} />
            </div>

            <div className="col-span-2 space-y-1.5">
              <Label htmlFor="address">Address</Label>
              <Input id="address" {...register("address")} />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
