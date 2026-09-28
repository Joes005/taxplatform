import { useState } from "react";
import { Link } from "react-router-dom";
import {
  CalendarClock,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  FileDown,
  Search,
  MoreVertical,
  Paperclip,
  UserCheck,
  RefreshCw,
  Eye,
  Send,
  RotateCcw,
  Calendar as CalendarIcon,
  CheckSquare,
  ShieldCheck,
} from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import {
  useComplianceControlCenter,
  useComplianceObligations,
  useSweepOverdueObligations,
} from "@/hooks/useComplianceObligations";
import { useCompanyUsers } from "@/hooks/useCompanyUsers";
import { complianceObligationService } from "@/services/complianceObligationService";
import { ComplianceHealthCard } from "@/components/compliance/ComplianceHealthCard";
import {
  ComplianceStatusBadge,
  ComplianceReadinessBadge,
} from "@/components/compliance/ComplianceStatusBadge";
import { ReadinessCheckDialog } from "@/components/compliance/ReadinessCheckDialog";
import { EvidencePanel } from "@/components/compliance/EvidencePanel";
import { AssignDialog } from "@/components/compliance/AssignDialog";
import {
  ReviewApprovalDialog,
  type ReviewActionType,
} from "@/components/compliance/ReviewApprovalDialog";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyCompanyState } from "@/pages/accounting/LedgersPage";
import { triggerBlobDownload, formatDate } from "@/lib/utils";
import type {
  ComplianceCategory,
  ComplianceObligation,
  ComplianceObligationStatus,
} from "@/types/compliance";

