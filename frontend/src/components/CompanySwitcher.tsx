import { useState } from "react";
import { Building2, Check, ChevronsUpDown } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

export function CompanySwitcher() {
  const { companies, activeCompany, switchCompany, user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [switching, setSwitching] = useState(false);

  if (companies.length === 0 && !user?.is_platform_super_admin) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-dashed border-border px-3 py-1.5 text-sm text-muted-foreground">
        <Building2 className="h-4 w-4" />
        No company yet
      </div>
    );
  }

  const handleSwitch = async (companyId: string) => {
    setSwitching(true);
    try {
      await switchCompany(companyId);
      toast({ title: "Company switched", variant: "success" });
      navigate("/dashboard");
    } catch (err) {
      toast({
        title: "Could not switch company",
        description: err instanceof Error ? err.message : undefined,
        variant: "destructive",
      });
    } finally {
      setSwitching(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="min-w-[12rem] justify-between" disabled={switching}>
          <span className="flex items-center gap-2 truncate">
            <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate">{activeCompany?.company_name ?? "Select company"}</span>
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel>Your companies</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {companies.map((c) => (
          <DropdownMenuItem
            key={c.company_id}
            onClick={() => handleSwitch(c.company_id)}
            className="flex items-center justify-between"
          >
            <div className="flex flex-col">
              <span className="font-medium">{c.company_name}</span>
              <span className="text-xs text-muted-foreground">{c.role_name}</span>
            </div>
            {activeCompany?.company_id === c.company_id && (
              <Check className={cn("h-4 w-4 text-primary")} />
            )}
          </DropdownMenuItem>
        ))}
        {companies.length === 0 && (
          <div className="px-2 py-3 text-xs text-muted-foreground">
            No company memberships yet.
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
