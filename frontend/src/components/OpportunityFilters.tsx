import React, { useState } from 'react';
import { cn } from '../lib/utils';
import { MapPin, Search, ChevronDown, Filter, Calendar } from 'lucide-react';

export interface OpportunityFiltersState {
  q?: string;
  type?: string;
  country?: string;
  funding?: string;
  deadline_within_days?: number;
  page?: number;
  limit?: number;
}

const CATEGORIES = [
  { label: 'All Opportunities', value: '' },
  { label: 'Scholarships', value: 'scholarship' },
  { label: 'Fellowships', value: 'fellowship' },
  { label: 'Internships', value: 'internship' },
  { label: 'Exchange Programs', value: 'exchange_program' },
  { label: 'Conferences', value: 'conference' },
  { label: 'Competitions', value: 'competition' },
  { label: 'Grants', value: 'grant' },
  { label: 'Online Courses', value: 'online_course' },
];

interface OpportunityFiltersProps {
  filters: OpportunityFiltersState;
  onFilterChange: (newFilters: Partial<OpportunityFiltersState>) => void;
}

export const OpportunityFilters: React.FC<OpportunityFiltersProps> = ({ filters, onFilterChange }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Handle pill click
  const handleCategoryClick = (cat: typeof CATEGORIES[0]) => {
    onFilterChange({ type: cat.value || undefined, page: 1 });
  };

  // Determine active pill
  const getIsActive = (cat: typeof CATEGORIES[0]) => {
    if (cat.value === '') {
      return !filters.type;
    }
    return filters.type === cat.value;
  };

  return (
    <div className="w-full flex flex-col gap-4 py-4 sticky top-0 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-md z-40 border-b border-[var(--border-color)]">
      
      {/* Top Search Bar */}
      <div className="flex flex-col md:flex-row w-full gap-3 px-4 max-w-7xl mx-auto">
        <div className="relative flex-1 group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 group-focus-within:text-indigo-500 w-5 h-5 transition-colors" />
          <input 
            type="text" 
            placeholder="Search scholarships, fellowships, programs..." 
            value={filters.q || ''}
            onChange={(e) => onFilterChange({ q: e.target.value, page: 1 })}
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-[var(--border-color)] bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-[var(--text-primary)] shadow-sm"
          />
        </div>
        <button 
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl border border-[var(--border-color)] hover:bg-[var(--bg-secondary)] transition-colors font-medium text-neutral-700 dark:text-neutral-300 shadow-sm whitespace-nowrap"
        >
          <Filter className="w-4 h-4" />
          Filters
        </button>
      </div>

      {/* Primary Pill Bar */}
      <div className="w-full overflow-x-auto no-scrollbar px-4">
        <div className="flex items-center gap-2 max-w-7xl mx-auto w-max md:w-full pb-2">
          {CATEGORIES.map((cat) => {
            const isActive = getIsActive(cat);
            return (
              <button
                key={cat.label}
                onClick={() => handleCategoryClick(cat)}
                className={cn(
                  "px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap border",
                  isActive 
                    ? "bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-600/20" 
                    : "bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border-color)] hover:border-indigo-300 dark:hover:border-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-900/30"
                )}
              >
                {cat.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Secondary Collapsible Filters */}
      {showAdvanced && (
        <div className="px-4 w-full animate-in slide-in-from-top-4 fade-in duration-200 max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-5 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50 border border-[var(--border-color)] shadow-inner">
            
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1">
                <MapPin className="w-3 h-3" /> Country
              </label>
              <input 
                type="text" 
                placeholder="e.g. United States, Germany, Japan" 
                value={filters.country || ''}
                onChange={(e) => onFilterChange({ country: e.target.value, page: 1 })}
                className="w-full px-3 py-2.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all text-sm"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1">
                <Filter className="w-3 h-3" /> Funding
              </label>
              <div className="relative">
                <select 
                  value={filters.funding || ''}
                  onChange={(e) => onFilterChange({ funding: e.target.value || undefined, page: 1 })}
                  className="w-full px-3 py-2.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all text-sm appearance-none"
                >
                  <option value="">Any Funding</option>
                  <option value="fully_funded">Fully Funded</option>
                  <option value="partially_funded">Partially Funded</option>
                  <option value="paid">Paid</option>
                  <option value="unpaid">Unpaid</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1">
                <Calendar className="w-3 h-3" /> Deadline
              </label>
              <div className="relative">
                <select 
                  value={filters.deadline_within_days || ''}
                  onChange={(e) => onFilterChange({ deadline_within_days: e.target.value ? parseInt(e.target.value) : undefined, page: 1 })}
                  className="w-full px-3 py-2.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all text-sm appearance-none"
                >
                  <option value="">Any Time</option>
                  <option value="7">Within 7 days</option>
                  <option value="30">Within 30 days</option>
                  <option value="90">Within 3 months</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
