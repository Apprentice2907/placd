import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import type { SearchFilters } from '../lib/api';
import { JobFilters } from '../components/JobFilters';
import { VirtualJobList } from '../components/VirtualJobList';
import { SearchBar } from '../components/SearchBar';

export const HiringPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const debounceRef = React.useRef<number | null>(null);

  const filtersFromUrl = (): Omit<SearchFilters, 'page'> => ({
    per_page: 24,
    sort: searchParams.get('sort') || 'newest',
    status: 'active',
    q: searchParams.get('q') || undefined,
    job_type: searchParams.get('job_type') || undefined,
    is_remote: searchParams.get('is_remote') === 'true' ? true : undefined,
    location: searchParams.get('location') || undefined,
    seniority: searchParams.get('seniority') || undefined,
    skills: searchParams.get('skills') || undefined,
    salary_min: searchParams.get('salary_min') ? Number(searchParams.get('salary_min')) : undefined,
    salary_max: searchParams.get('salary_max') ? Number(searchParams.get('salary_max')) : undefined,
  });

  const [filters, setFilters] = useState<Omit<SearchFilters, 'page'>>(filtersFromUrl);
  const [debouncedFilters, setDebouncedFilters] = useState<Omit<SearchFilters, 'page'>>(filtersFromUrl);
  const [localSearch, setLocalSearch] = useState(filters.q || '');

  // Derived tags for the search bar (e.g. from job_type, skills)
  const tags = useMemo(() => {
    const t = [];
    if (filters.skills) t.push(...filters.skills.split(',').filter(Boolean));
    if (filters.job_type) t.push(...filters.job_type.split(',').filter(Boolean).map(x => x.replace('-', ' ')));
    if (filters.is_remote) t.push('Remote');
    if (filters.seniority) t.push(...filters.seniority.split(',').filter(Boolean));
    return t;
  }, [filters]);

  const handleFilterChange = useCallback((newFilters: Partial<Omit<SearchFilters, 'page'>>, immediate = false) => {
    const merged = { ...filters, ...newFilters };
    setFilters(merged);

    const applyChanges = () => {
      setDebouncedFilters(merged);
      const params: Record<string, string> = {};
      if (merged.q) params.q = merged.q;
      if (merged.sort && merged.sort !== 'newest') params.sort = merged.sort;
      if (merged.job_type) params.job_type = merged.job_type;
      if (merged.is_remote) params.is_remote = 'true';
      if (merged.location) params.location = merged.location;
      if (merged.skills) params.skills = merged.skills;
      if (merged.seniority) params.seniority = merged.seniority;
      if (merged.salary_min) params.salary_min = String(merged.salary_min);
      if (merged.salary_max) params.salary_max = String(merged.salary_max);
      setSearchParams(params, { replace: true });
    };

    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    if (immediate) {
      applyChanges();
    } else {
      debounceRef.current = window.setTimeout(applyChanges, 300);
    }
  }, [filters, setSearchParams]);

  // Update query on localSearch change with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      onFilterChange({ q: localSearch || undefined });
    }, 300);
    return () => clearTimeout(timer);
  }, [localSearch]);

  const onFilterChange = (f: Partial<Omit<SearchFilters, 'page'>>, immediate = false) => {
    handleFilterChange(f, immediate);
  };

  const removeTag = (tag: string) => {
    // Basic tag removal logic
    if (tag === 'Remote') {
      onFilterChange({ is_remote: undefined });
      return;
    }
    const skills = (filters.skills || '').split(',').filter(Boolean);
    if (skills.includes(tag)) {
      onFilterChange({ skills: skills.filter(s => s !== tag).join(',') || undefined });
      return;
    }
    const jobTypes = (filters.job_type || '').split(',').filter(Boolean);
    const jtMatch = jobTypes.find(jt => jt.replace('-', ' ') === tag);
    if (jtMatch) {
      onFilterChange({ job_type: jobTypes.filter(jt => jt !== jtMatch).join(',') || undefined });
      return;
    }
    const seniorities = (filters.seniority || '').split(',').filter(Boolean);
    if (seniorities.includes(tag)) {
      onFilterChange({ seniority: seniorities.filter(s => s !== tag).join(',') || undefined });
      return;
    }
  };

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['jobs', debouncedFilters],
    queryFn: ({ pageParam = 1 }) => api.jobs.search({ ...debouncedFilters, page: pageParam as number }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.has_next ? lastPage.page + 1 : undefined,
  });

  const allJobs = data?.pages.flatMap((page) => page.jobs) || [];
  const totalJobs = data?.pages[0]?.total || 0;

  return (
    <div className="flex flex-col h-full bg-[#FFFFFF] w-full text-black">
      <SearchBar 
        searchQuery={localSearch} 
        setSearchQuery={setLocalSearch} 
        tags={tags} 
        onRemoveTag={removeTag} 
      />

      <div className="flex flex-1 overflow-hidden">
        <JobFilters filters={filters as any} onFilterChange={onFilterChange as any} />

        <main className="flex-1 overflow-y-auto bg-[#FFFFFF] px-[24px] py-6">
          {/* Header Row */}
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-[26px] text-black">
              <span className="font-[800]">{totalJobs.toLocaleString()}</span> <span className="font-[400]">Jobs Found</span>
            </h1>
            <div className="flex items-center gap-2 text-[14px] font-normal text-black cursor-pointer group">
              Sort by: <span className="font-bold underline decoration-2 underline-offset-4">Newest Post</span>
            </div>
          </div>

          {isError && (
            <div className="p-8 text-center rounded-2xl border border-red-200 bg-red-50 mb-6">
              <p className="text-red-600">Failed to load jobs. Please try again later.</p>
            </div>
          )}

          <VirtualJobList
            jobs={allJobs}
            isLoading={isLoading && !data}
            hasNextPage={hasNextPage}
            onLoadMore={fetchNextPage}
            isFetchingNextPage={isFetchingNextPage}
            className="w-full h-full pb-20"
          />
        </main>
      </div>
    </div>
  );
};

export default HiringPage;
