import React, { useState, useEffect, useRef } from 'react';
import { Bookmark, X, Bell, BellOff, Trash2, Plus } from 'lucide-react';

interface SavedSearch {
  id: string;
  name: string;
  filters: Record<string, string | number | boolean>;
  notification: 'browser' | 'email' | 'none';
  createdAt: string;
  matchCount?: number;
  newCount?: number;
}

const STORAGE_KEY = 'placd_saved_searches';
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// ─────────────────────────────────────────────────────────────────────────────
// Toast notification
// ─────────────────────────────────────────────────────────────────────────────
interface ToastProps { message: string; onDismiss: () => void; }
const Toast: React.FC<ToastProps> = ({ message, onDismiss }) => (
  <div
    className="toast-enter fixed top-4 right-4 z-[100] flex items-center gap-3 px-4 py-3 bg-indigo-600 text-white text-sm font-medium rounded-xl shadow-2xl max-w-sm"
    onClick={onDismiss}
  >
    <Bell className="w-4 h-4 shrink-0" />
    <span>{message}</span>
    <button onClick={onDismiss} className="ml-auto text-white/70 hover:text-white"><X className="w-4 h-4" /></button>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// Save Search Modal
// ─────────────────────────────────────────────────────────────────────────────
const SaveModal: React.FC<{
  currentFilters: Record<string, unknown>;
  onSave: (name: string, notif: SavedSearch['notification']) => void;
  onClose: () => void;
}> = ({ currentFilters, onSave, onClose }) => {
  const [name, setName] = useState('');
  const [notif, setNotif] = useState<SavedSearch['notification']>('browser');

  const filterSummary = Object.entries(currentFilters)
    .filter(([, v]) => v !== undefined && v !== '' && v !== null)
    .map(([k, v]) => `${k}: ${v}`)
    .slice(0, 4)
    .join(', ');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-[var(--color-bg-primary)] rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bookmark className="w-5 h-5 text-indigo-500" />
          <h2 className="text-lg font-bold text-[var(--color-text-primary)]">Save This Search</h2>
        </div>
        {filterSummary && (
          <p className="text-xs text-[var(--color-text-muted)] mb-4 bg-neutral-100 dark:bg-neutral-800 rounded-lg px-3 py-2 truncate">
            {filterSummary}
          </p>
        )}
        <input
          autoFocus
          type="text"
          placeholder="Search name (e.g. Remote ML roles)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && name.trim()) { onSave(name.trim(), notif); onClose(); } }}
          className="w-full px-3 py-2.5 text-sm rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500/40 mb-4"
        />
        <div className="mb-4">
          <p className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Notifications</p>
          <div className="flex gap-2">
            {(['browser', 'email', 'none'] as const).map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setNotif(n)}
                className={`flex-1 py-2 rounded-lg text-xs font-semibold border transition-colors ${
                  notif === n
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-indigo-400'
                }`}
              >
                {n.charAt(0).toUpperCase() + n.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)]">
            Cancel
          </button>
          <button
            disabled={!name.trim()}
            onClick={() => { if (name.trim()) { onSave(name.trim(), notif); onClose(); } }}
            className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold disabled:opacity-50 transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────
interface SavedSearchesProps {
  currentFilters: Record<string, unknown>;
  onApplySearch?: (filters: Record<string, unknown>) => void;
}

export const SavedSearches: React.FC<SavedSearchesProps> = ({ currentFilters, onApplySearch }) => {
  const [searches, setSearches] = useState<SavedSearch[]>(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; }
  });
  const [showModal, setShowModal] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  // Persist
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(searches));
  }, [searches]);

  // SSE connection for each saved search (simplified: one per page load)
  useEffect(() => {
    if (searches.length === 0) return;
    const search = searches[0]; // connect for first saved search

    try {
      const es = new EventSource(`${API_BASE}/alerts/stream?search_id=${search.id}`);
      esRef.current = es;

      es.addEventListener('new_jobs', (e) => {
        const data = JSON.parse((e as MessageEvent).data);
        const count = data?.count || 1;
        setToast(`${count} new job${count > 1 ? 's' : ''} matching "${search.name}"`);
        setSearches(prev => prev.map(s => s.id === search.id ? { ...s, newCount: (s.newCount || 0) + count } : s));
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('Placd — New Jobs', { body: `${count} new match for "${search.name}"`, icon: '/favicon.svg' });
        }
      });

      es.onerror = () => es.close();
    } catch { /* no SSE support */ }

    return () => { esRef.current?.close(); };
  }, [searches.length, API_BASE]);

  const handleSave = (name: string, notif: SavedSearch['notification']) => {
    const newSearch: SavedSearch = {
      id: `ss-${Date.now()}`,
      name,
      filters: currentFilters as Record<string, string | number | boolean>,
      notification: notif,
      createdAt: new Date().toISOString(),
    };
    setSearches(prev => [newSearch, ...prev]);

    // Request browser notification permission
    if (notif === 'browser' && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  };

  const handleDelete = (id: string) => {
    setSearches(prev => prev.filter(s => s.id !== id));
  };

  return (
    <>
      {/* Save button */}
      <button
        id="save-search-btn"
        onClick={() => setShowModal(true)}
        className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-text-muted)] hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
      >
        <Plus className="w-3.5 h-3.5" />
        Save search
      </button>

      {/* Saved searches list */}
      {searches.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          {searches.map(s => (
            <div
              key={s.id}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 group hover:bg-indigo-50 dark:hover:bg-indigo-900/10 cursor-pointer transition-colors"
              onClick={() => onApplySearch?.(s.filters)}
            >
              <Bookmark className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
              <span className="text-xs text-[var(--color-text-primary)] flex-1 truncate">{s.name}</span>
              {s.newCount ? (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-600 text-white">{s.newCount}</span>
              ) : null}
              {s.notification === 'browser' ? (
                <Bell className="w-3 h-3 text-[var(--color-text-muted)]" />
              ) : s.notification === 'none' ? (
                <BellOff className="w-3 h-3 text-[var(--color-text-muted)]" />
              ) : null}
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }}
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 transition-all"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <SaveModal
          currentFilters={currentFilters}
          onSave={handleSave}
          onClose={() => setShowModal(false)}
        />
      )}

      {/* Toast */}
      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
};
