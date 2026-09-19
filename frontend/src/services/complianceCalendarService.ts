import { apiClient } from "@/lib/api-client";
import type { CalendarDay, ComplianceDashboard } from "@/types/compliance";

export const complianceCalendarService = {
  range: (companyId: string, start: string, end: string) =>
    apiClient.get<CalendarDay[]>(`/compliance/calendar?company_id=${companyId}&start=${start}&end=${end}`),
  month: (companyId: string, year: number, month: number) =>
    apiClient.get<CalendarDay[]>(`/compliance/calendar/month?company_id=${companyId}&year=${year}&month=${month}`),
  dashboard: (companyId: string) =>
    apiClient.get<ComplianceDashboard>(`/compliance/dashboard?company_id=${companyId}`),
};
