import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  businessIncomePreviewService,
  incomeTaxDeductionService,
  incomeTaxLedgerClassificationService,
  type DeductionPayload,
} from "@/services/incomeTaxDeductionService";
import type { LedgerTaxClassification } from "@/types/incomeTax";

export function useDeductions(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-deductions", companyId, financialYearId] : ["income-tax-deductions", "none"],
    queryFn: () => incomeTaxDeductionService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}

export function useCreateDeduction(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: DeductionPayload) => incomeTaxDeductionService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-deductions", companyId] }),
  });
}

export function useDeleteDeduction(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => incomeTaxDeductionService.delete(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-deductions", companyId] }),
  });
}

export function useSetLedgerClassification(companyId: string) {
  return useMutation({
    mutationFn: ({ ledgerId, classification, notes }: { ledgerId: string; classification: LedgerTaxClassification; notes?: string }) =>
      incomeTaxLedgerClassificationService.set(companyId, ledgerId, classification, notes),
  });
}

export function useBusinessIncomePreview(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["business-income-preview", companyId, financialYearId] : ["business-income-preview", "none"],
    queryFn: () => businessIncomePreviewService.preview(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}
