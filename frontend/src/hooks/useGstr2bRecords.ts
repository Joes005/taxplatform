import { useQuery } from "@tanstack/react-query";

import { gstr2bRecordService } from "@/services/gstr2bRecordService";

export function useGstr2bRecords(companyId: string | undefined, periodId: string | undefined, page = 1) {
  return useQuery({
    queryKey: ["gstr2b-records", companyId, periodId, page],
    queryFn: () => gstr2bRecordService.list(companyId as string, periodId as string, page),
    enabled: !!companyId && !!periodId,
  });
}
