# Notion Vacation Planner

This Python program connects to a Notion database containing excursion options for a vacation and enriches it with AI-generated summaries and recommendations.

## Features

- Reads excursion descriptions from a Notion database
- Generates concise 3-sentence summaries for each excursion using OpenAI
- Creates relative recommendations for excursions based on location
- Provides personalized travel agent insights based on your family composition
- Dynamically reads family member details from a separate "People" database
- Updates the Notion database with the AI-generated content
- Can be configured to update all records or a specific record
- Selectively update only specific AI-generated fields

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   NOTION_API_KEY=your_notion_api_key
   NOTION_DATABASE_ID=your_excursions_database_id
   NOTION_PEOPLE_DATABASE_ID=your_people_database_id
   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

### Basic Usage

Run the program to update all excursion records with all AI-generated fields:
```
python notion_excursion_ai.py
```

### Selective Updates

Update only specific AI-generated fields:
```
# Update only the AI Summary field
python notion_excursion_ai.py --update-summary

# Update only the AI Recommendation field
python notion_excursion_ai.py --update-recommendation

# Update only the Guide Insights field
python notion_excursion_ai.py --update-insights

# Update both Summary and Recommendation fields
python notion_excursion_ai.py --update-summary --update-recommendation

# Explicitly update all fields (same as default)
python notion_excursion_ai.py --update-all
```

### Targeting Specific Records

Update only a specific record (by page ID):
```
python notion_excursion_ai.py --page-id your_page_id
```

Combine specific record with selective field updates:
```
# Update only the Guide Insights for a specific excursion
python notion_excursion_ai.py --page-id your_page_id --update-insights
```

### Debugging

Enable debug logging for more detailed output:
```
python notion_excursion_ai.py --debug
```

## Command-Line Arguments

| Argument | Description |
|----------|-------------|
| `--page-id PAGE_ID` | Process only a specific page (by ID) |
| `--update-summary` | Update the AI Summary field |
| `--update-recommendation` | Update the AI Recommendation field |
| `--update-insights` | Update the Guide Insights field |
| `--update-all` | Update all AI-generated fields (default if no specific update flags are provided) |
| `--debug` | Enable debug logging |

## Notion Database Structure

### Excursions Database

The program expects a Notion database with at least the following properties:
- Name (title)
- Description (text)
- Cruise Details (relation to another database with location information)
- MyAI Summary (text)
- MyAI Recommendation (text)
- Guide Insights (text)

### People Database

The program also uses a "People" database to generate personalized travel agent insights. This database should have:
- Name (title)
- Age (number)
- Profile (text) - Optional description of the person (e.g., "teenager who loves adventure") 