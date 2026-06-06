import httpx
from bs4 import BeautifulSoup
import json

r = httpx.get('https://www.google.com/about/careers/applications/jobs/results/')
soup = BeautifulSoup(r.text, 'html.parser')
jobs = soup.find_all("div", class_="sMn82b") # Just guessing, let's just find titles.
# Actually let's just print the script tags to see if there is JSON.
scripts = soup.find_all("script")
for s in scripts:
    if s.string and 'Software Engineer' in s.string:
        print("Found JSON script!")
        print(s.string[:200])

print("Titles:")
for h3 in soup.find_all("h3"):
    print(h3.text)
