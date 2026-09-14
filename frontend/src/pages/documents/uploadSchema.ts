import { z } from "zod";

import { DOCUMENT_TYPES } from "@/types/api";

export const uploadMetadataSchema = z.object({
  document_type: z.enum(DOCUMENT_TYPES, { message: "Select a document type" }),
  description: z.string().max(1000, "Description is too long").optional(),
});

export type UploadMetadataValues = z.infer<typeof uploadMetadataSchema>;
