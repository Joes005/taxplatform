import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  journalEntryService,
  paymentService,
  receiptService,
  type JournalEntryPayload,
  type PaymentPayload,
  type ReceiptPayload,
} from "@/services/paymentReceiptService";

export function usePayments(companyId: string | undefined) {
  return useQuery({
    queryKey: ["payments", companyId],
    queryFn: () => paymentService.list(companyId as string),
    enabled: !!companyId,
  });
}

export function useCreatePayment(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PaymentPayload) => paymentService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["payments", companyId] }),
  });
}

export function useReceipts(companyId: string | undefined) {
  return useQuery({
    queryKey: ["receipts", companyId],
    queryFn: () => receiptService.list(companyId as string),
    enabled: !!companyId,
  });
}

export function useCreateReceipt(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReceiptPayload) => receiptService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["receipts", companyId] }),
  });
}

export function useJournalEntries(companyId: string | undefined) {
  return useQuery({
    queryKey: ["journal-entries", companyId],
    queryFn: () => journalEntryService.list(companyId as string),
    enabled: !!companyId,
  });
}

export function useCreateJournalEntry(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: JournalEntryPayload) => journalEntryService.create(companyId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["journal-entries", companyId] }),
  });
}

export function usePostJournalEntry(companyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => journalEntryService.post(companyId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["journal-entries", companyId] }),
  });
}
