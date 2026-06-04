import React, { useState, useEffect, useCallback } from 'react';
import {
  DndContext,
  type DragEndEvent,
  DragOverlay,
  type DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Plus, Download, Briefcase, ChevronDown, ChevronUp, Trash2, ExternalLink, BarChart2,
} from 'lucide-react';
import { cn } from '../lib/utils';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type ApplicationStatus =
  | 'saved' | 'applied' | 'phone' | 'technical' | 'final' | 'offer' | 'rejected';

interface Application {
  id: string;
  jobId?: string;
  company: string;
  title: string;
  appliedDate: string;
  status: ApplicationStatus;
  notes: string;
  salary?: string;
  applyUrl?: string;
}

const COLUMNS: { id: ApplicationStatus; label: string; color: string }[] = [
  { id: 'saved',     label: 'Saved',         color: 'bg-neutral-500'  },
  { id: 'applied',   label: 'Applied',        color: 'bg-blue-500'     },
  { id: 'phone',     label: 'Phone Screen',   color: 'bg-indigo-500'   },
  { id: 'technical', label: 'Technical',      color: 'bg-violet-500'   },
  { id: 'final',     label: 'Final Round',    color: 'bg-amber-500'    },
  { id: 'offer',     label: 'Offer 🎉',       color: 'bg-emerald-500'  },
  { id: 'rejected',  label: 'Rejected',       color: 'bg-red-500'      },
];

const STORAGE_KEY = 'placd_applications';

