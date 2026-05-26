import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import DOMPurify from 'dompurify';
import { ArrowLeft, MapPin, Briefcase, ExternalLink, AlertTriangle, Building2, Calendar, DollarSign, CheckCircle2 } from 'lucide-react';

export const JobDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [reportSent, setReportSent] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['job', id],
    queryFn: () => api.jobs.get(id as string),
    enabled: !!id,
  });

  const handleReport = async () => {
    if (!id) return;
    try {
      await api.jobs.report(id, "Dead link");
      setReportSent(true);
    } catch (e) {
      console.error("Report failed", e);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-neutral-50 dark:bg-[#0a0a0a] flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-neutral-50 dark:bg-[#0a0a0a] flex items-center justify-center flex-col gap-4">
        <h1 className="text-2xl font-bold">Job Not Found</h1>
        <Link to="/" className="text-indigo-600 hover:underline">Return to search</Link>
      </div>
    );
  }

  const { job, keywords, similar_jobs } = data;
  const initialAvatar = job.company_name ? job.company_name.charAt(0).toUpperCase() : '?';
  const cleanHTML = DOMPurify.sanitize(job.description || '<p>No description provided.</p>');

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-[#0a0a0a] text-neutral-900 dark:text-neutral-100 pb-20">
      
      {/* Navigation */}
      <nav className="sticky top-0 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800 z-20">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-sm font-medium text-neutral-500 hover:text-neutral-900 dark:hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            Back to jobs
          </Link>
          <a 
            href={job.apply_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full font-bold shadow-md hover:shadow-lg transition-all hidden sm:flex items-center gap-2"
          >
            Apply Now
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-4 py-8">
        
        {/* Header section */}
        <div className="bg-white dark:bg-neutral-900 rounded-3xl p-6 sm:p-10 shadow-sm border border-neutral-200 dark:border-neutral-800 mb-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 mb-8">
            <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl bg-gradient-to-br from-neutral-100 to-neutral-200 dark:from-neutral-800 dark:to-neutral-700 border border-neutral-200 dark:border-neutral-700 flex items-center justify-center shrink-0 overflow-hidden shadow-md">
              {job.c_logo ? (
                <img src={job.c_logo} alt={job.company_name} className="w-full h-full object-cover" />
              ) : (
                <span className="text-3xl font-bold text-neutral-500 dark:text-neutral-400">{initialAvatar}</span>
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-lg font-bold text-neutral-700 dark:text-neutral-300">{job.company_name}</h2>
                {job.c_ats && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-neutral-100 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700">
                    {job.c_ats}
                  </span>
                )}
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-4 leading-tight">{job.title}</h1>
              
              <div className="flex flex-wrap items-center gap-4 text-sm font-medium text-neutral-600 dark:text-neutral-400">
                <div className="flex items-center gap-1.5 bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 rounded-lg">
                  <MapPin className="w-4 h-4" />
                  {job.location || 'Remote'}
                </div>
                <div className="flex items-center gap-1.5 bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 rounded-lg">
                  <Briefcase className="w-4 h-4" />
                  <span className="capitalize">{job.job_type || 'Full-time'}</span>
                </div>
                {job.salary_min && (
                  <div className="flex items-center gap-1.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 px-3 py-1.5 rounded-lg">
                    <DollarSign className="w-4 h-4" />
                    ${job.salary_min.toLocaleString()} {job.salary_max ? `- $${job.salary_max.toLocaleString()}` : ''}
                  </div>
                )}
                <div className="flex items-center gap-1.5 px-3 py-1.5">
                  <Calendar className="w-4 h-4 text-neutral-400" />
                  {new Date(job.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          </div>

          <div className="sm:hidden mt-6 mb-2">
             <a 
              href={job.apply_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold shadow-md flex justify-center items-center gap-2"
            >
              Apply Now
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* Two-column layout for desktop */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <div className="lg:col-span-2 space-y-8">
            <section className="bg-white dark:bg-neutral-900 rounded-3xl p-6 sm:p-10 shadow-sm border border-neutral-200 dark:border-neutral-800">
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-indigo-500" />
                About the role
              </h3>
              
              {/* Sanitized HTML */}
              <div 
                className="prose prose-neutral dark:prose-invert prose-indigo max-w-none prose-headings:font-bold prose-a:text-indigo-600 dark:prose-a:text-indigo-400 prose-img:rounded-xl"
                dangerouslySetInnerHTML={{ __html: cleanHTML }}
              />
              
              <div className="mt-10 pt-6 border-t border-neutral-200 dark:border-neutral-800 flex justify-between items-center">
                <p className="text-sm text-neutral-500">Think this job is expired?</p>
                <button 
                  onClick={handleReport}
                  disabled={reportSent}
                  className="flex items-center gap-2 text-sm font-medium text-amber-600 dark:text-amber-500 hover:text-amber-700 dark:hover:text-amber-400 transition-colors disabled:opacity-50"
                >
                  {reportSent ? (
                    <><CheckCircle2 className="w-4 h-4" /> Reported</>
                  ) : (
                    <><AlertTriangle className="w-4 h-4" /> Report Dead Link</>
                  )}
                </button>
              </div>
            </section>
          </div>

          {/* Sidebar */}
          <div className="space-y-8">
            {/* Keywords */}
            {keywords && keywords.length > 0 && (
              <section className="bg-white dark:bg-neutral-900 rounded-3xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
                <h3 className="text-sm font-bold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-4">
                  Resume Keywords
                </h3>
                <div className="flex flex-wrap gap-2">
                  {keywords.map((kw, idx) => (
                    <span 
                      key={idx} 
                      className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700"
                      title={`Relevance: ${(kw.weight * 100).toFixed(0)}%`}
                    >
                      {kw.keyword}
                    </span>
                  ))}
                </div>
                <p className="mt-4 text-[11px] text-neutral-400 leading-relaxed">
                  These keywords were extracted by AI. Include them in your resume to bypass ATS filters.
                </p>
              </section>
            )}

            {/* Similar Jobs */}
            {similar_jobs && similar_jobs.length > 0 && (
              <section>
                <h3 className="text-lg font-bold mb-4">Similar Roles</h3>
                <div className="flex flex-col gap-3">
                  {similar_jobs.map((simJob) => (
                    <Link 
                      key={simJob.id} 
                      to={`/jobs/${simJob.id}`}
                      className="p-4 rounded-2xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 hover:border-indigo-400 dark:hover:border-indigo-600 transition-colors block"
                    >
                      <h4 className="font-bold text-sm line-clamp-1 mb-1">{simJob.title}</h4>
                      <div className="flex items-center justify-between text-xs text-neutral-500">
                        <span className="font-medium">{simJob.company_name}</span>
                        <span>{simJob.location}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>

        </div>

      </main>
    </div>
  );
};
