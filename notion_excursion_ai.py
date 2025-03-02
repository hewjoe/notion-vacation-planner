#!/usr/bin/env python3
"""
Notion Vacation Planner - AI Enhancement for Excursion Database
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict
from itertools import combinations
import time

from openai import OpenAI
from notion_client import Client
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize API clients
notion = Client(auth=os.environ.get("NOTION_API_KEY"))
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Constants
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
NAME_PROPERTY = "Name"
DESCRIPTION_PROPERTY = "Description"
LOCATION_PROPERTY = "Cruise Details"  # This is a relation field pointing to Cruise Schedule database
AI_SUMMARY_PROPERTY = "MyAI Summary"
AI_RECOMMENDATION_PROPERTY = "MyAI Recommendation"

def get_database_pages(page_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch pages from the Notion database.
    
    Args:
        page_id: Optional ID of a specific page to fetch
        
    Returns:
        List of database page objects
    """
    if page_id:
        try:
            page = notion.pages.retrieve(page_id)
            return [page]
        except Exception as e:
            logger.error(f"Error fetching page {page_id}: {e}")
            return []
    
    try:
        all_pages = []
        query_result = notion.databases.query(database_id=DATABASE_ID)
        all_pages.extend(query_result["results"])
        
        # Handle pagination if there are more results
        while query_result.get("has_more", False):
            query_result = notion.databases.query(
                database_id=DATABASE_ID,
                start_cursor=query_result["next_cursor"]
            )
            all_pages.extend(query_result["results"])
        
        return all_pages
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        return []

def extract_text_content(rich_text_list: List[Dict[str, Any]]) -> str:
    """
    Extract plain text from a rich text object list.
    
    Args:
        rich_text_list: List of rich text objects from Notion API
        
    Returns:
        Plain text content
    """
    if not rich_text_list:
        return ""
    
    return "".join([text.get("plain_text", "") for text in rich_text_list])

def get_related_page_title(page_id: str) -> str:
    """
    Get the title of a related page.
    
    Args:
        page_id: ID of the related page
        
    Returns:
        Title of the related page
    """
    try:
        page = notion.pages.retrieve(page_id)
        properties = page.get("properties", {})
        
        # Find the title property (usually "Name" or "Title")
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                return extract_text_content(prop_value.get("title", []))
        
        return "Unknown Location"
    except Exception as e:
        logger.error(f"Error fetching related page {page_id}: {e}")
        return "Unknown Location"