// ─────────────────────────────────────────────────────────────────────────────
// Card component (sortable)
// ─────────────────────────────────────────────────────────────────────────────
const ApplicationCard: React.FC<{
  app: Application;
  onDelete: (id: string) => void;
  onNoteChange: (id: string, note: string) => void;
}> = ({ app, onDelete, onNoteChange }) => {
  const [expanded, setExpanded] = useState(false);
  const {
    attributes, listeners, setNodeRef, transform, transition, isDragging,
  } = useSortable({ id: app.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const initials = app.company ? app.company.charAt(0).toUpperCase() : '?';
  const colors = ['bg-indigo-500','bg-blue-500','bg-emerald-500','bg-violet-500','bg-amber-500'];
  const color = colors[app.company.length % colors.length];

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-white dark:bg-neutral-900 border border-[var(--color-border)] rounded-xl p-3 shadow-sm"
    >
      <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing">
        <div className="flex items-start gap-2.5">
          <div className={cn('w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0', color)}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{app.title}</p>
            <p className="text-xs text-[var(--color-text-secondary)] truncate">{app.company}</p>
          </div>
          <button
            onPointerDown={(e) => e.stopPropagation()}
            onClick={() => setExpanded(!expanded)}
            className="text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 p-0.5"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <span className="text-[10px] text-[var(--color-text-muted)]">
            {app.appliedDate ? new Date(app.appliedDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}
          </span>
          {app.salary && (
            <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">{app.salary}</span>
          )}
        </div>
      </div>

      {expanded && (
        <div
          onPointerDown={(e) => e.stopPropagation()}
          className="mt-2 pt-2 border-t border-[var(--color-border)]"
        >
          <textarea
            value={app.notes}
            onChange={(e) => onNoteChange(app.id, e.target.value)}
            placeholder="Add notes…"
            rows={3}
            className="w-full text-xs px-2 py-1.5 rounded-lg border border-[var(--color-border)] bg-neutral-50 dark:bg-neutral-800 text-[var(--color-text-primary)] resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          <div className="flex items-center justify-between mt-1.5">
            {app.applyUrl && (
              <a
                href={app.applyUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-[10px] text-indigo-600 dark:text-indigo-400 hover:underline"
              >
                View posting <ExternalLink className="w-2.5 h-2.5" />
              </a>
            )}
            <button
              onClick={() => onDelete(app.id)}
              className="ml-auto flex items-center gap-1 text-[10px] text-red-400 hover:text-red-600 transition-colors"
            >
              <Trash2 className="w-2.5 h-2.5" /> Remove
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Column component
// ─────────────────────────────────────────────────────────────────────────────
const KanbanColumn: React.FC<{
  column: typeof COLUMNS[0];
  apps: Application[];
  onDelete: (id: string) => void;
  onNoteChange: (id: string, note: string) => void;
  onAddApp: (status: ApplicationStatus) => void;
}> = ({ column, apps, onDelete, onNoteChange, onAddApp }) => (
  <div className="flex flex-col gap-2 min-w-[240px] w-[240px]">
    <div className="flex items-center gap-2 px-1">
      <div className={cn('w-2 h-2 rounded-full', column.color)} />
      <span className="text-xs font-semibold text-[var(--color-text-primary)]">{column.label}</span>
      <span className="ml-auto text-[10px] font-bold text-[var(--color-text-muted)] bg-neutral-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded-full">
        {apps.length}
      </span>
    </div>

    <div className="flex flex-col gap-2 bg-neutral-50 dark:bg-neutral-900/40 rounded-xl p-2 min-h-[100px]">
      <SortableContext items={apps.map(a => a.id)} strategy={verticalListSortingStrategy}>
        {apps.map(app => (
          <ApplicationCard key={app.id} app={app} onDelete={onDelete} onNoteChange={onNoteChange} />
        ))}
      </SortableContext>

      <button
        onClick={() => onAddApp(column.id)}
        className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-indigo-600 dark:hover:text-indigo-400 py-1 px-1 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/10 transition-colors"
      >
        <Plus className="w-3.5 h-3.5" /> Add
      </button>
    </div>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// Add Application Modal
// ─────────────────────────────────────────────────────────────────────────────
const AddModal: React.FC<{
  defaultStatus: ApplicationStatus;
  onSave: (app: Omit<Application, 'id'>) => void;
  onClose: () => void;
}> = ({ defaultStatus, onSave, onClose }) => {
  const [form, setForm] = useState<Omit<Application, 'id'>>({
    company: '',
    title: '',
    appliedDate: new Date().toISOString().slice(0, 10),
    status: defaultStatus,
    notes: '',
    salary: '',
    applyUrl: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.company || !form.title) return;
    onSave(form);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-[var(--color-bg-primary)] rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold text-[var(--color-text-primary)] mb-4">Add Application</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          {[
            { label: 'Company *', key: 'company', placeholder: 'Stripe' },
            { label: 'Role Title *', key: 'title', placeholder: 'Senior Engineer' },
            { label: 'Apply URL', key: 'applyUrl', placeholder: 'https://…' },
            { label: 'Salary / Stipend', key: 'salary', placeholder: '$120k' },
          ].map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1">{label}</label>
              <input
                type="text"
                placeholder={placeholder}
                value={(form as any)[key]}
                onChange={(e) => setForm(f => ({ ...f, [key]: e.target.value }))}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          ))}
          <div>
            <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-1">Date Applied</label>
            <input
              type="date"
              value={form.appliedDate}
              onChange={(e) => setForm(f => ({ ...f, appliedDate: e.target.value }))}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="flex gap-2 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] hover:bg-neutral-100 dark:hover:bg-neutral-800">
              Cancel
            </button>
            <button type="submit" className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors">
              Add
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────────────────────
export const ApplicationsPage: React.FC = () => {
  const [applications, setApplications] = useState<Application[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });
  const [activeId, setActiveId] = useState<string | null>(null);
  const [addModal, setAddModal] = useState<{ open: boolean; status: ApplicationStatus }>({ open: false, status: 'applied' });

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(applications));
  }, [applications]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    if (!over) return;
    const activeApp = applications.find(a => a.id === active.id);
    const overColumn = COLUMNS.find(c => c.id === over.id);
    if (!activeApp || !overColumn) return;
    setApplications(prev => prev.map(a => a.id === active.id ? { ...a, status: overColumn.id } : a));
  };

  const handleAddApp = (status: ApplicationStatus) => {
    setAddModal({ open: true, status });
  };

  const handleSaveApp = (app: Omit<Application, 'id'>) => {
    setApplications(prev => [...prev, { ...app, id: `app-${Date.now()}` }]);
  };

  const handleDeleteApp = (id: string) => {
    setApplications(prev => prev.filter(a => a.id !== id));
  };

  const handleNoteChange = useCallback((id: string, note: string) => {
    setApplications(prev => prev.map(a => a.id === id ? { ...a, notes: note } : a));
  }, []);

  const exportCSV = () => {
    const headers = ['Company', 'Title', 'Date Applied', 'Status', 'Salary', 'Notes', 'Apply URL'];
    const rows = applications.map(a => [
      a.company, a.title, a.appliedDate, a.status, a.salary || '', a.notes.replace(/\n/g, ' '), a.applyUrl || '',
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'applications.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const activeApp = applications.find(a => a.id === activeId);

  // Stats
  const stats = {
    applied: applications.filter(a => ['applied','phone','technical','final','offer'].includes(a.status)).length,
    inProgress: applications.filter(a => ['phone','technical','final'].includes(a.status)).length,
    offers: applications.filter(a => a.status === 'offer').length,
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)] text-[var(--color-text-primary)]">
      {/* Header */}
      <div className="border-b border-[var(--color-border)] px-6 py-4 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-indigo-500" />
          <h1 className="text-xl font-bold">Application Tracker</h1>
        </div>

        <div className="ml-auto flex items-center gap-3">
          {/* Stats */}
          <div className="hidden md:flex items-center gap-4 text-sm text-[var(--color-text-secondary)]">
            <span className="flex items-center gap-1">
              <BarChart2 className="w-4 h-4" />
              {stats.applied} applied
            </span>
            <span>{stats.inProgress} in progress</span>
            {stats.offers > 0 && (
              <span className="text-emerald-600 font-semibold">{stats.offers} offer{stats.offers > 1 ? 's' : ''} 🎉</span>
            )}
          </div>

          <button
            onClick={exportCSV}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>

          <button
            onClick={() => handleAddApp('applied')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>
      </div>

      {/* Kanban board */}
      <div className="overflow-x-auto p-6">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 min-w-max">
            {COLUMNS.map((col) => (
              <KanbanColumn
                key={col.id}
                column={col}
                apps={applications.filter(a => a.status === col.id)}
                onDelete={handleDeleteApp}
                onNoteChange={handleNoteChange}
                onAddApp={handleAddApp}
              />
            ))}
          </div>

          <DragOverlay>
            {activeApp && (
              <div className="bg-white dark:bg-neutral-900 border-2 border-indigo-500 rounded-xl p-3 shadow-2xl opacity-90 w-[240px]">
                <p className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{activeApp.title}</p>
                <p className="text-xs text-[var(--color-text-secondary)] truncate">{activeApp.company}</p>
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Add modal */}
      {addModal.open && (
        <AddModal
          defaultStatus={addModal.status}
          onSave={handleSaveApp}
          onClose={() => setAddModal({ open: false, status: 'applied' })}
        />
      )}
    </div>
  );
};
