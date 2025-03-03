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
PEOPLE_DATABASE_ID = os.environ.get("NOTION_PEOPLE_DATABASE_ID")  # Add this to your .env file
NAME_PROPERTY = "Name"
DESCRIPTION_PROPERTY = "Description"
LOCATION_PROPERTY = "Cruise Details"  # This is a relation field pointing to Cruise Schedule database
AI_SUMMARY_PROPERTY = "MyAI Summary"
AI_RECOMMENDATION_PROPERTY = "MyAI Recommendation"
GUIDE_INSIGHTS_PROPERTY = "Guide Insights"  # New field for travel agent insights

# People database properties
PERSON_NAME_PROPERTY = "Name"
PERSON_AGE_PROPERTY = "Age"
PERSON_PROFILE_PROPERTY = "Profile"

# Default family context in case the People database is not available
DEFAULT_FAMILY_CONTEXT = """
Family Composition:
- 14-year-old girl
- 15-year-old boy
- 46-year-old mom
- 46-year-old dad
- 48-year-old uncle
- 69-year-old grandmother
- 70-year-old grandfather
All family members are healthy and capable.
"""

def get_database_pages(database_id: str, page_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch pages from a Notion database.
    
    Args:
        database_id: ID of the database to query
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
        query_result = notion.databases.query(database_id=database_id)
        all_pages.extend(query_result["results"])
        
        # Handle pagination if there are more results
        while query_result.get("has_more", False):
            query_result = notion.databases.query(
                database_id=database_id,
                start_cursor=query_result["next_cursor"]
            )
            all_pages.extend(query_result["results"])
        
        return all_pages
    except Exception as e:
        logger.error(f"Error querying database {database_id}: {e}")
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

def extract_person_data(page: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract person data from a People database page.
    
    Args:
        page: Notion page object from People database
        
    Returns:
        Dictionary with extracted person data
    """
    properties = page.get("properties", {})
    
    name = ""
    name_property = properties.get(PERSON_NAME_PROPERTY, {})
    if name_property.get("type") == "title":
        name = extract_text_content(name_property.get("title", []))
    
    age = None
    age_property = properties.get(PERSON_AGE_PROPERTY, {})
    
    
    if age_property.get("type") == "formula":
        age = age_property.get("formula").get("number")
    
    profile = ""
    profile_property = properties.get(PERSON_PROFILE_PROPERTY, {})
    if profile_property.get("type") == "rich_text":
        profile = extract_text_content(profile_property.get("rich_text", []))
    
    response = {
        "name": name,
        "age": age,
        "profile": profile
    }
    logger.debug(f"Extracted person data: {response}")
    return response 

def build_family_context() -> str:
    """
    Build family context from the People database.
    
    Returns:
        Formatted family context string
    """
    if not PEOPLE_DATABASE_ID:
        logger.warning("NOTION_PEOPLE_DATABASE_ID not set in environment variables. Using default family context.")
        return DEFAULT_FAMILY_CONTEXT
    
    try:
        people_pages = get_database_pages(PEOPLE_DATABASE_ID)
        if not people_pages:
            logger.warning("No people found in People database. Using default family context.")
            return DEFAULT_FAMILY_CONTEXT
        
        people = []
        for page in people_pages:
            person = extract_person_data(page)
            if person["name"] and person["age"] is not None:
                people.append(person)
        
        if not people:
            logger.warning("No valid people data found in People database. Using default family context.")
            return DEFAULT_FAMILY_CONTEXT
        
        # Sort people by age (youngest to oldest)
        people.sort(key=lambda x: x["age"])
        
        # Build the context
        context = "Family Composition:\n"
        for person in people:
            profile_info = f" - {person['profile']}" if person["profile"] else ""
            context += f"- {person['name']}: {person['age']}-year-old{profile_info}\n"
        
        context += "\nAll family members are healthy and capable."
        logger.info(f"Family context: {context}")
        return context
        
    except Exception as e:
        logger.error(f"Error building family context: {e}")
        logger.warning("Using default family context due to error.")
        return DEFAULT_FAMILY_CONTEXT

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

def generate_guide_insights(description: str, location: str, family_context: str) -> str:
    """
    Generate travel agent insights for an excursion based on family composition.
    
    Args:
        description: Excursion description text
        location: Location name from the related Cruise Details
        family_context: Dynamic family context from People database
        
    Returns:
        Travel agent insights
    """
    if not description:
        return "No description available for insights."
    
    try:
        prompt = f"""As an experienced travel agent who has worked with similar families in {location}, provide 2-3 paragraphs of insights about this excursion, considering the following family composition:

{family_context}

Based on the excursion description below, provide specific insights about how this excursion would work for this family, including any tips for maximizing enjoyment for all age groups, potential challenges to consider, and recommendations for family dynamics. Keep the response limited to 2000 characters.

Excursion Description:
{description}"""

        response = openai_client.chat.completions.create(
            model="gpt-4.5-preview",
            messages=[
                {"role": "system", "content": "You are an experienced travel agent who specializes in multi-generational family cruise excursions. You have extensive experience with Mediterranean destinations and understand how to balance different age groups' needs and interests."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        insights = response.choices[0].message.content.strip()
        return insights
    except Exception as e:
        logger.error(f"Error generating guide insights: {e}")
        return "Error generating travel agent insights."

def update_notion_page(page_id: str, summary: str = None, recommendation: str = None, guide_insights: str = None) -> bool:
    """
    Update a Notion page with AI-generated content.
    
    Args:
        page_id: ID of the page to update
        summary: AI-generated summary (optional)
        recommendation: AI-generated recommendation (optional)
        guide_insights: Travel agent insights (optional)
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        properties = {}
        
        # Only include properties that have values
        if summary is not None:
            properties[AI_SUMMARY_PROPERTY] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": summary
                        }
                    }
                ]
            }
        
        if recommendation is not None:
            properties[AI_RECOMMENDATION_PROPERTY] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": recommendation
                        }
                    }
                ]
            }
        
        if guide_insights is not None:
            properties[GUIDE_INSIGHTS_PROPERTY] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": guide_insights
                        }
                    }
                ]
            }
        
        # Only update if there are properties to update
        if properties:
            notion.pages.update(
                page_id=page_id,
                properties=properties
            )
            return True
        else:
            logger.warning(f"No properties to update for page {page_id}")
            return False
    except Exception as e:
        logger.error(f"Error updating page {page_id}: {e}")
        return False

