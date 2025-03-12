# Sreality Scraper

Sreality Scraper is a Python-based web scraper that extracts real estate listings from [Sreality.cz](https://www.sreality.cz/). It allows users to scrape data on apartments and houses for sale across different regions in the Czech Republic.

> [!WARNING]
> This script is for educational and research purposes only
>
> Scraping data from websites may violate their terms of service

## Requirements

Before running the scraper, install the required Python dependencies from `requirements.txt`:

```sh
pip install -r requirements.txt
```

## Usage

Run the script with the following command:

```sh
python scraper.py <estate_type> <region> <pages>
```

## Parameters

| Parameter     | Description                                  | Allowed Values                                  |
| ------------- | -------------------------------------------- | ----------------------------------------------- |
| `estate_type` | Type of real estate to scrape                | `byty` (flats), `domy` (houses)                 |
| `region`      | Czech region where properties are located    | `praha`, `jihocesky-kraj`, `zlinsky-kraj`, etc. |
| `pages`       | Number of pages to scrape (positive integer) | `1, 2, 3, ...`                                  |

### Example Commands

**Scraping 3 pages of apartments in Prague:**

```sh
python scraper.py byty praha 3
```

**Scraping 5 pages of houses in the Zlín region:**

```sh
python scraper.py domy zlinsky-kraj 5
```

## Output

The script saves listings to a **CSV file** named:

```
sreality_<estate_type>_<region>_<timestamp>.csv
```

### **CSV Structure**

#### **Flats**

| Title | Property Type | Usable Area (m²) | Flat Type | Location | Price (CZK) | URL | Image |
| ----- | ------------- | ---------------- | --------- | -------- | ----------- | --- | ----- |

#### **Houses**

| Title | Property Type | Usable Area (m²) | Land Size (m²) | Location | Price (CZK) | URL | Image |
| ----- | ------------- | ---------------- | -------------- | -------- | ----------- | --- | ----- |
