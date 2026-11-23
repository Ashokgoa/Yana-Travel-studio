import { api, type QueryParams } from "@/services/api";
import type {
  AgentStatus,
  Customer,
  CustomerInput,
  DashboardSummary,
  Enquiry,
  EnquiryDetail,
  EnquiryInput,
  EnquiryStatus,
  Page,
  PlannerRef,
  RoleCode,
  TravelAgent,
  TravelAgentInput,
  User,
} from "@/types/crm";

export const authApi = {
  me: () => api.get<User>("/auth/me"),
  login: (email: string, password: string) => api.post<User>("/auth/login", { email, password }),
  logout: () => api.post<void>("/auth/logout"),
};

export const usersApi = {
  list: (params?: QueryParams) => api.get<User[]>("/users", params),
  assignable: () => api.get<PlannerRef[]>("/users/assignable"),
  create: (body: { email: string; full_name: string; role: RoleCode; password: string }) => api.post<User>("/users", body),
  update: (id: number, body: Partial<{ full_name: string; role: RoleCode; is_active: boolean; password: string }>) =>
    api.patch<User>(`/users/${id}`, body),
};

export const agentsApi = {
  list: (params?: QueryParams) => api.get<Page<TravelAgent>>("/travel-agents", params),
  countries: () => api.get<string[]>("/travel-agents/countries"),
  get: (id: number) => api.get<TravelAgent>(`/travel-agents/${id}`),
  create: (body: TravelAgentInput) => api.post<TravelAgent>("/travel-agents", body),
  update: (id: number, body: TravelAgentInput) => api.put<TravelAgent>(`/travel-agents/${id}`, body),
  setStatus: (id: number, status: AgentStatus) => api.patch<TravelAgent>(`/travel-agents/${id}/status`, { status }),
};

export const customersApi = {
  list: (params?: QueryParams) => api.get<Page<Customer>>("/customers", params),
  get: (id: number) => api.get<Customer>(`/customers/${id}`),
  create: (body: CustomerInput) => api.post<Customer>("/customers", body),
  update: (id: number, body: CustomerInput) => api.put<Customer>(`/customers/${id}`, body),
};

export const enquiriesApi = {
  list: (params?: QueryParams) => api.get<Page<Enquiry>>("/enquiries", params),
  get: (id: number) => api.get<EnquiryDetail>(`/enquiries/${id}`),
  create: (body: EnquiryInput) => api.post<EnquiryDetail>("/enquiries", body),
  update: (id: number, body: EnquiryInput) => api.put<EnquiryDetail>(`/enquiries/${id}`, body),
  changeStatus: (id: number, status: EnquiryStatus, note?: string) =>
    api.post<EnquiryDetail>(`/enquiries/${id}/status`, { status, note }),
};

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary"),
};
