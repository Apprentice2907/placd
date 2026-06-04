import os
import re

files_to_update = [
    "D:/Job Searcher/Placd/frontend/src/components/JobCard.tsx",
    "D:/Job Searcher/Placd/frontend/src/components/OpportunityCard.tsx",
    "D:/Job Searcher/Placd/frontend/src/components/JobFilters.tsx",
    "D:/Job Searcher/Placd/frontend/src/components/OpportunityFilters.tsx",
    "D:/Job Searcher/Placd/frontend/src/pages/HiringPage.tsx",
    "D:/Job Searcher/Placd/frontend/src/pages/OpportunitiesPage.tsx",
    "D:/Job Searcher/Placd/frontend/src/pages/HiringCalendarPage.tsx"
]

replacements = [
    (r'bg-white dark:bg-neutral-900', 'bg-[var(--bg-card)]'),
    (r'bg-neutral-50 dark:bg-\[\#0a0a0a\]', 'bg-[var(--bg-primary)]'),
    (r'bg-neutral-50 dark:bg-neutral-900', 'bg-[var(--bg-primary)]'),
    (r'border-neutral-200 dark:border-neutral-800', 'border-[var(--border-color)]'),
    (r'border-neutral-200 dark:border-neutral-700', 'border-[var(--border-color)]'),
    (r'border-neutral-300 dark:border-neutral-700', 'border-[var(--border-color)]'),
    (r'text-neutral-900 dark:text-white', 'text-[var(--text-primary)]'),
    (r'text-neutral-900 dark:text-neutral-100', 'text-[var(--text-primary)]'),
    (r'text-neutral-500 dark:text-neutral-400', 'text-[var(--text-secondary)]'),
    (r'text-neutral-600 dark:text-neutral-400', 'text-[var(--text-secondary)]'),
    (r'bg-neutral-100 dark:bg-neutral-800', 'bg-[var(--bg-secondary)]'),
    (r'bg-neutral-100 dark:bg-neutral-700', 'bg-[var(--bg-secondary)]'),
    (r'hover:bg-neutral-50 dark:hover:bg-neutral-800', 'hover:bg-[var(--bg-secondary)]'),
    (r'hover:bg-neutral-50 dark:hover:bg-neutral-700', 'hover:bg-[var(--bg-secondary)]'),
    (r'text-neutral-600 dark:text-neutral-300', 'text-[var(--text-secondary)]'),
    (r'bg-indigo-50 dark:bg-indigo-900/30', 'bg-[var(--accent-purple)]/10'),
    (r'bg-indigo-50 dark:bg-indigo-500/10', 'bg-[var(--accent-purple)]/10'),
    (r'text-indigo-700 dark:text-indigo-300', 'text-[var(--accent-purple)]'),
    (r'text-indigo-600 dark:text-indigo-400', 'text-[var(--accent-purple)]'),
    (r'hover:text-indigo-700 dark:hover:text-indigo-300', 'hover:text-[var(--accent-purple)]'),
    (r'border-indigo-100 dark:border-indigo-500/20', 'border-[var(--accent-purple)]/20'),
]

for filepath in files_to_update:
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (does not exist)")
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
        
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")
    else:
        print(f"No changes for {filepath}")
