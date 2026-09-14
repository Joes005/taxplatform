import { useAuth } from "@/hooks/useAuth";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime, initials } from "@/lib/utils";

export default function SettingsPage() {
  const { user, activeCompany } = useAuth();

  if (!user) return null;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Your account and session details</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-lg font-semibold text-primary-foreground">
              {initials(user.first_name, user.last_name)}
            </span>
            <div>
              <p className="font-medium">
                {user.first_name} {user.last_name}
              </p>
              <p className="text-sm text-muted-foreground">{user.email}</p>
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-4 border-t border-border pt-4 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Account status</dt>
              <dd className="mt-1">
                <Badge variant={user.is_active ? "success" : "secondary"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Email verified</dt>
              <dd className="mt-1">
                <Badge variant={user.is_verified ? "success" : "warning"}>
                  {user.is_verified ? "Verified" : "Pending verification"}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Platform role</dt>
              <dd className="mt-1">
                {user.is_platform_super_admin ? "Platform Super Admin" : "Standard user"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Last login</dt>
              <dd className="mt-1">{formatDateTime(user.last_login_at)}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {activeCompany && (
        <Card>
          <CardHeader>
            <CardTitle>Active session</CardTitle>
            <CardDescription>Company context for this session</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Company</span>
              <span className="font-medium">{activeCompany.company_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Role</span>
              <span className="font-medium">{activeCompany.role_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Permissions</span>
              <span className="font-medium">{activeCompany.permissions.length}</span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
