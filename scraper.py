import requests
from bs4 import BeautifulSoup
import pandas as pd
import sys
import re
from datetime import datetime
from typing import List, Dict, Optional

VALID_ESTATE_TYPES = ["byty", "domy"]

VALID_REGIONS = [
    "praha",
    "jihocesky-kraj",
    "jihomoravsky-kraj",
    "karlovarsky-kraj",
    "kralovehradecky-kraj",
    "liberecky-kraj",
    "moravskoslezsky-kraj",
    "olomoucky-kraj",
    "pardubicky-kraj",
    "plzensky-kraj",
    "stredocesky-kraj",
    "ustecky-kraj",
    "vysocina",
    "zlinsky-kraj",
]

VALID_FLAT_TYPES = [
    "1+kk",
    "1+1",
    "2+kk",
    "2+1",
    "3+kk",
    "3+1",
    "4+kk",
    "4+1",
    "5+kk",
    "5+1",
    "6 a více",
    "Atypický",
]

# heades to mimic browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}


def validate_args(estate_type: str, region: str, pages: str):
    """Validates command-line arguments"""
    if estate_type not in VALID_ESTATE_TYPES:
        raise ValueError(
            f"Invalid estate type: {estate_type}. Allowed: {VALID_ESTATE_TYPES}"
        )

    if region not in VALID_REGIONS:
        raise ValueError(f"Invalid region: {region}. Allowed: {VALID_REGIONS}")

    if not pages.isdigit() or int(pages) <= 0:
        raise ValueError(f"Pages must be a positive integer, got: {pages}")

    return estate_type, region, int(pages)


def clean_price(price_text: str) -> Optional[int]:
    """Extracts integer price from text"""
    price_numbers = re.findall(r"\d+", price_text)
    return int("".join(price_numbers)) if price_numbers else None


def parse_house(
    title: str, location: str, price: int, link: str, image_url: str
) -> Dict[str, str | int]:
    """Parses a house listing"""
    match = re.search(r"(\d+)\s*m².*?pozemek\s*(\d+)\s*m²", title)
    usable_area = int(match.group(1)) if match else None
    land_size = int(match.group(2)) if match else None

    return {
        "Title": title,
        "Property Type": "House",
        "Usable Area (m²)": usable_area,
        "Land Size (m²)": land_size,
        "Location": location,
        "Price (CZK)": price,
        "URL": link,
        "Image": image_url,
    }


def parse_flat(
    title: str, location: str, price: int, link: str, image_url: str
) -> Dict[str, str | int]:
    """Parses a flat listing"""
    match_area = re.search(r"(\d+)\s*m²", title)
    usable_area = int(match_area.group(1)) if match_area else None

    flat_type = None
    for f_type in VALID_FLAT_TYPES:
        if f_type in title:
            flat_type = f_type
            break

    return {
        "Title": title,
        "Property Type": "Flat",
        "Usable Area (m²)": usable_area,
        "Flat Type": flat_type,
        "Location": location,
        "Price (CZK)": price,
        "URL": link,
        "Image": image_url,
    }


def parse_listing(
    listing: BeautifulSoup, estate_type: str
) -> Optional[Dict[str, str | int]]:
    """Parses a single listing"""
    title_tag = listing.select_one("p.css-d7upve")
    location_tag = listing.select("p.css-d7upve")
    price_tag = listing.select_one("p.css-ca9wwd")
    link_tag = listing.select_one("a[href]")
    img_tag = listing.select_one("img.css-1q0j11k")

    if title_tag and location_tag and price_tag and link_tag:
        title = title_tag.text.strip()
        location = location_tag[1].text.strip() if len(location_tag) > 1 else "Unknown"
        price = clean_price(price_tag.text.strip())
        link = "https://www.sreality.cz" + link_tag["href"]
        image_url = "https:" + img_tag["src"] if img_tag else "No image"

        if estate_type == "domy":
            return parse_house(title, location, price, link, image_url)
        elif estate_type == "byty":
            return parse_flat(title, location, price, link, image_url)

    return None


def get_listings(
    estate_type: str, region: str, page: int
) -> List[Dict[str, str | int]]:
    """Fetches listings from Sreality.cz"""
    url = f"https://www.sreality.cz/hledani/prodej/{estate_type}/{region}?page={page}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Failed to retrieve data (Status Code: {response.status_code})")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    listings = []

    for item in soup.select("ul > li"):
        parsed_listing = parse_listing(item, estate_type)
        if parsed_listing:
            listings.append(parsed_listing)

    return listings


def scrape_multiple_pages(
    estate_type: str, region: str, pages: int
) -> List[Dict[str, str | int]]:
    """Scrapes multiple pages of listings"""
    all_listings = []
    for page in range(1, pages + 1):
        print(f"Scraping page {page}...")
        listings = get_listings(estate_type, region, page)
        if not listings:
            break
        all_listings.extend(listings)

    return all_listings


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python scraper.py <estate_type> <region> <pages>")
        print("Example: python scraper.py byty praha 3")
        sys.exit(1)

    try:
        estate_type, region, num_pages = validate_args(
            sys.argv[1], sys.argv[2], sys.argv[3]
        )
        print(f"✅ Scraping {num_pages} pages of {estate_type} in {region}...")

        data = scrape_multiple_pages(estate_type, region, num_pages)

        if data:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"sreality_{estate_type}_{region}_{timestamp}.csv"

            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding="utf-8")
            print(f"Data saved to {filename}")
        else:
            print("No data found.")
    except ValueError as e:
        print(e)
        sys.exit(1)
