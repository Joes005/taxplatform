import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Building2, Plus } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { useCompanies, useCreateCompany } from "@/hooks/useCompanies";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CompanyFormDialog } from "./CompanyFormDialog";
import type { CompanyFormValues } from "./companySchema";

export default function CompaniesListPage() {
  const { user, switchCompany } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading } = useCompanies(page, 20);
  const createCompany = useCreateCompany();

  useEffect(() => {
    if (searchParams.get("create") === "true") {
      setCreateOpen(true);
    }
  }, [searchParams]);

  const handleCreate = async (values: CompanyFormValues) => {
    const created = await createCompany.mutateAsync({
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
    toast({ title: "Company created successfully", variant: "success" });
    if (created?.id) {
      await switchCompany(created.id);
      navigate("/dashboard");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Companies</h1>
          <p className="text-sm text-muted-foreground">
            {user?.is_platform_super_admin
              ? "All companies on the platform"
              : "Companies you're a member of"}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-1.5 h-4 w-4" />
          New Company
        </Button>
      </div>

      <div className="rounded-lg border border-border bg-white">
        {isLoading ? (
          <div className="space-y-3 p-6">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Legal Name</TableHead>
                <TableHead>Trade Name</TableHead>
                <TableHead>Business Type</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>PAN</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((company) => (
                <TableRow key={company.id}>
                  <TableCell>
                    <Link
                      to={`/companies/${company.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {company.legal_name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {company.trade_name ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {company.business_type ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {[company.city, company.state].filter(Boolean).join(", ") || "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{company.pan ?? "—"}</TableCell>
                  <TableCell>
                    <Badge variant={company.is_active ? "success" : "secondary"}>
                      {company.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Building2 className="h-6 w-6" />
            </div>
            <div>
              <p className="text-base font-medium">No companies yet</p>
              <p className="text-xs text-muted-foreground max-w-sm mt-1">
                Create your first company workspace to set up default ledgers, financial year, and compliance profiles.
              </p>
            </div>
            <Button onClick={() => setCreateOpen(true)} className="mt-2">
              <Plus className="mr-1.5 h-4 w-4" />
              Create Company
            </Button>
          </div>
        )}
      </div>

      {data && data.pagination.total_pages > 1 && (
        <div className="flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-xs text-muted-foreground">
            Page {data.pagination.page} of {data.pagination.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.pagination.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}

      <CompanyFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Create company"
        description="Add a new company to the platform. Financial and compliance details can be refined later."
        onSubmit={handleCreate}
        submitLabel="Create company"
      />
    </div>
  );
}
