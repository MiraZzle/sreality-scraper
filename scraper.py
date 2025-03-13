import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sys
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)

THREAD_COUNT = 10

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}


def validate_args(estate_type: str, region: str, pages: str):
    """
    Validates command-line arguments.

    Parameters:
        estate_type (str): The type of estate. Must be one of the allowed values: "byty" or "domy".
        region (str): The region to search in. It must be either a valid region from VALID_REGIONS or "all".
        pages (str): A string representing the number of pages to scrape; must be a positive integer.

    Returns:
        tuple: A tuple (estate_type, region, pages) where pages is converted to an integer.

    Raises:
        ValueError: If the estate type is invalid, region is invalid, or pages is not a positive integer.
    """
    logging.info(
        f"Validating arguments: estate_type={estate_type}, region={region}, pages={pages}"
    )
    if estate_type not in VALID_ESTATE_TYPES:
        logging.error(f"Invalid estate type: {estate_type}")
        raise ValueError(
            f"Invalid estate type: {estate_type}. Allowed: {VALID_ESTATE_TYPES}"
        )

    if region != "all" and region not in VALID_REGIONS:
        logging.error(f"Invalid region: {region}")
        raise ValueError(
            f"Invalid region: {region}. Allowed: {VALID_REGIONS} or 'all'."
        )

    if not pages.isdigit() or int(pages) <= 0:
        logging.error(f"Invalid pages parameter: {pages}")
        raise ValueError(f"Pages must be a positive integer, got: {pages}")

    logging.info("Arguments validated successfully.")
    return estate_type, region, int(pages)


def clean_price(price_text: str) -> Optional[int]:
    """
    Extracts integer price from text.

    Parameters:
        price_text (str): The text containing the price information.

    Returns:
        Optional[int]: The extracted price as an integer if found, otherwise None.
    """
    logging.debug(f"Cleaning price from text: {price_text}")
    price_numbers = re.findall(r"\d+", price_text)
    result = int("".join(price_numbers)) if price_numbers else None
    logging.debug(f"Extracted price: {result}")
    return result


def extract_listing_details(url: str) -> Dict[str, Optional[str]]:
    """
    Fetches additional details from an individual listing page.

    Parameters:
        url (str): URL of the listing page.

    Returns:
        Dict[str, Optional[str]]: A dictionary with keys "Region", "District", "City", "Energy Rank".
                                  Each value is a string if available, or None if not.
    """
    logging.info(f"Extracting listing details from URL: {url}")
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        logging.error(
            f"Failed to retrieve listing details. Status Code: {response.status_code} for URL: {url}"
        )
        return {"District": None, "Region": None, "City": None, "Energy Rank": None}

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract location breadcrumbs
    breadcrumbs = soup.select("#userweb-map-layout-scroll-content nav ol li a")
    location_parts = [crumb.text.strip() for crumb in breadcrumbs]

    region = location_parts[3] if len(location_parts) > 3 else None
    district = location_parts[4] if len(location_parts) > 4 else None
    city = location_parts[5] if len(location_parts) > 5 else None

    # Extract energy efficiency rating
    energy_rank_tag = soup.select_one(
        "#userweb-map-layout-scroll-content p.css-1sdpd03"
    )
    energy_rank = energy_rank_tag.text.strip() if energy_rank_tag else None

    details = {
        "Region": region,
        "District": district,
        "City": city,
        "Energy Rank": energy_rank,
    }
    logging.debug(f"Extracted details: {details}")
    return details


def parse_house(
    title: str, location: str, price: int, link: str, image_url: str
) -> Dict[str, str | int]:
    """
    Parses a house listing to extract relevant details.

    Parameters:
        title (str): The title of the listing, which may include area details.
        location (str): The location information from the listing.
        price (int): The price of the house.
        link (str): URL link to the detailed listing page.
        image_url (str): URL of the listing image.

    Returns:
        Dict[str, str | int]: A dictionary containing parsed details of the house listing.
    """
    logging.info(f"Parsing house listing with title: {title}")
    match = re.search(r"(\d+)\s*m².*?pozemek\s*(\d+)\s*m²", title)
    usable_area = int(match.group(1)) if match else None
    land_size = int(match.group(2)) if match else None

    # Fetch additional details
    extra_details = extract_listing_details(link)

    parsed = {
        "Title": title,
        "Property Type": "House",
        "Usable Area (m²)": usable_area,
        "Land Size (m²)": land_size,
        "Location": location,
        "Region": extra_details["Region"],
        "District": extra_details["District"],
        "City": extra_details["City"],
        "Energy Rank": extra_details["Energy Rank"],
        "Price (CZK)": price,
        "URL": link,
        "Image": image_url,
    }
    logging.debug(f"Parsed house listing: {parsed}")
    return parsed


