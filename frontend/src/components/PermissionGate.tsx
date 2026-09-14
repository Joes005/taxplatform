import type { ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";

/**
 * Hides UI for users lacking a permission. This is a UX convenience only —
 * the backend is the source of truth and re-validates every request, so
 * hiding a button here never substitutes for a server-side check.
 */
export function PermissionGate({
  permission,
  children,
  fallback = null,
}: {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { hasPermission } = useAuth();
  return hasPermission(permission) ? <>{children}</> : <>{fallback}</>;
}
