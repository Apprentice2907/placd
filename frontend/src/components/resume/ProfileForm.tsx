import React from 'react';
import type { ResumeProfile } from '../../types/resume';
import { Plus, Trash2, User, Briefcase, FolderOpen } from 'lucide-react';

interface ProfileFormProps {
  profile: ResumeProfile;
  onChange: (profile: ResumeProfile) => void;
  onNext: () => void;
}

const inputClass = `
  w-full px-3 py-2.5 rounded-lg border border-white/10 bg-white/5 text-white text-sm
  placeholder:text-white/25 focus:outline-none focus:border-purple-500/60 focus:bg-white/8
  transition-all duration-200
`.trim();

const cardClass = `
  p-5 rounded-xl border border-white/10 bg-white/[0.03] space-y-4 relative
`.trim();

const sectionHeadingClass = `
  text-base font-semibold text-white/90 flex items-center gap-2 mb-4
`.trim();

export const ProfileForm: React.FC<ProfileFormProps> = ({ profile, onChange, onNext }) => {
  const updatePersonal = (field: keyof ResumeProfile['personal'], value: string) => {
    onChange({ ...profile, personal: { ...profile.personal, [field]: value } });
  };

  const addExperience = () => {
    onChange({
      ...profile,
      experience: [...profile.experience, { id: `exp_${Date.now()}`, company: '', role: '', start: '', end: '', location: '', bullets: [''] }]
    });
  };

  const updateExperience = (id: string, field: string, value: any) => {
    onChange({
      ...profile,
      experience: profile.experience.map(e => e.id === id ? { ...e, [field]: value } : e)
    });
  };

  const removeExperience = (id: string) => {
    onChange({ ...profile, experience: profile.experience.filter(e => e.id !== id) });
  };

  const addProject = () => {
    onChange({
      ...profile,
      projects: [...profile.projects, { id: `proj_${Date.now()}`, name: '', stack: [], link: '', bullets: [''] }]
    });
  };

  const updateProject = (id: string, field: string, value: any) => {
    onChange({
      ...profile,
      projects: profile.projects.map(p => p.id === id ? { ...p, [field]: value } : p)
    });
  };

  const removeProject = (id: string) => {
    onChange({ ...profile, projects: profile.projects.filter(p => p.id !== id) });
  };

  return (
    <div className="space-y-8 max-w-3xl mx-auto pb-12 animate-in fade-in">

      {/* Paste existing resume */}
      <section>
        <h2 className={sectionHeadingClass}>
          <span className="w-5 h-5 rounded bg-purple-500/20 flex items-center justify-center text-purple-400 text-xs">✦</span>
          Paste Existing Resume
          <span className="ml-1 text-xs font-normal text-white/30 tracking-normal">(Optional)</span>
        </h2>
        <div className={cardClass}>
          <p className="text-sm text-white/40 mb-3">
            Paste your existing resume — our AI will use it as context. You can skip the manual fields below.
          </p>
          <textarea
            className={`${inputClass} min-h-[130px]`}
            placeholder="Paste your full resume text here..."
            value={profile.raw_resume_text || ''}
            onChange={e => onChange({ ...profile, raw_resume_text: e.target.value })}
          />
        </div>
      </section>

      {/* Personal Info */}
      <section>
        <h2 className={sectionHeadingClass}>
          <User className="w-4 h-4 text-purple-400" />
          Personal Info
        </h2>
        <div className={cardClass}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input className={inputClass} placeholder="Full Name" value={profile.personal.name} onChange={e => updatePersonal('name', e.target.value)} />
            <input className={inputClass} placeholder="Email" value={profile.personal.email} onChange={e => updatePersonal('email', e.target.value)} />
            <input className={inputClass} placeholder="Phone" value={profile.personal.phone} onChange={e => updatePersonal('phone', e.target.value)} />
            <input className={inputClass} placeholder="Location (City, State)" value={profile.personal.location} onChange={e => updatePersonal('location', e.target.value)} />
            <input className={inputClass} placeholder="LinkedIn URL" value={profile.personal.linkedin} onChange={e => updatePersonal('linkedin', e.target.value)} />
            <input className={inputClass} placeholder="GitHub URL" value={profile.personal.github} onChange={e => updatePersonal('github', e.target.value)} />
          </div>
        </div>
      </section>

      {/* Experience */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeadingClass + ' mb-0'}>
            <Briefcase className="w-4 h-4 text-purple-400" />
            Experience
          </h2>
          <button
            onClick={addExperience}
            className="flex items-center gap-1.5 text-xs font-semibold text-purple-400 hover:text-purple-300 border border-purple-500/30 hover:border-purple-400/50 px-3 py-1.5 rounded-lg transition-all duration-200 bg-purple-500/5 hover:bg-purple-500/10"
          >
            <Plus className="w-3.5 h-3.5" /> Add
          </button>
        </div>
        <div className="space-y-4">
          {profile.experience.map(exp => (
            <div key={exp.id} className={cardClass}>
              <button
                onClick={() => removeExperience(exp.id)}
                className="absolute top-4 right-4 text-white/20 hover:text-red-400 transition-colors p-1 rounded"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <div className="grid grid-cols-2 gap-3 mr-8">
                <input className={inputClass} placeholder="Company" value={exp.company} onChange={e => updateExperience(exp.id, 'company', e.target.value)} />
                <input className={inputClass} placeholder="Role / Title" value={exp.role} onChange={e => updateExperience(exp.id, 'role', e.target.value)} />
                <input className={inputClass} placeholder="Start (e.g. Jun 2022)" value={exp.start} onChange={e => updateExperience(exp.id, 'start', e.target.value)} />
                <input className={inputClass} placeholder="End (or Present)" value={exp.end} onChange={e => updateExperience(exp.id, 'end', e.target.value)} />
              </div>
              <div>
                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider block mb-1.5">Bullets (one per line)</label>
                <textarea
                  className={`${inputClass} min-h-[90px]`}
                  placeholder="• Led backend migration reducing latency by 40%..."
                  value={exp.bullets.join('\n')}
                  onChange={e => updateExperience(exp.id, 'bullets', e.target.value.split('\n'))}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Projects */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className={sectionHeadingClass + ' mb-0'}>
            <FolderOpen className="w-4 h-4 text-purple-400" />
            Projects
          </h2>
          <button
            onClick={addProject}
            className="flex items-center gap-1.5 text-xs font-semibold text-purple-400 hover:text-purple-300 border border-purple-500/30 hover:border-purple-400/50 px-3 py-1.5 rounded-lg transition-all duration-200 bg-purple-500/5 hover:bg-purple-500/10"
          >
            <Plus className="w-3.5 h-3.5" /> Add
          </button>
        </div>
        <div className="space-y-4">
          {profile.projects.map(proj => (
            <div key={proj.id} className={cardClass}>
              <button
                onClick={() => removeProject(proj.id)}
                className="absolute top-4 right-4 text-white/20 hover:text-red-400 transition-colors p-1 rounded"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <div className="grid grid-cols-2 gap-3 mr-8">
                <input className={inputClass} placeholder="Project Name" value={proj.name} onChange={e => updateProject(proj.id, 'name', e.target.value)} />
                <input className={inputClass} placeholder="GitHub / Link" value={proj.link} onChange={e => updateProject(proj.id, 'link', e.target.value)} />
                <input className={`${inputClass} col-span-2`} placeholder="Tech Stack (comma separated, e.g. React, Node.js, PostgreSQL)" value={proj.stack.join(', ')} onChange={e => updateProject(proj.id, 'stack', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} />
              </div>
              <div>
                <label className="text-xs font-semibold text-white/40 uppercase tracking-wider block mb-1.5">Bullets (one per line)</label>
                <textarea
                  className={`${inputClass} min-h-[90px]`}
                  placeholder="• Built and deployed full-stack app handling 10k+ daily users..."
                  value={proj.bullets.join('\n')}
                  onChange={e => updateProject(proj.id, 'bullets', e.target.value.split('\n'))}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="flex justify-end pt-2">
        <button
          onClick={onNext}
          className="px-8 py-3 rounded-xl font-semibold text-sm text-white bg-purple-600 hover:bg-purple-500 transition-all duration-200 shadow-[0_0_20px_rgba(168,85,247,0.3)] hover:shadow-[0_0_28px_rgba(168,85,247,0.45)]"
        >
          Continue to Job Target →
        </button>
      </div>
    </div>
  );
};
