import React, { useState } from 'react';
import { api } from '../../lib/api';
import { LinkIcon, Edit3, RefreshCw } from 'lucide-react';

interface JobTargetFormProps {
  jdText: string;
  setJdText: (v: string) => void;
  company: string;
  setCompany: (v: string) => void;
  role: string;
  setRole: (v: string) => void;
  onAnalyze: () => void;
}

export const JobTargetForm: React.FC<JobTargetFormProps> = ({ jdText, setJdText, company, setCompany, role, setRole, onAnalyze }) => {
  const [inputMode, setInputMode] = useState<'url' | 'manual'>('url');
  const [jobUrl, setJobUrl] = useState('');
  const [isFetching, setIsFetching] = useState(false);

  const handleFetch = async () => {
    if (!jobUrl) return;
    setIsFetching(true);
    try {
      const data = await api.resume.scrapeJd(jobUrl);
      if (data.success && data.jd_text) {
        setJdText(data.jd_text);
        if (data.detected_company) setCompany(data.detected_company);
        if (data.detected_role) setRole(data.detected_role);
        setInputMode('manual');
      } else {
        alert("Couldn't extract job details automatically. Please enter manually.");
        setInputMode('manual');
      }
    } catch (e) {
      alert("Failed to fetch job. Please paste details manually.");
      setInputMode('manual');
    } finally {
      setIsFetching(false);
    }
  };

  const isReady = Boolean(jdText?.trim() && company?.trim() && role?.trim());

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in pb-10">
      <div className="flex items-center justify-between border-b border-neutral-200 pb-2">
        <h2 className="text-xl font-bold">Target Job</h2>
        <div className="flex p-1 bg-neutral-100 dark:bg-neutral-800 rounded-lg">
          <button 
            onClick={() => setInputMode('url')} 
            className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors ${inputMode === 'url' ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-neutral-500 hover:text-black dark:hover:text-white'}`}
          >
            <LinkIcon className="w-3.5 h-3.5"/> URL
          </button>
          <button 
            onClick={() => setInputMode('manual')} 
            className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors ${inputMode === 'manual' ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-neutral-500 hover:text-black dark:hover:text-white'}`}
          >
            <Edit3 className="w-3.5 h-3.5"/> Manual
          </button>
        </div>
      </div>

      {inputMode === 'url' ? (
        <div className="space-y-4">
          <p className="text-sm text-neutral-500">Paste a job posting URL and we'll extract the details automatically.</p>
          <div className="flex gap-2">
            <input 
              className="flex-1 input-field" 
              placeholder="https://boards.greenhouse.io/..." 
              value={jobUrl} 
              onChange={(e) => setJobUrl(e.target.value)} 
            />
            <button 
              onClick={handleFetch}
              disabled={!jobUrl || isFetching}
              className="px-6 bg-black dark:bg-white text-white dark:text-black font-medium rounded-lg disabled:opacity-50 flex items-center gap-2"
            >
              {isFetching ? <RefreshCw className="w-4 h-4 animate-spin"/> : 'Fetch'}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-semibold flex items-center gap-2 mb-1">
                Company <span className="text-[10px] font-normal px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded text-neutral-500">Editable</span>
              </label>
              <input className="input-field placeholder:text-neutral-300 dark:placeholder:text-neutral-700" placeholder="e.g. Stripe" value={company} onChange={e => setCompany(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-semibold flex items-center gap-2 mb-1">
                Role <span className="text-[10px] font-normal px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded text-neutral-500">Editable</span>
              </label>
              <input className="input-field placeholder:text-neutral-300 dark:placeholder:text-neutral-700" placeholder="e.g. Frontend Engineer" value={role} onChange={e => setRole(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="text-sm font-semibold block mb-1">Job Description</label>
            <textarea 
              className="input-field min-h-[300px]" 
              placeholder="Paste the full job description here..." 
              value={jdText} 
              onChange={e => setJdText(e.target.value)} 
            />
          </div>
          <div className="flex justify-end pt-4">
            <button 
              onClick={onAnalyze} 
              disabled={!isReady}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-lg font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Analyze This Job →
            </button>
          </div>
        </div>
      )}

      <style>{`
        .input-field {
          width: 100%;
          padding: 0.5rem 0.75rem;
          border-radius: 0.5rem;
          border: 1px solid var(--border-color);
          background: transparent;
          font-size: 0.875rem;
        }
        .input-field:focus { outline: none; border-color: #4f46e5; }
      `}</style>
    </div>
  );
}
