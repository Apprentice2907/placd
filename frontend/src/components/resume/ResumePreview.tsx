import React from 'react';
import type { ResumeProfile, RewriteResult } from '../../types/resume';
import { BulletToggle } from './BulletToggle';
import { Download, ArrowLeft } from 'lucide-react';

interface ResumePreviewProps {
  profile: ResumeProfile;
  rewrite: RewriteResult;
  bulletSelections: Record<string, 'original' | 'ai'>;
  onToggleBullet: (id: string, v: 'original' | 'ai') => void;
  onExport: () => void;
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="mb-3 mt-5 first:mt-0">
      <h2 className="text-[11px] font-bold uppercase tracking-[0.12em] text-gray-700 font-serif">
        {title}
      </h2>
      <hr className="border-t border-gray-800 mt-0.5" />
    </div>
  );
}

export const ResumePreview: React.FC<ResumePreviewProps> = ({
  profile, rewrite, bulletSelections, onToggleBullet, onExport
}) => {
  const getRewritten = (id: string) =>
    rewrite.rewritten_bullets?.find(b => b.id === id)?.bullets || [];

  const contactLine = [
    profile.personal.email,
    profile.personal.phone,
    profile.personal.location,
  ].filter(Boolean).join(' | ');

  const linksLine = [
    profile.personal.linkedin,
    profile.personal.github,
    profile.personal.portfolio,
  ].filter(Boolean).join(' | ');

  const allSkills = rewrite.skills_reordered?.length > 0
    ? rewrite.skills_reordered
    : [
        ...profile.skills.languages,
        ...profile.skills.frameworks,
        ...profile.skills.tools,
        ...profile.skills.databases,
      ].filter(Boolean);

  return (
    <div className="max-w-5xl mx-auto flex flex-col lg:flex-row gap-6 animate-in fade-in pb-10 items-start">

      {/* ── A4 Paper ── */}
      <div
        id="resume-preview-paper"
        className="flex-1 bg-white text-black shadow-2xl print:shadow-none"
        style={{
          fontFamily: 'Georgia, "Times New Roman", serif',
          minHeight: '1056px',
          padding: '0.75in',
          fontSize: '11pt',
          lineHeight: '1.45',
        }}
      >
        {/* Name */}
        <div className="text-center mb-3" style={{ borderBottom: '2px solid #111', paddingBottom: '10px' }}>
          <h1 style={{
            fontSize: '22pt',
            fontWeight: 700,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            marginBottom: '4px',
            fontFamily: 'Georgia, serif',
          }}>
            {profile.personal.name || 'Your Name'}
          </h1>
          {contactLine && (
            <p style={{ fontSize: '9.5pt', color: '#444', marginBottom: '2px' }}>{contactLine}</p>
          )}
          {linksLine && (
            <p style={{ fontSize: '9.5pt', color: '#444' }}>{linksLine}</p>
          )}
        </div>

        {/* Summary */}
        {rewrite.summary && (
          <div>
            <SectionHeader title="Professional Summary" />
            <p style={{ fontSize: '10pt', lineHeight: '1.5', color: '#222' }}>{rewrite.summary}</p>
          </div>
        )}

        {/* Experience */}
        {profile.experience.length > 0 && (
          <div>
            <SectionHeader title="Experience" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {profile.experience.map(exp => {
                const aiB = getRewritten(exp.id);
                const hasRewrite = aiB.length > 0;
                const dateStr = `${exp.start}${exp.end ? ` – ${exp.end}` : ''}`;

                return (
                  <div key={exp.id}>
                    {/* Role + Date */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontWeight: 700, fontSize: '11pt' }}>{exp.role}</span>
                      <span style={{ fontSize: '9.5pt', color: '#555' }}>{dateStr}</span>
                    </div>
                    {/* Company */}
                    <div style={{ fontStyle: 'italic', fontSize: '10pt', color: '#444', marginBottom: '4px' }}>
                      {exp.company}{exp.location ? `, ${exp.location}` : ''}
                    </div>

                    {/* Bullets — screen (with toggle) */}
                    <div className="print:hidden">
                      {hasRewrite ? (
                        <BulletToggle
                          originalBullets={exp.bullets}
                          aiBullets={aiB}
                          selection={bulletSelections[exp.id] || 'original'}
                          onToggle={v => onToggleBullet(exp.id, v)}
                        />
                      ) : (
                        <ul style={{ paddingLeft: '14px', margin: 0 }}>
                          {exp.bullets.filter(Boolean).map((b, i) => (
                            <li key={i} style={{ fontSize: '10pt', marginBottom: '2px', listStyleType: '\'•  \'' }}>{b}</li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {/* Bullets — print only */}
                    <div className="hidden print:block">
                      <ul style={{ paddingLeft: '14px', margin: 0 }}>
                        {((bulletSelections[exp.id] === 'ai' && hasRewrite) ? aiB : exp.bullets)
                          .filter(Boolean)
                          .map((b, i) => (
                            <li key={i} style={{ fontSize: '10pt', marginBottom: '2px', listStyleType: '\'•  \'' }}>{b}</li>
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
          <div>
            <SectionHeader title="Projects" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {profile.projects.map(proj => {
                const aiB = getRewritten(proj.id);
                const hasRewrite = aiB.length > 0;

                return (
                  <div key={proj.id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                        <span style={{ fontWeight: 700, fontSize: '11pt' }}>{proj.name}</span>
                        {proj.stack.length > 0 && (
                          <span style={{ fontStyle: 'italic', fontSize: '9.5pt', color: '#555' }}>
                            | {proj.stack.join(', ')}
                          </span>
                        )}
                      </div>
                      {proj.link && (
                        <span style={{ fontSize: '9pt', color: '#555' }}>{proj.link}</span>
                      )}
                    </div>

                    <div className="print:hidden" style={{ marginTop: '4px' }}>
                      {hasRewrite ? (
                        <BulletToggle
                          originalBullets={proj.bullets}
                          aiBullets={aiB}
                          selection={bulletSelections[proj.id] || 'original'}
                          onToggle={v => onToggleBullet(proj.id, v)}
                        />
                      ) : (
                        <ul style={{ paddingLeft: '14px', margin: 0 }}>
                          {proj.bullets.filter(Boolean).map((b, i) => (
                            <li key={i} style={{ fontSize: '10pt', marginBottom: '2px', listStyleType: '\'•  \'' }}>{b}</li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div className="hidden print:block" style={{ marginTop: '4px' }}>
                      <ul style={{ paddingLeft: '14px', margin: 0 }}>
                        {((bulletSelections[proj.id] === 'ai' && hasRewrite) ? aiB : proj.bullets)
                          .filter(Boolean)
                          .map((b, i) => (
                            <li key={i} style={{ fontSize: '10pt', marginBottom: '2px', listStyleType: '\'•  \'' }}>{b}</li>
                          ))}
                      </ul>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Education */}
        {profile.education.length > 0 && (
          <div>
            <SectionHeader title="Education" />
            {profile.education.map(edu => (
              <div key={edu.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
                <div>
                  <span style={{ fontWeight: 700, fontSize: '11pt' }}>{edu.institution}</span>
                  <div style={{ fontSize: '10pt', color: '#444', fontStyle: 'italic' }}>
                    {edu.degree}{edu.field ? ` in ${edu.field}` : ''}
                    {edu.gpa ? ` · GPA: ${edu.gpa}` : ''}
                  </div>
                </div>
                <span style={{ fontSize: '9.5pt', color: '#555' }}>{edu.graduation_year}</span>
              </div>
            ))}
          </div>
        )}

        {/* Skills */}
        {allSkills.length > 0 && (
          <div>
            <SectionHeader title="Technical Skills" />
            <p style={{ fontSize: '10pt', lineHeight: '1.6', color: '#222' }}>
              {allSkills.join(' · ')}
            </p>
          </div>
        )}

        {/* Achievements */}
        {profile.achievements?.length > 0 && (
          <div>
            <SectionHeader title="Achievements" />
            <ul style={{ paddingLeft: '14px', margin: 0 }}>
              {profile.achievements.filter(Boolean).map((ach, i) => (
                <li key={i} style={{ fontSize: '10pt', marginBottom: '2px', listStyleType: '\'•  \'' }}>{ach}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* ── Sidebar (no-print) ── */}
      <div className="w-full lg:w-60 shrink-0 space-y-4 no-print sticky top-8">
        {/* Export */}
        <div className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm">
          <h3 className="font-semibold text-gray-800 text-sm mb-1">Ready to export?</h3>
          <p className="text-xs text-gray-500 mb-4">Toggle bullets between AI and original, then export as PDF.</p>
          <button
            onClick={onExport}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4" /> Export PDF
          </button>
        </div>

        {/* Tips */}
        <div className="p-4 rounded-xl border border-gray-100 bg-gray-50">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-2">Tips</p>
          <ul className="text-xs text-gray-400 space-y-1.5 list-disc pl-4">
            <li>Toggle each bullet to switch between original and AI version</li>
            <li>Green keywords = present in resume</li>
            <li>Red keywords = consider adding manually</li>
            <li>Export prints only the white paper</li>
          </ul>
        </div>

        <button
          onClick={() => window.history.back()}
          className="w-full flex items-center justify-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors py-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to AI Insights
        </button>
      </div>
    </div>
  );
};
