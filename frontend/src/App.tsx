import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HiringPage } from './pages/HiringPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { HiringCalendarPage } from './pages/HiringCalendarPage';
import { OpportunitiesPage } from './pages/OpportunitiesPage';
import { ProfilePage } from './pages/ProfilePage';
import { ResumeBuilderPage } from './pages/ResumeBuilderPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { Sidebar } from './components/Sidebar';
import { MobileNav } from './components/MobileNav';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  const [isDark, setIsDark] = React.useState(() => {
    const saved = localStorage.getItem('placd-theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  React.useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('placd-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  const toggleTheme = () => setIsDark(!isDark);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {/* Main layout: sidebar (lg+) | content */}
        <div className="min-h-screen flex flex-col lg:flex-row bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] transition-colors">
          {/* Desktop sidebar */}
          <Sidebar isDark={isDark} toggleTheme={toggleTheme} />

          {/* Main content area */}
          <div className="flex-1 flex flex-col min-w-0 lg:h-screen overflow-hidden">
            <main className="flex-1 overflow-y-auto pb-16 lg:pb-0">
              <Routes>
                <Route path="/" element={<HiringPage />} />
                <Route path="/jobs/:id" element={<JobDetailPage />} />
                <Route path="/opportunities" element={<OpportunitiesPage />} />
                <Route path="/calendar" element={<HiringCalendarPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/resume-builder" element={<ResumeBuilderPage />} />
                <Route path="/applications" element={<ApplicationsPage />} />
              </Routes>
            </main>
          </div>
        </div>

        {/* Mobile bottom nav (hidden on lg+) */}
        <MobileNav />
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
