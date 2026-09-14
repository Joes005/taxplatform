import { z } from "zod";

export const companySchema = z.object({
  legal_name: z.string().min(1, "Legal name is required").max(255),
  trade_name: z.string().max(255).optional().or(z.literal("")),
  business_type: z.string().max(100).optional().or(z.literal("")),
  pan: z.string().max(10).optional().or(z.literal("")),
  gstin: z.string().max(15).optional().or(z.literal("")),
  tan: z.string().max(10).optional().or(z.literal("")),
  state: z.string().max(100).optional().or(z.literal("")),
  city: z.string().max(100).optional().or(z.literal("")),
  address: z.string().max(500).optional().or(z.literal("")),
  financial_year_start: z.string().optional().or(z.literal("")),
});

export type CompanyFormValues = z.infer<typeof companySchema>;
