import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { importService, type CreateImportJobPayload } from "@/services/importService";
import type { ImportType } from "@/types/accounting";

const keys = {
  all: (companyId: string) => ["imports", companyId] as const,
  list: (companyId: string) => ["imports", companyId, "list"] as const,
  detail: (companyId: string, jobId: string) => ["imports", companyId, "detail", jobId] as const,
  preview: (companyId: string, jobId: string, status?: string) =>
    ["imports", companyId, "preview", jobId, status] as const,
  errors: (companyId: string, jobId: string) => ["imports", companyId, "errors", jobId] as const,
};

export function useImportFields(importType: ImportType | null) {
  return useQuery({
    queryKey: ["import-fields", importType],
    queryFn: () => importService.getFields(importType as ImportType),
    enabled: !!importType,
  });
}

export function useImportJobs(companyId: string | undefined) {
  return useQuery({
    queryKey: companyId ? keys.list(companyId) : ["imports", "none"],
    queryFn: () => importService.list(companyId as string),
    enabled: !!companyId,
  });
}

export function useImportJob(companyId: string | undefined, jobId: string | undefined) {
  return useQuery({
    queryKey: companyId && jobId ? keys.detail(companyId, jobId) : ["imports", "none"],
    queryFn: () => importService.get(companyId as string, jobId as string),
    enabled: !!companyId && !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "PARSING" || status === "VALIDATING" || status === "PROCESSING" ? 1500 : false;
    },
  });
}

export function useImportPreview(companyId: string | undefined, jobId: string | undefined, status?: string) {
  return useQuery({
    queryKey: companyId && jobId ? keys.preview(companyId, jobId, status) : ["imports", "none"],
    queryFn: () => importService.preview(companyId as string, jobId as string, status),
    enabled: !!companyId && !!jobId,
  });
}

export function useImportErrors(companyId: string | undefined, jobId: string | undefined) {
  return useQuery({
    queryKey: companyId && jobId ? keys.errors(companyId, jobId) : ["imports", "none"],
    queryFn: () => importService.errors(companyId as string, jobId as string),
    enabled: !!companyId && !!jobId,
  });
}

export function useCreateImportJob(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateImportJobPayload) => importService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useCommitImportJob(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => importService.commit(companyId, jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}

export function useCancelImportJob(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => importService.cancel(companyId, jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.all(companyId) }),
  });
}
