import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { gstTaxRateService, type GSTTaxRatePayload } from "@/services/gstTaxRateService";

const keys = {
  all: (companyId: string) => ["gst-tax-rates", companyId] as const,
};

export function useGstTaxRates(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.all(companyId) : ["gst-tax-rates", "none"],
    queryFn: () => gstTaxRateService.list(companyId as string),
    enabled: !!companyId,
  });
}

export function useCreateGstTaxRate(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: GSTTaxRatePayload) => gstTaxRateService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
