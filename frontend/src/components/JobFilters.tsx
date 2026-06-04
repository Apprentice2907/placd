import React, { useState, useRef } from 'react';
import type { SearchFilters } from '../lib/api';
import { cn } from '../lib/utils';
import { Search, Filter, X, ChevronDown, ChevronUp, Bookmark } from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const WORK_MODES = ['Remote', 'Hybrid', 'Onsite'] as const;
const EXPERIENCE_LEVELS = ['Intern', 'Junior', 'Mid', 'Senior', 'Staff', 'Lead'] as const;
const JOB_FUNCTIONS = ['Engineering', 'Data', 'ML/AI', 'DevOps', 'Mobile', 'Design', 'Product'] as const;
const POSTED_WITHIN = [
  { label: '24h', value: '1' },
  { label: '3 days', value: '3' },
  { label: '1 week', value: '7' },
  { label: '1 month', value: '30' },
  { label: 'Any time', value: '' },
] as const;
const SOURCE_PLATFORMS = [
  'greenhouse', 'lever', 'ashby', 'himalayas', 'remoteok', 'naukri',
  'internshala', 'amazon_jobs', 'microsoft_careers', 'google_careers',
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// PillGroup helper
// ─────────────────────────────────────────────────────────────────────────────
const PillGroup = ({
  options,
  value,
  onChange,
  multi = false,
}: {
  options: readonly string[];
  value: string[];
  onChange: (v: string[]) => void;
  multi?: boolean;
}) => (
  <div className="flex flex-wrap gap-1.5">
    {options.map((opt) => {
      const isActive = value.includes(opt.toLowerCase());
      return (
        <button
          key={opt}
          type="button"
          onClick={() => {
            if (multi) {
              isActive
                ? onChange(value.filter(v => v !== opt.toLowerCase()))
                : onChange([...value, opt.toLowerCase()]);
            } else {
              onChange(isActive ? [] : [opt.toLowerCase()]);
            }
          }}
          className={cn(
            'px-3 py-1.5 rounded-full text-xs font-semibold border transition-all',
            isActive
              ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm shadow-indigo-600/20'
              : 'bg-transparent text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300'
          )}
        >
          {opt}
        </button>
      );
    })}
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// Collapsible filter section
// ─────────────────────────────────────────────────────────────────────────────
const FilterSection = ({
  label,
  activeCount,
  children,
  defaultOpen = false,
}: {
  label: string;
  activeCount?: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-[var(--color-border)] last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-3 px-1 text-sm font-semibold text-[var(--color-text-primary)] hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
      >
        <span className="flex items-center gap-2">
          {label}
          {activeCount ? (
            <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">
              {activeCount}
            </span>
          ) : null}
        </span>
        {open ? <ChevronUp className="w-4 h-4 opacity-50" /> : <ChevronDown className="w-4 h-4 opacity-50" />}
      </button>
      {open && <div className="pb-4">{children}</div>}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────────────────
interface JobFiltersProps {
  filters: Omit<SearchFilters, 'page'>;
  onFilterChange: (newFilters: Partial<Omit<SearchFilters, 'page'>>) => void;
  stats?: { total: number; internships: number; fulltime: number; remote: number };
  onSaveSearch?: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────
export const JobFilters: React.FC<JobFiltersProps> = ({ filters, onFilterChange, onSaveSearch }) => {
  const [showPanel, setShowPanel] = useState(false);
  const [localSearch, setLocalSearch] = useState((filters as any).q || '');
  const [skillInput, setSkillInput] = useState('');
  const searchTimeout = useRef<number | null>(null);

  // Parse multi-value string filters
  const parsePills = (val?: string): string[] =>
    val ? val.split(',').filter(Boolean) : [];

  const workModes = parsePills((filters as any).work_mode);
  const seniorities = parsePills((filters as any).seniority);
  const jobFunctions = parsePills((filters as any).job_function);
  const skills = parsePills((filters as any).skills);
  const sources = parsePills((filters as any).source_platform);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalSearch(val);
    if (searchTimeout.current) window.clearTimeout(searchTimeout.current);
    searchTimeout.current = window.setTimeout(() => {
      onFilterChange({ q: val || undefined });
    }, 300);
  };

  const handlePillChange = (key: keyof SearchFilters, vals: string[]) => {
    onFilterChange({ [key]: vals.length ? vals.join(',') : undefined } as any);
  };

  const addSkill = (skill: string) => {
    const trimmed = skill.trim();
    if (!trimmed || skills.length >= 5 || skills.includes(trimmed)) return;
    handlePillChange('skills', [...skills, trimmed]);
    setSkillInput('');
  };

  const removeSkill = (skill: string) => {
    handlePillChange('skills', skills.filter(s => s !== skill));
  };

  // Count active filters (excluding q and per_page/sort/status)
  const activeCount = [
    (filters as any).work_mode,
    (filters as any).seniority,
    (filters as any).job_function,
    (filters as any).location,
    (filters as any).skills,
    (filters as any).source_platform,
    (filters as any).posted_within,
    (filters as any).visa_sponsorship,
    (filters as any).equity,
    (filters as any).salary_min,
    (filters as any).salary_max,
  ].filter(Boolean).length;

  const clearAll = () => {
    setLocalSearch('');
    onFilterChange({
      q: undefined, job_type: undefined, is_remote: undefined,
      work_mode: undefined, seniority: undefined, job_function: undefined,
      location: undefined, skills: undefined, source_platform: undefined,
      posted_within: undefined, salary_min: undefined, salary_max: undefined,
      visa_sponsorship: undefined, equity: undefined,
    } as any);
  };

  return (
    <>
      {/* ── Top bar (always visible) ─────────────────────────────────────── */}
      <div className="w-full sticky top-0 z-40 bg-[var(--color-bg-primary)]/90 dark:bg-[var(--color-bg-surface)]/90 backdrop-blur-md border-b border-[var(--color-border)]">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          {/* Search input */}
          <div className="relative flex-1 group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 group-focus-within:text-indigo-500 transition-colors" />
            <input
              id="jobs-search"
              type="text"
              placeholder="Search roles, companies, skills…"
              value={localSearch}
              onChange={handleSearchChange}
              className="w-full pl-9 pr-4 py-2.5 text-sm rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 transition-all text-[var(--color-text-primary)]"
            />
            {localSearch && (
              <button
                onClick={() => { setLocalSearch(''); onFilterChange({ q: undefined }); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Save search button */}
          {onSaveSearch && (
            <button
              onClick={onSaveSearch}
              className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] hover:text-indigo-600 hover:border-indigo-400 transition-colors whitespace-nowrap"
            >
              <Bookmark className="w-4 h-4" />
              <span className="hidden sm:inline">Save</span>
            </button>
          )}

          {/* Filters button */}
          <button
            id="toggle-filters"
            onClick={() => setShowPanel(!showPanel)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-2.5 rounded-xl border text-sm font-medium transition-all whitespace-nowrap',
              showPanel || activeCount > 0
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-indigo-400'
            )}
          >
            <Filter className="w-4 h-4" />
            Filters
            {activeCount > 0 && (
              <span className="ml-0.5 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-white/20">
                {activeCount}
              </span>
            )}
          </button>

          {/* Clear all */}
          {activeCount > 0 && (
            <button
              onClick={clearAll}
              className="text-xs font-medium text-red-500 hover:text-red-700 whitespace-nowrap hidden sm:block"
            >
              Clear all
            </button>
          )}
        </div>

        {/* ── Filter panel (slide down) ──────────────────────────────────── */}
        {showPanel && (
          <div className="border-t border-[var(--color-border)] max-w-7xl mx-auto px-4 pb-4">
            <div className="pt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8">

              {/* Work Mode */}
              <FilterSection label="Work Mode" activeCount={workModes.length} defaultOpen>
                <PillGroup
                  options={WORK_MODES}
                  value={workModes}
                  onChange={(v) => handlePillChange('is_remote' as any, v)}
                  multi
                />
              </FilterSection>

              {/* Experience Level */}
              <FilterSection label="Experience Level" activeCount={seniorities.length} defaultOpen>
                <PillGroup
                  options={EXPERIENCE_LEVELS}
                  value={seniorities}
                  onChange={(v) => handlePillChange('seniority', v)}
                  multi
                />
              </FilterSection>

              {/* Job Function */}
              <FilterSection label="Job Function" activeCount={jobFunctions.length} defaultOpen>
                <PillGroup
                  options={JOB_FUNCTIONS}
                  value={jobFunctions}
                  onChange={(v) => handlePillChange('job_function', v)}
                  multi
                />
              </FilterSection>

              {/* Location */}
              <FilterSection label="Location" activeCount={(filters as any).location ? 1 : 0}>
                <input
                  type="text"
                  placeholder="City, country or Anywhere"
                  value={(filters as any).location || ''}
                  onChange={(e) => onFilterChange({ location: e.target.value || undefined })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] focus:outline-none focus:ring-1 focus:ring-indigo-500 text-[var(--color-text-primary)] transition-all"
                />
              </FilterSection>

              {/* Posted Within */}
              <FilterSection label="Posted Within" activeCount={(filters as any).posted_within ? 1 : 0}>
                <div className="flex flex-wrap gap-1.5">
                  {POSTED_WITHIN.map(({ label, value }) => {
                    const isActive = (filters as any).posted_within === value || (!value && !(filters as any).posted_within);
                    return (
                      <button
                        key={label}
                        type="button"
                        onClick={() => onFilterChange({ posted_within: value || undefined } as any)}
                        className={cn(
                          'px-3 py-1.5 rounded-full text-xs font-semibold border transition-all',
                          isActive
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'bg-transparent text-[var(--color-text-secondary)] border-[var(--color-border)] hover:border-indigo-400'
                        )}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </FilterSection>

              {/* Skills */}
              <FilterSection label="Skills" activeCount={skills.length}>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    placeholder="Add skill (max 5)"
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(skillInput); } }}
                    disabled={skills.length >= 5}
                    className="flex-1 px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] focus:outline-none focus:ring-1 focus:ring-indigo-500 text-[var(--color-text-primary)] disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={() => addSkill(skillInput)}
                    disabled={!skillInput.trim() || skills.length >= 5}
                    className="px-3 py-2 text-sm rounded-lg bg-indigo-600 text-white disabled:opacity-40 hover:bg-indigo-700 transition-colors"
                  >
                    +
                  </button>
                </div>
                {skills.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {skills.map(skill => (
                      <span key={skill} className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">
                        {skill}
                        <button onClick={() => removeSkill(skill)} className="hover:text-red-500"><X className="w-3 h-3" /></button>
                      </span>
                    ))}
                  </div>
                )}
              </FilterSection>

              {/* Source Platform */}
              <FilterSection label="Source Platform" activeCount={sources.length}>
                <div className="grid grid-cols-2 gap-1">
                  {SOURCE_PLATFORMS.map(src => {
                    const isChecked = sources.includes(src);
                    return (
                      <label key={src} className="flex items-center gap-2 py-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {
                            isChecked
                              ? handlePillChange('source_platform', sources.filter(s => s !== src))
                              : handlePillChange('source_platform', [...sources, src]);
                          }}
                          className="w-3.5 h-3.5 rounded border-neutral-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="text-xs text-[var(--color-text-secondary)] capitalize">{src.replace('_', ' ')}</span>
                      </label>
                    );
                  })}
                </div>
              </FilterSection>

              {/* Salary Range */}
              <FilterSection label="Salary Range" activeCount={(filters as any).salary_min || (filters as any).salary_max ? 1 : 0}>
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Min</label>
                    <input
                      type="number"
                      placeholder="0"
                      min={0}
                      value={(filters as any).salary_min || ''}
                      onChange={(e) => onFilterChange({ salary_min: e.target.value ? Number(e.target.value) : undefined })}
                      className="w-full mt-1 px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] focus:outline-none focus:ring-1 focus:ring-indigo-500 text-[var(--color-text-primary)]"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Max</label>
                    <input
                      type="number"
                      placeholder="Any"
                      min={0}
                      value={(filters as any).salary_max || ''}
                      onChange={(e) => onFilterChange({ salary_max: e.target.value ? Number(e.target.value) : undefined })}
                      className="w-full mt-1 px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] focus:outline-none focus:ring-1 focus:ring-indigo-500 text-[var(--color-text-primary)]"
                    />
                  </div>
                </div>
              </FilterSection>

              {/* Toggles */}
              <FilterSection label="Perks">
                <div className="space-y-2">
                  {[
                    { key: 'visa_sponsorship', label: 'Visa Sponsorship' },
                    { key: 'equity', label: 'Equity Offered' },
                  ].map(({ key, label }) => (
                    <label key={key} className="flex items-center justify-between cursor-pointer">
                      <span className="text-sm text-[var(--color-text-secondary)]">{label}</span>
                      <button
                        type="button"
                        role="switch"
                        aria-checked={(filters as any)[key] === true}
                        onClick={() => onFilterChange({ [key]: (filters as any)[key] ? undefined : true } as any)}
                        className={cn(
                          'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                          (filters as any)[key] ? 'bg-indigo-600' : 'bg-neutral-300 dark:bg-neutral-700'
                        )}
                      >
                        <span
                          className={cn(
                            'inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform',
                            (filters as any)[key] ? 'translate-x-4' : 'translate-x-0.5'
                          )}
                        />
                      </button>
                    </label>
                  ))}
                </div>
              </FilterSection>

            </div>

            {/* Mobile clear all */}
            {activeCount > 0 && (
              <button onClick={clearAll} className="mt-3 w-full py-2 rounded-lg border border-red-300 text-red-500 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-900/10 sm:hidden">
                Clear all filters
              </button>
            )}
          </div>
        )}
      </div>
    </>
  );
};
