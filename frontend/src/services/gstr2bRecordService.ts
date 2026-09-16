import { apiClient } from "@/lib/api-client";
import type { PaginatedData } from "@/types/api";
import type { GSTR2BRecord } from "@/types/gst";

export const gstr2bRecordService = {
  list: (companyId: string, returnPeriodId: string, page = 1, pageSize = 20) =>
    apiClient.get<PaginatedData<GSTR2BRecord>>(
      `/gst/gstr2b?company_id=${companyId}&return_period_id=${returnPeriodId}&page=${page}&page_size=${pageSize}`
    ),
};
