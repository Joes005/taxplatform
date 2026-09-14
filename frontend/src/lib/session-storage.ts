import type { ActiveCompanyContext, MembershipCompanySummary } from "@/types/api";

const SESSION_KEY = "taxplatform.session";

interface StoredSession {
  companies: MembershipCompanySummary[];
  activeCompany: ActiveCompanyContext | null;
}

export const sessionStorageHelper = {
  save: (session: StoredSession) => {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  },
  load: (): StoredSession | null => {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as StoredSession;
    } catch {
      return null;
    }
  },
  clear: () => {
    localStorage.removeItem(SESSION_KEY);
  },
};
