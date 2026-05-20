# NextCure Signal Room v1.2

Streamlit rebuild focused on ClinicalTrials.gov structured intelligence for the NextCure-relevant lanes:

- B7-H4 / VTCN1
- CDH6
- Alzheimer's / ApoE4
- Bone / Siglec-15

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## What v1.2 includes

- Premium dark BuildWell-style Streamlit interface
- "Run Clinical Intelligence Scan" power-on flow
- ClinicalTrials.gov API v2 ingestion
- Active trials by phase
- Geographic trial footprint by country
- Country × target-lane density heatmap
- Enrollment / patient population proxy charts
- Combination therapy matrix
- Forward catalyst calendar using primary completion dates
- Sponsor / competitor activity
- Trial development timeline
- Rules-based executive signal feed
- Auditable evidence table

## Intentional exclusions

No AI summaries, PubMed, patent scraping, stock interpretation, or web crawling yet. This version is intentionally constrained so the clinical registry intelligence layer can earn trust first.
