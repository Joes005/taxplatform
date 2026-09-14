import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Pencil } from "lucide-react";

import { useCompany, useUpdateCompany } from "@/hooks/useCompanies";
import { useToast } from "@/hooks/useToast";
import { PermissionGate } from "@/components/PermissionGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";
import { CompanyFormDialog } from "./CompanyFormDialog";
import type { CompanyFormValues } from "./companySchema";

export default function CompanyDetailsPage() {
  const { companyId } = useParams<{ companyId: string }>();
  const { toast } = useToast();
  const { data: company, isLoading } = useCompany(companyId);
  const updateCompany = useUpdateCompany(companyId ?? "");
  const [editOpen, setEditOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!company) return null;

  const handleUpdate = async (values: CompanyFormValues) => {
    await updateCompany.mutateAsync({
      ...values,
      trade_name: values.trade_name || null,
      business_type: values.business_type || null,
      pan: values.pan || null,
      gstin: values.gstin || null,
      tan: values.tan || null,
      state: values.state || null,
      city: values.city || null,
      address: values.address || null,
      financial_year_start: values.financial_year_start || null,
    });
    toast({ title: "Company updated", variant: "success" });
  };

  const fields: [string, string | null][] = [
    ["Legal Name", company.legal_name],
    ["Trade Name", company.trade_name],
    ["Business Type", company.business_type],
    ["PAN", company.pan],
    ["GSTIN", company.gstin],
    ["TAN", company.tan],
    ["State", company.state],
    ["City", company.city],
    ["Address", company.address],
    ["Financial Year Start", formatDate(company.financial_year_start)],
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link
            to="/companies"
            className="mb-2 flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> Back to companies
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{company.legal_name}</h1>
            <Badge variant={company.is_active ? "success" : "secondary"}>
              {company.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>
        </div>
        <PermissionGate permission="COMPANY_UPDATE">
          <Button variant="outline" onClick={() => setEditOpen(true)}>
            <Pencil className="mr-1.5 h-4 w-4" /> Edit
          </Button>
        </PermissionGate>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Company details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
            {fields.map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {label}
                </dt>
                <dd className="mt-1 text-sm">{value || "—"}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>

      <CompanyFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        title="Edit company"
        description="Update this company's profile details."
        defaultValues={{
          legal_name: company.legal_name,
          trade_name: company.trade_name ?? "",
          business_type: company.business_type ?? "",
          pan: company.pan ?? "",
          gstin: company.gstin ?? "",
          tan: company.tan ?? "",
          state: company.state ?? "",
          city: company.city ?? "",
          address: company.address ?? "",
          financial_year_start: company.financial_year_start ?? "",
        }}
        onSubmit={handleUpdate}
        submitLabel="Save changes"
      />
    </div>
  );
}
