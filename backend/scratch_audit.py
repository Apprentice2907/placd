import os
import ast

def audit_scraper(folder):
    adapter_path = os.path.join("d:/Job Searcher/Placd/backend/scrapers", folder, "adapter.py")
    if not os.path.exists(adapter_path):
        return None
    
    with open(adapter_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    has_unified_adapter = False
    has_fetch_jobs = False
    has_main = "__main__" in content
    method = "Unknown"
    if "playwright" in content.lower():
        method = "Playwright"
    elif "graphql" in content.lower():
        method = "GraphQL"
    elif "httpx" in content.lower() or "json" in content.lower():
        method = "JSON API"
    elif "bs4" in content.lower() or "beautifulsoup" in content.lower():
        method = "HTML Scraping"
    elif "curl_cffi" in content.lower():
        method = "curl_cffi"

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "UnifiedAdapter":
                    has_unified_adapter = True
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef) and item.name == "fetch_jobs":
                    has_fetch_jobs = True
    
    pagination = "PARTIAL"
    if "offset" in content.lower() and "while" in content.lower() or "page" in content.lower() and "while" in content.lower():
        pagination = "YES"
    elif "for category in" in content.lower() or "for query in" in content.lower() or "for term in" in content.lower():
        pagination = "PARTIAL"
    elif "sweep" in content.lower() or "paginate" in content.lower():
         pagination = "YES"
    else:
        pagination = "NO"
        
    status = "NEEDS FIX"
    if not has_unified_adapter or not has_fetch_jobs or not has_main or pagination == "NO":
        status = "NEEDS FIX"
    if method == "Playwright" and folder in ["google", "meta"]:
        status = "REWRITE"
        
    return {
        "scraper": folder,
        "method": method,
        "unified_adapter": "YES" if has_unified_adapter else "NO",
        "pagination": pagination,
        "status": status
    }

folders = [f for f in os.listdir("d:/Job Searcher/Placd/backend/scrapers") if os.path.isdir(os.path.join("d:/Job Searcher/Placd/backend/scrapers", f))]

print(f"{'Scraper':<15} | {'Method':<15} | {'UnifiedAdapter':<15} | {'Pagination':<12} | {'Status'}")
print("-" * 15 + "-|-" + "-" * 15 + "-|-" + "-" * 15 + "-|-" + "-" * 12 + "-|-" + "-" * 8)

for folder in folders:
    res = audit_scraper(folder)
    if res:
        print(f"{res['scraper']:<15} | {res['method']:<15} | {res['unified_adapter']:<15} | {res['pagination']:<12} | {res['status']}")

