from playwright.async_api import async_playwright

class JDScrapeFailed(Exception):
    pass

async def scrape_jd(url: str) -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to URL with a 15-second timeout, wait for networkidle
            await page.goto(url, timeout=15000, wait_until="networkidle")
            
            # Evaluate script to extract clean text from the body
            # Strips out scripts, styles, noscript, etc.
            text = await page.evaluate("""() => {
                const elementsToRemove = document.querySelectorAll('script, style, noscript, nav, footer, header, iframe');
                elementsToRemove.forEach(el => el.remove());
                return document.body ? document.body.innerText : '';
            }""")
            
            await browser.close()
            
            cleaned_text = text.strip() if text else ""
            
            if len(cleaned_text) < 200:
                raise JDScrapeFailed("Extracted text is too short, likely blocked or empty.")
                
            return cleaned_text
            
    except Exception as e:
        # Catch any exception (timeout, blocked, etc.) and raise JDScrapeFailed
        raise JDScrapeFailed(f"Failed to scrape JD: {str(e)}")
