import { Outlet } from "react-router-dom";
import { Landmark } from "lucide-react";

export function AuthLayout() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-secondary px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center justify-center gap-2">
          <Landmark className="h-7 w-7 text-primary" />
          <span className="text-lg font-semibold tracking-tight">Tax Compliance Platform</span>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
