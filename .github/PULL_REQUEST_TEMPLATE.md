## What does this PR do?
<!-- Describe your changes in detail here -->

## Which scraper(s) are affected?
<!-- List the adapters, ATS, or Playwright scripts touched by this PR (e.g., lever.py, wellfound.py) -->

## Jobs returned in test run
<!-- Paste the output or logs of your local test run showing how many jobs were successfully fetched -->
```text

```

## Checklist
- [ ] Checked: No mock data or fake job listings are included
- [ ] Checked: No hardcoded ATS tokens or company slugs (parameters are dynamically passed)
- [ ] Checked: Rate limiting and delay rules are respected (`REQUEST_DELAY` config utilized)
