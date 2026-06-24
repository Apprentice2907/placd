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
  w-full px-3 py-2.5 rounded-lg border border-white/10 bg-white/5 text-white text-sm
  placeholder:text-white/25 focus:outline-none focus:border-purple-500/60 focus:bg-white/8
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
        alert("Couldn't extract job details automatically. Please enter manually.");
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Target Job</h2>
          <p className="text-sm text-white/40 mt-0.5">Paste a job URL or enter details manually</p>
        </div>
        {/* Mode Toggle */}
        <div className="flex p-1 bg-white/5 border border-white/10 rounded-lg">
          <button
            onClick={() => setInputMode('url')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-all duration-200 ${
              inputMode === 'url'
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/40'
                : 'text-white/40 hover:text-white/70'
            }`}
          >
            <LinkIcon className="w-3.5 h-3.5" /> URL
          </button>
          <button
            onClick={() => setInputMode('manual')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-all duration-200 ${
              inputMode === 'manual'
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/40'
                : 'text-white/40 hover:text-white/70'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5" /> Manual
          </button>
        </div>
      </div>

      {/* URL Mode */}
      {inputMode === 'url' && (
        <div className="p-5 rounded-xl border border-white/10 bg-white/[0.03] space-y-4">
          <p className="text-sm text-white/40">Paste a job posting URL — we'll extract the details automatically.</p>
          <div className="flex gap-2">
            <input
              className={`${inputClass} flex-1`}
              placeholder="https://boards.greenhouse.io/company/jobs/..."
              value={jobUrl}
              onChange={e => setJobUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleFetch()}
            />
            <button
              onClick={handleFetch}
              disabled={!jobUrl || isFetching}
              className="px-5 bg-purple-600 hover:bg-purple-500 disabled:bg-white/10 disabled:text-white/30 text-white text-sm font-semibold rounded-lg flex items-center gap-2 transition-all duration-200 whitespace-nowrap"
            >
              {isFetching ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Fetch'}
            </button>
          </div>
          <button
            onClick={() => setInputMode('manual')}
            className="text-xs text-white/30 hover:text-white/50 transition-colors"
          >
            Or enter manually →
          </button>
        </div>
      )}

      {/* Manual Mode */}
      {inputMode === 'manual' && (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
          <div className="p-5 rounded-xl border border-white/10 bg-white/[0.03] space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider block mb-1.5">Company</label>
                <input
                  className={inputClass}
                  placeholder="e.g. Stripe"
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider block mb-1.5">Role</label>
                <input
                  className={inputClass}
                  placeholder="e.g. Frontend Engineer"
                  value={role}
                  onChange={e => setRole(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-white/40 uppercase tracking-wider block mb-1.5">Job Description</label>
              <textarea
                className={`${inputClass} min-h-[280px]`}
                placeholder="Paste the full job description here. The more detail, the better the AI tailoring..."
                value={jdText}
                onChange={e => setJdText(e.target.value)}
              />
            </div>
          </div>

          {isReady && (
            <div className="flex justify-end">
              <button
                onClick={onAnalyze}
                className="flex items-center gap-2 px-8 py-3 rounded-xl font-semibold text-sm text-white bg-purple-600 hover:bg-purple-500 transition-all duration-200 shadow-[0_0_20px_rgba(168,85,247,0.3)] hover:shadow-[0_0_28px_rgba(168,85,247,0.45)]"
              >
                <Sparkles className="w-4 h-4" />
                Analyze with AI →
              </button>
            </div>
          )}

          {!isReady && (
            <p className="text-center text-xs text-white/25">Fill in Company, Role, and Job Description to continue</p>
          )}
        </div>
      )}
    </div>
  );
};
