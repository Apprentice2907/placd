import React, { useState } from 'react';
import type { Job } from '../lib/api';
import { formatDistanceToNow } from 'date-fns';
import { MapPin, Briefcase, Bookmark, ExternalLink } from 'lucide-react';
import { cn } from '../lib/utils';

interface JobCardProps {
  job: Job;
  isActive?: boolean;
}

export const JobCard: React.FC<JobCardProps> = ({ job, isActive }) => {
  const [isSaved, setIsSaved] = useState(false);
  
  const formattedDate = job.created_at 
    ? formatDistanceToNow(new Date(job.created_at), { addSuffix: true })
    : 'Recently';

  const tags = [...(job.skills || []), ...(job.tags || [])].slice(0, 3);
  
  const getStatusBadge = () => {
    if (job.status === 'active') return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30">Active</span>;
    if (job.status === 'unverified') return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400 border border-amber-200 dark:border-amber-500/30">Unverified</span>;
    if (job.status === 'expired') return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400 border border-red-200 dark:border-red-500/30">Expired</span>;
    return null;
  };

  const initialAvatar = job.company_name ? job.company_name.charAt(0).toUpperCase() : '?';

  return (
    <div className={cn(
      "group relative flex flex-col justify-between p-5 rounded-2xl bg-white dark:bg-neutral-900 border transition-all duration-200",
      isActive 
        ? "border-indigo-500 ring-1 ring-indigo-500 shadow-md dark:shadow-indigo-500/10" 
        : "border-neutral-200 dark:border-neutral-800 hover:border-indigo-300 dark:hover:border-neutral-700 hover:shadow-lg dark:hover:shadow-black/50"
    )}>
      
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-neutral-100 to-neutral-200 dark:from-neutral-800 dark:to-neutral-700 border border-neutral-200 dark:border-neutral-700 flex items-center justify-center shrink-0 overflow-hidden shadow-sm relative">
            {job.c_logo ? (
              <img 
                src={job.c_logo} 
                alt={job.company_name} 
                className="w-full h-full object-cover relative z-10 bg-white" 
                loading="lazy" 
                onError={(e) => {
                  e.currentTarget.style.display = 'none';
                }}
              />
            ) : null}
            {(!job.c_logo) && (
              <span className="text-lg font-bold text-neutral-500 dark:text-neutral-400 absolute inset-0 flex items-center justify-center">{initialAvatar}</span>
            )}
            {/* Background fallback for broken images that are hidden by onError */}
            {job.c_logo && (
              <span className="text-lg font-bold text-neutral-500 dark:text-neutral-400 absolute inset-0 flex items-center justify-center z-0">{initialAvatar}</span>
            )}
          </div>
          <div>
            <h3 className="text-base font-semibold text-neutral-900 dark:text-white leading-tight line-clamp-1 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
              {job.title}
            </h3>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 font-medium mt-0.5">{job.company_name}</p>
          </div>
        </div>
        <button 
          onClick={(e) => { e.preventDefault(); setIsSaved(!isSaved); }}
          className="p-2 -m-2 text-neutral-400 hover:text-indigo-500 transition-colors"
          aria-label="Save job"
        >
          <Bookmark className={cn("w-5 h-5", isSaved && "fill-indigo-500 text-indigo-500")} />
        </button>
      </div>

      {/* Meta */}
      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
        <div className="flex items-center gap-1.5 bg-neutral-100 dark:bg-neutral-800 px-2 py-1 rounded-md">
          <MapPin className="w-3.5 h-3.5" />
          <span className="truncate max-w-[120px]">{job.location || 'Remote'}</span>
        </div>
        <div className="flex items-center gap-1.5 bg-neutral-100 dark:bg-neutral-800 px-2 py-1 rounded-md">
          <Briefcase className="w-3.5 h-3.5" />
          <span className="capitalize">{job.job_type || 'Full-time'}</span>
        </div>
        {job.salary_min && (
          <div className="flex items-center gap-1.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 px-2 py-1 rounded-md font-medium">
            ${job.salary_min.toLocaleString()}
            {job.salary_max ? ` - $${job.salary_max.toLocaleString()}` : '+'}
          </div>
        )}
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span key={tag} className="px-2 py-1 rounded-md text-[11px] font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-500/20">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-neutral-100 dark:border-neutral-800/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getStatusBadge()}
          <span className="text-[11px] text-neutral-400 font-medium">{formattedDate}</span>
        </div>
        
        <a 
          href={job.apply_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-sm font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          Apply
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

    </div>
  );
};
