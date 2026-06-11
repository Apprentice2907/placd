import React from 'react';
import type { ResumeProfile } from '../../types/resume';
import { Plus, Trash2 } from 'lucide-react';

interface ProfileFormProps {
  profile: ResumeProfile;
  onChange: (profile: ResumeProfile) => void;
  onNext: () => void;
}

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
    onChange({
      ...profile,
      experience: profile.experience.filter(e => e.id !== id)
    });
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
    onChange({
      ...profile,
      projects: profile.projects.filter(p => p.id !== id)
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in max-w-3xl mx-auto pb-10">
      <section>
        <h2 className="text-xl font-bold border-b border-neutral-200 pb-2 mb-4">Personal Info</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input className="input-field" placeholder="Full Name" value={profile.personal.name} onChange={e => updatePersonal('name', e.target.value)} />
          <input className="input-field" placeholder="Email" value={profile.personal.email} onChange={e => updatePersonal('email', e.target.value)} />
          <input className="input-field" placeholder="Phone" value={profile.personal.phone} onChange={e => updatePersonal('phone', e.target.value)} />
          <input className="input-field" placeholder="Location" value={profile.personal.location} onChange={e => updatePersonal('location', e.target.value)} />
          <input className="input-field" placeholder="LinkedIn URL" value={profile.personal.linkedin} onChange={e => updatePersonal('linkedin', e.target.value)} />
          <input className="input-field" placeholder="GitHub URL" value={profile.personal.github} onChange={e => updatePersonal('github', e.target.value)} />
        </div>
      </section>

      <section>
        <div className="flex justify-between items-center border-b border-neutral-200 pb-2 mb-4">
          <h2 className="text-xl font-bold">Experience</h2>
          <button onClick={addExperience} className="text-indigo-600 text-sm font-bold flex items-center gap-1"><Plus className="w-4 h-4"/> Add</button>
        </div>
        <div className="space-y-6">
          {profile.experience.map(exp => (
            <div key={exp.id} className="p-4 border rounded-lg space-y-4 relative bg-neutral-50 dark:bg-neutral-900/50">
              <button onClick={() => removeExperience(exp.id)} className="absolute top-4 right-4 text-red-500 hover:bg-red-50 p-1 rounded"><Trash2 className="w-4 h-4"/></button>
              <div className="grid grid-cols-2 gap-4 mr-8">
                <input className="input-field" placeholder="Company" value={exp.company} onChange={e => updateExperience(exp.id, 'company', e.target.value)} />
                <input className="input-field" placeholder="Role" value={exp.role} onChange={e => updateExperience(exp.id, 'role', e.target.value)} />
                <input className="input-field" placeholder="Start Date" value={exp.start} onChange={e => updateExperience(exp.id, 'start', e.target.value)} />
                <input className="input-field" placeholder="End Date" value={exp.end} onChange={e => updateExperience(exp.id, 'end', e.target.value)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-semibold">Bullets (One per line)</label>
                <textarea className="input-field min-h-[100px]" placeholder="One bullet per line..." value={exp.bullets.join('\n')} onChange={e => updateExperience(exp.id, 'bullets', e.target.value.split('\n'))} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="flex justify-between items-center border-b border-neutral-200 pb-2 mb-4">
          <h2 className="text-xl font-bold">Projects</h2>
          <button onClick={addProject} className="text-indigo-600 text-sm font-bold flex items-center gap-1"><Plus className="w-4 h-4"/> Add</button>
        </div>
        <div className="space-y-6">
          {profile.projects.map(proj => (
            <div key={proj.id} className="p-4 border rounded-lg space-y-4 relative bg-neutral-50 dark:bg-neutral-900/50">
              <button onClick={() => removeProject(proj.id)} className="absolute top-4 right-4 text-red-500 hover:bg-red-50 p-1 rounded"><Trash2 className="w-4 h-4"/></button>
              <div className="grid grid-cols-2 gap-4 mr-8">
                <input className="input-field" placeholder="Project Name" value={proj.name} onChange={e => updateProject(proj.id, 'name', e.target.value)} />
                <input className="input-field" placeholder="Link" value={proj.link} onChange={e => updateProject(proj.id, 'link', e.target.value)} />
                <input className="input-field col-span-2" placeholder="Tech Stack (comma separated)" value={proj.stack.join(', ')} onChange={e => updateProject(proj.id, 'stack', e.target.value.split(',').map(s=>s.trim()))} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-semibold">Bullets (One per line)</label>
                <textarea className="input-field min-h-[100px]" placeholder="One bullet per line..." value={proj.bullets.join('\n')} onChange={e => updateProject(proj.id, 'bullets', e.target.value.split('\n'))} />
              </div>
            </div>
          ))}
        </div>
      </section>
      
      <div className="flex justify-end pt-4">
        <button onClick={onNext} className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-lg font-bold transition-colors">Continue to Job Target →</button>
      </div>

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
