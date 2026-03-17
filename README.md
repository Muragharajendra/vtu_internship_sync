# VTU Internship Sync Tool

Production-grade RPA implementation that reliably synchronizes internship diary records from Account-2 to Account-1.

## Features
- Complete data scraping via BeautifulSoup
- Resilient form navigation & submission via Selenium
- Deduplication: Never blindly overwrites entries.
- Automated CAPTCHA pausing and manual-entry workflows.
- Dynamic AI fill: Optionally leverages OpenAI/Anthropic to generate plausible summaries if blank.
- CLI arguments ensuring robust operation modes (`--dry-run`, `--sync`, `--resume`, `--headless`).
- Screenshot logging and checkpoint-based automatic resuming.

## Prerequisites
- **Python 3.10+**
- **Google Chrome** installed on your system.
- Chromium WebDriver dynamically managed via Selenium 4.x.

## Installation

1. Create a virtual environment and load requirements:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Generate credentials file from template:
```bash
cp .env.example .env
```
Open `.env` and fill in the necessary `ACCOUNT1_*` and `ACCOUNT2_*` fields.

- If you want to enable **Razorpay checkout** in the web UI, also set:
  - `RAZORPAY_KEY_ID`
  - `RAZORPAY_KEY_SECRET`

If using AI fallbacks, fill the appropriate `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

## Usage

**Dry Run Mode** (Highly Recommended First)
This will log in, pull the entry data, perform the difference calculation, and output what it *would* have posted to Account 1. No submissions will be made.
```bash
python main.py --dry-run
```

**Full Sync**
Executes complete dual-login evaluation and targets missing Account 1 records for injection.
```bash
python main.py --sync
```

**Headless Operation**
Adds headless Chrome flags (useful for headless servers). Wait times apply.
```bash
python main.py --sync --headless
```

**Resuming Failed Executions**
If an error throws mid-run (like an element not loading or the browser crashing), `checkpoint.json` tracks the `date` ID's that failed. Use resume flag to skip all logic and immediately inject those entries.
```bash
python main.py --resume
```

## Setup Notes: Finding CSS Selectors

Before running this script reliably, you **must complete the mappings in `config.py`**. The VTU portal changes often, rendering hardcoded CSS selectors obsolete. Follow these steps to map them:

1. Open Chrome and go to `https://internship.vtu.ac.in/login` 
2. **Right-click -> Inspect** the desired element (Username input box, login button, etc.).
3. Under the `Elements` tab, right-click the highlighted code -> `Copy` -> `Copy selector` (or XPath).
4. Update this string in the appropriate constant defined inside `config.py`.
5. For tables/scraping, ensure your row-selector grabs the `<tr/>` correctly.

## Error Handling & Resiliency
- Every time Selenium encounters a Timeout, the script auto-takes a screenshot into `/logs/screenshots/` labeled by the current timestamp or date-record. Refer to these images if UI updates break the current selectors.
- Network operations auto-retry with exponential back-off up to 3 times before fatally throwing exceptions.
