import { useState } from "react";
import { MoreHorizontal, Plus, Users as UsersIcon } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import {
  useCompanyUsers,
  useCreateCompanyUser,
  useDeactivateCompanyUser,
  useUpdateCompanyUser,
} from "@/hooks/useCompanyUsers";
import { PermissionGate } from "@/components/PermissionGate";
import { ConfirmDialog } from "@/components/ConfirmDialog";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDate, initials } from "@/lib/utils";
import type { CompanyUser, MembershipStatus } from "@/types/api";
import { AddUserDialog } from "./AddUserDialog";
import { EditUserDialog } from "./EditUserDialog";
import type { AddUserFormValues, EditUserFormValues } from "./userSchemas";

const STATUS_VARIANT: Record<MembershipStatus, "success" | "secondary" | "warning"> = {
  ACTIVE: "success",
  INACTIVE: "secondary",
  INVITED: "warning",
};

export default function UsersPage() {
  const { activeCompany } = useAuth();
  const { toast } = useToast();
  const companyId = activeCompany?.company_id;

  const { data, isLoading } = useCompanyUsers(companyId, 1, 50);
  const createUser = useCreateCompanyUser(companyId ?? "");
  const updateUser = useUpdateCompanyUser(companyId ?? "");
  const deactivateUser = useDeactivateCompanyUser(companyId ?? "");

  const [addOpen, setAddOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<CompanyUser | null>(null);
  const [deactivatingUser, setDeactivatingUser] = useState<CompanyUser | null>(null);

  if (!activeCompany) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-24 text-center">
        <UsersIcon className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm font-medium">No active company selected</p>
        <p className="text-xs text-muted-foreground">
          Choose a company from the switcher above to manage its users.
        </p>
      </div>
    );
  }

  const handleAdd = async (values: AddUserFormValues) => {
    await createUser.mutateAsync(values);
    toast({ title: "User added", variant: "success" });
  };

  const handleEdit = async (values: EditUserFormValues) => {
    if (!editingUser) return;
    await updateUser.mutateAsync({ userId: editingUser.user_id, payload: values });
    toast({ title: "User updated", variant: "success" });
  };

  const handleDeactivate = async () => {
    if (!deactivatingUser) return;
    await deactivateUser.mutateAsync(deactivatingUser.user_id);
    toast({ title: "User deactivated", variant: "success" });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
          <p className="text-sm text-muted-foreground">
            Manage who has access to {activeCompany.company_name}
          </p>
        </div>
        <PermissionGate permission="USER_CREATE">
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" />
            Add user
          </Button>
        </PermissionGate>
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
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((member) => (
                <TableRow key={member.membership_id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-secondary text-xs font-semibold">
                        {initials(member.first_name, member.last_name)}
                      </span>
                      <span className="font-medium">
                        {member.first_name} {member.last_name}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{member.email}</TableCell>
                  <TableCell>{member.role_name}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[member.status]}>{member.status}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(member.joined_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <PermissionGate permission="USER_UPDATE">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setEditingUser(member)}>
                            Change role / edit
                          </DropdownMenuItem>
                          <PermissionGate permission="USER_DEACTIVATE">
                            <DropdownMenuItem
                              className="text-destructive"
                              disabled={member.status !== "ACTIVE"}
                              onClick={() => setDeactivatingUser(member)}
                            >
                              Deactivate
                            </DropdownMenuItem>
                          </PermissionGate>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </PermissionGate>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
            <UsersIcon className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium">No users yet</p>
            <p className="text-xs text-muted-foreground">Add your first team member to get started.</p>
          </div>
        )}
      </div>

      <AddUserDialog open={addOpen} onOpenChange={setAddOpen} onSubmit={handleAdd} />
      <EditUserDialog
        open={!!editingUser}
        onOpenChange={(open) => !open && setEditingUser(null)}
        user={editingUser}
        onSubmit={handleEdit}
      />
      <ConfirmDialog
        open={!!deactivatingUser}
        onOpenChange={(open) => !open && setDeactivatingUser(null)}
        title="Deactivate user"
        description={`This will revoke ${deactivatingUser?.email ?? "this user"}'s access to ${activeCompany.company_name}. They can be reactivated later.`}
        confirmLabel="Deactivate"
        onConfirm={handleDeactivate}
      />
    </div>
  );
}
