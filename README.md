# Hack Search

<p align="center">
<img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge" />
  <img alt="Web Scraping" src="https://img.shields.io/badge/Web%20Scraping-374151?style=for-the-badge" />
  <img alt="BeautifulSoup" src="https://img.shields.io/badge/BeautifulSoup-374151?style=for-the-badge" />
  <img alt="Data Science" src="https://img.shields.io/badge/Data%20Science-1F77B4?style=for-the-badge" />
</p>

<p align="center">
  <strong>A focused hackathon discovery engine for online and hybrid competitions with cash prizes and strong product or AI relevance.</strong>
</p>

Hack Search collects hackathon listings from several platforms, filters for high-value opportunities, and produces a consolidated report. The project is built for fast discovery where eligibility, format, prize quality, and domain fit matter.

## Core Capabilities

- Scrapes major hackathon platforms through dedicated source adapters.
- Filters events by prize, format, geography, and technology focus.
- Generates structured reports for review and prioritization.
- Includes a lightweight server for local exploration.

## Technical Architecture

Each platform scraper lives behind a dedicated module, with shared models, focus scoring, utility functions, and report generation. This keeps new source integration isolated from filtering and output logic.

## Architecture Diagram

```mermaid
flowchart LR
  Platforms["Hackathon Platforms"] --> Adapters["Source-Specific Scrapers"]
  Adapters --> Models["Shared Event Models"]
  Models --> Focus["Prize, Format, and Domain Filters"]
  Focus --> Report["Consolidated Report"]
  Focus --> Server["Local Review Server"]
  Report --> Review["Opportunity Review"]
  Server --> Review

  classDef inputs fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D,stroke-width:2px;
  classDef process fill:#ECFCCB,stroke:#65A30D,color:#365314,stroke-width:2px;
  classDef data fill:#DBEAFE,stroke:#2563EB,color:#1E3A8A,stroke-width:2px;
  classDef agent fill:#FAE8FF,stroke:#C026D3,color:#701A75,stroke-width:2px;
  classDef output fill:#DCFCE7,stroke:#16A34A,color:#14532D,stroke-width:2px;
  class Platforms,Adapters,Focus,Server process;
  class Models data;
  class Report,Review output;
  linkStyle default stroke:#52525B,stroke-width:2px;
```

## Technology Stack

- Python scraper pipeline with Requests, BeautifulSoup, and lxml.
- Source adapters for Devfolio, Devpost, DoraHacks, ETHGlobal, MLH, Unstop, and related platforms.
- Report generation layer for consolidated opportunity output.
- Optional server entry point for local browsing.

## Repository Structure

- `scrape.py` - Batch scraping entry point.
- `server.py` - Local server entry point.
- `scrapers/models.py` - Shared event models.
- `scrapers/focus.py` - Relevance and domain-fit logic.
- `scrapers/report.py` - Report generation.
- `requirements.txt` - Python dependencies.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
python scrape.py
```

## Professional Context

This project demonstrates source-specific data engineering, filtering strategy, and practical automation for competitive opportunity discovery.
