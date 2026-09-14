import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function ForbiddenPage() {
  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center text-center">
      <ShieldAlert className="h-12 w-12 text-muted-foreground" />
      <h1 className="mt-4 text-2xl font-semibold">403 — Access denied</h1>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        You don&apos;t have permission to view this page. If you believe this is a mistake,
        contact your company administrator.
      </p>
      <Button asChild className="mt-6">
        <Link to="/dashboard">Back to dashboard</Link>
      </Button>
    </div>
  );
}
