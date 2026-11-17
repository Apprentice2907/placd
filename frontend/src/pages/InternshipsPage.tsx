import React, { useEffect, useMemo, useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { VirtualJobList } from '../components/VirtualJobList';
import { cn } from '../lib/utils';

const DURATIONS = [
  { label: 'Any duration', value: 0 },
  { label: 'Up to 2 months', value: 2 },
  { label: 'Up to 3 months', value: 3 },
  { label: 'Up to 6 months', value: 6 },
];

// Keys must match INTERESTS in backend/utils/matching.py
const INTERESTS = [
  { key: '', label: 'All' },
  { key: 'ai', label: 'AI & ML' },
  { key: 'data', label: 'Data' },
  { key: 'web', label: 'Web' },
  { key: 'mobile', label: 'Mobile apps' },
  { key: 'cloud', label: 'Cloud & DevOps' },
  { key: 'security', label: 'Cybersecurity' },
  { key: 'design', label: 'UI/UX Design' },
];
const INTEREST_STORAGE_KEY = 'placd_interest';

function readSavedInterest(): string {
  try {
    const saved = localStorage.getItem(INTEREST_STORAGE_KEY) || '';
    return INTERESTS.some((i) => i.key === saved) ? saved : '';
  } catch {
    return '';
  }
}

const Toggle: React.FC<{ label: string; active: boolean; onClick: () => void }> = ({ label, active, onClick }) => (
  <button
    type="button"
    aria-pressed={active}
    onClick={onClick}
    className={cn(
      'shrink-0 whitespace-nowrap px-[14px] py-[7px] rounded-[9999px] border-[1.5px] text-[13px] font-[600] transition-colors',
      active ? 'bg-black border-black text-white' : 'bg-white border-[#E0E0E0] text-[#333333] hover:border-black'
    )}
  >
    {label}
  </button>
);

export const InternshipsPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [indiaOnly, setIndiaOnly] = useState(true);
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [paidOnly, setPaidOnly] = useState(true);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [maxDuration, setMaxDuration] = useState(0);
  const [interest, setInterest] = useState(readSavedInterest);
  const [includeRelated, setIncludeRelated] = useState(false);
  const [smallCompanies, setSmallCompanies] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(INTEREST_STORAGE_KEY, interest);
    } catch {
      // Remembering the choice is only a convenience
    }
  }, [interest]);

  useEffect(() => {
    const timer = setTimeout(() => setQuery(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const filters = useMemo(() => ({
    filter: 'internship',
    sort: 'best',
    status: 'active',
    per_page: 24,
    q: query || undefined,
    country: indiaOnly ? 'india' : undefined,
    remote: remoteOnly ? true : undefined,
    paid_only: paidOnly ? true : undefined,
    verified_only: verifiedOnly ? true : undefined,
    max_duration_months: maxDuration || undefined,
    interest: interest || undefined,
    include_related: interest && includeRelated ? true : undefined,
    small_companies: smallCompanies ? true : undefined,
  }), [query, indiaOnly, remoteOnly, paidOnly, verifiedOnly, maxDuration, interest, includeRelated, smallCompanies]);

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['internships', filters],
    queryFn: ({ pageParam = 1 }) => api.jobs.search({ ...filters, page: pageParam as number }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.has_next ? lastPage.page + 1 : undefined,
  });

  const jobs = data?.pages.flatMap((page) => page.jobs) || [];
  const total = data?.pages[0]?.total || 0;

  return (
    <div className="flex flex-col h-full bg-white w-full text-black overflow-hidden px-[24px] py-6">
      <div className="shrink-0 mb-5">
        <h1 className="text-[26px]">
          <span className="font-[800]">{total.toLocaleString()}</span>{' '}
          <span className="font-[400]">Internships Found</span>
        </h1>
        <p className="mt-1 text-[13px] text-[#555555]">
          A real internship never asks you to pay. Don't send money for registration, training or a certificate.
        </p>

        <p className="mt-4 text-[13px] font-[700]">What are you interested in?</p>
        <div className="mt-2 flex items-center gap-2 overflow-x-auto no-scrollbar md:flex-wrap md:overflow-visible">
          {INTERESTS.map((i) => (
            <Toggle key={i.key || 'all'} label={i.label} active={interest === i.key} onClick={() => setInterest(i.key)} />
          ))}
        </div>
        {interest && (
          <label className="mt-2 flex items-center gap-2 text-[13px] text-[#333333] cursor-pointer w-fit">
            <input type="checkbox" checked={includeRelated} onChange={(e) => setIncludeRelated(e.target.checked)} />
            Also show related fields
          </label>
        )}

        {/* On phones the extra filters fold away so the internships stay visible */}
        <button
          type="button"
          aria-expanded={filtersOpen}
          onClick={() => setFiltersOpen(!filtersOpen)}
          className="mt-3 md:hidden text-[13px] font-[700] underline underline-offset-4"
        >
          {filtersOpen ? 'Hide filters' : 'More filters'}
        </button>

        <div className={cn(filtersOpen ? 'block' : 'hidden', 'md:block')}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by role or skill..."
          aria-label="Search internships"
          className="mt-4 w-full max-w-[520px] px-[14px] py-[9px] rounded-[8px] border-[1.5px] border-[#E0E0E0] text-[14px] outline-none focus:border-black"
        />

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Toggle label="Startups & small companies" active={smallCompanies} onClick={() => setSmallCompanies(!smallCompanies)} />
          <Toggle label="India" active={indiaOnly} onClick={() => setIndiaOnly(!indiaOnly)} />
          <Toggle label="Remote" active={remoteOnly} onClick={() => setRemoteOnly(!remoteOnly)} />
          <Toggle label="Paid" active={paidOnly} onClick={() => setPaidOnly(!paidOnly)} />
          <Toggle label="Verified links only" active={verifiedOnly} onClick={() => setVerifiedOnly(!verifiedOnly)} />
          <select
            value={maxDuration}
            onChange={(e) => setMaxDuration(Number(e.target.value))}
            aria-label="Maximum duration"
            className="px-[12px] py-[7px] rounded-[9999px] border-[1.5px] border-[#E0E0E0] bg-white text-[13px] font-[600] outline-none hover:border-black"
          >
            {DURATIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
        </div>
        <p className="mt-2 text-[12px] text-[#777777]">
          Strong chance, Good fit and Stretch are based on company size, applicants so far and how new a post is.
          They are a guide, not a prediction.
        </p>
        </div>
      </div>

      {isError && (
        <div className="p-8 text-center rounded-2xl border border-red-200 bg-red-50 mb-6 shrink-0">
          <p className="text-red-600">Failed to load internships. Please try again later.</p>
        </div>
      )}

      <div className="flex-1 overflow-y-auto no-scrollbar pb-20">
        <VirtualJobList
          jobs={jobs}
          isLoading={isLoading && !data}
          hasNextPage={hasNextPage}
          onLoadMore={fetchNextPage}
          isFetchingNextPage={isFetchingNextPage}
          className="w-full"
        />
      </div>
    </div>
  );
};

export default InternshipsPage;
