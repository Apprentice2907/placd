import axios from 'axios';

// Ensure the base URL points to our FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Job {
  id: string;
  title: string;
  company: string;
  company_logo_url: string | null;
  company_domain?: string | null;
  location: string | null;
  job_type: string | null;
  is_remote?: boolean | number;
  description?: string | null;
  apply_url: string;
  created_at?: string;
  posted_at?: string;
  skills: string[] | string | null;
  tags?: string[] | null;
  status?: string;
  stipend_display: string | null;
  who_can_apply: string | null;
  match_score?: number | null;
  source?: string | null;
  source_platform?: string | null;
  last_date?: string | null;
  trust_score?: number;
  company_tier?: number;
}

export interface JobSearchResponse {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
}

export interface JobDetailResponse {
  job: Job;
  keywords: { keyword: string; weight: number }[];
  similar_jobs: Job[];
}

export interface SearchFilters {
  q?: string;
  job_type?: string;
  is_remote?: boolean;
  category?: string;
  location?: string;
  experience_level?: string;
  page?: number;
  per_page?: number;
  sort?: string;
  status?: string;
  quality?: 'high' | 'verified' | 'all';
  // Sprint 3 additions
  skills?: string;
  seniority?: string;
  job_function?: string;
  source_platform?: string;
  posted_within?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  visa_sponsorship?: boolean;
  equity?: boolean;
}

export interface CalendarEvent {
  id: string;
  date: string;
  company: string;
  title: string;
  type: string;
  category: string;
  source_url: string | null;
  verified: boolean;
  job_count: number;
}

export interface CalendarResponse {
  month: number;
  year: number;
  events: CalendarEvent[];
  last_updated: string;
}

export const api = {
  jobs: {
    search: async (filters: SearchFilters): Promise<JobSearchResponse> => {
      const params = {
        page: filters.page,
        limit: filters.per_page,
        search: filters.q,
        type: filters.job_type,
        source: filters.category, // Assuming category mapped to source or just unused here, can leave it
        status: filters.status,
        is_remote: filters.is_remote
      };
      // Map remote to type='remote' if needed by the backend
      if (filters.is_remote) params.type = 'remote';
      const { data } = await apiClient.get('/jobs', { params });
      return {
        ...data,
        jobs: data.results || data.jobs || [],
        has_next: data.page * data.limit < data.total
      };
    },
    get: async (id: string): Promise<JobDetailResponse> => {
      const { data } = await apiClient.get(`/jobs/${id}`);
      return data;
    },
    report: async (id: string, reason: string): Promise<{ message: string }> => {
      const { data } = await apiClient.post(`/jobs/${id}/report`, { reason });
      return data;
    },
  },
  stats: {
    quick: async (): Promise<{ total: number; internships: number; fulltime: number; remote: number }> => {
      const { data } = await apiClient.get('/stats/quick');
      return data;
    },
  },
  calendar: {
    get: async (year: number, month: number, category: string = 'all', view: string = 'month'): Promise<CalendarResponse> => {
      const { data } = await apiClient.get('/calendar', { params: { year, month, category, view } });
      return data;
    }
  },
  opportunities: {
    search: async (params?: { type?: string; country?: string; funding?: string; deadline_within_days?: number; q?: string; page?: number; limit?: number }): Promise<OpportunitiesResponse> => {
      const { data } = await apiClient.get('/opportunities', { params });
      return {
        opportunities: data.data || [],
        total: data.pagination?.total_items || 0,
        page: data.pagination?.page || 1,
        limit: data.pagination?.per_page || 24
      };
    },
    stats: async (): Promise<{ by_type: Record<string, number>; active: number; total: number }> => {
      const { data } = await apiClient.get('/opportunities/stats');
      return data;
    }
  },
  profile: {
    get: async (sessionId: string): Promise<any> => {
      const { data } = await apiClient.get(`/profile/${sessionId}`);
      return data;
    },
    upsert: async (profileData: any): Promise<{status: string; message: string}> => {
      const { data } = await apiClient.post('/profile', profileData);
      return data;
    },
    delete: async (sessionId: string): Promise<{status: string; message: string}> => {
      const { data } = await apiClient.delete(`/profile/${sessionId}`);
      return data;
    }
  },
  resume: {
    generate: async (payload: {
      session_id: string;
      job_id?: string;
      job_title?: string;
      company_name?: string;
      job_description?: string;
      document_type?: 'resume' | 'cover_letter' | 'both';
      regenerate_with_projects?: string[];
      existing_generation_id?: string;
    }): Promise<any> => {
      const { data } = await apiClient.post('/resume/generate', payload);
      return data;
    },
    fetchJob: async (url: string): Promise<{title: string; company: string; description: string}> => {
      const { data } = await apiClient.post('/resume/fetch-job', { url });
      return data;
    },
    confirm: async (generationId: string): Promise<{pdf_url?: string; cover_letter_pdf_url?: string}> => {
      const { data } = await apiClient.post(`/resume/confirm/${generationId}`);
      return data;
    }
  }
};

export interface Opportunity {
  id: string
  title: string
  organization: string
  opportunity_type:
    | 'scholarship' | 'fellowship' | 'internship'
    | 'exchange_program' | 'conference' | 'competition'
    | 'training' | 'online_course' | 'grant' | 'other'
  funding_type: 'fully_funded' | 'partially_funded' | 'paid' | 'unpaid' | 'unknown'
  country: string | null
  region: string | null
  deadline: string | null
  source_url: string
  source_name: string
  tags: string[]
  status: 'active' | 'expired' | 'unverified'
  first_seen_at: string
  description: string | null
}

export interface OpportunitiesResponse {
  opportunities: Opportunity[]
  total: number
  page: number
  limit: number
}

// Exported standalone functions as requested
export async function fetchOpportunities(params?: {
  type?: string
  country?: string
  funding?: string
  deadline_within_days?: number
  q?: string
  page?: number
  limit?: number
}): Promise<OpportunitiesResponse> {
  const { data } = await apiClient.get('/opportunities', { params });
  return {
    opportunities: data.data || [],
    total: data.pagination?.total_items || 0,
    page: data.pagination?.page || 1,
    limit: data.pagination?.per_page || 24
  };
}

export async function fetchOpportunityStats(): Promise<{
  by_type: Record<string, number>
  active: number
  total: number
}> {
  const { data } = await apiClient.get('/opportunities/stats');
  return data;
}
