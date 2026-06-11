import React, { useRef } from 'react';
import type { ResumeProfile, RewriteResult } from '../../types/resume';
import { BulletToggle } from './BulletToggle';
import { Download, FileText } from 'lucide-react';

interface ResumePreviewProps {
  profile: ResumeProfile;
  rewrite: RewriteResult;
  bulletSelections: Record<string, 'original' | 'ai'>;
  onToggleBullet: (id: string, v: 'original' | 'ai') => void;
  onExport: () => void;
}

export const ResumePreview: React.FC<ResumePreviewProps> = ({ profile, rewrite, bulletSelections, onToggleBullet, onExport }) => {
  const contentRef = useRef<HTMLDivElement>(null);

  const getRewritten = (id: string) => {
    return rewrite.rewritten_bullets?.find(b => b.id === id)?.bullets || [];
  };

  return (
    <div className="max-w-5xl mx-auto flex flex-col md:flex-row gap-6 animate-in fade-in pb-10 items-start">
      <div className="flex-1 bg-white text-black border border-neutral-200 p-8 shadow-sm print:shadow-none print:border-none print:p-0 min-h-[1056px] w-full" ref={contentRef}>
        <div className="text-center space-y-1 border-b-2 border-black pb-4 mb-4">
          <h1 className="text-3xl font-bold uppercase tracking-wider">{profile.personal.name || 'Your Name'}</h1>
          <p className="text-sm text-neutral-600">
            {[profile.personal.email, profile.personal.phone, profile.personal.location].filter(Boolean).join(' | ')}
          </p>
          <p className="text-sm text-neutral-600">
            {[profile.personal.linkedin, profile.personal.github].filter(Boolean).join(' | ')}
          </p>
        </div>

        {/* Summary */}
        {rewrite.summary && (
          <div className="mb-5">
            <h2 className="text-md font-bold uppercase tracking-widest border-b border-neutral-300 mb-2 pb-1 text-neutral-800">Summary</h2>
            <p className="text-sm leading-relaxed">{rewrite.summary}</p>
          </div>
        )}

        {/* Experience */}
        {profile.experience.length > 0 && (
          <div className="mb-5">
            <h2 className="text-md font-bold uppercase tracking-widest border-b border-neutral-300 mb-2 pb-1 text-neutral-800">Experience</h2>
            <div className="space-y-5">
              {profile.experience.map(exp => {
                const aiB = getRewritten(exp.id);
                const hasRewrite = aiB.length > 0;
                
                return (
                  <div key={exp.id}>
                    <div className="flex justify-between items-baseline font-bold text-neutral-900">
                      <span>{exp.role}</span>
                      <span className="text-sm font-normal text-neutral-600">{exp.start} {exp.end ? `- ${exp.end}` : ''}</span>
                    </div>
                    <div className="italic text-sm mb-1.5 text-neutral-700">{exp.company}</div>
                    
                    <div className="print:hidden">
                      {hasRewrite ? (
                        <BulletToggle 
                          originalBullets={exp.bullets} 
                          aiBullets={aiB} 
                          selection={bulletSelections[exp.id] || 'original'} 
                          onToggle={v => onToggleBullet(exp.id, v)} 
                        />
                      ) : (
                        <ul className="list-disc pl-5 text-sm space-y-1">
                          {exp.bullets.map((b, i) => <li key={i}>{b}</li>)}
                        </ul>
                      )}
                    </div>
                    
                    <div className="hidden print:block">
                      <ul className="list-disc pl-5 text-sm space-y-1">
                        {((bulletSelections[exp.id] === 'ai' && hasRewrite) ? aiB : exp.bullets).map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Projects */}
        {profile.projects.length > 0 && (
          <div className="mb-5">
            <h2 className="text-md font-bold uppercase tracking-widest border-b border-neutral-300 mb-2 pb-1 text-neutral-800">Projects</h2>
            <div className="space-y-5">
              {profile.projects.map(proj => {
                const aiB = getRewritten(proj.id);
                const hasRewrite = aiB.length > 0;
                
                return (
                  <div key={proj.id}>
                    <div className="flex justify-between items-baseline font-bold text-neutral-900 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span>{proj.name}</span>
                        {proj.stack.length > 0 && <span className="font-normal text-sm text-neutral-500 italic">| {proj.stack.join(', ')}</span>}
                      </div>
                      {proj.link && <a href={proj.link} className="text-xs font-normal text-indigo-600">Link</a>}
                    </div>
                    
                    <div className="print:hidden">
                      {hasRewrite ? (
                        <BulletToggle 
                          originalBullets={proj.bullets} 
                          aiBullets={aiB} 
                          selection={bulletSelections[proj.id] || 'original'} 
                          onToggle={v => onToggleBullet(proj.id, v)} 
                        />
                      ) : (
                        <ul className="list-disc pl-5 text-sm space-y-1">
                          {proj.bullets.map((b, i) => <li key={i}>{b}</li>)}
                        </ul>
                      )}
                    </div>
                    
                    <div className="hidden print:block">
                      <ul className="list-disc pl-5 text-sm space-y-1">
                        {((bulletSelections[proj.id] === 'ai' && hasRewrite) ? aiB : proj.bullets).map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Skills */}
        <div className="mb-2">
          <h2 className="text-md font-bold uppercase tracking-widest border-b border-neutral-300 mb-2 pb-1 text-neutral-800">Skills</h2>
          <p className="text-sm leading-relaxed">
            {rewrite.skills_reordered?.length > 0 ? rewrite.skills_reordered.join(', ') : [
              ...profile.skills.languages, ...profile.skills.frameworks, ...profile.skills.tools, ...profile.skills.databases
            ].filter(Boolean).join(', ')}
          </p>
        </div>
        
      </div>
      
      <div className="w-full md:w-64 shrink-0 space-y-4 no-print sticky top-8">
        <div className="bg-indigo-50 border border-indigo-100 dark:bg-indigo-900/20 dark:border-indigo-800 p-5 rounded-xl">
          <h3 className="font-bold text-indigo-900 dark:text-indigo-300 mb-2 flex items-center gap-2"><FileText className="w-4 h-4"/> Ready to export?</h3>
          <p className="text-sm text-indigo-700 dark:text-indigo-400 mb-5">Review your selections using the toggles on the left, then download your tailored resume.</p>
          <button 
            onClick={onExport}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-lg font-bold flex items-center justify-center gap-2 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4"/> Export PDF
          </button>
        </div>
      </div>
    </div>
  );
};