export default function ComplianceDashboardPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";

  // Filters for All Obligations tab
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [readinessFilter, setReadinessFilter] = useState<string>("all");

  // Dialog states
  const [readinessModalObligation, setReadinessModalObligation] = useState<ComplianceObligation | null>(null);
  const [evidenceModalObligation, setEvidenceModalObligation] = useState<ComplianceObligation | null>(null);
  const [assignModalObligation, setAssignModalObligation] = useState<ComplianceObligation | null>(null);
  const [reviewDialogState, setReviewDialogState] = useState<{
    open: boolean;
    obligation: ComplianceObligation | null;
    actionType: ReviewActionType;
  }>({
    open: false,
    obligation: null,
    actionType: "SUBMIT",
  });

  const [isExporting, setIsExporting] = useState(false);

  // Queries
  const { data: summary, isLoading: isSummaryLoading, refetch: refetchSummary } =
    useComplianceControlCenter(companyId);

  const { data: obligationsData, isLoading: isObligationsLoading } = useComplianceObligations(
    companyId,
    {
      search: searchTerm || undefined,
      category: categoryFilter === "all" ? undefined : (categoryFilter as ComplianceCategory),
      status: statusFilter === "all" ? undefined : (statusFilter as ComplianceObligationStatus),
      readiness_status: readinessFilter === "all" ? undefined : readinessFilter,
      page: 1,
      page_size: 100,
    }
  );

  const { data: companyUsers } = useCompanyUsers(companyId, 1, 100);
  const sweepMutation = useSweepOverdueObligations(companyId);

  if (!activeCompany) return <EmptyCompanyState icon={CalendarClock} />;

  const userMap = new Map<string, string>();
  companyUsers?.items.forEach((u) => {
    userMap.set(u.user_id, `${u.first_name} ${u.last_name}`);
  });

  const getUserLabel = (id?: string | null) => (id ? userMap.get(id) || id.slice(0, 8) : "—");

  const handleSweep = async () => {
    try {
      const res = await sweepMutation.mutateAsync();
      toast({
        title: "Overdue sweep completed",
        description: `${res.marked_overdue} obligation(s) marked overdue.`,
        variant: "success",
      });
      refetchSummary();
    } catch {
      toast({
        title: "Sweep failed",
        description: "Could not evaluate overdue obligations.",
        variant: "destructive",
      });
    }
  };

  const handleExport = async (type: "obligations" | "readiness", format: "csv" | "xlsx") => {
    setIsExporting(true);
    try {
      let res;
      if (type === "obligations") {
        res = await complianceObligationService.exportObligations(companyId, format);
      } else {
        res = await complianceObligationService.exportReadiness(companyId, format);
      }
      triggerBlobDownload(res.blob, res.filename || `compliance-${type}.${format}`);
      toast({
        title: "Report exported",
        description: `Exported ${type} report as ${format.toUpperCase()}.`,
        variant: "success",
      });
    } catch {
      toast({
        title: "Export failed",
        description: "Could not generate export.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const openReviewModal = (obligation: ComplianceObligation, actionType: ReviewActionType) => {
    setReviewDialogState({
      open: true,
      obligation,
      actionType,
    });
  };

  const calcDaysOverdue = (dueDate: string) => {
    const diff = Date.now() - new Date(dueDate).getTime();
    return Math.max(1, Math.floor(diff / (1000 * 60 * 60 * 24)));
  };

  const allObligations: ComplianceObligation[] = obligationsData?.items || [];
  const overdueList: ComplianceObligation[] = allObligations.filter(
    (ob) => ob.is_overdue || ob.status === "OVERDUE"
  );
  const blockedList: ComplianceObligation[] = allObligations.filter(
    (ob) => ob.status === "BLOCKED" || ob.readiness_status === "BLOCKED"
  );
  const awaitingReviewList: ComplianceObligation[] = allObligations.filter(
    (ob) => ob.status === "READY_FOR_REVIEW" || ob.status === "UNDER_REVIEW"
  );
  const upcomingList: ComplianceObligation[] = [...allObligations]
    .filter((ob) => !["COMPLETED", "FULFILLED", "CANCELLED"].includes(ob.status))
    .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime());

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Compliance Control Center</h1>
            <Badge variant="outline" className="border-primary/40 text-primary text-xs">
              Phase 13
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Centrally orchestrate obligations, prerequisites, cross-module readiness, evidence, and CA sign-off.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSweep}
            disabled={sweepMutation.isPending}
            className="h-8 text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${sweepMutation.isPending ? "animate-spin" : ""}`} />
            Sweep Overdue
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" disabled={isExporting} className="h-8 text-xs flex items-center gap-1.5">
                <FileDown className="h-3.5 w-3.5" />
                Export Reports
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Compliance Exports</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => handleExport("obligations", "csv")}>
                Obligations Status (CSV)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport("obligations", "xlsx")}>
                Obligations Status (Excel)
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleExport("readiness", "csv")}>
                Prerequisite Readiness (CSV)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport("readiness", "xlsx")}>
                Prerequisite Readiness (Excel)
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button variant="outline" size="sm" asChild className="h-8 text-xs">
            <Link to="/compliance/calendar" className="flex items-center gap-1.5">
              <CalendarIcon className="h-3.5 w-3.5" /> Calendar
            </Link>
          </Button>

          <Button variant="outline" size="sm" asChild className="h-8 text-xs">
            <Link to="/compliance/tasks" className="flex items-center gap-1.5">
              <CheckSquare className="h-3.5 w-3.5" /> Tasks
            </Link>
          </Button>

          <Button size="sm" asChild className="h-8 text-xs">
            <Link to="/compliance/obligations" className="flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" /> Manage Rules
            </Link>
          </Button>
        </div>
      </div>

      {/* Compliance Health Card */}
      <ComplianceHealthCard companyId={companyId} />

      {/* Summary KPI Cards */}
      {isSummaryLoading ? (
        <Skeleton className="h-20 w-full" />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Card className="border-border">
            <CardContent className="pt-4 pb-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total</p>
              <p className="mt-1 text-xl font-bold">{summary?.total_obligations ?? 0}</p>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="pt-4 pb-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Due Soon (7d)</p>
              <p className="mt-1 text-xl font-bold text-amber-500">{summary?.due_soon ?? 0}</p>
            </CardContent>
          </Card>
          <Card className={`border-border ${summary && summary.overdue > 0 ? "border-destructive/50 bg-destructive/5" : ""}`}>
            <CardContent className="pt-4 pb-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Overdue</p>
              <p className={`mt-1 text-xl font-bold ${summary && summary.overdue > 0 ? "text-destructive" : ""}`}>
                {summary?.overdue ?? 0}
              </p>
            </CardContent>
          </Card>
          <Card className={`border-border ${summary && summary.blocked > 0 ? "border-amber-500/50 bg-amber-500/5" : ""}`}>
            <CardContent className="pt-4 pb-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Blocked</p>
              <p className={`mt-1 text-xl font-bold ${summary && summary.blocked > 0 ? "text-amber-500" : ""}`}>
                {summary?.blocked ?? 0}
              </p>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="pt-4 pb-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Awaiting Review</p>
              <p className="mt-1 text-xl font-bold text-sky-500">{summary?.awaiting_review ?? 0}</p>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="pt-4 pb-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Completed</p>
              <p className="mt-1 text-xl font-bold text-emerald-500">{summary?.completed ?? 0}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Workspace Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="bg-muted/60 p-1">
          <TabsTrigger value="overview" className="text-xs">
            Urgent &amp; Action Items
            {(overdueList.length > 0 || blockedList.length > 0 || awaitingReviewList.length > 0) && (
              <Badge variant="destructive" className="ml-1.5 text-[10px] py-0 px-1">
                {overdueList.length + blockedList.length + awaitingReviewList.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="all" className="text-xs">
            All Obligations ({obligationsData?.pagination?.total ?? obligationsData?.items?.length ?? 0})
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Actionable Overview */}
        <TabsContent value="overview" className="space-y-6">
          {/* Overdue Section */}
          {overdueList.length > 0 && (
            <Card className="border-destructive/40 shadow-sm">
              <CardHeader className="pb-3 bg-destructive/5 border-b border-destructive/20">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-destructive" />
                  <div>
                    <CardTitle className="text-sm font-semibold text-destructive">
                      Overdue Obligations ({overdueList.length})
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Past statutory deadline. Requires immediate review, filing preparation, or penalty assessment.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="text-xs">Obligation</TableHead>
                      <TableHead className="text-xs">Category</TableHead>
                      <TableHead className="text-xs">Due Date</TableHead>
                      <TableHead className="text-xs">Overdue By</TableHead>
                      <TableHead className="text-xs">Owner</TableHead>
                      <TableHead className="text-xs">Readiness</TableHead>
                      <TableHead className="text-xs text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {overdueList.map((ob) => (
                      <TableRow key={ob.id} className="text-xs">
                        <TableCell>
                          <div className="font-semibold text-foreground">{ob.name}</div>
                          <div className="text-[11px] text-muted-foreground font-mono">{ob.code}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[10px]">{ob.category}</Badge>
                        </TableCell>
                        <TableCell className="font-medium text-destructive">{formatDate(ob.due_date)}</TableCell>
                        <TableCell>
                          <Badge variant="destructive" className="text-[10px]">
                            {ob.days_overdue ?? calcDaysOverdue(ob.due_date)} days
                          </Badge>
                        </TableCell>
                        <TableCell>{getUserLabel(ob.assigned_to)}</TableCell>
                        <TableCell>
                          <ComplianceReadinessBadge status={ob.readiness_status} />
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs px-2"
                              onClick={() => setReadinessModalObligation(ob)}
                            >
                              Check
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs px-2"
                              onClick={() => setEvidenceModalObligation(ob)}
                            >
                              <Paperclip className="h-3 w-3" />
                            </Button>
                            <Button
                              size="sm"
                              className="h-7 text-xs px-2"
                              onClick={() => openReviewModal(ob, "COMPLETE")}
                            >
                              Complete
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* Blocked Obligations */}
          {blockedList.length > 0 && (
            <Card className="border-amber-500/40 shadow-sm">
              <CardHeader className="pb-3 bg-amber-500/5 border-b border-amber-500/20">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                  <div>
                    <CardTitle className="text-sm font-semibold text-amber-500">
                      Blocked by Prerequisites ({blockedList.length})
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Upstream accounting reconciliation, invoices, or tax profiles missing. Resolve blockers to proceed.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="text-xs">Obligation</TableHead>
                      <TableHead className="text-xs">Due Date</TableHead>
                      <TableHead className="text-xs">Status</TableHead>
                      <TableHead className="text-xs">Blocking Issues</TableHead>
                      <TableHead className="text-xs text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {blockedList.map((ob: ComplianceObligation) => {
                      const failures =
                        (ob.readiness_details?.blocking_failures as string[]) ||
                        ob.readiness_details?.checks?.filter((c) => c.blocking && c.status === "FAIL").map((c) => c.check_code) ||
                        [];
                      return (
                        <TableRow key={ob.id} className="text-xs">
                          <TableCell>
                            <div className="font-semibold text-foreground">{ob.name}</div>
                            <div className="text-[11px] text-muted-foreground font-mono">{ob.code}</div>
                          </TableCell>
                          <TableCell>{formatDate(ob.due_date)}</TableCell>
                          <TableCell>
                            <ComplianceStatusBadge status={ob.status} />
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {failures.map((f) => (
                                <Badge key={f} variant="destructive" className="text-[10px] py-0 px-1 font-mono">
                                  {f}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs"
                              onClick={() => setReadinessModalObligation(ob)}
                            >
                              Resolve Blocker
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* Awaiting CA / Auditor Review */}
          {awaitingReviewList.length > 0 && (
            <Card className="border-sky-500/40 shadow-sm">
              <CardHeader className="pb-3 bg-sky-500/5 border-b border-sky-500/20">
                <div className="flex items-center gap-2">
                  <UserCheck className="h-5 w-5 text-sky-500" />
                  <div>
                    <CardTitle className="text-sm font-semibold text-sky-600">
                      Awaiting CA / Auditor Sign-Off ({awaitingReviewList.length})
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Submitted for verification. Auditor or Admin review required before marking completed.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="text-xs">Obligation</TableHead>
                      <TableHead className="text-xs">Due Date</TableHead>
                      <TableHead className="text-xs">Status</TableHead>
                      <TableHead className="text-xs">Reviewer</TableHead>
                      <TableHead className="text-xs text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {awaitingReviewList.map((ob) => (
                      <TableRow key={ob.id} className="text-xs">
                        <TableCell>
                          <div className="font-semibold text-foreground">{ob.name}</div>
                          <div className="text-[11px] text-muted-foreground font-mono">{ob.code}</div>
                        </TableCell>
                        <TableCell>{formatDate(ob.due_date)}</TableCell>
                        <TableCell>
                          <ComplianceStatusBadge status={ob.status} />
                        </TableCell>
                        <TableCell>{getUserLabel(ob.reviewer_id)}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs"
                              onClick={() => setEvidenceModalObligation(ob)}
                            >
                              <Paperclip className="h-3 w-3 mr-1" /> Evidence
                            </Button>
                            <Button
                              variant="default"
                              size="sm"
                              className="h-7 text-xs"
                              onClick={() => openReviewModal(ob, "APPROVE")}
                            >
                              Approve
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs text-destructive hover:text-destructive"
                              onClick={() => openReviewModal(ob, "REJECT")}
                            >
                              Return
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* Upcoming Obligations */}
          <Card className="border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-semibold">Upcoming Statutory Deadlines</CardTitle>
                  <CardDescription className="text-xs">
                    Next compliance obligations ordered chronologically by statutory due date.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {upcomingList.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No upcoming deadlines in the next 30 days.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="text-xs">Obligation</TableHead>
                      <TableHead className="text-xs">Category</TableHead>
                      <TableHead className="text-xs">Frequency</TableHead>
                      <TableHead className="text-xs">Due Date</TableHead>
                      <TableHead className="text-xs">Readiness</TableHead>
                      <TableHead className="text-xs">Status</TableHead>
                      <TableHead className="text-xs text-right">Quick Check</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {upcomingList.map((ob) => (
                      <TableRow key={ob.id} className="text-xs">
                        <TableCell>
                          <div className="font-semibold text-foreground">{ob.name}</div>
                          <div className="text-[11px] text-muted-foreground font-mono">{ob.code}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[10px]">{ob.category}</Badge>
                        </TableCell>
                        <TableCell className="capitalize text-muted-foreground">
                          {ob.frequency.toLowerCase().replace("_", " ")}
                        </TableCell>
                        <TableCell className="font-medium">{formatDate(ob.due_date)}</TableCell>
                        <TableCell>
                          <ComplianceReadinessBadge status={ob.readiness_status} />
                        </TableCell>
                        <TableCell>
                          <ComplianceStatusBadge status={ob.status} />
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => setReadinessModalObligation(ob)}
                          >
                            Check Readiness
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: All Obligations */}
        <TabsContent value="all" className="space-y-4">
          {/* Filters Bar */}
          <Card className="border-border">
            <CardContent className="p-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Search obligation name or code..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-8 h-8 text-xs"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                    <SelectTrigger className="w-[120px] h-8 text-xs">
                      <SelectValue placeholder="Category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all" className="text-xs">All Categories</SelectItem>
                      <SelectItem value="GST" className="text-xs">GST</SelectItem>
                      <SelectItem value="TDS" className="text-xs">TDS</SelectItem>
                      <SelectItem value="INCOME_TAX" className="text-xs">Income Tax</SelectItem>
                      <SelectItem value="AUDIT" className="text-xs">Audit</SelectItem>
                      <SelectItem value="BANK" className="text-xs">Bank</SelectItem>
                      <SelectItem value="ACCOUNTING" className="text-xs">Accounting</SelectItem>
                      <SelectItem value="GENERAL" className="text-xs">General</SelectItem>
                    </SelectContent>
                  </Select>

                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-[120px] h-8 text-xs">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all" className="text-xs">All Statuses</SelectItem>
                      <SelectItem value="DRAFT" className="text-xs">Draft</SelectItem>
                      <SelectItem value="ACTIVE" className="text-xs">Active</SelectItem>
                      <SelectItem value="IN_PROGRESS" className="text-xs">In Progress</SelectItem>
                      <SelectItem value="READY_FOR_REVIEW" className="text-xs">Ready Review</SelectItem>
                      <SelectItem value="APPROVED" className="text-xs">Approved</SelectItem>
                      <SelectItem value="COMPLETED" className="text-xs">Completed</SelectItem>
                      <SelectItem value="BLOCKED" className="text-xs">Blocked</SelectItem>
                      <SelectItem value="OVERDUE" className="text-xs">Overdue</SelectItem>
                    </SelectContent>
                  </Select>

                  <Select value={readinessFilter} onValueChange={setReadinessFilter}>
                    <SelectTrigger className="w-[130px] h-8 text-xs">
                      <SelectValue placeholder="Readiness" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all" className="text-xs">All Readiness</SelectItem>
                      <SelectItem value="READY" className="text-xs">Ready</SelectItem>
                      <SelectItem value="READY_WITH_WARNINGS" className="text-xs">With Warnings</SelectItem>
                      <SelectItem value="BLOCKED" className="text-xs">Blocked</SelectItem>
                      <SelectItem value="MISSING_DATA" className="text-xs">Missing Data</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Obligations Master Table */}
          <Card className="border-border">
            <CardContent className="p-0">
              {isObligationsLoading ? (
                <div className="p-6 space-y-2">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : !obligationsData || obligationsData.items.length === 0 ? (
                <div className="p-12 text-center text-xs text-muted-foreground space-y-2">
                  <p className="font-semibold text-foreground">No compliance obligations match your filters.</p>
                  <p>Generate obligations for this financial year or configure recurring schedules.</p>
                  <Button variant="outline" size="sm" asChild className="mt-2 text-xs">
                    <Link to="/compliance/obligations">Go to Obligation Rules</Link>
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="text-xs">Code &amp; Name</TableHead>
                      <TableHead className="text-xs">Category</TableHead>
                      <TableHead className="text-xs">Frequency</TableHead>
                      <TableHead className="text-xs">Due Date</TableHead>
                      <TableHead className="text-xs">Prerequisites</TableHead>
                      <TableHead className="text-xs">Status</TableHead>
                      <TableHead className="text-xs">Owner / Reviewer</TableHead>
                      <TableHead className="text-xs text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {obligationsData.items.map((ob) => (
                      <TableRow key={ob.id} className="text-xs">
                        <TableCell>
                          <div className="font-semibold text-foreground">{ob.name}</div>
                          <div className="text-[11px] text-muted-foreground font-mono">{ob.code}</div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[10px]">{ob.category}</Badge>
                        </TableCell>
                        <TableCell className="capitalize text-muted-foreground">
                          {ob.frequency.toLowerCase().replace("_", " ")}
                        </TableCell>
                        <TableCell className="font-medium">{formatDate(ob.due_date)}</TableCell>
                        <TableCell>
                          <div
                            className="cursor-pointer"
                            onClick={() => setReadinessModalObligation(ob)}
                            title="Click to inspect prerequisite checklist"
                          >
                            <ComplianceReadinessBadge status={ob.readiness_status} />
                          </div>
                        </TableCell>
                        <TableCell>
                          <ComplianceStatusBadge status={ob.status} />
                        </TableCell>
                        <TableCell>
                          <div className="space-y-0.5">
                            <div className="text-foreground">
                              <span className="text-[10px] text-muted-foreground">Owner: </span>
                              {getUserLabel(ob.assigned_to)}
                            </div>
                            {ob.reviewer_id && (
                              <div className="text-muted-foreground text-[11px]">
                                <span className="text-[10px]">Reviewer: </span>
                                {getUserLabel(ob.reviewer_id)}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                                <MoreVertical className="h-3.5 w-3.5" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="text-xs">
                              <DropdownMenuLabel>Obligation Actions</DropdownMenuLabel>
                              <DropdownMenuItem onClick={() => setReadinessModalObligation(ob)}>
                                <Eye className="h-3.5 w-3.5 mr-2" /> Check Readiness
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => setEvidenceModalObligation(ob)}>
                                <Paperclip className="h-3.5 w-3.5 mr-2" /> Evidence Documents
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => setAssignModalObligation(ob)}>
                                <UserCheck className="h-3.5 w-3.5 mr-2" /> Assign Owner / Reviewer
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={() => openReviewModal(ob, "SUBMIT")}>
                                <Send className="h-3.5 w-3.5 mr-2" /> Submit for Review
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openReviewModal(ob, "APPROVE")}>
                                <CheckCircle2 className="h-3.5 w-3.5 mr-2" /> Approve (CA Sign-off)
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openReviewModal(ob, "REJECT")}>
                                <AlertTriangle className="h-3.5 w-3.5 mr-2" /> Return for Changes
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openReviewModal(ob, "COMPLETE")}>
                                <CheckCircle2 className="h-3.5 w-3.5 mr-2" /> Mark Completed
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openReviewModal(ob, "REOPEN")}>
                                <RotateCcw className="h-3.5 w-3.5 mr-2" /> Reopen Obligation
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Cross-Module Readiness Dialog */}
      <ReadinessCheckDialog
        open={!!readinessModalObligation}
        onOpenChange={(open) => !open && setReadinessModalObligation(null)}
        companyId={companyId}
        obligation={readinessModalObligation}
      />

      {/* Evidence Management Dialog */}
      <EvidencePanel
        open={!!evidenceModalObligation}
        onOpenChange={(open) => !open && setEvidenceModalObligation(null)}
        companyId={companyId}
        obligation={evidenceModalObligation}
      />

      {/* Assign Owner/Reviewer Dialog */}
      <AssignDialog
        open={!!assignModalObligation}
        onOpenChange={(open) => !open && setAssignModalObligation(null)}
        companyId={companyId}
        obligation={assignModalObligation}
      />

      {/* Review, Approve, Reject, Complete, Reopen Dialog */}
      <ReviewApprovalDialog
        open={reviewDialogState.open}
        onOpenChange={(open) =>
          setReviewDialogState((prev) => ({ ...prev, open }))
        }
        companyId={companyId}
        obligation={reviewDialogState.obligation}
        actionType={reviewDialogState.actionType}
      />
    </div>
  );
}
