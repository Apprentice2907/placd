import React, { useState, useEffect } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Briefcase, ExternalLink, RefreshCw } from 'lucide-react';
import { api } from '../lib/api';
import type { CalendarEvent, CalendarResponse } from '../lib/api';
import { cn } from '../lib/utils';
import { Link } from 'react-router-dom';

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'internship', label: 'Internships' },
  { id: 'fulltime', label: 'Full-time' },
  { id: 'remote', label: 'Remote' },
];

const VIEWS = [
  { id: 'month', label: 'Month' },
  { id: 'week', label: 'Week' },
  { id: '3day', label: '3 Day' }
];

const getCategoryColorClass = (category: string) => {
  switch (category) {
    case 'faang': return 'bg-[#E6F1FB] text-[#0C447C] dark:bg-[#0C447C]/20 dark:text-[#E6F1FB]';
    case 'hft': return 'bg-[#FAEEDA] text-[#854F0B] dark:bg-[#854F0B]/20 dark:text-[#FAEEDA]';
    case 'ai_lab': return 'bg-[#EEEDFE] text-[#3C3489] dark:bg-[#3C3489]/20 dark:text-[#EEEDFE]';
    case 'startup':
    case 'india': return 'bg-[#EAF3DE] text-[#3B6D11] dark:bg-[#3B6D11]/20 dark:text-[#EAF3DE]';
    case 'fellowship':
    case 'scholarship': return 'bg-[#FAECE7] text-[#993C1D] dark:bg-[#993C1D]/20 dark:text-[#FAECE7]';
    default: return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300';
  }
};

const getDaysInMonth = (year: number, month: number) => new Date(year, month, 0).getDate();
const getFirstDayOfMonth = (year: number, month: number) => new Date(year, month - 1, 1).getDay();

