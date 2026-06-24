import React, { useState } from 'react';
import { api } from '../../lib/api';
import { LinkIcon, Edit3, RefreshCw, Sparkles } from 'lucide-react';

interface JobTargetFormProps {
  jdText: string;
  setJdText: (v: string) => void;
  company: string;
  setCompany: (v: string) => void;
  role: string;
  setRole: (v: string) => void;
  onAnalyze: () => void;
}

const inputClass = `
  w-full px-3 py-2.5 rounded-lg border border-gray-300 bg-white text-gray-900 text-sm
  placeholder:text-gray-400 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/20
  transition-all duration-200
`.trim();

export const JobTargetForm: React.FC<JobTargetFormProps> = ({
  jdText, setJdText, company, setCompany, role, setRole, onAnalyze
}) => {
  const [inputMode, setInputMode] = useState<'url' | 'manual'>('url');
  const [jobUrl, setJobUrl] = useState('');
  const [isFetching, setIsFetching] = useState(false);

  const handleFetch = async () => {
    if (!jobUrl) return;
    setIsFetching(true);
    try {
      const data = await api.resume.fetchJob(jobUrl);
      if (data.success && data.jd_text) {
        setJdText(data.jd_text);
        if (data.detected_company) setCompany(data.detected_company);
        if (data.detected_role) setRole(data.detected_role);
        setInputMode('manual');
      } else {
        alert("Couldn't extract job details. Please enter manually.");
        setInputMode('manual');
      }
    } catch {
      alert("Failed to fetch job. Please paste details manually.");
      setInputMode('manual');
    } finally {
      setIsFetching(false);
    }
  };

  const isReady = Boolean(jdText?.trim() && company?.trim() && role?.trim());

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in pb-10">

      {/* Header + Mode toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-800">Target Job</h2>
          <p className="text-sm text-gray-500 mt-0.5">Paste a job URL or enter details manually</p>
        </div>
        <div className="flex p-1 bg-gray-100 border border-gray-200 rounded-lg">
          <button
            onClick={() => setInputMode('url')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-all duration-200 ${
              inputMode === 'url'
                ? 'bg-white text-violet-600 border border-violet-200 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <LinkIcon className="w-3.5 h-3.5" /> URL
          </button>
          <button
            onClick={() => setInputMode('manual')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-all duration-200 ${
              inputMode === 'manual'
                ? 'bg-white text-violet-600 border border-violet-200 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5" /> Manual
          </button>
        </div>
      </div>

      {/* URL mode */}
      {inputMode === 'url' && (
        <div className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm space-y-4">
          <p className="text-sm text-gray-500">Paste a job posting URL — we'll extract the details automatically.</p>
          <div className="flex gap-2">
            <input
              className={`${inputClass} flex-1`}
              placeholder="https://boards.greenhouse.io/..."
              value={jobUrl}
              onChange={e => setJobUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleFetch()}
            />
            <button
              onClick={handleFetch}
              disabled={!jobUrl || isFetching}
              className="px-5 bg-violet-600 hover:bg-violet-700 disabled:bg-gray-200 disabled:text-gray-400 text-white text-sm font-semibold rounded-lg flex items-center gap-2 transition-all duration-200 whitespace-nowrap"
            >
              {isFetching ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Fetch'}
            </button>
          </div>
          <button
            onClick={() => setInputMode('manual')}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Or enter manually →
          </button>
        </div>
      )}

      {/* Manual mode */}
      {inputMode === 'manual' && (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
          <div className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-500 block mb-1.5">Company</label>
                <input className={inputClass} placeholder="e.g. Stripe" value={company} onChange={e => setCompany(e.target.value)} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 block mb-1.5">Role</label>
                <input className={inputClass} placeholder="e.g. Frontend Engineer" value={role} onChange={e => setRole(e.target.value)} />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1.5">Job Description</label>
              <textarea
                className={`${inputClass} min-h-[260px]`}
                placeholder="Paste the full job description here..."
                value={jdText}
                onChange={e => setJdText(e.target.value)}
              />
            </div>
          </div>

          {isReady ? (
            <div className="flex justify-end">
              <button
                onClick={onAnalyze}
                className="flex items-center gap-2 px-8 py-2.5 rounded-xl font-semibold text-sm text-white bg-violet-600 hover:bg-violet-700 transition-colors shadow-sm"
              >
                <Sparkles className="w-4 h-4" />
                Analyze with AI →
              </button>
            </div>
          ) : (
            <p className="text-center text-xs text-gray-400">Fill in Company, Role, and Job Description to continue</p>
          )}
        </div>
      )}
    </div>
  );
};
