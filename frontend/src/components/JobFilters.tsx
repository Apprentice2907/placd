import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { SearchFilters } from '../lib/api';
import { api } from '../lib/api';
import { cn } from '../lib/utils';
import { ChevronRight } from 'lucide-react';

const FilterSection = ({
  label,
  children,
  defaultOpen = true,
}: {
  label: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between mb-[12px] text-[14px] font-[600] text-[#111111]"
      >
        {label}
        <ChevronRight className={cn("w-4 h-4 transition-transform duration-200 text-[#111111]", open ? "rotate-90" : "")} />
      </button>
      <div className={cn("grid transition-[grid-template-rows] duration-200 ease-in-out", open ? "grid-rows-[1fr]" : "grid-rows-[0fr]")}>
        <div className="overflow-hidden">
          {children}
        </div>
      </div>
    </div>
  );
};

const CheckboxItem = ({
  label,
  count,
  checked,
  onChange,
}: {
  label: string;
  count: number | undefined;
  checked: boolean;
  onChange: () => void;
}) => {
  return (
    <label className="flex items-center justify-between h-[32px] w-full cursor-pointer hover:bg-[#F9FAFB] rounded-[6px] px-1 -mx-1 group">
      <input type="checkbox" className="hidden" checked={checked} onChange={onChange} />
      <div className="flex items-center">
        <div className={cn(
          "w-[16px] h-[16px] flex items-center justify-center transition-colors",
          checked ? "bg-[#111111] border-[#111111] rounded-[3px]" : "bg-white border-[1.5px] border-[#D1D5DB] rounded-[3px]"
        )}>
          {checked && (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          )}
        </div>
        <span className="text-[13px] text-[#333333] ml-[8px]">{label}</span>
      </div>
      <span className={cn(
        "text-[11px] font-[600] px-[7px] py-[1px] rounded-full",
        count === undefined ? "bg-[#F3F4F6] text-[#D1D5DB]" : checked ? "bg-[#DCFCE7] text-[#16A34A]" : "bg-[#F3F4F6] text-[#666666]"
      )}>
        {count ?? '—'}
      </span>
    </label>
  );
};

interface JobFiltersProps {
  filters: Omit<SearchFilters, 'page'>;
  onFilterChange: (newFilters: Partial<Omit<SearchFilters, 'page'>>, immediate?: boolean) => void;
  stats?: any;
}

export const JobFilters: React.FC<JobFiltersProps> = ({ filters, onFilterChange }) => {
  const [studentMode, setStudentMode] = useState<boolean>(() => {
    return localStorage.getItem('placd_student_mode') === 'true';
  });

  const [localMin, setLocalMin] = useState(filters.salary_min || '');
  const [localMax, setLocalMax] = useState(filters.salary_max || '');

  // Fetch live facet counts — cached for 5 minutes
  const { data: facets } = useQuery({
    queryKey: ['job-facets'],
    queryFn: () => api.jobs.facets(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });

  const et = facets?.employment_type ?? {};
  const sn = facets?.seniority ?? {};

  const parsePills = (val?: string): string[] => val ? val.split(',').filter(Boolean) : [];
  
  const jobTypes = parsePills(filters.job_type as string);
  const isRemote = filters.is_remote === true;
  const seniorities = parsePills(filters.seniority as string);

  const handlePillToggle = (key: string, value: string, current: string[]) => {
    const isChecked = current.includes(value);
    const updated = isChecked ? current.filter(v => v !== value) : [...current, value];
    onFilterChange({ [key]: updated.length ? updated.join(',') : undefined } as any, false);
  };

  const handleApply = () => {
    onFilterChange({ ...filters }, true);
  };

  const handleReset = () => {
    setStudentMode(false);
    setLocalMin('');
    setLocalMax('');
    onFilterChange({
      job_type: undefined,
      is_remote: undefined,
      seniority: undefined,
      salary_min: undefined,
      salary_max: undefined,
      student_mode: undefined
    } as any, true);
  };

  useEffect(() => {
    localStorage.setItem('placd_student_mode', String(studentMode));
    if (studentMode !== filters.student_mode) {
      onFilterChange({ student_mode: studentMode || undefined } as any, false);
    }
  }, [studentMode, onFilterChange, filters]);

  const handleSalaryBlur = () => {
    onFilterChange({ 
      salary_min: localMin ? Number(localMin) : undefined,
      salary_max: localMax ? Number(localMax) : undefined
    }, false);
  };

  return (
    <aside className="w-[260px] shrink-0 h-[calc(100vh-108px)] overflow-y-auto flex flex-col bg-white hidden lg:flex no-scrollbar">
      <div className="flex-1 flex flex-col px-6 py-6">
        
        {/* Type of Employment */}
        <FilterSection label="Type of Employment">
          <div className="flex flex-col">
            <CheckboxItem 
              label="Full Time Jobs" 
              count={et.full_time} 
              checked={jobTypes.includes('full-time')} 
              onChange={() => handlePillToggle('job_type', 'full-time', jobTypes)} 
            />
            <CheckboxItem 
              label="Part Time Jobs" 
              count={et.part_time} 
              checked={jobTypes.includes('part-time')} 
              onChange={() => handlePillToggle('job_type', 'part-time', jobTypes)} 
            />
            <CheckboxItem 
              label="Remote Jobs" 
              count={et.remote} 
              checked={isRemote} 
              onChange={() => onFilterChange({ is_remote: isRemote ? undefined : true } as any)} 
            />
            <CheckboxItem 
              label="Internships" 
              count={et.internship} 
              checked={jobTypes.includes('training')} 
              onChange={() => handlePillToggle('job_type', 'training', jobTypes)} 
            />
          </div>
        </FilterSection>

        {/* Seniority Level */}
        <FilterSection label="Seniority Level">
          <div className="flex flex-col">
            <CheckboxItem 
              label="Student Level" 
              count={sn.student} 
              checked={seniorities.includes('student')} 
              onChange={() => handlePillToggle('seniority', 'student', seniorities)} 
            />
            <CheckboxItem 
              label="Entry Level" 
              count={sn.entry} 
              checked={seniorities.includes('entry')} 
              onChange={() => handlePillToggle('seniority', 'entry', seniorities)} 
            />
            <CheckboxItem 
              label="Mid Level" 
              count={sn.mid} 
              checked={seniorities.includes('mid')} 
              onChange={() => handlePillToggle('seniority', 'mid', seniorities)} 
            />
            <CheckboxItem 
              label="Senior Level" 
              count={sn.senior} 
              checked={seniorities.includes('senior')} 
              onChange={() => handlePillToggle('seniority', 'senior', seniorities)} 
            />
            <CheckboxItem 
              label="Directors" 
              count={sn.director} 
              checked={seniorities.includes('director')} 
              onChange={() => handlePillToggle('seniority', 'director', seniorities)} 
            />
            <CheckboxItem 
              label="VP or Above" 
              count={sn.vp} 
              checked={seniorities.includes('vp')} 
              onChange={() => handlePillToggle('seniority', 'vp', seniorities)} 
            />
          </div>
        </FilterSection>

        {/* Student Mode toggle */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div className="text-[13px] font-[600] text-[#111111]">
              Student Mode
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={studentMode}
              onClick={() => setStudentMode(!studentMode)}
              className={cn(
                'relative inline-flex h-[22px] w-[40px] shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out',
                studentMode ? 'bg-[#16A34A]' : 'bg-[#E5E7EB]'
              )}
            >
              <span
                className={cn(
                  'pointer-events-none inline-block h-[18px] w-[18px] transform rounded-full bg-white transition duration-200 ease-in-out',
                  studentMode ? 'translate-x-[18px]' : 'translate-x-0'
                )}
              />
            </button>
          </div>
        </div>

        {/* Salary Range */}
        <FilterSection label="Salary Range">
          <div className="mt-2">
            <div className="relative w-full h-[3px] bg-[#E5E7EB] rounded-full mb-6">
              {/* Fake slider thumb */}
              <div className="absolute left-[20%] right-[30%] h-full bg-[#111111]"></div>
              <div className="absolute left-[20%] top-1/2 -translate-y-1/2 w-[16px] h-[16px] bg-[#111111] rounded-full border-[2px] border-white shadow-[0_1px_4px_rgba(0,0,0,0.2)] cursor-grab"></div>
              <div className="absolute right-[30%] top-1/2 -translate-y-1/2 w-[16px] h-[16px] bg-[#111111] rounded-full border-[2px] border-white shadow-[0_1px_4px_rgba(0,0,0,0.2)] cursor-grab"></div>
            </div>

            <div className="flex justify-between items-center gap-2">
              <div className="flex-1">
                <input
                  type="number"
                  placeholder="MIN"
                  value={localMin}
                  onChange={(e) => setLocalMin(e.target.value)}
                  onBlur={handleSalaryBlur}
                  className="w-[90px] px-[10px] py-[6px] text-[13px] rounded-[6px] border-[1.5px] border-[#E5E7EB] bg-white outline-none focus:border-[#111111]"
                />
              </div>
              <div className="w-2 h-[2px] bg-neutral-300"></div>
              <div className="flex-1 text-right">
                <input
                  type="number"
                  placeholder="MAX"
                  value={localMax}
                  onChange={(e) => setLocalMax(e.target.value)}
                  onBlur={handleSalaryBlur}
                  className="w-[90px] px-[10px] py-[6px] text-[13px] rounded-[6px] border-[1.5px] border-[#E5E7EB] bg-white outline-none focus:border-[#111111]"
                />
              </div>
            </div>
          </div>
        </FilterSection>

        {/* Bottom Buttons */}
        <div className="pt-2 flex gap-[8px] mb-[24px]">
          <button 
            onClick={handleApply}
            className="flex-1 bg-[#111111] text-white text-[13px] font-[600] p-[10px] rounded-[7px]"
          >
            APPLY
          </button>
          <button 
            onClick={handleReset}
            className="flex-1 bg-white text-[#111111] border-[1.5px] border-[#D1D5DB] text-[13px] font-[600] p-[10px] rounded-[7px]"
          >
            RESET
          </button>
        </div>

      </div>

    </aside>
  );
};
