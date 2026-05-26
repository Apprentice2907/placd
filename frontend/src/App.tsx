import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HiringPage } from './pages/HiringPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { HiringCalendarPage } from './pages/HiringCalendarPage';
import { Briefcase, Calendar, Sun, Moon } from 'lucide-react';
import { cn } from './lib/utils';

// Query Client setup
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const Navigation: React.FC = () => {
  const location = useLocation();
  const [isDark, setIsDark] = React.useState(false);

  React.useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark(!isDark);
  
  return (
    <nav className="sticky top-0 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-md z-50 border-b border-neutral-200 dark:border-neutral-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-bold text-xl tracking-tight text-indigo-600 dark:text-indigo-400">
          <Briefcase className="w-6 h-6" />
          Placd
        </Link>
        <div className="flex items-center gap-1 sm:gap-2">
          <Link 
            to="/" 
            className={cn(
              "px-3 py-2 sm:px-4 rounded-lg font-medium text-sm transition-colors",
              location.pathname === '/' 
                ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300" 
                : "text-neutral-600 hover:bg-neutral-50 dark:text-neutral-400 dark:hover:bg-neutral-800"
            )}
          >
            Jobs
          </Link>
          <Link 
            to="/calendar" 
            className={cn(
              "px-3 py-2 sm:px-4 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 hidden sm:flex",
              location.pathname === '/calendar' 
                ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300" 
                : "text-neutral-600 hover:bg-neutral-50 dark:text-neutral-400 dark:hover:bg-neutral-800"
            )}
          >
            <Calendar className="w-4 h-4" />
            Recruiting Calendar
          </Link>
          <div className="w-px h-6 bg-neutral-200 dark:bg-neutral-800 mx-1 sm:mx-2 hidden sm:block"></div>
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-neutral-500 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800 transition-colors focus:outline-none"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </nav>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col bg-neutral-50 dark:bg-[#0a0a0a]">
          <Navigation />
          <div className="flex-1">
            <Routes>
              <Route path="/" element={<HiringPage />} />
              <Route path="/jobs/:id" element={<JobDetailPage />} />
              <Route path="/calendar" element={<HiringCalendarPage />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
