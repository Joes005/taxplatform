export interface SuccessEnvelope<T> {
  success: true;
  data: T;
  message?: string | null;
}

export interface ErrorEnvelope {
  success: false;
  error: {
    code: string;
    message: string;
    fields?: Record<string, string[]>;
  };
}

export type ApiEnvelope<T> = SuccessEnvelope<T> | ErrorEnvelope;

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface PaginatedData<T> {
  items: T[];
  pagination: PaginationMeta;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_platform_super_admin: boolean;
  last_login_at: string | null;
  created_at: string;
}

export type MembershipStatus = "ACTIVE" | "INACTIVE" | "INVITED";

export interface MembershipCompanySummary {
  company_id: string;
  company_name: string;
  role_code: string;
  role_name: string;
  status: MembershipStatus;
}

export interface ActiveCompanyContext {
  company_id: string;
  company_name: string;
  role_code: string;
  role_name: string;
  permissions: string[];
}

export interface LoginResponseData {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  companies: MembershipCompanySummary[];
  active_company: ActiveCompanyContext | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Company {
  id: string;
  legal_name: string;
  trade_name: string | null;
  business_type: string | null;
  pan: string | null;
  gstin: string | null;
  tan: string | null;
  state: string | null;
  city: string | null;
  address: string | null;
  financial_year_start: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CompanyUser {
  membership_id: string;
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role_code: string;
  role_name: string;
  status: MembershipStatus;
  joined_at: string | null;
}

export interface Role {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system_role: boolean;
  permissions: string[];
}

export interface AuditLog {
  id: string;
  company_id: string | null;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  description: string | null;
  ip_address: string | null;
  user_agent: string | null;
  log_metadata: Record<string, unknown> | null;
  created_at: string;
}
