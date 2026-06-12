import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
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

export const JobFilters: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [studentMode, setStudentMode] = useState<boolean>(() => {
    return localStorage.getItem('placd_student_mode') === 'true';
  });

  const [localMin, setLocalMin] = useState(searchParams.get('salary_min') || '');
  const [localMax, setLocalMax] = useState(searchParams.get('salary_max') || '');

  const { data: facets } = useQuery({
    queryKey: ['job-facets'],
    queryFn: () => api.jobs.facets(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const et = facets?.employment_type ?? {};

  // Read checkbox state directly from URL
  const isChecked = (paramKey: string, value: string) =>
    searchParams.getAll(paramKey).includes(value);

  // Toggle filter — single update, no local state
  const toggleFilter = (paramKey: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    const existing = next.getAll(paramKey);
    next.delete(paramKey);
    
    if (existing.includes(value)) {
      existing.filter(v => v !== value).forEach(v => next.append(paramKey, v));
    } else {
      [...existing, value].forEach(v => next.append(paramKey, v));
    }
    setSearchParams(next, { replace: false });
  };

  const handleRemoteToggle = () => {
    const next = new URLSearchParams(searchParams);
    if (next.get('is_remote') === 'true') {
      next.delete('is_remote');
    } else {
      next.set('is_remote', 'true');
    }
    setSearchParams(next, { replace: false });
  };

  const handleReset = () => {
    setStudentMode(false);
    setLocalMin('');
    setLocalMax('');
    const next = new URLSearchParams(searchParams);
    next.delete('job_type');
    next.delete('is_remote');
    next.delete('salary_min');
    next.delete('salary_max');
    next.delete('student_mode');
    setSearchParams(next, { replace: false });
  };

  useEffect(() => {
    localStorage.setItem('placd_student_mode', String(studentMode));
    const next = new URLSearchParams(searchParams);
    if (studentMode) {
      next.set('student_mode', 'true');
    } else {
      next.delete('student_mode');
    }
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: false });
    }
  }, [studentMode]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSalaryBlur = () => {
    const next = new URLSearchParams(searchParams);
    if (localMin) next.set('salary_min', localMin);
    else next.delete('salary_min');
    
    if (localMax) next.set('salary_max', localMax);
    else next.delete('salary_max');
    
    setSearchParams(next, { replace: false });
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
              checked={isChecked('job_type', 'fulltime')} 
              onChange={() => toggleFilter('job_type', 'fulltime')} 
            />
            <CheckboxItem 
              label="Part Time Jobs" 
              count={et.part_time} 
              checked={isChecked('job_type', 'part-time')} 
              onChange={() => toggleFilter('job_type', 'part-time')} 
            />
            <CheckboxItem 
              label="Remote Jobs" 
              count={et.remote} 
              checked={searchParams.get('is_remote') === 'true'} 
              onChange={handleRemoteToggle} 
            />
            <CheckboxItem 
              label="Internships" 
              count={et.internship} 
              checked={isChecked('job_type', 'internship')} 
              onChange={() => toggleFilter('job_type', 'internship')} 
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
            onClick={handleReset}
            className="w-full bg-white text-[#111111] border-[1.5px] border-[#D1D5DB] text-[13px] font-[600] p-[10px] rounded-[7px] hover:bg-gray-50"
          >
            RESET ALL FILTERS
          </button>
        </div>

      </div>

    </aside>
  );
};
