import React, { useState, useEffect } from 'react';
import type { Job } from '../lib/api';
import { MapPin, Bookmark, BadgeCheck, Sparkles, Zap } from 'lucide-react';
import { cn } from '../lib/utils';

// Helper for colored hash
const colors = [
  'bg-red-500', 'bg-blue-500', 'bg-green-500',
  'bg-yellow-500', 'bg-purple-500', 'bg-pink-500',
  'bg-indigo-500', 'bg-teal-500'
];

function getHashColor(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

// Eligibility Badge Logic
function getEligibilityBadge(text?: string | null) {
  if (!text) return null;
  const lower = text.toLowerCase();
  if (lower.includes('3rd year') || lower.includes('btech') || lower.includes('pre-final')) {
    return { label: text, style: 'bg-blue-100 text-blue-700 border-blue-200' };
  }
  if (lower.includes('fresher') || lower.includes('0 experience')) {
    return { label: text, style: 'bg-green-100 text-green-700 border-green-200' };
  }
  return { label: text, style: 'bg-gray-100 text-gray-700 border-gray-200' };
}

// Truncate Helpers
function truncate(str: string, length: number) {
  if (!str) return '';
  return str.length > length ? str.substring(0, length) + '...' : str;
}

// Source badge config
const SOURCE_BADGE_CONFIG: Record<string, { label: string; color: string }> = {
  greenhouse: { label: 'via Greenhouse', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' },
  lever: { label: 'via Lever', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' },
  ashby: { label: 'via Ashby', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' },
  workday: { label: 'via Workday', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' },
  linkedin: { label: 'via LinkedIn', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  naukri: { label: 'via Naukri', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  indeed: { label: 'via Indeed', color: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400' },
  internshala: { label: 'via Internshala', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  wellfound: { label: 'via Wellfound', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' },
  jobspy: { label: 'via JobSpy', color: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400' },
};

function daysSince(dateStr: string): number {
  const d = new Date(dateStr);
  const now = new Date();
  return Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
}

// Match Score Ring Component
const MatchScoreRing = ({ score }: { score?: number | null }) => {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    // Trigger animation after mount
    setTimeout(() => setMounted(true), 100);
  }, []);

  if (score == null) return null;
  const radius = 14;
  const circumference = 2 * Math.PI * radius;
  // Start at 0 (full offset) and animate to real score
  const strokeDashoffset = mounted ? circumference - score * circumference : circumference;
  
  let color = 'text-green-500';
  if (score < 0.4) color = 'text-red-500';
  else if (score < 0.7) color = 'text-amber-500';

  return (
    <div className="relative w-10 h-10 flex items-center justify-center shrink-0">
      <svg className="w-10 h-10 transform -rotate-90">
        <circle
          className="text-neutral-200 dark:text-neutral-800"
          strokeWidth="3"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="20"
          cy="20"
        />
        <circle
          className={cn(color, "transition-all duration-1000 ease-out")}
          strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="20"
          cy="20"
        />
      </svg>
      <span className="absolute text-[11px] font-bold text-neutral-700 dark:text-neutral-300">
        {Math.round(score * 100)}%
      </span>
    </div>
  );
};

interface JobCardProps {
  job: Job;
  isActive?: boolean;
  onOpen?: () => void;
}

export const JobCard: React.FC<JobCardProps> = ({ job, isActive, onOpen }) => {
  const [isSaved, setIsSaved] = useState(job.status === 'shortlisted');
  const [imgError, setImgError] = useState(false);

  const toggleBookmark = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const newStatus = isSaved ? 'active' : 'shortlisted';
    try {
      await fetch(`/api/jobs/${job.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      setIsSaved(!isSaved);
    } catch (err) {
      console.error('Failed to update status', err);
    }
  };

  const initialAvatar = job.company ? job.company.charAt(0).toUpperCase() : '?';
  const hashColor = getHashColor(job.company || '');
  const eligibility = getEligibilityBadge(job.who_can_apply);

  let parsedSkills: string[] = [];
  if (typeof job.skills === 'string') {
    try {
      parsedSkills = JSON.parse(job.skills);
    } catch (e) {
      parsedSkills = job.skills.split(',').map(s => s.trim());
    }
  } else if (Array.isArray(job.skills)) {
    parsedSkills = job.skills;
  }
  const displayedSkills = parsedSkills.slice(0, 3);
  const extraSkillsCount = parsedSkills.length - 3;

  return (
    <div 
      onClick={() => onOpen ? onOpen() : undefined}
      className={cn(
        "group relative flex flex-col p-5 rounded-xl bg-white dark:bg-neutral-900 border transition-all duration-150 hover:shadow-md hover:-translate-y-0.5 cursor-pointer",
        isActive ? "border-indigo-500 shadow-sm" : "border-neutral-200 dark:border-neutral-800",
        onOpen ? "cursor-pointer" : ""
      )}
    >
        
        {/* Bookmark Icon */}
        <button 
          onClick={toggleBookmark}
          className="absolute top-4 left-4 p-1.5 text-neutral-400 hover:text-indigo-500 transition-colors z-10 bg-white/50 dark:bg-black/50 backdrop-blur-sm rounded-full"
        >
          <Bookmark className={cn("w-5 h-5", isSaved && "fill-indigo-500 text-indigo-500")} />
        </button>

        {/* Match Score */}
        <div className="absolute top-4 right-4 z-10">
          <MatchScoreRing score={job.match_score} />
        </div>

        <div className="pt-8">
          {/* Top Row: Logo, Company, Title */}
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 shrink-0 rounded-full overflow-hidden flex items-center justify-center border border-neutral-100 dark:border-neutral-800">
              {job.company_logo_url && !imgError ? (
                <img 
                  src={job.company_logo_url} 
                  alt={job.company} 
                  className="w-full h-full object-cover bg-white"
                  onError={() => setImgError(true)}
                />
              ) : job.company_domain && !imgError ? (
                <img 
                  src={`https://logo.clearbit.com/${job.company_domain}`} 
                  alt={job.company} 
                  className="w-full h-full object-cover bg-white"
                  onError={() => setImgError(true)}
                />
              ) : (
                <div className={cn("w-full h-full flex items-center justify-center text-white font-bold text-lg", hashColor)}>
                  {initialAvatar}
                </div>
              )}
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-neutral-900 dark:text-neutral-100 text-sm">
                {truncate(job.company || 'Unknown Company', 20)}
              </span>
              <span className="text-sm text-neutral-500 dark:text-neutral-400 font-medium">
                {truncate(job.title, 35)}
              </span>
            </div>
          </div>

          {/* Middle Row: Pills + Trust Badges */}
          <div className="flex flex-wrap gap-2 mb-3">
            {job.location && (
              <span className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                <MapPin className="w-3 h-3" />
                {job.location}
              </span>
            )}
            {(job.is_remote === 1 || job.is_remote === true) && (
              <span className="px-2 py-1 text-xs font-medium rounded-md bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                Remote
              </span>
            )}
            <span className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              <span className="font-serif font-bold px-0.5">₹</span>
              {job.stipend_display || 'Not mentioned'}
            </span>
            {/* Trust badges */}
            {(job.trust_score ?? 0) >= 100 && (
              <span className="flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-md bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400 border border-violet-200 dark:border-violet-800">
                <BadgeCheck className="w-3 h-3" /> Top Company
              </span>
            )}
            {job.source && SOURCE_BADGE_CONFIG[job.source.toLowerCase()] && (
              ['greenhouse','lever','ashby','workday'].includes(job.source.toLowerCase()) && (
                <span className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                  <Zap className="w-3 h-3" /> Direct
                </span>
              )
            )}
            {job.created_at && daysSince(job.created_at) <= 3 && (
              <span className="flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-md bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400">
                <Sparkles className="w-3 h-3" /> New
              </span>
            )}
          </div>

          {/* Eligibility Row */}
          {eligibility && (
            <div className="mb-3">
              <span className={cn("px-2 py-1 text-xs font-medium rounded-md border", eligibility.style)}>
                {eligibility.label}
              </span>
            </div>
          )}

          {/* Skills Row */}
          {parsedSkills.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-auto pt-2 border-t border-neutral-100 dark:border-neutral-800">
              {displayedSkills.map(skill => (
                <span key={skill} className="px-2 py-0.5 text-[10px] font-medium rounded bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
                  {skill}
                </span>
              ))}
              {extraSkillsCount > 0 && (
                <span className="px-2 py-0.5 text-[10px] font-medium rounded bg-neutral-50 text-neutral-500 dark:bg-neutral-800/50 dark:text-neutral-500">
                  +{extraSkillsCount} more
                </span>
              )}
            </div>
          )}
          {/* Source Badge */}
          {job.source && SOURCE_BADGE_CONFIG[job.source.toLowerCase()] && (
            <div className="mt-2 pt-2 border-t border-neutral-100 dark:border-neutral-800">
              <span className={cn("px-2 py-0.5 text-[10px] font-medium rounded", SOURCE_BADGE_CONFIG[job.source.toLowerCase()].color)}>
                {SOURCE_BADGE_CONFIG[job.source.toLowerCase()].label}
              </span>
            </div>
          )}
        </div>
    </div>
  );
};
