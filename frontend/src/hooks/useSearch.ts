import { useQuery } from "@tanstack/react-query";
import { searchService, type SearchParams } from "@/services/searchService";

export const searchKeys = {
  all: (companyId: string) => ["search", companyId] as const,
  query: (companyId: string, params: SearchParams) => ["search", companyId, params] as const,
};

export function useGlobalSearch(companyId: string | undefined, params: SearchParams, enabled = true) {
  const queryTrimmed = params.q.trim();
  const shouldRun = !!companyId && queryTrimmed.length >= 2 && enabled;

  return useQuery({
    queryKey: companyId ? searchKeys.query(companyId, params) : ["search", "none"],
    queryFn: () => searchService.search(companyId as string, params),
    enabled: shouldRun,
    staleTime: 5_000,
  });
}
