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
  is_student_eligible?: boolean;
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
  student_mode?: boolean;
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
      try {
        const { data } = await apiClient.get('/v2/jobs/search', { params: filters });
        return data;
      } catch (error) {
        console.error("Error fetching jobs:", error);
        return { jobs: [], total: 0, page: 1, per_page: 24, has_next: false };
      }
    },
    facets: async (): Promise<{
      employment_type: Record<string, number>;
      seniority: Record<string, number>;
      total: number;
    }> => {
      try {
        const { data } = await apiClient.get('/v2/jobs/facets');
        return data;
      } catch {
        return { employment_type: {}, seniority: {}, total: 0 };
      }
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
    scrapeJd: async (_url: string): Promise<{success: boolean; jd_text?: string; detected_company?: string; detected_role?: string; fallback?: boolean}> => {
      return { success: true, jd_text: "We are looking for a Senior Frontend Engineer...", detected_company: "DummyCorp", detected_role: "Frontend Engineer" };
    },
    research: async (_payload: {company: string; role: string; jd_text: string}): Promise<any> => {
      return {
        top_keywords: ["React", "TypeScript", "Performance"],
        culture_signals: ["Fast-paced", "Innovative"],
        emphasis_notes: "Focus heavily on frontend performance and React ecosystem.",
        example_strong_bullets: ["Improved load times by 40% using React.lazy"]
      };
    },
    rewrite: async (_payload: {profile: any; research: any; jd_text: string}): Promise<any> => {
      return {
        rewritten_bullets: [
          {
            id: 'exp_1',
            text: "Engineered scalable React/TypeScript applications resulting in 30% faster page loads, perfectly aligning with frontend performance goals."
          }
        ]
      };
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
