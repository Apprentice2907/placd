import React, { useState } from 'react';
import type { Opportunity } from '../lib/api';
import { formatDistanceToNow, format } from 'date-fns';
import { MapPin, Briefcase, Bookmark, ExternalLink } from 'lucide-react';
import { cn } from '../lib/utils';

interface OpportunityCardProps {
  opportunity: Opportunity;
  isActive?: boolean;
}

const TYPE_MAP: Record<string, string> = {
  scholarship: 'Scholarship',
  fellowship: 'Fellowship',
  internship: 'Internship',
  exchange_program: 'Exchange Program',
  conference: 'Conference',
  competition: 'Competition',
  training: 'Training',
  online_course: 'Online Course',
  grant: 'Grant',
  other: 'Opportunity',
};

export const OpportunityCard: React.FC<OpportunityCardProps> = ({ opportunity: opp, isActive }) => {
  const [isSaved, setIsSaved] = useState(false);
  
  const now = new Date();
  const deadlineDate = opp.deadline ? new Date(opp.deadline) : null;
  const isClosed = deadlineDate ? deadlineDate < now : false;
  const daysUntilDeadline = deadlineDate ? Math.ceil((deadlineDate.getTime() - now.getTime()) / (1000 * 3600 * 24)) : null;

  const getDeadlineDisplay = () => {
    if (isClosed) {
      return <span className="text-[11px] font-bold text-red-500 dark:text-red-400 uppercase tracking-wide">Closed</span>;
    }
    if (deadlineDate) {
      const isUrgent = daysUntilDeadline !== null && daysUntilDeadline <= 7;
      return (
        <span className={cn("text-[11px] font-medium", isUrgent ? "text-amber-600 dark:text-amber-400" : "text-neutral-400")}>
          Deadline: {format(deadlineDate, 'MMM d, yyyy')}
        </span>
      );
    }
    const formattedDate = opp.first_seen_at 
      ? formatDistanceToNow(new Date(opp.first_seen_at), { addSuffix: true })
      : 'Recently';
    return <span className="text-[11px] text-black/40 dark:text-white/40 font-mono font-medium">Added {formattedDate}</span>;
  };

  const tags = [...(opp.tags || [])].slice(0, 3);
  const initialAvatar = opp.organization ? opp.organization.charAt(0).toUpperCase() : '?';
  const displayType = TYPE_MAP[opp.opportunity_type] || 'Opportunity';

  return (
    <div className={cn(
      "group relative flex flex-col justify-between p-6 rounded-xl bg-[#f5f5f7] dark:bg-[#111118] border border-black/8 dark:border-white/8 transition-all duration-150 hover:shadow-sm hover:-translate-y-px",
      isClosed && "opacity-60 grayscale-[50%]",
      isActive && "ring-2 ring-indigo-500 shadow-md"
    )}>
      
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-neutral-100 to-neutral-200 dark:from-neutral-800 dark:to-neutral-700 border border-[var(--border-color)] flex items-center justify-center shrink-0 overflow-hidden shadow-sm relative">
            <span className="text-lg font-bold text-[var(--text-secondary)] absolute inset-0 flex items-center justify-center">{initialAvatar}</span>
          </div>
          <div>
            <h3 className="text-base font-semibold text-black dark:text-white leading-tight line-clamp-1 group-hover:text-[#6366f1] transition-colors">
              {opp.title}
            </h3>
            <p className="text-xs font-mono text-black/40 dark:text-white/40 uppercase tracking-wide mt-1">{opp.organization}</p>
          </div>
        </div>
        <button 
          onClick={(e) => { e.preventDefault(); setIsSaved(!isSaved); }}
          className="p-2 -m-2 text-neutral-400 hover:text-indigo-500 transition-colors"
          aria-label="Save opportunity"
        >
          <Bookmark className={cn("w-5 h-5", isSaved && "fill-indigo-500 text-indigo-500")} />
        </button>
      </div>

      {/* Meta */}
      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-black/80 dark:text-white/80 font-mono">
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-white dark:bg-[#0a0a0f] border border-black/8 dark:border-white/8">
          <MapPin className="w-3.5 h-3.5" />
          <span className="truncate max-w-[120px]">{opp.country || 'Global'}</span>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-white dark:bg-[#0a0a0f] border border-black/8 dark:border-white/8">
          <Briefcase className="w-3.5 h-3.5" />
          <span>{displayType}</span>
        </div>
        {opp.funding_type === 'fully_funded' && (
          <div className="flex items-center gap-1.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 px-2 py-1 rounded-md font-medium">
            Fully Funded
          </div>
        )}
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span key={tag} className="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 rounded-full px-2.5 py-0.5 text-xs font-mono">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-neutral-100 dark:border-neutral-800/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getDeadlineDisplay()}
        </div>
        
        <a 
          href={opp.source_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-sm font-semibold text-[#6366f1] hover:text-[#4f46e5] transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          View
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

    </div>
  );
};
