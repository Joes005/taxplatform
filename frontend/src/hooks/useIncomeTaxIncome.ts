import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  incomeTaxExemptIncomeService,
  incomeTaxHousePropertyService,
  incomeTaxOtherIncomeService,
  incomeTaxSalaryService,
  type ExemptIncomePayload,
  type HousePropertyIncomePayload,
  type OtherIncomePayload,
  type SalaryIncomePayload,
} from "@/services/incomeTaxIncomeService";

export function useSalaryIncome(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-salary", companyId, financialYearId] : ["income-tax-salary", "none"],
    queryFn: () => incomeTaxSalaryService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}
export function useCreateSalaryIncome(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SalaryIncomePayload) => incomeTaxSalaryService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-salary", companyId] }),
  });
}
export function useDeleteSalaryIncome(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => incomeTaxSalaryService.delete(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-salary", companyId] }),
  });
}

export function useHousePropertyIncome(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-house-property", companyId, financialYearId] : ["income-tax-house-property", "none"],
    queryFn: () => incomeTaxHousePropertyService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}
export function useCreateHousePropertyIncome(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: HousePropertyIncomePayload) => incomeTaxHousePropertyService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-house-property", companyId] }),
  });
}
export function useDeleteHousePropertyIncome(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => incomeTaxHousePropertyService.delete(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-house-property", companyId] }),
  });
}

export function useOtherIncome(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-other-income", companyId, financialYearId] : ["income-tax-other-income", "none"],
    queryFn: () => incomeTaxOtherIncomeService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}
export function useCreateOtherIncome(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: OtherIncomePayload) => incomeTaxOtherIncomeService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-other-income", companyId] }),
  });
}
export function useDeleteOtherIncome(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => incomeTaxOtherIncomeService.delete(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-other-income", companyId] }),
  });
}

export function useExemptIncome(companyId: string | undefined, financialYearId: string | undefined) {
  return useQuery({
    queryKey: companyId && financialYearId ? ["income-tax-exempt-income", companyId, financialYearId] : ["income-tax-exempt-income", "none"],
    queryFn: () => incomeTaxExemptIncomeService.list(companyId as string, financialYearId as string),
    enabled: !!companyId && !!financialYearId,
  });
}
export function useCreateExemptIncome(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ExemptIncomePayload) => incomeTaxExemptIncomeService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-exempt-income", companyId] }),
  });
}
export function useDeleteExemptIncome(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => incomeTaxExemptIncomeService.delete(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["income-tax-exempt-income", companyId] }),
  });
}
