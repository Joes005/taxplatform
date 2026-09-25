import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Loader2, ArrowRight, FileText, UserCheck, Receipt, Building, ShieldAlert } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/useAuth";
import { useGlobalSearch } from "@/hooks/useSearch";
import type { SearchResultItem } from "@/types/dashboard";

interface GlobalSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GlobalSearchDialog({ open, onOpenChange }: GlobalSearchDialogProps) {
  const navigate = useNavigate();
  const { activeCompany } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useGlobalSearch(
    activeCompany?.company_id,
    { q: searchTerm, limit: 20 },
    open
  );

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setSearchTerm("");
    }
  }, [open]);

  const handleSelect = (item: SearchResultItem) => {
    onOpenChange(false);
    navigate(item.target_url);
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "CUSTOMER":
      case "VENDOR":
        return <UserCheck className="h-4 w-4 text-blue-500" />;
      case "SALES_INVOICE":
      case "PURCHASE_INVOICE":
      case "RECEIPT":
      case "PAYMENT":
        return <Receipt className="h-4 w-4 text-emerald-500" />;
      case "BANK_TRANSACTION":
      case "LEDGER":
        return <Building className="h-4 w-4 text-purple-500" />;
      case "AUDIT_FINDING":
      case "COMPLIANCE_OBLIGATION":
        return <ShieldAlert className="h-4 w-4 text-amber-500" />;
      case "DOCUMENT":
      default:
        return <FileText className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl p-0 gap-0 overflow-hidden">
        <DialogHeader className="p-4 pb-2 border-b border-border">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground shrink-0" />
            <Input
              ref={inputRef}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search customers, vendors, invoices, bank records, ledgers, documents... (min 2 chars)"
              className="border-0 shadow-none focus-visible:ring-0 px-0 h-9 text-sm"
            />
            {isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground shrink-0" />}
          </div>
          <DialogTitle className="sr-only">Global Company Search</DialogTitle>
        </DialogHeader>

        <div className="max-h-[60vh] overflow-y-auto p-2">
          {!activeCompany ? (
            <div className="p-6 text-center text-sm text-muted-foreground">
              Please select an active company to search records.
            </div>
          ) : searchTerm.trim().length < 2 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">
              Type at least 2 characters to search across customers, invoices, documents, banking, and compliance.
            </div>
          ) : isLoading ? (
            <div className="p-6 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Searching company records...
            </div>
          ) : data?.items.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">
              No matching records found for &quot;{searchTerm}&quot; in {activeCompany.company_name}.
            </div>
          ) : (
            <div className="space-y-1">
              <div className="px-2 py-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                Search Results ({data?.total ?? 0})
              </div>
              {data?.items.map((item) => (
                <div
                  key={`${item.type}-${item.id}`}
                  onClick={() => handleSelect(item)}
                  className="flex items-center justify-between p-2.5 rounded-md hover:bg-muted cursor-pointer transition-colors group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted border border-border">
                      {getTypeIcon(item.type)}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-foreground truncate">
                          {item.title}
                        </span>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 uppercase">
                          {item.type.replace(/_/g, " ")}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                        {item.identifier && (
                          <span className="font-mono text-foreground/80">{item.identifier}</span>
                        )}
                        {item.subtitle && <span>• {item.subtitle}</span>}
                        {item.date && <span>• {item.date}</span>}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {item.amount !== null && item.amount !== undefined && (
                      <span className="text-xs font-semibold text-foreground">
                        ₹{Number(item.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </span>
                    )}
                    {item.status && (
                      <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                        {item.status}
                      </Badge>
                    )}
                    <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
