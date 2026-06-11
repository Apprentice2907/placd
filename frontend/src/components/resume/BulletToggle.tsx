import React, { useMemo } from 'react';
import { Sparkles, History } from 'lucide-react';
import { diff_match_patch } from 'diff-match-patch';

interface BulletToggleProps {
  originalBullets: string[];
  aiBullets: string[];
  selection: 'original' | 'ai';
  onToggle: (v: 'original' | 'ai') => void;
}

export const BulletToggle: React.FC<BulletToggleProps> = ({ originalBullets, aiBullets, selection, onToggle }) => {
  const diffs = useMemo(() => {
    if (selection !== 'ai') return null;
    const dmp = new diff_match_patch();
    
    return aiBullets.map((aiBullet, i) => {
      const orig = originalBullets[i] || '';
      const diff = dmp.diff_main(orig, aiBullet);
      dmp.diff_cleanupSemantic(diff);
      return diff;
    });
  }, [originalBullets, aiBullets, selection]);

  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg overflow-hidden my-2 text-left">
      <div className="flex bg-neutral-100 dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
        <button 
          onClick={() => onToggle('ai')}
          className={`flex-1 py-1.5 text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${selection === 'ai' ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400 border-b-2 border-indigo-500' : 'text-neutral-500 hover:text-black dark:hover:text-white'}`}
        >
          <Sparkles className="w-3.5 h-3.5"/> Optimized
        </button>
        <button 
          onClick={() => onToggle('original')}
          className={`flex-1 py-1.5 text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${selection === 'original' ? 'bg-white dark:bg-neutral-950 text-black dark:text-white border-b-2 border-neutral-400' : 'text-neutral-500 hover:text-black dark:hover:text-white'}`}
        >
          <History className="w-3.5 h-3.5"/> Original
        </button>
      </div>
      <div className="p-3 bg-white dark:bg-neutral-950 text-sm space-y-1.5">
        {selection === 'ai' && diffs ? (
          diffs.map((diffArray, i) => (
            <div key={i} className="flex items-start gap-2 leading-relaxed">
              <span className="text-neutral-400 mt-0.5">•</span>
              <span>
                {diffArray.map((part, j) => {
                  const [op, text] = part;
                  if (op === 1) return <ins key={j} className="text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30 no-underline font-medium">{text}</ins>;
                  if (op === -1) return <del key={j} className="text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30 line-through opacity-70">{text}</del>;
                  
                  // Check for our [ADD METRIC HERE] placeholder
                  if (op === 0 && text.includes('[ADD METRIC HERE]')) {
                    const parts = text.split('[ADD METRIC HERE]');
                    return (
                      <span key={j}>
                        {parts.map((p, idx) => (
                          <React.Fragment key={idx}>
                            {p}
                            {idx < parts.length - 1 && (
                              <span className="bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-400 font-bold px-1 rounded mx-1">[ADD METRIC HERE]</span>
                            )}
                          </React.Fragment>
                        ))}
                      </span>
                    );
                  }
                  
                  return <span key={j}>{text}</span>;
                })}
              </span>
            </div>
          ))
        ) : (
          originalBullets.map((b, i) => (
            <div key={i} className="flex items-start gap-2 leading-relaxed">
              <span className="text-neutral-400 mt-0.5">•</span>
              <span>{b}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
