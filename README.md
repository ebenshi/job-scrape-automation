# NYC Job Scraper

A Python script that automatically scrapes new graduate job postings from the [SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions) GitHub repository and syncs them with a Notion database, with automatic age tracking.

## What it does

This scraper monitors the SimplifyJobs New Grad Positions repository for new job postings and automatically:

1. **Scrapes job data** from the GitHub repository's README.md file
2. **Filters for NYC positions** using location-based pattern matching
3. **Creates Notion pages** for new NYC job postings with the following properties:
   - Job Title
   - Company
   - Source Link (application URL)
   - Age (in days since posting)
   - Location
4. **Updates existing pages** with current age information from the GitHub repository
5. **Sends Slack notifications** when new jobs are added (optional)

## Features

- **Automatic age tracking**: Syncs age data from the GitHub repo to keep Notion pages current
- **NYC filtering**: Only tracks jobs in New York City area using comprehensive location patterns
- **Duplicate prevention**: Uses URL-based tracking to avoid duplicate entries
- **Real-time updates**: Can update ages for all existing pages or run in normal mode
- **Slack integration**: Optional notifications for new job postings
- **Error handling**: Robust error handling for API failures and edge cases

## Setup

### Prerequisites

- Python 3.7+
- Notion API token
- Notion database with the following properties:
  - Job Title (Title)
  - Company (Rich Text)
  - Source Link (URL)
  - Age (Rich Text)
  - Location (Rich Text)

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
NOTION_TOKEN=your_notion_integration_token
NOTION_DB_ID=your_notion_database_id
SLACK_WEBHOOK_URL=your_slack_webhook_url  # Optional
GH_PAT=your_github_personal_access_token  # Optional, helps with rate limits
```

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Normal Operation
Runs the full scraper: adds new NYC jobs and updates ages for all existing pages.

```bash
python scraper.py
```

### Age Update Only
Updates ages for all existing pages without adding new jobs.

```bash
python scraper.py --update-ages
```

## How it works

1. **Fetches GitHub data**: Downloads the README.md from the SimplifyJobs repository
2. **Parses job tables**: Extracts job information from markdown tables
3. **Filters for NYC**: Uses regex patterns to identify NYC-area positions
4. **Checks for duplicates**: Compares against previously seen URLs
5. **Creates Notion pages**: Adds new jobs to your Notion database
6. **Updates ages**: Syncs current age data from GitHub repo to Notion
7. **Sends notifications**: Optional Slack alerts for new postings

## Age Tracking

The scraper automatically keeps age information current by:
- Matching Source Link URLs between Notion pages and GitHub repo rows
- Updating the Age property with the current value from the GitHub repository
- Handling various age formats (days, weeks, months) and normalizing them

## NYC Location Patterns

The scraper recognizes NYC locations using these patterns:
- NYC, NY, New York
- Manhattan, Brooklyn, Queens, Bronx, Staten Island
- Various abbreviations and formats

## Error Handling

- Graceful handling of API rate limits
- Robust error recovery for network issues
- Detailed logging of successes and failures
- Continues processing even if individual pages fail

## Requirements

See `requirements.txt` for Python package dependencies:
- requests
- beautifulsoup4
- python-dotenv (if using .env files)
