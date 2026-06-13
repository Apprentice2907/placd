import React from 'react';
import { Bell } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../lib/utils';

export const Navbar: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { name: 'Finds Jobs', path: '/' },
    { name: 'Company Reviews', path: '/reviews' },
    { name: 'Find Salaries', path: '/salaries' },
    { name: 'Resume Builder', path: '/resume-builder' },
    { name: 'Employers / Post Job', path: '/post-job' },
  ];

  return (
    <nav className="w-full h-[56px] bg-[#0A0A0A] text-white flex items-center justify-between px-6 shrink-0 z-50">
      {/* Logo Area */}
      <div className="flex items-center">
        <Link to="/" className="flex items-center hover:opacity-90 transition-opacity">
          <div className="flex items-center text-[18px] font-bold leading-[1.1] text-white">
            <span className="text-right">PLA<br/>CD</span>
            <div className="w-px h-8 bg-white mx-1.5"/>
          </div>
        </Link>
      </div>

      {/* Center Navigation */}
      <div className="hidden md:flex items-center h-full gap-8">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
          return (
            <Link
              key={item.name}
              to={item.path}
              className={cn(
                "h-full flex items-center border-b-[2px] transition-colors text-[14px] font-medium",
                isActive 
                  ? "border-white text-white" 
                  : "border-transparent text-neutral-400 hover:text-neutral-200"
              )}
            >
              {item.name}
            </Link>
          );
        })}
      </div>

      {/* Right Area (User Profile & Notifications) */}
      <div className="flex items-center gap-6">
        <button className="text-neutral-400 hover:text-white transition-colors">
          <Bell className="w-5 h-5" />
        </button>
      </div>
    </nav>
  );
};
