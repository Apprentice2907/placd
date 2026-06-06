import React from 'react';
import { Search, MapPin, Briefcase, DollarSign, ChevronDown, X } from 'lucide-react';

interface SearchBarProps {
  searchQuery: string;
  setSearchQuery: (val: string) => void;
  tags: string[];
  onRemoveTag: (tag: string) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ 
  searchQuery, 
  setSearchQuery,
  tags,
  onRemoveTag 
}) => {
  return (
    <div className="w-[calc(100%-48px)] mx-[24px] mt-[12px] mb-[12px] h-[52px] bg-white border border-[#E5E7EB] rounded-[12px] flex items-center pl-[24px] shrink-0 z-40 shadow-[0_1px_4px_rgba(0,0,0,0.06)]">
      
      {/* Left: Search & Tags */}
      <div className="flex items-center flex-1 min-w-0">
        <Search className="w-[16px] h-[16px] text-[#999999] shrink-0 mr-3" />
        <div className="flex items-center gap-2 flex-1 overflow-x-auto no-scrollbar">
          {tags.map((tag) => (
            <span 
              key={tag}
              className="flex items-center gap-1.5 px-[10px] py-[4px] bg-[#F3F4F6] rounded-full text-[13px] font-medium text-[#333333] whitespace-nowrap"
            >
              {tag}
              <button 
                onClick={() => onRemoveTag(tag)}
                className="hover:text-black focus:outline-none"
              >
                <X className="w-[12px] h-[12px] text-[#999999]" />
              </button>
            </span>
          ))}
          <input 
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={tags.length === 0 ? "Search..." : ""}
            className="flex-1 bg-transparent border-none outline-none text-[14px] placeholder-[#999999] min-w-[60px]"
          />
        </div>
      </div>

      <div className="w-[1px] h-[24px] bg-[#E0E0E0] mx-[16px]"></div>

      {/* Middle: Dropdowns */}
      <div className="hidden lg:flex items-center h-full">
        <button className="h-full flex items-center gap-[8px] text-[14px] font-medium text-[#333333] hover:text-[#000000] px-[16px]">
          <MapPin className="w-[16px] h-[16px] text-[#999999]" />
          All Countries
          <ChevronDown className="w-[16px] h-[16px] text-[#999999]" />
        </button>
        <div className="w-[1px] h-[24px] bg-[#E5E7EB]"></div>
        <button className="h-full flex items-center gap-[8px] text-[14px] font-medium text-[#333333] hover:text-[#000000] px-[16px]">
          <Briefcase className="w-[16px] h-[16px] text-[#999999]" />
          Job Type
          <ChevronDown className="w-[16px] h-[16px] text-[#999999]" />
        </button>
        <div className="w-[1px] h-[24px] bg-[#E5E7EB]"></div>
        <button className="h-full flex items-center gap-[8px] text-[14px] font-medium text-[#333333] hover:text-[#000000] px-[16px]">
          <DollarSign className="w-[16px] h-[16px] text-[#999999]" />
          Salary Range
          <ChevronDown className="w-[16px] h-[16px] text-[#999999]" />
        </button>
      </div>

      {/* Right: Button */}
      <div className="ml-auto h-full flex">
        <button className="h-full bg-[#111111] text-white text-[13px] font-[700] tracking-[0.03em] px-[28px] rounded-r-[11px] hover:bg-[#222222] transition-colors">
          START SEARCHING
        </button>
      </div>

    </div>
  );
};
