import React from 'react';

// ─── Pulse wrapper ─────────────────────────────────────────────────────────
const Pulse: React.FC<{ className?: string; style?: React.CSSProperties }> = ({ className = '', style }) => (
  <div className={`animate-pulse rounded bg-gray-200 dark:bg-gray-700 ${className}`} style={style} />
);

// ─── JobCardSkeleton ───────────────────────────────────────────────────────
export const JobCardSkeleton: React.FC = () => (
  <div className="relative flex flex-col p-5 rounded-xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 h-[152px]">
    {/* top-left bookmark placeholder */}
    <Pulse className="absolute top-4 left-4 w-5 h-5 rounded-full" />
    {/* top-right match ring placeholder */}
    <Pulse className="absolute top-4 right-4 w-10 h-10 rounded-full" />

    <div className="pt-8 flex flex-col gap-3">
      {/* Logo + company/title */}
      <div className="flex items-center gap-3">
        <Pulse className="w-10 h-10 rounded-full shrink-0" />
        <div className="flex flex-col gap-1.5 flex-1">
          <Pulse className="h-3.5 w-32 rounded" />
          <Pulse className="h-3 w-48 rounded" />
        </div>
      </div>
      {/* Pills */}
      <div className="flex gap-2">
        <Pulse className="h-5 w-20 rounded-md" />
        <Pulse className="h-5 w-14 rounded-md" />
        <Pulse className="h-5 w-24 rounded-md" />
      </div>
      {/* Skills */}
      <div className="flex gap-1.5">
        <Pulse className="h-4 w-16 rounded" />
        <Pulse className="h-4 w-12 rounded" />
        <Pulse className="h-4 w-10 rounded" />
      </div>
    </div>
  </div>
);

// ─── JobDetailSkeleton ─────────────────────────────────────────────────────
export const JobDetailSkeleton: React.FC = () => (
  <div className="flex flex-col p-6 gap-6">
    {/* Header */}
    <div className="flex items-center gap-4 mt-4">
      <Pulse className="w-16 h-16 rounded-xl shrink-0" />
      <div className="flex flex-col gap-2 flex-1">
        <Pulse className="h-5 w-3/4 rounded" />
        <Pulse className="h-4 w-1/2 rounded" />
        <Pulse className="h-3.5 w-1/3 rounded" />
      </div>
    </div>

    {/* Quick facts row */}
    <div className="flex gap-3">
      {[1,2,3,4].map(i => <Pulse key={i} className="h-8 flex-1 rounded-lg" />)}
    </div>

    {/* Skills */}
    <div>
      <Pulse className="h-4 w-24 rounded mb-3" />
      <div className="flex flex-wrap gap-2">
        {[1,2,3,4,5].map(i => <Pulse key={i} className="h-6 w-20 rounded-full" />)}
      </div>
    </div>

    {/* Role summary */}
    <div className="flex flex-col gap-2">
      <Pulse className="h-4 w-full rounded" />
      <Pulse className="h-4 w-5/6 rounded" />
    </div>

    {/* Description */}
    <div className="flex flex-col gap-2">
      {[1,2,3,4,5,6].map(i => <Pulse key={i} className={`h-3.5 rounded ${i % 3 === 0 ? 'w-2/3' : 'w-full'}`} />)}
    </div>

    {/* Action bar */}
    <div className="mt-auto pt-4 border-t border-neutral-200 dark:border-neutral-800">
      <Pulse className="h-11 w-full rounded-lg" />
    </div>
  </div>
);

// ─── FiltersSkeleton ───────────────────────────────────────────────────────
export const FiltersSkeleton: React.FC = () => (
  <div className="w-full flex flex-col gap-4 py-4 border-b border-[var(--border-color)]">
    {/* Search bar */}
    <div className="px-4">
      <Pulse className="h-12 w-full rounded-xl" />
    </div>
    {/* Pills row */}
    <div className="flex gap-2 px-4">
      {[100, 90, 70, 80, 90].map((w, i) => (
        <Pulse key={i} className={`h-8 rounded-full`} style={{ width: `${w}px` }} />
      ))}
    </div>
  </div>
);

// ─── StatsSkeleton ─────────────────────────────────────────────────────────
export const StatsSkeleton: React.FC = () => (
  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
    {[1,2,3,4].map(i => (
      <div key={i} className="p-4 rounded-xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 flex flex-col gap-2">
        <Pulse className="h-3 w-20 rounded" />
        <Pulse className="h-7 w-12 rounded" />
      </div>
    ))}
  </div>
);
