import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ListTodo, Plus, ShieldCheck } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import {
  useComplianceObligations,
  useCreateComplianceObligation,
  useGenerateComplianceTask,
} from "@/hooks/useComplianceObligations";
import { useComplianceRules, useSetComplianceRuleActive } from "@/hooks/useComplianceRules";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { formatDate } from "@/lib/utils";
import { EmptyCompanyState, EmptyTableState } from "@/pages/accounting/LedgersPage";

const schema = z.object({
  code: z.string().min(1, "Code is required").max(50),
  name: z.string().min(1, "Name is required").max(200),
  description: z.string().optional(),
  category: z.enum(["GST", "TDS", "INCOME_TAX", "AUDIT", "ACCOUNTING", "BANK", "GENERAL", "OTHER"] as const),
  module: z.enum(["GST", "TDS", "INCOME_TAX", "ACCOUNTING", "AUDIT", "GENERAL"] as const),
  frequency: z.enum(["MONTHLY", "QUARTERLY", "ANNUAL", "ONE_TIME"] as const),
  start_date: z.string().min(1, "Start date is required"),
  due_date: z.string().min(1, "Due date is required"),
  grace_date: z.string().optional(),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const),
});

type FormValues = z.infer<typeof schema>;

export default function ComplianceObligationsPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id ?? "";

  const [open, setOpen] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const { data: obligationsData, isLoading: obligationsLoading } = useComplianceObligations(companyId);
  const { data: rulesData, isLoading: rulesLoading } = useComplianceRules(companyId);

  const createObligation = useCreateComplianceObligation(companyId);
  const generateTask = useGenerateComplianceTask(companyId);
  const setRuleActive = useSetComplianceRuleActive(companyId);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      category: "GST",
      module: "GST",
      frequency: "MONTHLY",
      priority: "MEDIUM",
      start_date: new Date().toISOString().slice(0, 10),
      due_date: new Date(Date.now() + 15 * 86400000).toISOString().slice(0, 10),
    },
  });

  if (!activeCompany) return <EmptyCompanyState icon={ShieldCheck} />;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await createObligation.mutateAsync({
        ...values,
        description: values.description || undefined,
        grace_date: values.grace_date || undefined,
      });
      toast({ title: "Compliance obligation created", variant: "success" });
      setOpen(false);
      reset();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  };

  const handleGenerateTask = async (obligationId: string, name: string) => {
    try {
      await generateTask.mutateAsync({ obligationId, title: `File ${name}` });
      toast({ title: "Compliance task generated", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not generate task",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "destructive",
      });
    }
  };

  const handleToggleRule = async (ruleId: string, currentActive: boolean) => {
    try {
      await setRuleActive.mutateAsync({ id: ruleId, active: !currentActive });
      toast({
        title: !currentActive ? "Rule activated" : "Rule deactivated",
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Action failed",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Obligations &amp; Rules</h1>
          <p className="text-sm text-muted-foreground">
            Configure statutory obligations, custom compliance requirements, and automated due-date rules.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} className="gap-1.5">
          <Plus className="h-4 w-4" /> New Obligation
        </Button>
      </div>

      <Tabs defaultValue="obligations">
        <TabsList>
          <TabsTrigger value="obligations">Obligations</TabsTrigger>
          <TabsTrigger value="rules">Statutory &amp; Custom Rules</TabsTrigger>
        </TabsList>

        <TabsContent value="obligations" className="space-y-4 pt-2">
          <div className="rounded-lg border border-border bg-white">
            {obligationsLoading ? (
              <div className="space-y-3 p-6">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : obligationsData && obligationsData.items.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Module</TableHead>
                    <TableHead>Frequency</TableHead>
                    <TableHead>Due Date</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {obligationsData.items.map((ob) => (
                    <TableRow key={ob.id}>
                      <TableCell className="font-mono text-xs font-semibold">{ob.code}</TableCell>
                      <TableCell className="font-medium">{ob.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{ob.category}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{ob.module}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{ob.frequency}</TableCell>
                      <TableCell>{formatDate(ob.due_date)}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            ob.priority === "CRITICAL" || ob.priority === "HIGH"
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {ob.priority}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleGenerateTask(ob.id, ob.name)}
                          className="gap-1 text-primary hover:text-primary"
                        >
                          <ListTodo className="h-3.5 w-3.5" /> Generate Task
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyTableState
                icon={ShieldCheck}
                title="No compliance obligations created"
                hint="Add recurring GST, TDS, or income tax filing obligations to automatically track deadlines and generate tasks."
              />
            )}
          </div>
        </TabsContent>

        <TabsContent value="rules" className="space-y-4 pt-2">
          <div className="rounded-lg border border-border bg-white">
            {rulesLoading ? (
              <div className="space-y-3 p-6">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : rulesData && rulesData.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rule Code</TableHead>
                    <TableHead>Rule Name</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Module</TableHead>
                    <TableHead>Frequency</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rulesData.map((rule) => (
                    <TableRow key={rule.id}>
                      <TableCell className="font-mono text-xs font-semibold">{rule.code}</TableCell>
                      <TableCell>
                        <p className="font-medium">{rule.name}</p>
                        {rule.description && (
                          <p className="text-xs text-muted-foreground">{rule.description}</p>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{rule.category}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{rule.module}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{rule.frequency}</TableCell>
                      <TableCell>
                        <Badge variant={rule.is_active ? "success" : "secondary"}>
                          {rule.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleToggleRule(rule.id, rule.is_active)}
                        >
                          {rule.is_active ? "Deactivate" : "Activate"}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyTableState
                icon={ShieldCheck}
                title="No compliance rules found"
                hint="Statutory GST and TDS compliance rules determine task due dates and calendar events."
              />
            )}
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add compliance obligation</DialogTitle>
            <DialogDescription>
              Create a statutory or internal compliance requirement to track and generate tasks for.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && (
              <Alert variant="destructive">
                <AlertDescription>{serverError}</AlertDescription>
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ob-code">Code</Label>
                <Input id="ob-code" placeholder="e.g. GSTR1_MONTHLY" {...register("code")} />
                {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ob-name">Name</Label>
                <Input id="ob-name" placeholder="GSTR-1 Monthly Return" {...register("name")} />
                {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Category</Label>
                <Controller
                  control={control}
                  name="category"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="GST">GST</SelectItem>
                        <SelectItem value="TDS">TDS</SelectItem>
                        <SelectItem value="INCOME_TAX">Income Tax</SelectItem>
                        <SelectItem value="AUDIT">Audit</SelectItem>
                        <SelectItem value="ACCOUNTING">Accounting</SelectItem>
                        <SelectItem value="BANK">Bank</SelectItem>
                        <SelectItem value="GENERAL">General</SelectItem>
                        <SelectItem value="OTHER">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Module</Label>
                <Controller
                  control={control}
                  name="module"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="GST">GST</SelectItem>
                        <SelectItem value="TDS">TDS</SelectItem>
                        <SelectItem value="INCOME_TAX">Income Tax</SelectItem>
                        <SelectItem value="ACCOUNTING">Accounting</SelectItem>
                        <SelectItem value="AUDIT">Audit</SelectItem>
                        <SelectItem value="GENERAL">General</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Frequency</Label>
                <Controller
                  control={control}
                  name="frequency"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="MONTHLY">Monthly</SelectItem>
                        <SelectItem value="QUARTERLY">Quarterly</SelectItem>
                        <SelectItem value="ANNUAL">Annual</SelectItem>
                        <SelectItem value="ONE_TIME">One Time</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Priority</Label>
                <Controller
                  control={control}
                  name="priority"
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="LOW">Low</SelectItem>
                        <SelectItem value="MEDIUM">Medium</SelectItem>
                        <SelectItem value="HIGH">High</SelectItem>
                        <SelectItem value="CRITICAL">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ob-start">Start Date</Label>
                <Input id="ob-start" type="date" {...register("start_date")} />
                {errors.start_date && (
                  <p className="text-xs text-destructive">{errors.start_date.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ob-due">Due Date</Label>
                <Input id="ob-due" type="date" {...register("due_date")} />
                {errors.due_date && (
                  <p className="text-xs text-destructive">{errors.due_date.message}</p>
                )}
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating…" : "Create Obligation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
