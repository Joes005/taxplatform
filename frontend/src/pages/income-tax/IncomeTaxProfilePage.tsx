import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Landmark } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import {
  useCreateIncomeTaxProfile,
  useIncomeTaxProfile,
  useUpdateIncomeTaxProfile,
} from "@/hooks/useIncomeTaxProfile";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { EmptyCompanyState } from "@/pages/accounting/LedgersPage";
import type { TaxpayerType } from "@/types/incomeTax";

const TAXPAYER_TYPES: TaxpayerType[] = ["INDIVIDUAL", "HUF", "PARTNERSHIP", "LLP", "COMPANY", "TRUST", "OTHER"];

const schema = z.object({
  pan: z.string().min(1, "PAN is required"),
  legal_name: z.string().min(1, "Legal name is required"),
  trade_name: z.string().optional(),
  taxpayer_type: z.string().min(1),
  business_nature: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  pincode: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function IncomeTaxProfilePage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  if (!activeCompany) return <EmptyCompanyState icon={Landmark} />;
  const companyId = activeCompany.company_id;

  const { data: profile, isLoading, isError } = useIncomeTaxProfile(companyId);
  const createMutation = useCreateIncomeTaxProfile(companyId);
  const updateMutation = useUpdateIncomeTaxProfile(companyId);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { taxpayer_type: "INDIVIDUAL" } });

  useEffect(() => {
    if (profile) {
      reset({
        pan: profile.pan,
        legal_name: profile.legal_name,
        trade_name: profile.trade_name ?? "",
        taxpayer_type: profile.taxpayer_type,
        business_nature: profile.business_nature ?? "",
        address: profile.address ?? "",
        city: profile.city ?? "",
        state: profile.state ?? "",
        pincode: profile.pincode ?? "",
      });
    }
  }, [profile, reset]);

  if (isLoading) return <Skeleton className="h-64 w-full" />;

  const onSubmit = async (values: FormValues) => {
    try {
      if (profile) {
        await updateMutation.mutateAsync({ ...values, taxpayer_type: values.taxpayer_type as TaxpayerType });
        toast({ title: "Profile updated", variant: "success" });
      } else {
        await createMutation.mutateAsync({ ...values, taxpayer_type: values.taxpayer_type as TaxpayerType });
        toast({ title: "Profile created", variant: "success" });
      }
    } catch (err) {
      toast({ title: "Save failed", description: err instanceof ApiError ? err.message : undefined, variant: "destructive" });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Income Tax Profile</h1>
        <p className="text-sm text-muted-foreground">
          PAN is checked for structural format only — never verified against the e-filing portal.
        </p>
      </div>

      {isError && !profile && (
        <Alert><AlertDescription>No profile yet — fill this in to get started.</AlertDescription></Alert>
      )}

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="pan">PAN</Label>
                <Input id="pan" {...register("pan")} disabled={!!profile} maxLength={10} />
                {errors.pan && <p className="text-xs text-destructive">{errors.pan.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="legal-name">Legal name</Label>
                <Input id="legal-name" {...register("legal_name")} />
                {errors.legal_name && <p className="text-xs text-destructive">{errors.legal_name.message}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="trade-name">Trade name</Label>
                <Input id="trade-name" {...register("trade_name")} />
              </div>
              <div className="space-y-1.5">
                <Label>Taxpayer type</Label>
                <Controller
                  control={control}
                  name="taxpayer_type"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value} disabled={!!profile}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {TAXPAYER_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="business-nature">Business nature</Label>
              <Input id="business-nature" {...register("business_nature")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="address">Address</Label>
              <Input id="address" {...register("address")} />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="city">City</Label>
                <Input id="city" {...register("city")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="state">State</Label>
                <Input id="state" {...register("state")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pincode">Pincode</Label>
                <Input id="pincode" {...register("pincode")} />
              </div>
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : profile ? "Update Profile" : "Create Profile"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
