### Affinity Answers Take-Home Assignment

## Requirements

- Python 3.9+
- Bash with `curl` (or `wget`), `awk`, `sort`, `cut` — Linux, macOS, WSL or Git Bash on Windows

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Question 1 — MD Computers scraper

```bash
cd q1_python
python mdcomputers_scraper.py "external harddrive"                       # JSON to stdout, all pages
python mdcomputers_scraper.py "external harddrive" --format csv -o drives.csv
python mdcomputers_scraper.py ssd --max-pages 1                          # first page only
python -m unittest -v test_scraper.py                                    # offline parser tests
```

Each product: `product_id`, `name`, `url`, `price`, `mrp`, `discount_percent` (prices are integers in INR).

## Question 2 — Rfam SQL

```bash
cd q2_sql
python run_queries.py                              # all three queries
python run_queries.py q3_families_page_9           # one query
```

Or paste `queries.sql` into any MySQL client:
`mysql --user rfamro --host mysql-rfam-public.ebi.ac.uk --port 4497 --database Rfam`
(public read-only account, no password). Q3 aggregates the large `full_region` table, so it is the slowest of the three.

## Question 3 — Shell script

```bash
chmod +x q3_shell/companies_by_founding_year.sh
./q3_shell/companies_by_founding_year.sh \
  https://raw.githubusercontent.com/datasets/s-and-p-500-companies/refs/heads/main/data/constituents.csv
```

Accepts a URL or a local file path. Prints `Company  Location  Founded`, oldest first.
Output is tab-separated (aligned with `column` when printed to a terminal), so it pipes cleanly:
`... | head -20`, `... > companies.tsv`.

