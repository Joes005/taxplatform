import { apiClient } from "@/lib/api-client";
import type {
  GSTR1B2BRow,
  GSTR1B2CLargeRow,
  GSTR1B2COthersRow,
  GSTR1DocumentSummaryRow,
  GSTR1HSNRow,
  GSTR1NoteRow,
  GSTR1Overview,
  GSTR1ValidationResponse,
} from "@/types/gst";

const base = (companyId: string, periodId: string) =>
  `/gst/return-periods/${periodId}/gstr1?company_id=${companyId}`;

export const gstr1Service = {
  overview: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1Overview>(base(companyId, periodId)),
  b2b: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1B2BRow[]>(`/gst/return-periods/${periodId}/gstr1/b2b?company_id=${companyId}`),
  b2cLarge: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1B2CLargeRow[]>(
      `/gst/return-periods/${periodId}/gstr1/b2c-large?company_id=${companyId}`
    ),
  b2cOthers: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1B2COthersRow[]>(
      `/gst/return-periods/${periodId}/gstr1/b2c-others?company_id=${companyId}`
    ),
  exports: (companyId: string, periodId: string) =>
    apiClient.get<unknown[]>(`/gst/return-periods/${periodId}/gstr1/exports?company_id=${companyId}`),
  creditNotes: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1NoteRow[]>(
      `/gst/return-periods/${periodId}/gstr1/credit-notes?company_id=${companyId}`
    ),
  debitNotes: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1NoteRow[]>(
      `/gst/return-periods/${periodId}/gstr1/debit-notes?company_id=${companyId}`
    ),
  hsnSummary: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1HSNRow[]>(`/gst/return-periods/${periodId}/gstr1/hsn?company_id=${companyId}`),
  documentSummary: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1DocumentSummaryRow[]>(
      `/gst/return-periods/${periodId}/gstr1/documents?company_id=${companyId}`
    ),
  validation: (companyId: string, periodId: string) =>
    apiClient.get<GSTR1ValidationResponse>(
      `/gst/return-periods/${periodId}/gstr1/validation?company_id=${companyId}`
    ),
};
