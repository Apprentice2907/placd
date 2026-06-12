import React, { useState, useEffect, useMemo } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { JobFilters } from '../components/JobFilters';
import { VirtualJobList } from '../components/VirtualJobList';
import { SearchBar } from '../components/SearchBar';

export const HiringPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [localSearch, setLocalSearch] = useState(searchParams.get('q') || '');

  // Derived tags for the search bar (e.g. from job_type, skills)
  const tags = useMemo(() => {
    const t = [];
    if (searchParams.get('skills')) t.push(...searchParams.get('skills')!.split(',').filter(Boolean));
    if (searchParams.get('job_type')) t.push(...searchParams.get('job_type')!.split(',').filter(Boolean).map(x => x.replace('-', ' ')));
    if (searchParams.get('is_remote') === 'true') t.push('Remote');
    if (searchParams.get('seniority')) t.push(...searchParams.get('seniority')!.split(',').filter(Boolean));
    return t;
  }, [searchParams]);

  // Update query on localSearch change with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      const next = new URLSearchParams(searchParams);
      if (localSearch) {
        next.set('q', localSearch);
      } else {
        next.delete('q');
      }
      if (next.toString() !== searchParams.toString()) {
        setSearchParams(next, { replace: true });
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [localSearch, searchParams, setSearchParams]);

  const removeTag = (tag: string) => {
    const next = new URLSearchParams(searchParams);
    
    if (tag === 'Remote') {
      next.delete('is_remote');
    } else {
      const skills = (next.get('skills') || '').split(',').filter(Boolean);
      if (skills.includes(tag)) {
        const updated = skills.filter(s => s !== tag);
        if (updated.length) next.set('skills', updated.join(','));
        else next.delete('skills');
      } else {
        const jobTypes = (next.get('job_type') || '').split(',').filter(Boolean);
        const jtMatch = jobTypes.find(jt => jt.replace('-', ' ') === tag);
        if (jtMatch) {
          const updated = jobTypes.filter(jt => jt !== jtMatch);
          if (updated.length) next.set('job_type', updated.join(','));
          else next.delete('job_type');
        } else {
          const seniorities = (next.get('seniority') || '').split(',').filter(Boolean);
          if (seniorities.includes(tag)) {
            const updated = seniorities.filter(s => s !== tag);
            if (updated.length) next.set('seniority', updated.join(','));
            else next.delete('seniority');
          }
        }
      }
    }
    setSearchParams(next, { replace: false });
  };

  const parsedFilters = useMemo(() => {
    return {
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
    };
  }, [searchParams]);

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['jobs', searchParams.toString()],
    queryFn: ({ pageParam = 1 }) => api.jobs.search({ ...parsedFilters, page: pageParam as number }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.has_next ? lastPage.page + 1 : undefined,
  });

  const allJobs = data?.pages.flatMap((page) => page.jobs) || [];
  const totalJobs = data?.pages[0]?.total || 0;

  return (
    <div className="flex flex-col h-full bg-[#FFFFFF] w-full text-black overflow-hidden">
      <div className="shrink-0">
        <SearchBar 
          searchQuery={localSearch} 
          setSearchQuery={setLocalSearch} 
          tags={tags} 
          onRemoveTag={removeTag} 
        />
      </div>

      <div className="flex flex-1 overflow-hidden">
        <JobFilters />

        <main className="flex-1 flex flex-col overflow-hidden bg-[#FFFFFF] px-[24px] py-6">
          {/* Header Row */}
          <div className="flex items-center justify-between mb-6 shrink-0">
            <h1 className="text-[26px] text-black">
              <span className="font-[800]">{totalJobs.toLocaleString()}</span> <span className="font-[400]">Jobs Found</span>
            </h1>
            <div className="flex items-center gap-2 text-[14px] font-normal text-black cursor-pointer group">
              Sort by: <span className="font-bold underline decoration-2 underline-offset-4">Newest Post</span>
            </div>
          </div>

          {isError && (
            <div className="p-8 text-center rounded-2xl border border-red-200 bg-red-50 mb-6 shrink-0">
              <p className="text-red-600">Failed to load jobs. Please try again later.</p>
            </div>
          )}

          <div className="flex-1 overflow-y-auto no-scrollbar pb-20">
            <VirtualJobList
              jobs={allJobs}
              isLoading={isLoading && !data}
              hasNextPage={hasNextPage}
              onLoadMore={fetchNextPage}
              isFetchingNextPage={isFetchingNextPage}
              className="w-full"
            />
          </div>
        </main>
      </div>
    </div>
  );
};

export default HiringPage;
