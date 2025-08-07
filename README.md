# Playwright

This repository provides a Playwright script for scraping Instagram posts.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
2. Set the `SESSIONID` environment variable with a valid Instagram session cookie.
3. Run the scraper:
   ```bash
   python main.py
   ```

The script outputs the top five posts from `@brooklyn_apartmentrentals` mentioning
"studio" or "1 bedroom" ranked by likes, comments and views.
