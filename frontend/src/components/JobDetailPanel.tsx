import React, { useState, useEffect } from 'react';
import type { Job } from '../lib/api';
import { ExternalLink, Bookmark, Share2, X, MapPin, Briefcase, DollarSign, Clock, BadgeCheck, Zap } from 'lucide-react';
import { cn } from '../lib/utils';
import { JobDetailSkeleton } from './Skeletons';

const colors = [
  'bg-red-500', 'bg-blue-500', 'bg-green-500', 'bg-yellow-500',
  'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-teal-500',
];
function getHashColor(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function formatDate(iso?: string | null): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return ''; }
}

interface JobDetailPanelProps {
  job: Job | null;
  isOpen: boolean;
  onClose: () => void;
  isLoading?: boolean;
}

export const JobDetailPanel: React.FC<JobDetailPanelProps> = ({ job, isOpen, onClose, isLoading }) => {
  const [isSaved, setIsSaved] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);
  const [copyDone, setCopyDone] = useState(false);

  // Sync isSaved
  useEffect(() => {
    if (job) setIsSaved(job.status === 'shortlisted');
    setImgError(false);
    setDescExpanded(false);
  }, [job?.id]);

  // Escape key closes panel
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  // Push/pop history state so browser back closes panel
  useEffect(() => {
    if (isOpen) {
      window.history.pushState({ panelOpen: true }, '');
      const popHandler = () => onClose();
      window.addEventListener('popstate', popHandler);
      return () => window.removeEventListener('popstate', popHandler);
    }
  }, [isOpen, onClose]);

  const toggleSave = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!job) return;
    const newStatus = isSaved ? 'active' : 'shortlisted';
    try {
      await fetch(`/api/jobs/${job.id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      setIsSaved(!isSaved);
    } catch { /* noop */ }
  };

  const handleShare = async () => {
    if (!job) return;
    const url = `${window.location.origin}/jobs/${job.id}`;
    if (navigator.share) {
      await navigator.share({ title: job.title, url });
    } else {
      await navigator.clipboard.writeText(url);
      setCopyDone(true);
      setTimeout(() => setCopyDone(false), 2000);
    }
  };

  let parsedSkillsRequired: string[] = [];
  let parsedSkillsPreferred: string[] = [];
  if (job) {
    const raw = job.skills;
    if (typeof raw === 'string') {
      try { parsedSkillsRequired = JSON.parse(raw); } catch { parsedSkillsRequired = raw.split(',').map(s => s.trim()); }
    } else if (Array.isArray(raw)) {
      parsedSkillsRequired = raw;
    }
  }

  const hashColor = job ? getHashColor(job.company || '') : 'bg-indigo-500';
  const initialAvatar = job?.company ? job.company.charAt(0).toUpperCase() : '?';
  const description = job?.description || '';
  const isLongDesc = description.length > 600;
  const displayedDesc = (!descExpanded && isLongDesc) ? description.slice(0, 600) + '…' : description;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className="relative w-full max-w-[480px] md:max-w-[480px] bg-[var(--color-bg-primary)] dark:bg-[var(--color-bg-surface)] h-full shadow-2xl flex flex-col slide-in-right overflow-hidden
          max-md:max-w-full max-md:!bottom-0 max-md:!top-auto max-md:!h-[92vh] max-md:rounded-t-2xl max-md:slide-in-up"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 p-2 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 hover:text-neutral-900 dark:hover:text-white transition-colors"
          aria-label="Close panel"
        >
          <X className="w-4 h-4" />
        </button>

        {isLoading || !job ? (
          <JobDetailSkeleton />
        ) : (
          <>
            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto">
              {/* Header */}
              <div className="p-6 pb-4 border-b border-[var(--color-border)]">
                <div className="flex items-start gap-4 mt-4">
                  <div className="w-16 h-16 shrink-0 rounded-xl overflow-hidden flex items-center justify-center border border-neutral-200 dark:border-neutral-800">
                    {job.company_logo_url && !imgError ? (
                      <img src={job.company_logo_url} alt={job.company} className="w-full h-full object-contain bg-white p-1" onError={() => setImgError(true)} />
                    ) : job.company_domain && !imgError ? (
                      <img src={`https://logo.clearbit.com/${job.company_domain}`} alt={job.company} className="w-full h-full object-contain bg-white p-1" onError={() => setImgError(true)} />
                    ) : (
                      <div className={cn('w-full h-full flex items-center justify-center text-white font-bold text-2xl', hashColor)}>
                        {initialAvatar}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-lg font-bold text-[var(--color-text-primary)] leading-tight line-clamp-2">
                      {job.title}
                    </h2>
                    <p className="text-sm text-[var(--color-text-secondary)] mt-0.5 font-medium">{job.company}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-1.5">
                      {job.posted_at && (
                        <span className="text-xs text-[var(--color-text-muted)]">
                          Posted {formatDate(job.posted_at || job.created_at)}
                        </span>
                      )}
                      {/* Color-coded source badge */}
                      {job.source && (
                        <span className={cn(
                          "px-2 py-0.5 text-[10px] font-semibold rounded-full uppercase tracking-wide",
                          ['greenhouse','lever','ashby','workday','bamboohr','recruitee'].includes(job.source.toLowerCase())
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300'
                            : ['linkedin','naukri','internshala'].includes(job.source.toLowerCase())
                              ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300'
                              : 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300'
                        )}>
                          via {job.source}
                        </span>
                      )}
                      {/* Trust badges */}
                      {(job.trust_score ?? 0) >= 100 && (
                        <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold rounded-full bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400 border border-violet-200 dark:border-violet-800">
                          <BadgeCheck className="w-3 h-3" /> Top Company
                        </span>
                      )}
                      {job.source && ['greenhouse','lever','ashby','workday'].includes(job.source.toLowerCase()) && (
                        <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                          <Zap className="w-3 h-3" /> Direct
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick facts row */}
              <div className="px-6 py-4 border-b border-[var(--color-border)]">
                <div className="grid grid-cols-2 gap-3">
                  {job.location && (
                    <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                      <MapPin className="w-4 h-4 text-indigo-500 shrink-0" />
                      <span className="truncate">{job.location}</span>
                    </div>
                  )}
                  {(job.is_remote === true || job.is_remote === 1) && (
                    <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                      <Briefcase className="w-4 h-4 shrink-0" />
                      Remote
                    </div>
                  )}
                  {job.job_type && (
                    <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                      <Clock className="w-4 h-4 text-indigo-500 shrink-0" />
                      <span className="capitalize">{job.job_type}</span>
                    </div>
                  )}
                  {job.stipend_display && (
                    <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                      <DollarSign className="w-4 h-4 text-indigo-500 shrink-0" />
                      <span>{job.stipend_display}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Skills */}
              {parsedSkillsRequired.length > 0 && (
                <div className="px-6 py-4 border-b border-[var(--color-border)]">
                  <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-widest mb-3">
                    Required Skills
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {parsedSkillsRequired.map(skill => (
                      <span
                        key={skill}
                        className="px-2.5 py-1 text-xs font-medium rounded-full bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/20"
                      >
                        {skill}
                      </span>
                    ))}
                    {parsedSkillsPreferred.map(skill => (
                      <span
                        key={skill}
                        className="px-2.5 py-1 text-xs font-medium rounded-full bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Eligibility */}
              {job.who_can_apply && (
                <div className="px-6 py-4 border-b border-[var(--color-border)]">
                  <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-widest mb-2">
                    Eligibility
                  </h3>
                  <p className="text-sm text-[var(--color-text-secondary)]">{job.who_can_apply}</p>
                </div>
              )}

              {/* Description */}
              {description && (
                <div className="px-6 py-4">
                  <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-widest mb-3">
                    Description
                  </h3>
                  <div className="text-sm text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">
                    {displayedDesc}
                  </div>
                  {isLongDesc && (
                    <button
                      onClick={() => setDescExpanded(!descExpanded)}
                      className="mt-3 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      {descExpanded ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Sticky action bar */}
            <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-bg-primary)] dark:bg-[var(--color-bg-surface)]">
              <div className="flex gap-2">
                <a
                  href={job.apply_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 py-3 px-4 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl transition-colors text-sm"
                >
                  Apply Now <ExternalLink className="w-4 h-4" />
                </a>
                <button
                  onClick={toggleSave}
                  className={cn(
                    'p-3 rounded-xl border transition-colors',
                    isSaved
                      ? 'bg-indigo-100 border-indigo-300 text-indigo-700 dark:bg-indigo-500/10 dark:border-indigo-500/30 dark:text-indigo-300'
                      : 'border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-indigo-600 hover:border-indigo-300'
                  )}
                  aria-label="Save job"
                >
                  <Bookmark className={cn('w-4 h-4', isSaved && 'fill-current')} />
                </button>
                <button
                  onClick={handleShare}
                  className="p-3 rounded-xl border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-indigo-600 hover:border-indigo-300 transition-colors"
                  aria-label="Share job"
                >
                  {copyDone ? (
                    <span className="text-xs font-medium text-emerald-500">Copied!</span>
                  ) : (
                    <Share2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