def extract_page_data(page: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant data from a page object.
    
    Args:
        page: Notion page object
        
    Returns:
        Dictionary with extracted data
    """
    properties = page.get("properties", {})
    
    name = ""
    name_property = properties.get(NAME_PROPERTY, {})
    if name_property.get("type") == "title":
        name = extract_text_content(name_property.get("title", []))
    
    description = ""
    description_property = properties.get(DESCRIPTION_PROPERTY, {})
    if description_property.get("type") == "rich_text":
        description = extract_text_content(description_property.get("rich_text", []))
    
    location = ""
    location_property = properties.get(LOCATION_PROPERTY, {})
    
    # Handle relation property type
    if location_property.get("type") == "relation":
        relation_list = location_property.get("relation", [])
        if relation_list:
            # Get the first related page ID
            related_page_id = relation_list[0].get("id")
            if related_page_id:
                # Fetch the title of the related page
                location = get_related_page_title(related_page_id)
    
    return {
        "id": page.get("id", ""),
        "name": name,
        "description": description,
        "location": location
    }

def generate_ai_summary(description: str) -> str:
    """
    Generate a 3-sentence summary of an excursion description using OpenAI.
    
    Args:
        description: Excursion description text
        
    Returns:
        AI-generated summary
    """
    if not description:
        return "No description available to summarize."
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.5-preview",  # or another appropriate model
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant providing concise summaries of vacation excursions."},
                {"role": "user", "content": f"Create a 3-sentence summary of this vacation excursion that highlights its key value and appeal. Make it engaging and informative for a family planning their vacation. Here's the excursion description:\n\n{description}"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        return "Error generating summary."

def generate_recommendations(excursions_by_location: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    """
    Generate relative recommendations for excursions based on location.
    
    Args:
        excursions_by_location: Dictionary mapping locations to lists of excursions
        
    Returns:
        Dictionary mapping excursion IDs to recommendation text
    """
    recommendations = {}
    
    for location, excursions in excursions_by_location.items():
        if len(excursions) <= 1:
            # If only one excursion at this location, no comparisons needed
            for excursion in excursions:
                recommendations[excursion["id"]] = f"This is the only excursion option for {location}."
            continue
            
        # For locations with multiple excursions, generate comparative recommendations
        try:
            # Prepare excursion data for comparison
            excursion_data = []
            for excursion in excursions:
                excursion_data.append({
                    "id": excursion["id"],
                    "name": excursion["name"],
                    "description": excursion["description"][:300] + "..." if len(excursion["description"]) > 300 else excursion["description"]
                })
            
            # Create a contextual description of all excursions at this location
            context = f"Excursions at {location}:\n\n"
            for i, exc in enumerate(excursion_data, 1):
                context += f"{i}. {exc['name']}: {exc['description']}\n\n"
            
            # Generate recommendations for each excursion
            for excursion in excursion_data:
                prompt = f"""Given the following excursion options at {location}, provide a brief recommendation (2-3 sentences) for the excursion "{excursion['name']}" that compares it to the other options and highlights when this option might be the best choice for a family vacation.

{context}

Recommendation for "{excursion['name']}":"""
                
                response = openai_client.chat.completions.create(
                    model="gpt-4.5-preview",
                    messages=[
                        {"role": "system", "content": "You are a helpful travel advisor providing comparative recommendations for vacation excursions."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
                
                recommendations[excursion["id"]] = response.choices[0].message.content.strip()
                
                # Add a small delay to avoid rate limits
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error generating recommendations for {location}: {e}")
            # Provide a fallback recommendation for all excursions at this location
            for excursion in excursions:
                recommendations[excursion["id"]] = f"Consider comparing with other options at {location}."
    
    return recommendations

def update_notion_page(page_id: str, summary: str, recommendation: str) -> bool:
    """
    Update a Notion page with AI-generated content.
    
    Args:
        page_id: ID of the page to update
        summary: AI-generated summary
        recommendation: AI-generated recommendation
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                AI_SUMMARY_PROPERTY: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": summary
                            }
                        }
                    ]
                },
                AI_RECOMMENDATION_PROPERTY: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": recommendation
                            }
                        }
                    ]
                }
            }
        )
        return True
    except Exception as e:
        logger.error(f"Error updating page {page_id}: {e}")
        return False

def main() -> None:
    """Main function to run the program."""
    parser = argparse.ArgumentParser(description="Enhance Notion excursion database with AI-generated content")
    parser.add_argument("--page-id", help="Process only a specific page (by ID)")
    args = parser.parse_args()
    
    # Check for required environment variables
    if not all([os.environ.get("NOTION_API_KEY"), os.environ.get("NOTION_DATABASE_ID"), os.environ.get("OPENAI_API_KEY")]):
        logger.error("Missing required environment variables. Please check your .env file.")
        sys.exit(1)
    
    # Fetch pages from the database
    logger.info("Fetching pages from Notion database...")
    pages = get_database_pages(args.page_id)
    
    if not pages:
        logger.error("No pages found in the database.")
        sys.exit(1)
    
    logger.info(f"Found {len(pages)} page(s) to process.")
    
    # Extract data from pages
    excursions = []
    for page in pages:
        excursion_data = extract_page_data(page)
        if excursion_data["description"]:
            excursions.append(excursion_data)
        else:
            logger.warning(f"Skipping page {excursion_data['id']} ({excursion_data['name']}) - no description found.")
    
    # Group excursions by location for recommendation generation
    excursions_by_location = defaultdict(list)
    for excursion in excursions:
        excursions_by_location[excursion["location"]].append(excursion)
    
    # Generate AI summaries and recommendations
    logger.info("Generating AI content...")
    updates_count = 0
    
    # Generate recommendations first (requires comparative analysis)
    recommendations = generate_recommendations(excursions_by_location)
    
    # Process each excursion
    for excursion in excursions:
        # Generate summary
        logger.info(f"Generating summary for: {excursion['name']}")
        summary = generate_ai_summary(excursion["description"])
        
        # Get the pre-generated recommendation
        recommendation = recommendations.get(excursion["id"], "No recommendation available.")
        
        # Update Notion page
        logger.info(f"Updating Notion page: {excursion['name']}")
        if update_notion_page(excursion["id"], summary, recommendation):
            updates_count += 1
        
        # Add a small delay to avoid rate limits
        time.sleep(1)
    
    logger.info(f"Process completed. Updated {updates_count} out of {len(excursions)} excursions.")

if __name__ == "__main__":
    main() 