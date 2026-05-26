import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { SearchFilters } from '../lib/api';
import { JobFilters } from '../components/JobFilters';
import { JobCard } from '../components/JobCard';
import { Briefcase } from 'lucide-react';

export const HiringPage: React.FC = () => {
  const [filters, setFilters] = useState<SearchFilters>({ page: 1, per_page: 24, sort: 'newest', status: 'active' });
  const [activeIndex, setActiveIndex] = useState(-1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => api.jobs.search(filters),
    placeholderData: (prev) => prev,
  });

  // Handle J/K keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      const jobsCount = data?.jobs?.length || 0;
      if (jobsCount === 0) return;

      if (e.key === 'j') {
        setActiveIndex((prev) => Math.min(prev + 1, jobsCount - 1));
      } else if (e.key === 'k') {
        setActiveIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter' && activeIndex >= 0) {
        // We could programmatic navigate here, but for now just visual
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [data, activeIndex]);

  // Reset active index when data changes
  useEffect(() => {
    setActiveIndex(-1);
  }, [filters]);

  const handleFilterChange = (newFilters: Partial<SearchFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-[#0a0a0a] text-neutral-900 dark:text-neutral-100 flex flex-col">
      <JobFilters filters={filters} onFilterChange={handleFilterChange} />
      
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-8">
        
        {/* Header Meta */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold tracking-tight">
            {isLoading ? 'Loading jobs...' : `${data?.total?.toLocaleString() || 0} active jobs`}
          </h1>
          <div className="text-sm text-neutral-500 dark:text-neutral-400 hidden sm:block">
            Press <kbd className="px-1.5 py-0.5 border border-neutral-200 dark:border-neutral-700 rounded-md shadow-sm bg-white dark:bg-neutral-800 font-mono text-xs">J</kbd> and <kbd className="px-1.5 py-0.5 border border-neutral-200 dark:border-neutral-700 rounded-md shadow-sm bg-white dark:bg-neutral-800 font-mono text-xs">K</kbd> to navigate
          </div>
        </div>

        {/* Content */}
        {isError && (
          <div className="p-8 text-center rounded-2xl border border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10">
            <p className="text-red-600 dark:text-red-400">Failed to load jobs. Please try again later.</p>
          </div>
        )}

        {isLoading && !data && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-48 rounded-2xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 p-5 animate-pulse">
                <div className="flex gap-4">
                  <div className="w-12 h-12 bg-neutral-200 dark:bg-neutral-800 rounded-xl"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-neutral-200 dark:bg-neutral-800 rounded w-3/4"></div>
                    <div className="h-3 bg-neutral-200 dark:bg-neutral-800 rounded w-1/2"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && data?.jobs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 bg-neutral-100 dark:bg-neutral-800 rounded-2xl flex items-center justify-center mb-4">
              <Briefcase className="w-8 h-8 text-neutral-400" />
            </div>
            <h2 className="text-lg font-bold">No jobs found</h2>
            <p className="text-neutral-500 dark:text-neutral-400 mt-2 max-w-md">Try adjusting your filters or search terms to see more results.</p>
            <button 
              onClick={() => setFilters({ page: 1, per_page: 24, sort: 'newest', status: 'active' })}
              className="mt-6 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
            >
              Clear all filters
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {data?.jobs.map((job, idx) => (
            <JobCard key={job.id} job={job} isActive={idx === activeIndex} />
          ))}
        </div>

        {/* Pagination */}
        {data && data.total > 0 && (
          <div className="mt-12 flex items-center justify-center gap-2">
            <button
              disabled={filters.page === 1}
              onClick={() => handleFilterChange({ page: (filters.page || 1) - 1 })}
              className="px-4 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 disabled:opacity-50 font-medium text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
            >
              Previous
            </button>
            <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400 px-4">
              Page {filters.page} of {Math.ceil(data.total / (filters.per_page || 24))}
            </span>
            <button
              disabled={!data.has_next}
              onClick={() => handleFilterChange({ page: (filters.page || 1) + 1 })}
              className="px-4 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 disabled:opacity-50 font-medium text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
            >
              Next
            </button>
          </div>
        )}

      </main>
    </div>
  );
};