export const HiringCalendarPage: React.FC = () => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedView, setSelectedView] = useState('month');
  const [data, setData] = useState<CalendarResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);

  const fetchCalendar = async () => {
    setLoading(true);
    try {
      const response = await api.calendar.get(
        currentDate.getFullYear(), 
        currentDate.getMonth() + 1, 
        selectedCategory, 
        selectedView
      );
      setData(response);
    } catch (err) {
      console.error('Failed to fetch calendar:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalendar();
  }, [currentDate.getFullYear(), currentDate.getMonth(), selectedCategory, selectedView]);

  const prevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth() + 1; // 1-12
  const daysInMonth = getDaysInMonth(currentYear, currentMonth);
  const firstDay = getFirstDayOfMonth(currentYear, currentMonth);
  
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === currentYear && today.getMonth() === currentDate.getMonth();

  // Process days for month view
  const days = [];
  // Previous month padding
  for (let i = 0; i < firstDay; i++) {
    days.push({ type: 'padding', day: null });
  }
  // Current month days
  for (let i = 1; i <= daysInMonth; i++) {
    days.push({ type: 'current', day: i });
  }

  const eventsByDay: Record<number, CalendarEvent[]> = {};
  if (data?.events) {
    data.events.forEach(ev => {
      // Ensure UTC/Local mismatch doesn't put it on wrong day (simplified)
      const dayStr = ev.date.split('-')[2];
      const dayNum = parseInt(dayStr, 10);
      if (!eventsByDay[dayNum]) eventsByDay[dayNum] = [];
      eventsByDay[dayNum].push(ev);
    });
  }

  const formatLastUpdated = (isoString?: string) => {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    const diffMs = new Date().getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins} min ago`;
    return `${Math.floor(diffMins / 60)} hours ago`;
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] p-4 sm:p-8 flex flex-col items-center">
      <div className="max-w-7xl w-full">
        
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight flex items-center gap-3 mb-2">
            <CalendarIcon className="w-8 h-8 text-indigo-500" />
            Hiring calendar
          </h1>
          <p className="text-[var(--text-secondary)] text-lg">
            All job and internship openings on their actual dates.
          </p>
        </header>

        {/* Toolbar */}
        <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-6 mb-8">
          {/* Categories */}
          <div className="flex overflow-x-auto pb-2 -mx-4 px-4 sm:mx-0 sm:px-0 sm:pb-0 w-full xl:w-auto hide-scrollbar gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={cn(
                  "px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors",
                  selectedCategory === cat.id
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "bg-white dark:bg-neutral-800 border border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]"
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-4 w-full xl:w-auto justify-between xl:justify-end">
            {/* View Toggle */}
            <div className="flex bg-white dark:bg-neutral-800 rounded-lg p-1 border border-[var(--border-color)]">
              {VIEWS.map(v => (
                <button
                  key={v.id}
                  onClick={() => setSelectedView(v.id)}
                  className={cn(
                    "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    selectedView === v.id
                      ? "bg-[var(--bg-secondary)] text-[var(--text-primary)] shadow-sm"
                      : "text-[var(--text-secondary)] hover:text-neutral-700 dark:hover:text-neutral-200"
                  )}
                >
                  {v.label}
                </button>
              ))}
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-4 bg-white dark:bg-neutral-800 border border-[var(--border-color)] rounded-lg p-1">
              <button onClick={prevMonth} className="p-1.5 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors">
                <ChevronLeft className="w-5 h-5" />
              </button>
              <div className="font-semibold w-32 text-center">
                {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
              </div>
              <button onClick={nextMonth} className="p-1.5 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors">
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Sync Status */}
        <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)] mb-4 font-medium justify-end">
          <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
          Last synced {formatLastUpdated(data?.last_updated)}
        </div>

        {/* Calendar Grid (Month View) */}
        {selectedView === 'month' && (
          <div className="bg-[var(--bg-card)] rounded-2xl border border-[var(--border-color)] overflow-hidden shadow-sm">
            {/* Weekdays */}
            <div className="grid grid-cols-7 border-b border-[var(--border-color)]">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                <div key={day} className="py-3 text-center text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                  {day}
                </div>
              ))}
            </div>
            
            {/* Days Grid */}
            <div className="grid grid-cols-7 auto-rows-fr">
              {days.map((d, idx) => {
                const isToday = isCurrentMonth && d.day === today.getDate();
                const dayEvents = d.day ? eventsByDay[d.day] || [] : [];
                const displayEvents = dayEvents.slice(0, 2);
                const hasMore = dayEvents.length > 2;

                return (
                  <div 
                    key={idx} 
                    className={cn(
                      "min-h-[120px] p-2 border-b border-r border-[var(--border-color)] last:border-r-0 relative transition-colors",
                      d.type === 'padding' ? "bg-neutral-50/50 dark:bg-neutral-900/50" : "hover:bg-[var(--bg-secondary)]/30",
                      // remove right border from last column
                      (idx + 1) % 7 === 0 && "border-r-0"
                    )}
                  >
                    {d.day && (
                      <div className="flex flex-col h-full">
                        <div className="flex justify-between items-start mb-2">
                          <span className={cn(
                            "w-7 h-7 flex items-center justify-center rounded-full text-sm font-medium",
                            isToday ? "bg-indigo-600 text-white" : "text-neutral-700 dark:text-neutral-300"
                          )}>
                            {d.day}
                          </span>
                        </div>
                        
                        <div className="flex-1 flex flex-col gap-1.5 overflow-hidden">
                          {displayEvents.map(ev => (
                            <button
                              key={ev.id}
                              onClick={() => setSelectedEvent(ev)}
                              className={cn(
                                "text-left text-xs px-2 py-1.5 rounded-md truncate font-medium transition-all hover:opacity-90 w-full flex items-center gap-1.5",
                                getCategoryColorClass(ev.category)
                              )}
                              title={`${ev.company} - ${ev.title}`}
                            >
                              <span className="truncate">{ev.company}</span>
                              {ev.verified && (
                                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 flex-shrink-0" title="Verified cycle"></span>
                              )}
                            </button>
                          ))}
                          {hasMore && (
                            <div className="text-xs text-[var(--text-secondary)] font-medium px-2 py-1">
                              +{dayEvents.length - 2} more
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {selectedView !== 'month' && (
          <div className="p-12 text-center text-neutral-500 border border-dashed border-[var(--border-color)] rounded-2xl">
            {selectedView} view coming soon!
          </div>
        )}

        {/* Legend */}
        <div className="mt-6 flex flex-wrap gap-4 items-center justify-center sm:justify-start text-sm">
          <span className="font-semibold text-[var(--text-secondary)] mr-2">Legend:</span>
          {['internship', 'fulltime', 'remote'].map(cat => {
            const label = CATEGORIES.find(c => c.id === cat)?.label;
            if (!label) return null;
            return (
              <div key={cat} className="flex items-center gap-2">
                <div className={cn("w-3 h-3 rounded-full", getCategoryColorClass(cat).split(' ')[0])}></div>
                <span className="text-[var(--text-secondary)]">{label}</span>
              </div>
            );
          })}
        </div>

      </div>

      {/* Slide-over Modal for Event Details */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50 backdrop-blur-sm" onClick={() => setSelectedEvent(null)}>
          <div 
            className="bg-[var(--bg-card)] w-full max-w-md rounded-3xl shadow-2xl overflow-hidden border border-[var(--border-color)]"
            onClick={e => e.stopPropagation()}
          >
            <div className={cn("p-6 border-b border-black/5 dark:border-white/5", getCategoryColorClass(selectedEvent.category).split(' ')[0])}>
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-2xl font-bold mb-1 text-inherit">{selectedEvent.company}</h3>
                  <p className="text-sm font-medium opacity-80 uppercase tracking-wider">{selectedEvent.type}</p>
                </div>
              </div>
            </div>
            
            <div className="p-6">
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-[var(--text-secondary)] mb-1">Event Date</p>
                  <p className="font-semibold text-lg">{new Date(selectedEvent.date).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
                </div>
                
                <div>
                  <p className="text-sm text-[var(--text-secondary)] mb-1">Description</p>
                  <p className="font-medium">{selectedEvent.title}</p>
                </div>

                <div className="flex items-center gap-3 py-3 border-y border-neutral-100 dark:border-neutral-800">
                  <div className="bg-[var(--accent-purple)]/10 p-2 rounded-lg">
                    <Briefcase className="w-5 h-5 text-[var(--accent-purple)]" />
                  </div>
                  <div>
                    <p className="font-bold text-lg">{selectedEvent.job_count}</p>
                    <p className="text-xs text-[var(--text-secondary)]">Active listings</p>
                  </div>
                </div>
              </div>

              <div className="mt-8 flex gap-3">
                <Link
                  to={`/?q=${encodeURIComponent(selectedEvent.company)}`}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-3 px-4 rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors"
                >
                  <Briefcase className="w-5 h-5" />
                  View Jobs
                </Link>
                {selectedEvent.source_url && (
                  <a
                    href={selectedEvent.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 text-[var(--text-primary)] py-3 px-4 rounded-xl font-semibold flex items-center justify-center transition-colors"
                    title="Source Link"
                  >
                    <ExternalLink className="w-5 h-5" />
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
