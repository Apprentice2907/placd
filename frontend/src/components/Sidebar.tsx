import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Briefcase, Calendar, Globe, Sun, Moon, FileText, User, KanbanSquare } from 'lucide-react';
import { cn } from '../lib/utils';

interface SidebarProps {
  isDark: boolean;
  toggleTheme: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isDark, toggleTheme }) => {
  const location = useLocation();

  const navItems = [
    { name: 'Jobs', path: '/', icon: Briefcase, activePaths: ['/', '/jobs'] },
    { name: 'Applications', path: '/applications', icon: KanbanSquare, activePaths: ['/applications'] },
    { name: 'Opportunities', path: '/opportunities', icon: Globe, activePaths: ['/opportunities'] },
    { name: 'Recruiting Calendar', path: '/calendar', icon: Calendar, activePaths: ['/calendar'] },
  ];

  return (
    <aside className="hidden lg:flex flex-col w-64 h-screen sticky top-0 bg-[var(--bg-card)] border-r border-[var(--border-color)] transition-colors z-40 shrink-0">
      <div className="p-6">
        <Link to="/" className="flex items-center gap-2 font-bold text-lg tracking-tight text-[#6366f1]">
          <Briefcase className="w-7 h-7" />
          Placd
        </Link>
      </div>

      <div className="flex-1 px-4 py-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = item.activePaths.some(p => p === '/' ? location.pathname === p : location.pathname.startsWith(p));
          
          return (
            <Link
              key={item.name}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-all duration-200",
                isActive 
                  ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400" 
                  : "text-black/80 dark:text-white/80 hover:bg-black/5 dark:hover:bg-white/5"
              )}
            >
              <item.icon className={cn("w-5 h-5", isActive ? "text-indigo-600 dark:text-indigo-400" : "text-black/40 dark:text-white/40")} />
              {item.name}
            </Link>
          );
        })}
      </div>

      <div className="px-4 py-2 mt-2">
        <h3 className="px-3 text-xs font-semibold tracking-widest uppercase text-black/30 dark:text-white/30 mb-1">Tools</h3>
        <div className="space-y-1">
          <Link
            to="/resume-builder"
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-all duration-200",
              location.pathname.startsWith('/resume-builder')
                ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400" 
                : "text-black/80 dark:text-white/80 hover:bg-black/5 dark:hover:bg-white/5"
            )}
          >
            <FileText className={cn("w-5 h-5", location.pathname.startsWith('/resume-builder') ? "text-indigo-600 dark:text-indigo-400" : "text-black/40 dark:text-white/40")} />
            Resume Builder
          </Link>
          <Link
            to="/profile"
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-all duration-200",
              location.pathname.startsWith('/profile')
                ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400" 
                : "text-black/80 dark:text-white/80 hover:bg-black/5 dark:hover:bg-white/5"
            )}
          >
            <User className={cn("w-5 h-5", location.pathname.startsWith('/profile') ? "text-indigo-600 dark:text-indigo-400" : "text-black/40 dark:text-white/40")} />
            My Profile
          </Link>
        </div>
      </div>

      <div className="p-4 border-t border-[var(--border-color)]">
        <button
          onClick={toggleTheme}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-black/80 dark:text-white/80 hover:bg-black/5 dark:hover:bg-white/5 transition-all duration-200"
        >
          {isDark ? (
            <>
              <Sun className="w-5 h-5 text-black/40 dark:text-white/40" />
              Light Mode
            </>
          ) : (
            <>
              <Moon className="w-5 h-5 text-black/40 dark:text-white/40" />
              Dark Mode
            </>
          )}
        </button>
      </div>
    </aside>
  );
};
