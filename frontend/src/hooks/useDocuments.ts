import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  documentService,
  type DocumentListFilters,
  type UpdateDocumentPayload,
  type UploadDocumentPayload,
} from "@/services/documentService";

// Hierarchical keys ("documents", companyId, ...) so a mutation can
// invalidate every list AND detail query for a company with one call —
// invalidateQueries matches by key prefix, so ["documents", companyId] only
// reaches queries actually nested under it.
const documentKeys = {
  all: (companyId: string) => ["documents", companyId] as const,
  list: (filters: DocumentListFilters) =>
    ["documents", filters.companyId, "list", filters] as const,
  detail: (companyId: string, documentId: string) =>
    ["documents", companyId, "detail", documentId] as const,
};

export function useDocuments(filters: DocumentListFilters | null) {
  return useQuery({
    queryKey: filters ? documentKeys.list(filters) : ["documents", "none"],
    queryFn: () => documentService.list(filters as DocumentListFilters),
    enabled: !!filters?.companyId,
  });
}

export function useDocument(companyId: string | undefined, documentId: string | undefined) {
  return useQuery({
    queryKey: companyId && documentId ? documentKeys.detail(companyId, documentId) : ["documents", "none"],
    queryFn: () => documentService.get(companyId as string, documentId as string),
    enabled: !!companyId && !!documentId,
  });
}

export function useUploadDocument(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UploadDocumentPayload) => documentService.upload(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentKeys.all(companyId) }),
  });
}

export function useUpdateDocument(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, payload }: { documentId: string; payload: UpdateDocumentPayload }) =>
      documentService.update(companyId, documentId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentKeys.all(companyId) }),
  });
}

export function useArchiveDocument(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => documentService.archive(companyId, documentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentKeys.all(companyId) }),
  });
}

export function useRestoreDocument(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => documentService.restore(companyId, documentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentKeys.all(companyId) }),
  });
}
