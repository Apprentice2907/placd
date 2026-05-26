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
  company_name: string;
  location: string;
  job_type: string;
  is_remote: boolean;
  apply_url: string;
  created_at: string;
  skills: string[] | null;
  tags: string[] | null;
  status: string;
  company_id?: string;
  description?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  c_logo?: string;
  c_ats?: string;
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
      const { data } = await apiClient.get('/jobs/search', { params: filters });
      return data;
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
  calendar: {
    get: async (year: number, month: number, category: string = 'all', view: string = 'month'): Promise<CalendarResponse> => {
      const { data } = await apiClient.get('/calendar', { params: { year, month, category, view } });
      return data;
    }
  }
};
