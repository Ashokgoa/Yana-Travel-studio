// Mirrors backend/app/schemas/{user,crm}.py

export type RoleCode = "admin" | "planner";

export type User = {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  role: { id: number; code: RoleCode; name: string };
  created_at: string;
};

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type AgentStatus = "active" | "inactive";

export type TravelAgentInput = {
  company_name: string;
  contact_person?: string | null;
  email?: string | null;
  phone?: string | null;
  country?: string | null;
  address?: string | null;
  company_details?: string | null;
  internal_notes?: string | null;
  status: AgentStatus;
};

export type TravelAgent = TravelAgentInput & {
  id: number;
  created_at: string;
  updated_at: string;
  customer_count: number;
  enquiry_count: number;
};

export type TravelAgentRef = { id: number; company_name: string; status: AgentStatus };

export type CustomerInput = {
  travel_agent_id: number | null;
  name: string;
  phone?: string | null;
  email?: string | null;
  nationality?: string | null;
  country_of_residence?: string | null;
  adults: number;
  children: number;
  children_ages: number[];
  special_requirements?: string | null;
  is_active?: boolean;
};

export type Customer = CustomerInput & {
  id: number;
  is_active: boolean;
  travel_agent: TravelAgentRef | null;
  created_at: string;
  updated_at: string;
  enquiry_count: number;
};

export const ENQUIRY_STATUSES = [
  "new",
  "in_progress",
  "proposal_generated",
  "sent_to_agent",
  "revision_requested",
  "approved",
  "booking_confirmed",
  "cancelled",
] as const;
export type EnquiryStatus = (typeof ENQUIRY_STATUSES)[number];

export type BudgetBasis = "per_person" | "total";

export type PlannerRef = { id: number; full_name: string };

export type EnquiryInput = {
  travel_agent_id: number;
  customer_id: number;
  enquiry_date: string;
  travel_start_date: string | null;
  travel_end_date: string | null;
  adults: number;
  children: number;
  destination_preferences: string | null;
  budget_amount: string | null;
  budget_currency: string;
  budget_basis: BudgetBasis | null;
  assigned_planner_id: number | null;
  internal_comments: string | null;
};

export type Enquiry = EnquiryInput & {
  id: number;
  reference: string;
  status: EnquiryStatus;
  travel_agent: TravelAgentRef;
  customer: { id: number; name: string };
  assigned_planner: PlannerRef | null;
  total_travellers: number;
  created_at: string;
  updated_at: string;
};

export type StatusHistoryEntry = {
  id: number;
  from_status: EnquiryStatus | null;
  to_status: EnquiryStatus;
  note: string | null;
  changed_by: PlannerRef | null;
  created_at: string;
};

export type EnquiryDetail = Enquiry & { status_history: StatusHistoryEntry[] };

export type DashboardSummary = {
  total_enquiries: number;
  by_status: Record<EnquiryStatus, number>;
  active_agents: number;
  customers: number;
  recent_enquiries: Enquiry[];
};
