import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  incomeTaxAdvanceTaxService,
  incomeTaxCreditService,
  incomeTaxSelfAssessmentTaxService,
  type CreditEntryPayload,
  type TaxPaymentPayload,
} from "@/services/incomeTaxPaymentService";

export function useAdvanceTaxPayments(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-advance-tax", companyId, financialYearId] : ["income-tax-advance-tax", "none"],
    queryFn: () => incomeTaxAdvanceTaxService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}
export function useCreateAdvanceTaxPayment(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaxPaymentPayload) => incomeTaxAdvanceTaxService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-advance-tax", companyId] }),
  });
}

export function useSelfAssessmentTaxPayments(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-self-assessment-tax", companyId, financialYearId] : ["income-tax-self-assessment-tax", "none"],
    queryFn: () => incomeTaxSelfAssessmentTaxService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}
export function useCreateSelfAssessmentTaxPayment(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaxPaymentPayload) => incomeTaxSelfAssessmentTaxService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-self-assessment-tax", companyId] }),
  });
}

export function useCreditEntries(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-credits", companyId, financialYearId] : ["income-tax-credits", "none"],
    queryFn: () => incomeTaxCreditService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}
export function useCreateCreditEntry(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreditEntryPayload) => incomeTaxCreditService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-credits", companyId] }),
  });
}