def parse_flat(
    title: str, location: str, price: int, link: str, image_url: str
) -> Dict[str, str | int]:
    """
    Parses a flat listing to extract relevant details.

    Parameters:
        title (str): The title of the listing, which may include area and type details.
        location (str): The location information from the listing.
        price (int): The price of the flat.
        link (str): URL link to the detailed listing page.
        image_url (str): URL of the listing image.

    Returns:
        Dict[str, str | int]: A dictionary containing parsed details of the flat listing.
    """
    logging.info(f"Parsing flat listing with title: {title}")
    match = re.search(r"(\d+)\s*m²", title)
    usable_area = int(match.group(1)) if match else None

    flat_type = next((ftype for ftype in VALID_FLAT_TYPES if ftype in title), None)

    extra_details = extract_listing_details(link)

    parsed = {
        "Title": title,
        "Property Type": "Flat",
        "Usable Area (m²)": usable_area,
        "Flat Type": flat_type,
        "Location": location,
        "Region": extra_details["Region"],
        "District": extra_details["District"],
        "City": extra_details["City"],
        "Energy Rank": extra_details["Energy Rank"],
        "Price (CZK)": price,
        "URL": link,
        "Image": image_url,
    }
    logging.debug(f"Parsed flat listing: {parsed}")
    return parsed


def parse_listing(
    listing: BeautifulSoup, estate_type: str
) -> Optional[Dict[str, str | int]]:
    """
    Parses a single listing HTML element.

    Parameters:
        listing (BeautifulSoup): The BeautifulSoup object representing the listing element.
        estate_type (str): The type of estate ("byty" or "domy") to determine the parsing method.

    Returns:
        Optional[Dict[str, str | int]]: A dictionary with parsed listing details if successful,
                                         otherwise None if essential elements are missing.
    """
    logging.debug("Parsing individual listing element.")
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

    logging.warning("Listing element missing required fields; skipping listing.")
    return None


def get_listings(
    estate_type: str, region: str, page: int
) -> List[Dict[str, str | int]]:
    """
    Fetches listings from Sreality.cz for a given estate type, region, and page number.

    Parameters:
        estate_type (str): The type of estate to fetch (e.g., "byty", "domy").
        region (str): The region from which to fetch listings, or "all" for all regions.
        page (int): The page number to scrape.

    Returns:
        List[Dict[str, str | int]]: A list of dictionaries, each representing a listing.
    """
    logging.info(
        f"Fetching listings from page {page} for estate_type={estate_type} and region={region}"
    )
    url = (
        f"https://www.sreality.cz/hledani/prodej/{estate_type}/{region}?page={page}"
        if region != "all"
        else f"https://www.sreality.cz/hledani/prodej/{estate_type}?page={page}"
    )

    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        logging.error(
            f"Failed to retrieve data from {url} (Status Code: {response.status_code})"
        )
        print(f"Failed to retrieve data (Status Code: {response.status_code})")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    listings = []

    for item in soup.select("ul > li"):
        parsed_listing = parse_listing(item, estate_type)
        if parsed_listing:
            listings.append(parsed_listing)

    logging.info(f"Page {page} fetched with {len(listings)} listings.")
    return listings


def scrape_multiple_pages(
    estate_type: str, region: str, pages: int
) -> List[Dict[str, str | int]]:
    """
    Scrapes multiple pages of listings using parallel threads.

    Parameters:
        estate_type (str): The type of estate to scrape (e.g., "byty", "domy").
        region (str): The region to scrape listings from, or "all" for all regions.
        pages (int): The total number of pages to scrape.

    Returns:
        List[Dict[str, str | int]]: A list of dictionaries, each representing a listing from all scraped pages.
    """
    logging.info(
        f"Starting to scrape {pages} pages for estate_type={estate_type} and region={region}"
    )
    all_listings = []
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        futures = {
            executor.submit(get_listings, estate_type, region, page): page
            for page in range(1, pages + 1)
        }

        for future in as_completed(futures):
            page_num = futures[future]
            try:
                listings = future.result()
                if listings:
                    all_listings.extend(listings)
                    print(f"✅ Page {page_num} scraped successfully")
                    logging.info(
                        f"Page {page_num} scraped successfully with {len(listings)} listings."
                    )
                else:
                    print(f"⚠️ Page {page_num} returned no listings")
                    logging.warning(f"Page {page_num} returned no listings.")
            except Exception as e:
                print(f"❌ Error scraping page {page_num}: {e}")
                logging.error(f"Error scraping page {page_num}: {e}")

    logging.info(f"Scraping completed. Total listings scraped: {len(all_listings)}")
    return all_listings


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python scraper.py <estate_type> <region|all> <pages>")
        print("Example: python scraper.py byty praha 3")
        print("Example: python scraper.py domy all 5")
        sys.exit(1)

    try:
        estate_type, region, num_pages = validate_args(
            sys.argv[1], sys.argv[2], sys.argv[3]
        )
        logging.info(
            f"Arguments received and validated: estate_type={estate_type}, region={region}, num_pages={num_pages}"
        )
        print(f"Scraping {num_pages} pages of {estate_type} in {region}...")

        data = scrape_multiple_pages(estate_type, region, num_pages)

        if data:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"sreality_{estate_type}_{region}_{timestamp}.csv"

            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding="utf-8")
            print(f"✅ Data saved to {filename}")
            logging.info(f"Data saved to {filename}")
        else:
            print("❌ No data found.")
            logging.warning("No data found to save.")
    except ValueError as e:
        logging.exception(
            "An error occurred while validating arguments or scraping data."
        )
        print(e)
        sys.exit(1)
