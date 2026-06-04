import React, { useRef, useEffect, useCallback, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { Job } from '../lib/api';
import { JobCard } from './JobCard';
import { JobCardSkeleton } from './Skeletons';
import { ChevronUp, Briefcase } from 'lucide-react';

interface VirtualJobListProps {
  jobs: Job[];
  onJobSelect?: (job: Job) => void;
  selectedJobId?: string | null;
  isLoading: boolean;
  hasNextPage?: boolean;
  onLoadMore?: () => void;
  isFetchingNextPage?: boolean;
  className?: string;
}

export const VirtualJobList: React.FC<VirtualJobListProps> = ({
  jobs,
  onJobSelect,
  selectedJobId,
  isLoading,
  hasNextPage,
  onLoadMore,
  isFetchingNextPage,
  className = '',
}) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);

  const rowVirtualizer = useVirtualizer({
    count: jobs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 160,
    overscan: 5,
    measureElement: (el) => el.getBoundingClientRect().height,
  });

  // IntersectionObserver on sentinel → trigger onLoadMore
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasNextPage || !onLoadMore) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetchingNextPage) {
          onLoadMore();
        }
      },
      { root: parentRef.current, threshold: 0.1 }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, onLoadMore, isFetchingNextPage]);

  // Scroll-to-top button logic
  useEffect(() => {
    const el = parentRef.current;
    if (!el) return;
    const handleScroll = () => setShowScrollTop(el.scrollTop > 500);
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = useCallback(() => {
    parentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Loading skeleton
  if (isLoading && jobs.length === 0) {
    return (
      <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 ${className}`}>
        {Array.from({ length: 8 }).map((_, i) => (
          <JobCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  // Empty state
  if (!isLoading && jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-20 h-20 rounded-2xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-5">
          <Briefcase className="w-10 h-10 text-neutral-400" />
        </div>
        <h2 className="text-xl font-bold text-[var(--color-text-primary)]">No jobs found</h2>
        <p className="text-[var(--color-text-secondary)] mt-2 max-w-sm text-sm">
          No jobs found. Try different filters.
        </p>
      </div>
    );
  }

  const virtualItems = rowVirtualizer.getVirtualItems();

  return (
    <div className="relative">
      <div
        ref={parentRef}
        className={`overflow-y-auto ${className}`}
        style={{ maxHeight: 'calc(100vh - 220px)' }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            position: 'relative',
            width: '100%',
          }}
        >
          {virtualItems.map((virtualRow) => {
            const job = jobs[virtualRow.index];
            if (!job) return null;
            return (
              <div
                key={virtualRow.key}
                data-index={virtualRow.index}
                ref={rowVirtualizer.measureElement}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualRow.start}px)`,
                  paddingBottom: '16px',
                }}
              >
                <JobCard
                  job={job}
                  isActive={job.id === selectedJobId}
                  onOpen={onJobSelect ? () => onJobSelect(job) : undefined}
                />
              </div>
            );
          })}
        </div>

        {/* Sentinel for infinite scroll */}
        {hasNextPage && (
          <div ref={sentinelRef} className="h-8 w-full" />
        )}

        {/* Loading more indicator */}
        {isFetchingNextPage && (
          <div className="py-6 flex justify-center">
            <div className="flex gap-1">
              {[0,1,2].map(i => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Scroll to top button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-6 right-6 z-40 p-3 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/30 transition-all hover:scale-105 active:scale-95"
          aria-label="Scroll to top"
        >
          <ChevronUp className="w-5 h-5" />
        </button>
      )}
    </div>
  );
};
