import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { FileText, Download, CheckCircle2, AlertCircle, RefreshCw, Link as LinkIcon, Edit3 } from 'lucide-react';
import { Link } from 'react-router-dom';

export const ResumeBuilderPage: React.FC = () => {
  const sessionId = localStorage.getItem('placd-session-id') || '';
  
  const [hasProfile, setHasProfile] = useState(false);
  const [profileLoading, setProfileLoading] = useState(true);

  // Job Targeting State
  const [inputMode, setInputMode] = useState<'url' | 'manual'>('url');
  const [jobUrl, setJobUrl] = useState('');
  const [isFetchingJob, setIsFetchingJob] = useState(false);
  
  const [jobTitle, setJobTitle] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [docType, setDocType] = useState<'resume' | 'cover_letter' | 'both'>('both');

  // Generation State
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  
  // Selected Projects State for cheap regeneration
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);

  useEffect(() => {
    const checkProfile = async () => {
      if (!sessionId) {
        setProfileLoading(false);
        return;
      }
      try {
        await api.profile.get(sessionId);
        setHasProfile(true);
      } catch (e) {
        setHasProfile(false);
      } finally {
        setProfileLoading(false);
      }
    };
    checkProfile();
  }, [sessionId]);

  const handleFetchJob = async () => {
    if (!jobUrl) return;
    setIsFetchingJob(true);
    try {
      const data = await api.resume.fetchJob(jobUrl);
      if (data.title || data.description) {
        setJobTitle(data.title);
        setCompanyName(data.company);
        setJobDescription(data.description);
        setInputMode('manual');
      } else {
        alert("Couldn't extract job details. Please enter manually.");
        setInputMode('manual');
      }
    } catch (e) {
      alert("Failed to fetch job. Please paste details manually.");
      setInputMode('manual');
    } finally {
      setIsFetchingJob(false);
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setResult(null);
    try {
      const data = await api.resume.generate({
        session_id: sessionId,
        job_title: jobTitle,
        company_name: companyName,
        job_description: jobDescription,
        document_type: docType
      });
      setResult(data);
      setSelectedProjects(data.selected_projects || []);
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to generate documents');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCheapRegenerate = async () => {
    if (!result?.generation_id) return;
    setIsRegenerating(true);
    try {
      const data = await api.resume.generate({
        session_id: sessionId,
        job_title: jobTitle,
        company_name: companyName,
        job_description: jobDescription,
        document_type: docType,
        regenerate_with_projects: selectedProjects,
        existing_generation_id: result.generation_id
      });
      setResult(data);
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to regenerate resume');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleGeneratePDF = async () => {
    if (!result?.generation_id) return;
    setIsConfirming(true);
    try {
      const data = await api.resume.confirm(result.generation_id);
      setResult({ ...result, ...data });
    } catch (e) {
      alert('Failed to generate PDF. Make sure LibreOffice is installed.');
    } finally {
      setIsConfirming(false);
    }
  };

  const toggleProject = (proj: string) => {
    if (selectedProjects.includes(proj)) {
      setSelectedProjects(selectedProjects.filter(p => p !== proj));
    } else {
      setSelectedProjects([...selectedProjects, proj]);
    }
  };

  const getDownloadUrl = (path: string) => {
    if (!path) return '';
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    try {
      const origin = new URL(apiBase).origin;
      return `${origin}${path}`;
    } catch {
      return path;
    }
  };

  const hasChanges = result && selectedProjects.length !== (result.selected_projects?.length || 0) || 
                     selectedProjects.some(p => !result.selected_projects?.includes(p));

  return (
    <div className="max-w-7xl mx-auto py-10 px-4 h-[calc(100vh-80px)] flex flex-col lg:flex-row gap-8">
      
      {/* LEFT PANEL */}
      <div className="w-full lg:w-2/5 space-y-6 flex flex-col h-full overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] pr-4 border-r border-[var(--border-color)]">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Resume Builder</h1>
          <p className="text-[var(--text-secondary)] mt-1">Tailor your resume instantly for any job.</p>
        </div>

        {profileLoading ? (
          <div className="text-sm">Checking profile...</div>
        ) : hasProfile ? (
          <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg text-sm font-medium">
            <CheckCircle2 className="w-5 h-5" /> Profile loaded
          </div>
        ) : (
          <div className="flex flex-col gap-2 p-4 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 rounded-lg text-sm font-medium border border-amber-200 dark:border-amber-900">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5" /> No profile found
            </div>
            <p className="font-normal opacity-90">You need to set up your profile before generating a tailored resume.</p>
            <Link to="/profile" className="text-indigo-600 dark:text-indigo-400 underline font-medium mt-1">Set up profile →</Link>
          </div>
        )}

        {/* Job Targeting Section */}
        <hr className="border-black/8 dark:border-white/8 my-2" />
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-black dark:text-white">Target Job</h2>
            <div className="flex p-1 bg-neutral-100 dark:bg-neutral-800 rounded-lg">
              <button 
                onClick={() => setInputMode('url')} 
                className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors ${inputMode === 'url' ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white'}`}
              >
                <LinkIcon className="w-3.5 h-3.5"/> URL
              </button>
              <button 
                onClick={() => setInputMode('manual')} 
                className={`px-3 py-1.5 text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors ${inputMode === 'manual' ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white'}`}
              >
                <Edit3 className="w-3.5 h-3.5"/> Manual
              </button>
            </div>
          </div>

          {inputMode === 'url' ? (
            <div className="space-y-3">
              <p className="text-sm text-[var(--text-secondary)]">Paste a job posting URL and we'll extract the details automatically.</p>
              <div className="flex gap-2">
                <input 
                  className="flex-1 bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" 
                  placeholder="https://boards.greenhouse.io/..." 
                  value={jobUrl} 
                  onChange={(e) => setJobUrl(e.target.value)} 
                />
                <button 
                  onClick={handleFetchJob}
                  disabled={!jobUrl || isFetchingJob}
                  className="px-4 bg-foreground text-background font-medium rounded-lg disabled:opacity-50 flex items-center gap-2"
                >
                  {isFetchingJob ? <RefreshCw className="w-4 h-4 animate-spin"/> : 'Fetch'}
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-3 animate-in fade-in slide-in-from-top-2">
              <input 
                className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" 
                placeholder="Job Title (e.g. Frontend Engineer)" 
                value={jobTitle} 
                onChange={(e) => setJobTitle(e.target.value)} 
              />
              <input 
                className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30" 
                placeholder="Company Name (e.g. Stripe)" 
                value={companyName} 
                onChange={(e) => setCompanyName(e.target.value)} 
              />
              <textarea 
                className="w-full bg-white dark:bg-[#1a1a24] border border-black/10 dark:border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-black/30 dark:placeholder:text-white/30 min-h-[180px] resize-y" 
                placeholder="Paste the full job description here..." 
                value={jobDescription} 
                onChange={(e) => setJobDescription(e.target.value)} 
              />
              {jobUrl && (
                 <button onClick={() => setInputMode('url')} className="text-xs text-indigo-500 hover:underline">← Back to URL fetcher</button>
              )}
            </div>
          )}
        </div>

        <div className="space-y-3 pt-4 border-t border-[var(--border-color)]">
          <h2 className="text-xs font-semibold tracking-widest uppercase text-black/40 dark:text-white/40 mb-2">What to generate</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label className={`flex flex-col items-center justify-center p-3 border rounded-xl cursor-pointer transition-all ${docType === 'resume' ? 'border-indigo-500 ring-2 ring-indigo-500 bg-indigo-500/5 text-indigo-700 dark:text-indigo-400' : 'border-[var(--border-color)] hover:border-neutral-400 dark:hover:border-neutral-600'}`}>
              <input type="radio" className="sr-only" name="docType" checked={docType === 'resume'} onChange={() => setDocType('resume')} />
              <span className="font-medium text-sm">Resume</span>
            </label>
            <label className={`flex flex-col items-center justify-center p-3 border rounded-xl cursor-pointer transition-all ${docType === 'cover_letter' ? 'border-indigo-500 ring-2 ring-indigo-500 bg-indigo-500/5 text-indigo-700 dark:text-indigo-400' : 'border-[var(--border-color)] hover:border-neutral-400 dark:hover:border-neutral-600'}`}>
              <input type="radio" className="sr-only" name="docType" checked={docType === 'cover_letter'} onChange={() => setDocType('cover_letter')} />
              <span className="font-medium text-sm">Cover Letter</span>
            </label>
            <label className={`flex flex-col items-center justify-center p-3 border rounded-xl cursor-pointer transition-all ${docType === 'both' ? 'border-indigo-500 ring-2 ring-indigo-500 bg-indigo-500/5 text-indigo-700 dark:text-indigo-400 ring-1 ring-indigo-500' : 'border-[var(--border-color)] hover:border-neutral-400 dark:hover:border-neutral-600'}`}>
              <input type="radio" className="sr-only" name="docType" checked={docType === 'both'} onChange={() => setDocType('both')} />
              <span className="font-medium text-sm text-center">Both<br/><span className="text-[10px] opacity-80">(Recommended)</span></span>
            </label>
          </div>
        </div>

        <button 
          onClick={handleGenerate}
          disabled={!hasProfile || !jobTitle || !companyName || !jobDescription || isGenerating}
          className="w-full py-3.5 mt-auto bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex justify-center items-center gap-2"
        >
          {isGenerating ? <RefreshCw className="w-5 h-5 animate-spin" /> : <FileText className="w-5 h-5" />}
          {isGenerating ? 'Generating...' : 'Generate Documents'}
        </button>
      </div>

      {/* RIGHT PANEL */}
      <div className="w-full lg:w-3/5 h-full overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] flex flex-col lg:pl-4">
        
        {!result && !isGenerating && (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 border border-black/8 dark:border-white/8 rounded-xl bg-[#f5f5f7] dark:bg-[#111118] relative overflow-hidden">
            <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, currentColor 1px, transparent 0)', backgroundSize: '24px 24px' }}></div>
            <div className="relative z-10 flex flex-col items-center">
              <div className="w-16 h-16 bg-white dark:bg-[#1a1a24] shadow-sm border border-black/10 dark:border-white/10 text-indigo-500 rounded-2xl flex items-center justify-center mb-6">
                <FileText className="w-8 h-8" />
              </div>
              <h3 className="text-2xl font-bold text-black dark:text-white">Ready to Tailor</h3>
              <p className="text-black/60 dark:text-white/60 max-w-md mt-3 mb-8">Provide the job details on the left, and our AI will dynamically tailor your documents.</p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left text-sm text-black/80 dark:text-white/80">
                <div className="flex gap-3 bg-white dark:bg-[#1a1a24] p-4 rounded-lg border border-black/8 dark:border-white/8">
                  <CheckCircle2 className="w-5 h-5 text-indigo-500 shrink-0" />
                  <span>Extracts ATS keywords and integrates them naturally</span>
                </div>
                <div className="flex gap-3 bg-white dark:bg-[#1a1a24] p-4 rounded-lg border border-black/8 dark:border-white/8">
                  <CheckCircle2 className="w-5 h-5 text-indigo-500 shrink-0" />
                  <span>Selects the most relevant projects for the role</span>
                </div>
                <div className="flex gap-3 bg-white dark:bg-[#1a1a24] p-4 rounded-lg border border-black/8 dark:border-white/8">
                  <CheckCircle2 className="w-5 h-5 text-indigo-500 shrink-0" />
                  <span>Rewrites experience bullets to match requirements</span>
                </div>
                <div className="flex gap-3 bg-white dark:bg-[#1a1a24] p-4 rounded-lg border border-black/8 dark:border-white/8">
                  <CheckCircle2 className="w-5 h-5 text-indigo-500 shrink-0" />
                  <span>Outputs highly formatted, ATS-friendly DOCX & PDF</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {isGenerating && (
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="relative mb-8">
              <div className="absolute inset-0 bg-indigo-500/20 rounded-full blur-xl animate-pulse"></div>
              <RefreshCw className="w-16 h-16 text-indigo-500 animate-spin relative" />
            </div>
            <h3 className="text-2xl font-bold">Analyzing Job Description...</h3>
            <p className="text-[var(--text-secondary)] mt-2">Extracting ATS keywords, selecting projects, and tailoring bullets</p>
          </div>
        )}

        {result && (
          <div className="space-y-8 pb-10 animate-in fade-in slide-in-from-bottom-4">
            
            {/* Header Result */}
            <div className="p-6 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-3xl flex flex-col sm:flex-row gap-6 justify-between items-start sm:items-center">
              <div>
                <h2 className="text-2xl font-bold">Generation Complete</h2>
                <p className="text-[var(--text-secondary)] mt-1">Review your tailored documents below.</p>
              </div>
              {result.match_score > 0 && (
                <div 
                  className={`px-4 py-2 rounded-2xl text-lg font-mono font-bold border flex items-center gap-2
                  ${result.match_score > 70 ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:border-green-900/50' : 
                    result.match_score >= 40 ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:border-amber-900/50' : 
                    'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:border-red-900/50'}`}
                  title="Estimated ATS match based on your profile vs the JD"
                >
                  {result.match_score}% Match
                </div>
              )}
            </div>

            {/* Downloads */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {result.docx_url && (
                <div className="p-6 border border-[var(--border-color)] rounded-2xl bg-[var(--bg-card)] flex flex-col gap-6 shadow-sm">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
                      <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <h4 className="font-bold text-lg">Resume.docx</h4>
                      <p className="text-sm text-[var(--text-secondary)]">ATS-friendly layout</p>
                    </div>
                  </div>
                  <div className="flex flex-col gap-3 mt-auto">
                    <a href={getDownloadUrl(result.docx_url)} download className="w-full py-2.5 bg-blue-600 text-white hover:bg-blue-700 rounded-xl text-center font-bold text-sm transition-colors flex justify-center items-center gap-2 shadow-sm">
                      <Download className="w-4 h-4"/> Download DOCX
                    </a>
                    {result.pdf_url ? (
                      <a href={getDownloadUrl(result.pdf_url)} download className="w-full py-2.5 bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-xl text-center font-bold text-sm transition-colors flex justify-center items-center gap-2">
                        <Download className="w-4 h-4"/> Download PDF
                      </a>
                    ) : (
                      <button onClick={handleGeneratePDF} disabled={isConfirming} className="w-full py-2.5 border border-[var(--border-color)] hover:bg-[var(--bg-secondary)] rounded-xl font-bold text-sm transition-colors flex justify-center items-center gap-2">
                        {isConfirming ? <RefreshCw className="w-4 h-4 animate-spin"/> : <FileText className="w-4 h-4"/>}
                        {isConfirming ? 'Generating PDF...' : 'Generate PDF'}
                      </button>
                    )}
                  </div>
                </div>
              )}

              {result.cover_letter_docx_url && (
                <div className="p-6 border border-[var(--border-color)] rounded-2xl bg-[var(--bg-card)] flex flex-col gap-6 shadow-sm">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-xl">
                      <FileText className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                      <h4 className="font-bold text-lg">Cover_Letter.docx</h4>
                      <p className="text-sm text-[var(--text-secondary)]">Tailored to {companyName}</p>
                    </div>
                  </div>
                  <div className="flex flex-col gap-3 mt-auto">
                    <a href={getDownloadUrl(result.cover_letter_docx_url)} download className="w-full py-2.5 bg-purple-600 text-white hover:bg-purple-700 rounded-xl text-center font-bold text-sm transition-colors flex justify-center items-center gap-2 shadow-sm">
                      <Download className="w-4 h-4"/> Download DOCX
                    </a>
                    {result.cover_letter_pdf_url && (
                      <a href={getDownloadUrl(result.cover_letter_pdf_url)} download className="w-full py-2.5 bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-xl text-center font-bold text-sm transition-colors flex justify-center items-center gap-2">
                        <Download className="w-4 h-4"/> Download PDF
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* ATS Keywords */}
              {result.ats_keywords && result.ats_keywords.length > 0 && (
                <div className="space-y-4">
                  <h3 className="font-bold text-lg flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-green-500"/> Found Keywords
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {result.ats_keywords.map((kw: string, i: number) => (
                      <span key={i} className="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 rounded-full px-2.5 py-0.5 text-xs font-mono">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Selected Projects Configuration */}
              {result.selected_projects && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-bold text-lg">Included Projects</h3>
                    {hasChanges && (
                       <button 
                         onClick={handleCheapRegenerate}
                         disabled={isRegenerating}
                         className="text-xs bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400 px-3 py-1.5 rounded-full font-bold flex items-center gap-1 hover:bg-indigo-200 transition-colors"
                       >
                         {isRegenerating ? <RefreshCw className="w-3 h-3 animate-spin"/> : 'Update DOCX'}
                       </button>
                    )}
                  </div>
                  <div className="space-y-2">
                    {result.selected_projects.map((proj: string, i: number) => {
                      const isSelected = selectedProjects.includes(proj);
                      return (
                        <div 
                          key={i} 
                          onClick={() => toggleProject(proj)}
                          className={`p-3 border rounded-xl flex items-center justify-between cursor-pointer transition-colors select-none ${isSelected ? 'border-indigo-500 bg-indigo-50/30 dark:bg-indigo-900/10' : 'border-[var(--border-color)] opacity-60 hover:opacity-100'}`}
                        >
                          <span className="font-medium text-sm">{proj}</span>
                          <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${isSelected ? 'bg-indigo-500 border-indigo-500' : 'border-black/20 dark:border-white/20 bg-white dark:bg-transparent'}`}>
                            {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                          </div>
                        </div>
                      )
                    })}
                    <p className="text-xs text-[var(--text-secondary)] mt-2 italic">Deselect projects you don't want included and hit Update.</p>
                  </div>
                </div>
              )}
            </div>

            <div className="pt-6 border-t border-[var(--border-color)] flex justify-end gap-4">
              <button onClick={handleGenerate} className="px-6 py-2.5 border border-[var(--border-color)] hover:bg-[var(--bg-secondary)] rounded-xl font-bold text-sm transition-colors flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> Regenerate All
              </button>
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
};