def main() -> None:
    """Main function to run the program."""
    parser = argparse.ArgumentParser(description="Enhance Notion excursion database with AI-generated content")
    parser.add_argument("--page-id", help="Process only a specific page (by ID)")
    parser.add_argument("--update-summary", action="store_true", help="Update the AI Summary field")
    parser.add_argument("--update-recommendation", action="store_true", help="Update the AI Recommendation field")
    parser.add_argument("--update-insights", action="store_true", help="Update the Guide Insights field")
    parser.add_argument("--update-all", action="store_true", help="Update all AI-generated fields (default if no specific update flags are provided)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Check for required environment variables
    if not all([os.environ.get("NOTION_API_KEY"), os.environ.get("NOTION_DATABASE_ID"), os.environ.get("OPENAI_API_KEY")]):
        logger.error("Missing required environment variables. Please check your .env file.")
        sys.exit(1)
    
    # Determine which fields to update
    update_summary = args.update_summary
    update_recommendation = args.update_recommendation
    update_insights = args.update_insights
    
    # If no specific update flags are provided, update all fields
    if not any([update_summary, update_recommendation, update_insights, args.update_all]):
        logger.info("No specific update flags provided. Updating all fields.")
        update_summary = update_recommendation = update_insights = True
    elif args.update_all:
        update_summary = update_recommendation = update_insights = True
    
    # Build dynamic family context if needed
    family_context = None
    if update_insights:
        logger.info("Building family context from People database...")
        family_context = build_family_context()
        logger.info("Family context built successfully.")
    
    # Fetch pages from the excursions database
    logger.info("Fetching pages from Notion excursions database...")
    pages = get_database_pages(DATABASE_ID, args.page_id)
    
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
    
    # Generate AI content and update pages
    logger.info("Generating AI content...")
    updates_count = 0
    
    # Generate recommendations if needed (requires comparative analysis)
    recommendations = {}
    if update_recommendation:
        # Group excursions by location for recommendation generation
        excursions_by_location = defaultdict(list)
        for excursion in excursions:
            excursions_by_location[excursion["location"]].append(excursion)
        
        recommendations = generate_recommendations(excursions_by_location)
    
    # Process each excursion
    for excursion in excursions:
        # Values to update (None by default)
        summary = None
        recommendation = None
        guide_insights = None
        
        # Generate summary if needed
        if update_summary:
            logger.info(f"Generating summary for: {excursion['name']}")
            summary = generate_ai_summary(excursion["description"])
        
        # Get the pre-generated recommendation if needed
        if update_recommendation:
            recommendation = recommendations.get(excursion["id"], "No recommendation available.")
        
        # Generate travel agent insights if needed
        if update_insights:
            logger.info(f"Generating travel agent insights for: {excursion['name']}")
            guide_insights = generate_guide_insights(excursion["description"], excursion["location"], family_context)
        
        # Update Notion page
        logger.info(f"Updating Notion page: {excursion['name']}")
        if update_notion_page(excursion["id"], summary, recommendation, guide_insights):
            updates_count += 1
        
        # Add a small delay to avoid rate limits
        time.sleep(1)
    
    # Log summary of updates
    logger.info(f"Process completed. Updated {updates_count} out of {len(excursions)} excursions.")
    if update_summary:
        logger.info(f"Updated AI Summary field.")
    if update_recommendation:
        logger.info(f"Updated AI Recommendation field.")
    if update_insights:
        logger.info(f"Updated Guide Insights field.")

if __name__ == "__main__":
    main() 