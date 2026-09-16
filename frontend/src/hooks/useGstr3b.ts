import { useQuery } from "@tanstack/react-query";

import { gstr3bService } from "@/services/gstr3bService";

export function useGstr3b(companyId: string | undefined, periodId: string | undefined) {
  return useQuery({
    queryKey: ["gstr3b", companyId, periodId],
    queryFn: () => gstr3bService.get(companyId as string, periodId as string),
    enabled: !!companyId && !!periodId,
  });
}
