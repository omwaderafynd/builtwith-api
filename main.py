from fastapi import FastAPI, HTTPException, Query, Header, Depends
from typing import List, Dict, Union
import requests
from bs4 import BeautifulSoup
import urllib.parse
import ssl
import warnings

# === Ignore SSL warnings for scraping ===
warnings.filterwarnings("ignore")
ssl._create_default_https_context = ssl._create_unverified_context

app = FastAPI(title="BuiltWith Technology Scraper API", version="1.0")

# === Replace this key with your own secret key and use it via Render ENV VAR ===
import os
API_KEY = os.getenv("API_KEY", "default-secret-key")

# === Auth Dependency ===
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key.")

# === BuiltWith Scraper Functions ===
def get_builtwith_url(website_url: str) -> str:
    encoded_url = urllib.parse.quote(website_url, safe='')
    return f"https://builtwith.com/?{encoded_url}"

def fetch_technologies(builtwith_url: str) -> Union[str, List[Dict[str, str]]]:
    try:
        response = requests.get(builtwith_url, verify=False, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Error fetching BuiltWith page: {e}"

    soup = BeautifulSoup(response.text, 'html.parser')
    tech_rows = soup.find_all("div", class_="row mb-1 mt-1")
    technologies = []

    for row in tech_rows:
        try:
            name = row.find("h2").get_text(strip=True)
            description = row.find_all("p")[1].get_text(strip=True)
            categories = [a.get_text(strip=True) for a in row.find_all("a", class_="text-muted")]
            technologies.append({
                "Technology": name,
                "Description": description,
                "Categories": ", ".join(categories)
            })
        except Exception:
            continue

    return technologies

# === API Endpoint ===
@app.get("/get_tech", summary="Fetch technologies used by a website")
def get_tech(
    website_url: str = Query(..., description="Full website URL with https://"),
    _: str = Depends(verify_api_key)
):
    builtwith_url = get_builtwith_url(website_url)
    result = fetch_technologies(builtwith_url)

    if isinstance(result, str):
        raise HTTPException(status_code=500, detail=result)

    if not result:
        raise HTTPException(status_code=404, detail="No technologies found or BuiltWith layout changed.")

    return {
        "website": website_url,
        "builtwith_url": builtwith_url,
        "technologies_found": len(result),
        "technologies": result
    }
