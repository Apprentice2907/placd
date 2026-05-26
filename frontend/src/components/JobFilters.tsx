import React, { useState } from 'react';
import type { SearchFilters } from '../lib/api';
import { cn } from '../lib/utils';
import { MapPin, Search, ChevronDown, Calendar, Briefcase, Filter } from 'lucide-react';

const CATEGORIES = [
  { label: 'All Jobs', value: '' },
  { label: 'Internships', value: 'internship' },
  { label: 'Full-time', value: 'fulltime' },
  { label: 'Remote', value: 'remote_first' }, // or is_remote=true
  { label: 'FAANG', value: 'faang' },
  { label: 'Startups', value: 'startup' },
  { label: 'AI Labs', value: 'ai_lab' },
  { label: 'HFT', value: 'hft' },
  { label: 'New Grad', value: 'new_grad' },
  { label: 'Research', value: 'research' },
];

interface JobFiltersProps {
  filters: SearchFilters;
  onFilterChange: (newFilters: Partial<SearchFilters>) => void;
}

export const JobFilters: React.FC<JobFiltersProps> = ({ filters, onFilterChange }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Handle pill click
  const handleCategoryClick = (cat: typeof CATEGORIES[0]) => {
    if (cat.value === '') {
      onFilterChange({ category: undefined, job_type: undefined, is_remote: undefined, page: 1 });
    } else if (cat.value === 'internship' || cat.value === 'fulltime') {
      onFilterChange({ job_type: cat.value, category: undefined, is_remote: undefined, page: 1 });
    } else if (cat.value === 'remote_first') {
      onFilterChange({ is_remote: true, job_type: undefined, category: undefined, page: 1 });
    } else {
      onFilterChange({ category: cat.value, job_type: undefined, is_remote: undefined, page: 1 });
    }
  };

  // Determine active pill
  const getIsActive = (cat: typeof CATEGORIES[0]) => {
    if (cat.value === '') {
      return !filters.category && !filters.job_type && filters.is_remote === undefined;
    }
    if (cat.value === 'internship' || cat.value === 'fulltime') {
      return filters.job_type === cat.value;
    }
    if (cat.value === 'remote_first') {
      return filters.is_remote === true;
    }
    return filters.category === cat.value;
  };

  return (
    <div className="w-full flex flex-col gap-4 py-4 sticky top-0 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-md z-40 border-b border-neutral-200 dark:border-neutral-800">
      
      {/* Top Search Bar */}
      <div className="flex flex-col md:flex-row w-full gap-3 px-4 max-w-7xl mx-auto">
        <div className="relative flex-1 group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 group-focus-within:text-indigo-500 w-5 h-5 transition-colors" />
          <input 
            type="text" 
            placeholder="Search roles, companies, keywords..." 
            value={filters.q || ''}
            onChange={(e) => onFilterChange({ q: e.target.value, page: 1 })}
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-neutral-900 dark:text-neutral-100 shadow-sm"
          />
        </div>
        <button 
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors font-medium text-neutral-700 dark:text-neutral-300 shadow-sm whitespace-nowrap"
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
                    : "bg-white dark:bg-neutral-900 text-neutral-600 dark:text-neutral-400 border-neutral-200 dark:border-neutral-800 hover:border-indigo-300 dark:hover:border-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-900/30"
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-5 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-800 shadow-inner">
            
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1">
                <MapPin className="w-3 h-3" /> Location
              </label>
              <input 
                type="text" 
                placeholder="e.g. San Francisco, London" 
                value={filters.location || ''}
                onChange={(e) => onFilterChange({ location: e.target.value, page: 1 })}
                className="w-full px-3 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all text-sm"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1">
                <Briefcase className="w-3 h-3" /> Experience
              </label>
              <div className="relative">
                <select 
                  value={filters.experience_level || ''}
                  onChange={(e) => onFilterChange({ experience_level: e.target.value || undefined, page: 1 })}
                  className="w-full px-3 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all text-sm appearance-none"
                >
                  <option value="">Any Experience</option>
                  <option value="entry">Entry Level</option>
                  <option value="mid">Mid Level</option>
                  <option value="senior">Senior</option>
                  <option value="lead">Lead / Staff</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-neutral-500 uppercase tracking-wider flex items-center gap-1">
                <Calendar className="w-3 h-3" /> Sort By
              </label>
              <div className="relative">
                <select 
                  value={filters.sort || 'newest'}
                  onChange={(e) => onFilterChange({ sort: e.target.value, page: 1 })}
                  className="w-full px-3 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all text-sm appearance-none"
                >
                  <option value="newest">Newest First</option>
                  <option value="relevance">Relevance</option>
                  <option value="oldest">Oldest First</option>
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
