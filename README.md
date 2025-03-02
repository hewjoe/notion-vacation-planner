# Notion Vacation Planner

This Python program connects to a Notion database containing excursion options for a vacation and enriches it with AI-generated summaries and recommendations.

## Features

- Reads excursion descriptions from a Notion database
- Generates concise 3-sentence summaries for each excursion using OpenAI
- Creates relative recommendations for excursions based on location
- Updates the Notion database with the AI-generated content
- Can be configured to update all records or a specific record

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   NOTION_API_KEY=your_notion_api_key
   NOTION_DATABASE_ID=your_notion_database_id
   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

Run the program to update all excursion records:
```
python notion_excursion_ai.py
```

Update only a specific record:
```
python notion_excursion_ai.py --page-id your_page_id
```

## Notion Database Structure

The program expects a Notion database with at least the following properties:
- Name (title)
- Description (text)
- Location (select)
- AI Summary (text)
- AI Recommendation (text) 