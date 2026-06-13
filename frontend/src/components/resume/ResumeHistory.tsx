import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Clock, Download, ExternalLink } from 'lucide-react';

interface HistoryItem {
  id: string;
  job_url: string;
  job_title: string;
  company_name: string;
  ats_score_before: number;
  ats_score_after: number;
  docx_url: string;
  pdf_url: string;
  created_at: string;
}

export const ResumeHistory: React.FC = () => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const sessionId = localStorage.getItem('placd-session-id') || '';
        const data = await api.resume.history(sessionId);
        setHistory(data);
      } catch (e) {
        console.error("Failed to fetch history", e);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  if (loading) return null;
  if (history.length === 0) return null;

  return (
    <div className="max-w-3xl mx-auto mt-12 animate-in fade-in pb-10">
      <h3 className="text-lg font-bold flex items-center gap-2 mb-4 border-b border-neutral-200 pb-2">
        <Clock className="w-5 h-5 text-neutral-400" />
        Recently Generated Resumes
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {history.map(item => (
          <div key={item.id} className="p-4 border border-neutral-200 dark:border-neutral-800 rounded-xl bg-white dark:bg-neutral-900 shadow-sm flex flex-col justify-between">
            <div>
              <h4 className="font-bold text-base truncate">{item.job_title || 'Untitled Role'}</h4>
              <p className="text-sm text-neutral-500 mb-3">{item.company_name || 'Unknown Company'}</p>
              
              <div className="flex gap-4 text-xs font-medium mb-4">
                <div className="flex flex-col">
                  <span className="text-neutral-400">Score Before</span>
                  <span className="text-neutral-600 dark:text-neutral-300">{item.ats_score_before || 0}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-neutral-400">Score After</span>
                  <span className="text-green-600">{item.ats_score_after || 0}</span>
                </div>
              </div>
            </div>
            
            <div className="flex gap-2 border-t border-neutral-100 dark:border-neutral-800 pt-3">
              {item.docx_url && (
                <a href={import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace('/api', '') + item.docx_url : `http://localhost:8000${item.docx_url}`} download className="flex-1 text-center py-1.5 bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors">
                  <Download className="w-3.5 h-3.5" /> DOCX
                </a>
              )}
              {item.pdf_url && (
                <a href={import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace('/api', '') + item.pdf_url : `http://localhost:8000${item.pdf_url}`} download className="flex-1 text-center py-1.5 bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors">
                  <Download className="w-3.5 h-3.5" /> PDF
                </a>
              )}
              {item.job_url && (
                <a href={item.job_url} target="_blank" rel="noreferrer" className="px-2 py-1.5 bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded flex items-center justify-center text-neutral-500 transition-colors">
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
