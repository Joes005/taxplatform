import * as React from "react";

import { tokenStorage } from "@/lib/token-storage";
import { sessionStorageHelper } from "@/lib/session-storage";
import { authService } from "@/services/authService";
import type { ActiveCompanyContext, MembershipCompanySummary, User } from "@/types/api";

interface AuthContextValue {
  user: User | null;
  companies: MembershipCompanySummary[];
  activeCompany: ActiveCompanyContext | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  switchCompany: (companyId: string) => Promise<void>;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [companies, setCompanies] = React.useState<MembershipCompanySummary[]>([]);
  const [activeCompany, setActiveCompany] = React.useState<ActiveCompanyContext | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    async function restoreSession() {
      const accessToken = tokenStorage.getAccessToken();
      if (!accessToken) {
        setIsLoading(false);
        return;
      }
      try {
        const restoredUser = await authService.me();
        setUser(restoredUser);
        const cached = sessionStorageHelper.load();
        if (cached) {
          setCompanies(cached.companies);
          setActiveCompany(cached.activeCompany);
        }
      } catch {
        tokenStorage.clear();
        sessionStorageHelper.clear();
      } finally {
        setIsLoading(false);
      }
    }
    restoreSession();
  }, []);

  const login = React.useCallback(async (email: string, password: string) => {
    const data = await authService.login(email, password);
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    sessionStorageHelper.save({ companies: data.companies, activeCompany: data.active_company });
    setUser(data.user);
    setCompanies(data.companies);
    setActiveCompany(data.active_company);
  }, []);

  const logout = React.useCallback(async () => {
    const refreshToken = tokenStorage.getRefreshToken();
    try {
      if (refreshToken) await authService.logout(refreshToken);
    } catch {
      // Best-effort revoke; always clear client state regardless.
    }
    tokenStorage.clear();
    sessionStorageHelper.clear();
    setUser(null);
    setCompanies([]);
    setActiveCompany(null);
  }, []);

  const switchCompany = React.useCallback(
    async (companyId: string) => {
      const context = await authService.selectCompany(companyId);
      setActiveCompany(context);
      sessionStorageHelper.save({ companies, activeCompany: context });
    },
    [companies]
  );

  const hasPermission = React.useCallback(
    (permission: string) => {
      if (user?.is_platform_super_admin) return true;
      return activeCompany?.permissions.includes(permission) ?? false;
    },
    [user, activeCompany]
  );

  const value: AuthContextValue = {
    user,
    companies,
    activeCompany,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
    switchCompany,
    hasPermission,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
