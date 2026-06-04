import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Search, Briefcase, Bookmark, User, KanbanSquare } from 'lucide-react';
import { cn } from '../lib/utils';

interface MobileNavProps {
  newJobCount?: number;
}

export const MobileNav: React.FC<MobileNavProps> = ({ newJobCount }) => {
  const location = useLocation();

  const items = [
    { name: 'Search', path: '/', icon: Search, activePaths: [] as string[] },
    { name: 'Jobs', path: '/', icon: Briefcase, activePaths: ['/', '/jobs'], badge: newJobCount },
    { name: 'Tracker', path: '/applications', icon: KanbanSquare, activePaths: ['/applications'] },
    { name: 'Saved', path: '/?status=shortlisted', icon: Bookmark, activePaths: [] as string[] },
    { name: 'Profile', path: '/profile', icon: User, activePaths: ['/profile'] },
  ];

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-[var(--color-bg-primary)] border-t border-[var(--color-border)]"
      aria-label="Mobile navigation"
    >
      <div className="flex items-center justify-around px-2 py-2">
        {items.map((item) => {
          const isActive = item.activePaths.some(p =>
            p === '/'
              ? location.pathname === '/' || location.pathname === '/jobs'
              : location.pathname.startsWith(p)
          );
          return (
            <Link
              key={item.name}
              to={item.path}
              className={cn(
                'relative flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg transition-colors',
                isActive
                  ? 'text-indigo-600 dark:text-indigo-400'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              )}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="relative">
                <item.icon className="w-5 h-5" />
                {item.badge && item.badge > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-0.5 text-[10px] font-bold leading-4 text-center rounded-full bg-red-500 text-white">
                    {item.badge > 99 ? '99+' : item.badge}
                  </span>
                )}
              </div>
              <span className="text-[10px] font-medium">{item.name}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
};
