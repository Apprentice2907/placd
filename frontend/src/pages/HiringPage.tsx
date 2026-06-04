import React, { useState, useEffect, useCallback } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import type { Job, SearchFilters } from '../lib/api';
import { JobFilters } from '../components/JobFilters';
import { VirtualJobList } from '../components/VirtualJobList';
import { JobDetailPanel } from '../components/JobDetailPanel';

export const HiringPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const debounceRef = React.useRef<number | null>(null);

  // Build filters from URL params
  const filtersFromUrl = (): Omit<SearchFilters, 'page'> => ({
    per_page: 24,
    sort: searchParams.get('sort') || 'newest',
    status: 'active',
    q: searchParams.get('q') || undefined,
    job_type: searchParams.get('job_type') || undefined,
    is_remote: searchParams.get('is_remote') === 'true' ? true : undefined,
    location: searchParams.get('location') || undefined,
    experience_level: searchParams.get('experience_level') || undefined,
    skills: searchParams.get('skills') || undefined,
    seniority: searchParams.get('seniority') || undefined,
    job_function: searchParams.get('job_function') || undefined,
    source_platform: searchParams.get('source_platform') || undefined,
    posted_within: searchParams.get('posted_within') || undefined,
    salary_min: searchParams.get('salary_min') ? Number(searchParams.get('salary_min')) : undefined,
    salary_max: searchParams.get('salary_max') ? Number(searchParams.get('salary_max')) : undefined,
  });

  const [filters, setFilters] = useState<Omit<SearchFilters, 'page'>>(filtersFromUrl);

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['stats-quick'],
    queryFn: () => api.stats.quick(),
    staleTime: 5 * 60 * 1000,
  });

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['jobs', filters],
    queryFn: ({ pageParam = 1 }) => api.jobs.search({ ...filters, page: pageParam as number }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.has_next ? lastPage.page + 1 : undefined,
  });

  const allJobs = data?.pages.flatMap((page) => page.jobs) || [];
  const totalJobs = data?.pages[0]?.total || 0;

  const handleFilterChange = useCallback((newFilters: Partial<Omit<SearchFilters, 'page'>>) => {
    const merged = { ...filters, ...newFilters };
    setFilters(merged);

    // Debounce URL update 300ms
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      const params: Record<string, string> = {};
      if (merged.q) params.q = merged.q;
      if (merged.sort && merged.sort !== 'newest') params.sort = merged.sort;
      if (merged.job_type) params.job_type = merged.job_type;
      if (merged.is_remote) params.is_remote = 'true';
      if (merged.location) params.location = merged.location;
      if (merged.experience_level) params.experience_level = merged.experience_level;
      if (merged.skills) params.skills = merged.skills;
      if (merged.seniority) params.seniority = merged.seniority;
      if (merged.job_function) params.job_function = merged.job_function;
      if (merged.source_platform) params.source_platform = merged.source_platform;
      if (merged.posted_within) params.posted_within = merged.posted_within;
      if (merged.salary_min) params.salary_min = String(merged.salary_min);
      if (merged.salary_max) params.salary_max = String(merged.salary_max);
      setSearchParams(params, { replace: true });
    }, 300);
  }, [filters, setSearchParams]);

  const handleJobSelect = (job: Job) => {
    setSelectedJob(job);
    setIsPanelOpen(true);
  };

  const handlePanelClose = () => {
    setIsPanelOpen(false);
  };

  // J/K keyboard navigation
  const [activeIndex, setActiveIndex] = useState(-1);
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (allJobs.length === 0) return;
      if (e.key === 'j') {
        const next = Math.min(activeIndex + 1, allJobs.length - 1);
        setActiveIndex(next);
        setSelectedJob(allJobs[next]);
        setIsPanelOpen(true);
      } else if (e.key === 'k') {
        const prev = Math.max(activeIndex - 1, 0);
        setActiveIndex(prev);
        setSelectedJob(allJobs[prev]);
        setIsPanelOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [allJobs, activeIndex]);

  useEffect(() => { setActiveIndex(-1); }, [filters]);

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] flex flex-col">
      <JobFilters filters={filters as any} onFilterChange={handleFilterChange as any} stats={stats} />

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h1 className="text-2xl font-bold tracking-tight">
            {isLoading ? 'Loading jobs…' : `${totalJobs.toLocaleString()} active jobs`}
          </h1>
          <div className="text-sm text-[var(--color-text-muted)] hidden sm:flex items-center gap-1">
            Press{' '}
            <kbd className="px-1.5 py-0.5 border border-[var(--color-border)] rounded shadow-sm font-mono text-xs bg-white dark:bg-neutral-800">J</kbd>
            {' '}/{' '}
            <kbd className="px-1.5 py-0.5 border border-[var(--color-border)] rounded shadow-sm font-mono text-xs bg-white dark:bg-neutral-800">K</kbd>
            {' '}to navigate
          </div>
        </div>

        {isError && (
          <div className="p-8 text-center rounded-2xl border border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10">
            <p className="text-red-600 dark:text-red-400">Failed to load jobs. Please try again later.</p>
          </div>
        )}

        <VirtualJobList
          jobs={allJobs}
          onJobSelect={handleJobSelect}
          selectedJobId={selectedJob?.id || null}
          isLoading={isLoading && !data}
          hasNextPage={hasNextPage}
          onLoadMore={fetchNextPage}
          isFetchingNextPage={isFetchingNextPage}
          className="w-full"
        />
      </main>

      {/* Job Detail Panel */}
      <JobDetailPanel
        job={selectedJob}
        isOpen={isPanelOpen}
        onClose={handlePanelClose}
      />
    </div>
  );
};
