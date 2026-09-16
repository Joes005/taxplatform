import { useQuery } from "@tanstack/react-query";

import { gstr1Service } from "@/services/gstr1Service";

function useGstr1Query<T>(
  key: string,
  fn: (companyId: string, periodId: string) => Promise<T>,
  companyId: string | undefined,
  periodId: string | undefined
) {
  return useQuery({
    queryKey: [key, companyId, periodId],
    queryFn: () => fn(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}

export const useGstr1Overview = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-overview", gstr1Service.overview, companyId, periodId);

export const useGstr1B2B = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-b2b", gstr1Service.b2b, companyId, periodId);

export const useGstr1B2CLarge = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-b2c-large", gstr1Service.b2cLarge, companyId, periodId);

export const useGstr1B2COthers = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-b2c-others", gstr1Service.b2cOthers, companyId, periodId);

export const useGstr1CreditNotes = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-credit-notes", gstr1Service.creditNotes, companyId, periodId);

export const useGstr1DebitNotes = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-debit-notes", gstr1Service.debitNotes, companyId, periodId);

export const useGstr1HSN = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-hsn", gstr1Service.hsnSummary, companyId, periodId);

export const useGstr1Documents = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-documents", gstr1Service.documentSummary, companyId, periodId);

export const useGstr1Validation = (companyId?: string, periodId?: string) =>
  useGstr1Query("gstr1-validation", gstr1Service.validation, companyId, periodId);
