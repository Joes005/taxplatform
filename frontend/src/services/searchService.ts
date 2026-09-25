import { apiClient } from "@/lib/api-client";
import type { SearchResponse } from "@/types/dashboard";

export interface SearchParams {
  q: string;
  types?: string[];
  limit?: number;
}

export const searchService = {
  search: (companyId: string, params: SearchParams) => {
    const searchParams = new URLSearchParams({
      company_id: companyId,
      q: params.q,
    });
    if (params.types && params.types.length > 0) {
      searchParams.set("types", params.types.join(","));
    }
    if (params.limit) {
      searchParams.set("limit", params.limit.toString());
    }
    return apiClient.get<SearchResponse>(`/search?${searchParams.toString()}`);
  },
};
