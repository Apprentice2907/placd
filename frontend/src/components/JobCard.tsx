import React, { useState } from 'react';
import type { Job } from '../lib/api';
import { MoreHorizontal } from 'lucide-react';
import { cn } from '../lib/utils';

const AVATAR_COLORS: Record<string, string> = {
  A: '#EF4444', B: '#3B82F6', C: '#8B5CF6', D: '#8B5CF6',
  E: '#F59E0B', F: '#6366F1', G: '#10B981', H: '#EC4899',
  I: '#14B8A6', J: '#F97316', K: '#84CC16', L: '#06B6D4',
  M: '#8B5CF6', N: '#EF4444', O: '#F59E0B', P: '#6366F1',
  Q: '#10B981', R: '#EC4899', S: '#3B82F6', T: '#6366F1',
  U: '#14B8A6', V: '#F97316', W: '#84CC16', X: '#06B6D4',
  Y: '#8B5CF6', Z: '#EF4444',
};

function getAvatarColor(name: string) {
  const firstLetter = name ? name.charAt(0).toUpperCase() : '?';
  return AVATAR_COLORS[firstLetter] || '#9CA3AF';
}

function truncate(str: string, length: number) {
  if (!str) return '';
  return str.length > length ? str.substring(0, length) + '...' : str;
}

interface JobCardProps {
  job: Job;
}

export const JobCard: React.FC<JobCardProps> = ({ job }) => {
  const [imgError, setImgError] = useState(false);
  
  const [isSaved, setIsSaved] = useState(() => {
    return localStorage.getItem(`saved_job_${job.id}`) === 'true';
  });

  const companyDisplay = (job as any).company_name || job.company || '';
  const initialAvatar = companyDisplay ? companyDisplay.charAt(0).toUpperCase() : '?';

  let parsedSkills: string[] = [];
  if (typeof job.skills === 'string') {
    try {
      parsedSkills = JSON.parse(job.skills);
    } catch (e) {
      parsedSkills = job.skills.split(',').map(s => s.trim());
    }
  } else if (Array.isArray(job.skills)) {
    parsedSkills = job.skills;
  }
  const displayedSkills = parsedSkills.slice(0, 3);

  // Formatting date for "24 March 2024"
  const formattedDate = job.created_at ? new Intl.DateTimeFormat('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric'
  }).format(new Date(job.created_at)) : '';

  const handleApply = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (job.apply_url) {
      window.open(job.apply_url, '_blank');
    }
  };

  const toggleSave = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newState = !isSaved;
    setIsSaved(newState);
    if (newState) {
      localStorage.setItem(`saved_job_${job.id}`, 'true');
    } else {
      localStorage.removeItem(`saved_job_${job.id}`);
    }
  };

  return (
    <div 
      className={cn(
        "group relative flex flex-col p-[18px] rounded-[12px] bg-white border-[1.5px] border-[#E8E8E8] transition-all duration-150 hover:border-black hover:shadow-[0_4px_16px_rgba(0,0,0,0.09)]"
      )}
    >
      {/* Top Row */}
      <div className="flex justify-between items-start">
        <div className="flex gap-3 items-center">
          <div className="w-[48px] h-[48px] shrink-0 rounded-[10px] overflow-hidden flex items-center justify-center bg-white">
            {job.company_logo_url && !imgError ? (
              <img 
                src={job.company_logo_url} 
                alt={companyDisplay} 
                className="w-full h-full object-contain"
                onError={() => setImgError(true)}
              />
            ) : job.company_domain && !imgError ? (
              <img 
                src={`https://logo.clearbit.com/${job.company_domain}`} 
                alt={companyDisplay} 
                className="w-full h-full object-contain"
                onError={() => setImgError(true)}
              />
            ) : (
              <div 
                className="w-full h-full flex items-center justify-center text-white font-[700] text-[20px]"
                style={{ backgroundColor: getAvatarColor(companyDisplay) }}
              >
                {initialAvatar}
              </div>
            )}
          </div>
          <div>
            <h3 className="text-[16px] font-[700] text-[#111111] leading-[1.3]">
              {truncate(job.title, 40)}
            </h3>
            <p className="text-[11px] font-[600] text-[#888888] tracking-[0.05em] uppercase mt-0.5">
              {companyDisplay || 'Unknown Company'}
            </p>
          </div>
        </div>
        <button className="text-[#888888] hover:text-black mt-1">
          <MoreHorizontal className="w-5 h-5" />
        </button>
      </div>

      {/* Location */}
      <div className="mt-[12px] flex items-center text-[12px] text-[#888888] uppercase tracking-[0.04em]">
        <svg width="11" height="13" viewBox="0 0 11 13" fill="none" className="mr-1.5 shrink-0">
          <path d="M5.5 0C3.01 0 1 2.01 1 4.5c0 3.375 4.5 8.5 4.5 8.5s4.5-5.125 4.5-8.5C10 2.01 7.99 0 5.5 0zm0 6.083A1.583 1.583 0 1 1 5.5 2.917a1.583 1.583 0 0 1 0 3.166z" fill="#888888"/>
        </svg>
        {job.location || 'ANYWHERE'}
      </div>

      {/* Meta Row */}
      <div className="mt-[12px] flex justify-between items-center text-[13px] font-[600] text-[#333333]">
        <span className="capitalize">{(job as any).seniority ? (job as any).seniority.replace('-', ' ') : 'Mid Level'}</span>
        <span className="capitalize">{job.is_remote ? 'Remote' : (job.job_type ? job.job_type.replace('-', ' ') : 'Full Time')}</span>
        <span>{job.stipend_display || 'Not Disclosed'}</span>
      </div>

      {/* Description */}
      <div 
        className="mt-[10px] text-[13px] text-[#555555] leading-[1.6]"
        style={{
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        }}
      >
        {job.description || "In this position, you will work closely with cross-functional peers to make offers, bundles, and messaging efficient and seamless. You will also participate in the design process to create beautiful and functional user interfaces."}
      </div>

      {/* Tags & Student Badge */}
      <div className="mt-[12px] flex flex-wrap gap-[6px]">
        {job.is_student_eligible && (
          <span className="px-[12px] py-[4px] bg-[#16A34A] text-white text-[12px] rounded-[9999px]">
            Student Friendly
          </span>
        )}
        {displayedSkills.map(skill => (
          <span key={skill} className="px-[12px] py-[4px] bg-[#F3F4F6] text-[#374151] text-[12px] rounded-[9999px]">
            {skill}
          </span>
        ))}
      </div>

      <div className="flex-1" />

      {/* Footer */}
      <div className="mt-[14px] pt-[12px] border-t border-[#F0F0F0] flex items-center justify-between">
        <span className="text-[12px] text-[#AAAAAA]">
          {formattedDate || 'Recently posted'}
        </span>
        <div className="flex gap-[8px]">
          <button 
            onClick={handleApply}
            className="bg-[#000000] text-[#FFFFFF] text-[12px] font-[600] px-[16px] py-[7px] rounded-[6px] hover:bg-[#333333] transition-colors"
          >
            Apply Now →
          </button>
          <button 
            onClick={toggleSave}
            className={cn(
              "px-[9px] py-[7px] rounded-[6px] border-[1.5px] bg-white transition-colors flex items-center justify-center",
              isSaved 
                ? "border-[#000] text-[#000]" 
                : "border-[#E0E0E0] text-[#666666] hover:border-[#000] hover:text-[#000]"
            )}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill={isSaved ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};
