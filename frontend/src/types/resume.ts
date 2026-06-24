export interface ResumeProfile {
  id: string;
  label: string;
  personal: {
    name: string;
    email: string;
    phone: string;
    location: string;
    linkedin: string;
    github: string;
    portfolio: string;
  };
  education: Array<{
    id: string;
    institution: string;
    degree: string;
    field: string;
    graduation_year: string;
    gpa: string;
    coursework: string[];
  }>;
  experience: Array<{
    id: string;
    company: string;
    role: string;
    start: string;
    end: string;
    location: string;
    bullets: string[];
  }>;
  projects: Array<{
    id: string;
    name: string;
    stack: string[];
    link: string;
    bullets: string[];
  }>;
  skills: {
    languages: string[];
    frameworks: string[];
    tools: string[];
    databases: string[];
  };
  achievements: string[];
  raw_resume_text?: string;
}

export interface ResearchResult {
  top_keywords: string[];
  culture_signals: string[];
  emphasis_notes: string;
  example_strong_bullets: string[];
}

export interface RewriteResult {
  summary: string;
  rewritten_bullets: Array<{ id: string; bullets: string[] }>;
  skills_reordered: string[];
  match_score: number;
  missing_keywords: string[];
  placeholders: string[];
}

export interface FlatBulletItem {
  id: string;
  type: "experience" | "project";
  company?: string;
  role?: string;
  name?: string;
  stack?: string[];
  raw_bullets: string[];
}

export interface KeywordTag {
  keyword: string;
  status: 'PRESENT' | 'MISSING';
}

export type AnalysisPhase = 'generating' | 'critiquing' | 'refining' | 'keywords' | null;
