import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

#!/usr/bin/env python3
"""
ApplyBridge -- Main CLI Entry Point
Usage:
    python main.py scrape [--query "..."] [--location "..."] [--source google_jobs]
    python main.py search <query>
    python main.py stats
    python main.py list [--source google_jobs] [--status new] [--limit 20]
"""

import argparse
import os
import sys
import os
import asyncio
import logging

# Fix Windows console encoding for Rich output
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from db.database import init_db, search_jobs, get_all_jobs, get_job_stats, update_job_status
from workers.scraper import scrape_all, print_scrape_summary
from utils.filters import filter_jobs

console = Console()


def cmd_scrape(args: argparse.Namespace) -> None:
    """Run scrapers and store results."""
    console.print(Panel(
        f"[bold]>> Scraping jobs[/bold]\n"
        f"   Query: [cyan]{args.query}[/cyan]\n"
        f"   Location: [cyan]{args.location}[/cyan]\n"
        f"   Sources: [cyan]{args.source or 'all'}[/cyan]",
        title="ApplyBridge Scraper",
        border_style="blue",
    ))

    sources = [args.source] if args.source else None
    new_count = asyncio.run(scrape_all(query=args.query, location=args.location, sources=sources))

    if new_count > 0:
        console.print(f"\n[bold green][OK] Done! {new_count} new raw jobs added.[/bold green]")
        console.print("[dim]Run 'python main.py enrich' to extract skills and classify jobs.[/dim]")
    else:
        console.print("\n[yellow][OK] Scrape complete, but no new jobs were found.[/yellow]")
    print_scrape_summary()


def _handle_enrich(args: argparse.Namespace) -> None:
    """Extract skills and classify jobs."""
    from workers.enricher import process_enrichment_queue
    asyncio.run(process_enrichment_queue())

def _handle_dedup(args: argparse.Namespace) -> None:
    """Run batch deduplication."""
    from utils.dedup import run_batch_dedup
    run_batch_dedup()


def cmd_search(args: argparse.Namespace) -> None:
    """Full-text search across stored jobs."""
    init_db()
    results = search_jobs(args.query, limit=args.limit)

    if not results:
        console.print(f"[yellow]No results for '{args.query}'[/yellow]")
        return

    _print_jobs_table(results, title=f"Search: '{args.query}'")


def cmd_list(args: argparse.Namespace) -> None:
    """List stored jobs with optional filtering."""
    init_db()
    jobs = get_all_jobs(source=args.source, status=args.status, limit=args.limit)

    if args.filter:
        jobs = filter_jobs(jobs, min_score=args.min_score)

    if not jobs:
        console.print("[yellow]No jobs found matching criteria.[/yellow]")
        return

    _print_jobs_table(jobs, title="Job Listings")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show database statistics."""
    init_db()
    print_scrape_summary()


def cmd_status(args: argparse.Namespace) -> None:
    """Update a job's application status."""
    init_db()
    update_job_status(args.job_id, args.status)
    console.print(f"[green][OK] Job #{args.job_id} status -> {args.status}[/green]")


def _print_jobs_table(jobs: list[dict], title: str = "Jobs") -> None:
    """Pretty-print a list of jobs as a rich table."""
    table = Table(title=title, show_header=True, show_lines=True)
    table.add_column("ID", style="dim", width=5)
    table.add_column("Title", style="bold cyan", min_width=25, max_width=40)
    table.add_column("Company", style="green", min_width=15, max_width=25)
    table.add_column("Location", min_width=10, max_width=20)
    table.add_column("Source", style="magenta", width=12)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Status", width=10)

    for job in jobs:
        score = job.get("match_score", 0)
        score_str = f"{score:.0%}" if score else "—"
        score_style = "green" if score >= 0.5 else "yellow" if score >= 0.3 else "dim"

        table.add_row(
            str(job.get("id", "")),
            job.get("title", "")[:40],
            job.get("company", "")[:25],
            job.get("location", "")[:20],
            job.get("source", ""),
            f"[{score_style}]{score_str}[/{score_style}]",
            job.get("status", "new"),
        )

    console.print(table)
    console.print(f"[dim]Showing {len(jobs)} job(s)[/dim]\n")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="applybridge",
        description="🌉 ApplyBridge — AI-Powered Job Search Automation",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── scrape ───────────────────────────────────────────────────────────
    p_scrape = subparsers.add_parser("scrape", help="Scrape jobs from configured sources")
    p_scrape.add_argument("-q", "--query", default="",
                          help="Search query (default: empty for full ingestion)")
    p_scrape.add_argument("-l", "--location", default="",
                          help="Location filter (default: empty)")
    p_scrape.add_argument("-s", "--source", default=None,
                          help="Specific source to scrape (google_jobs, internshala)")
    p_scrape.set_defaults(func=cmd_scrape)

    # ── enrich ───────────────────────────────────────────────────────────
    p_enrich = subparsers.add_parser("enrich", help="Run the background enrichment worker")
    p_enrich.set_defaults(func=_handle_enrich)

    # ── dedup ────────────────────────────────────────────────────────────
    p_dedup = subparsers.add_parser("dedup", help="Run batch fuzzy deduplication across the entire database")
    p_dedup.set_defaults(func=_handle_dedup)

    # ── search ───────────────────────────────────────────────────────────
    p_search = subparsers.add_parser("search", help="Full-text search stored jobs")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=20, help="Max results")
    p_search.set_defaults(func=cmd_search)

    # ── list ─────────────────────────────────────────────────────────────
    p_list = subparsers.add_parser("list", help="List stored jobs")
    p_list.add_argument("-s", "--source", default=None, help="Filter by source")
    p_list.add_argument("--status", default=None, help="Filter by status")
    p_list.add_argument("--limit", type=int, default=20, help="Max results")
    p_list.add_argument("--filter", action="store_true", help="Apply skill matching filter")
    p_list.add_argument("--min-score", type=float, default=0.3, help="Minimum match score")
    p_list.set_defaults(func=cmd_list)

    # ── stats ────────────────────────────────────────────────────────────
    p_stats = subparsers.add_parser("stats", help="Show database statistics")
    p_stats.set_defaults(func=cmd_stats)

    # ── status ───────────────────────────────────────────────────────────
    p_status = subparsers.add_parser("status", help="Update a job's status")
    p_status.add_argument("job_id", type=int, help="Job ID")
    p_status.add_argument("status", choices=["new", "applied", "rejected", "interview", "offer"],
                          help="New status")
    p_status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        console.print(Panel(
            "[bold cyan]ApplyBridge[/bold cyan]\n"
            "[dim]AI-Powered Job Search Automation[/dim]\n\n"
            "Commands:\n"
            "  [green]scrape[/green]   - Scrape jobs from web sources\n"
            "  [green]search[/green]   - Full-text search stored jobs\n"
            "  [green]list[/green]     - List and filter jobs\n"
            "  [green]stats[/green]    - View database statistics\n"
            "  [green]status[/green]   - Update job application status\n\n"
            "Run [cyan]python main.py <command> --help[/cyan] for details.",
            title="Welcome",
            border_style="blue",
        ))
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
