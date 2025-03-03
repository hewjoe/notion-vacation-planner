#!/usr/bin/env python3
"""
Notion Vacation Planner - AI Enhancement for Excursion Database
"""

import os
import sys
import argparse
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from itertools import combinations
import time

from openai import OpenAI
from notion_client import Client
from dotenv import load_dotenv
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize API clients
notion = Client(auth=os.environ.get("NOTION_API_KEY"))
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
perplexity_client = OpenAI(api_key=os.environ.get("PERPLEXITY_API_KEY"), base_url="https://api.perplexity.ai")

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

class PerplexityClient(BaseModel):
    name: str
    category: str
    summary: str
    activity_description: str
    insights: str
    labels: List[str]
    link: Optional[str] = None

def clean_json_string(json_string: str) -> str:
    """
    Clean a JSON string by removing markdown code blocks and extra whitespace.
    
    Args:
        json_string: The JSON string to clean, potentially containing markdown code blocks
        
    Returns:
        A cleaned JSON string ready for parsing
    """
    # Remove markdown code blocks if present
    json_string = re.sub(r'```json\s*', '', json_string)
    json_string = re.sub(r'```\s*', '', json_string)
    
    # Strip any leading/trailing whitespace
    return json_string.strip()

def get_ship_activities() -> List[Dict[str, Any]]:
    """
    Generate a list of activities available on the Royal Caribbean Explorer of the Seas.
    Uses Perplexity API to generate structured data.
    
    Returns:
        List of activity dictionaries
    """
    logger.info("Generating ship activities for Royal Caribbean Explorer of the Seas")
    
    try:
        logger.info("Querying Perplexity for ship activities")
        
        # Define the prompt for Perplexity
        prompt = """
        Generate a list of all activities available on the Royal Caribbean Explorer of the Seas cruise ship.
        Limit the list to the top 25 activities.
        For each activity, provide the following information in a structured JSON format:
        - name: The name of the activity
        - category: The category (e.g., Entertainment, Dining, Sports, Relaxation, etc.)
        - summary: A brief one-sentence summary
        - activity_description: A detailed description (2-3 sentences)
        - insights: Tips or insights about the activity (1-2 sentences)
        - labels: Array of labels/tags that apply to this activity (e.g., "Family-Friendly", "Adults Only", "Active", "Relaxing", etc.)
        - link: URL to more information (can be null)
        
        Return the data as a JSON array of objects, with each object representing one activity.
        Format your response as valid JSON only, with no other text.
        """
        
        # Query Perplexity
        # First check if Perplexity API key is available
        if not os.environ.get("PERPLEXITY_API_KEY"):
            logger.error("PERPLEXITY_API_KEY not set in environment variables")
            return []
                
        try:
            # Query Perplexity API
            response = perplexity_client.chat.completions.create(
                model="sonar-pro",  # Using a smaller model for better JSON formatting
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides structured data about cruise ship activities in valid JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=3500
            )
            
            # Extract the content from the response
            content = response.choices[0].message.content
            
            # Clean the content to ensure it's valid JSON
            content = clean_json_string(content)
            logger.debug(f"Cleaned JSON content: {content}")
            
            try:
                import json
                
                # Try to parse JSON directly
                try:
                    # First try to parse as is
                    activities = json.loads(content)
                    
                    # Check if it's a dictionary with an activities key
                    if isinstance(activities, dict):
                        if 'activities' in activities:
                            activities = activities['activities']
                        # If it has only one key and that key contains a list, use that
                        elif len(activities) == 1 and isinstance(list(activities.values())[0], list):
                            activities = list(activities.values())[0]
                    
                    # Ensure activities is a list
                    if not isinstance(activities, list):
                        logger.warning(f"Expected a list of activities but got: {type(activities)}")
                        # Try to find a list in the response
                        if isinstance(activities, dict):
                            for key, value in activities.items():
                                if isinstance(value, list) and len(value) > 0:
                                    activities = value
                                    logger.info(f"Found activities list under key: {key}")
                                    break
                            else:
                                logger.error("Could not find activities array in response")
                                return []
                        else:
                            logger.error("Response is not a dictionary or list")
                            return []
                
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    # Try to extract JSON from the text
                    import re
                    
                    # Look for a JSON array
                    json_array_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
                    if json_array_match:
                        try:
                            array_text = json_array_match.group(0)
                            logger.debug(f"Found JSON array: {array_text}")
                            activities = json.loads(array_text)
                        except json.JSONDecodeError as e2:
                            logger.error(f"Failed to parse extracted JSON array: {e2}")
                            return []
                    else:
                        # Look for individual JSON objects and combine them
                        json_objects = re.findall(r'\{\s*"name".*?\}', content, re.DOTALL)
                        if json_objects:
                            try:
                                activities = []
                                for obj_text in json_objects:
                                    activities.append(json.loads(obj_text))
                                logger.info(f"Extracted {len(activities)} individual JSON objects")
                            except json.JSONDecodeError as e3:
                                logger.error(f"Failed to parse individual JSON objects: {e3}")
                                return []
                        else:
                            logger.error("Could not find JSON array or objects in response")
                            return []
                
                # Validate and normalize each activity
                validated_activities = []
                for activity in activities:
                    if not isinstance(activity, dict):
                        logger.warning(f"Skipping invalid activity format: {activity}")
                        continue
                    
                    # Ensure all required fields exist
                    required_fields = ["name", "category", "summary", "activity_description", "insights"]
                    for field in required_fields:
                        if field not in activity:
                            activity[field] = f"No {field} provided"
                    
                    # Ensure link field exists
                    if "link" not in activity:
                        activity["link"] = None
                    
                    # Ensure labels field exists
                    if "labels" not in activity:
                        activity["labels"] = []
                    elif isinstance(activity["labels"], str):
                        # If labels is a string, split it into a list
                        activity["labels"] = [label.strip() for label in activity["labels"].split(",")]
                    
                    validated_activities.append(activity)
                
                logger.info(f"Successfully generated {len(validated_activities)} ship activities")
                return validated_activities
                
            except Exception as e:
                logger.error(f"Failed to process response from Perplexity: {e}")
                logger.debug(f"Response content: {content}")
                
                # Try to extract activities from non-JSON response as a fallback
                try:
                    # Create a simple activity from the text response
                    fallback_activity = {
                        "name": "Cruise Activity",
                        "category": "Other",
                        "summary": "Activity from text response",
                        "activity_description": content[:500] if len(content) > 500 else content,
                        "insights": "Generated from text response",
                        "labels": ["Auto-Generated"],
                        "link": None
                    }
                    logger.warning("Created fallback activity from text response")
                    return [fallback_activity]
                except Exception:
                    return []
                
        except Exception as e:
            logger.error(f"Error querying Perplexity API: {e}")
            return []
    
    except Exception as e:
        logger.error(f"Error generating ship activities: {e}")
        return []

def check_activity_similarity(new_activity_name: str, existing_activities: List[Dict[str, Any]]) -> Optional[str]:
    """
    Check if a new activity name is similar to any existing activities using OpenAI.
    
    Args:
        new_activity_name: Name of the new activity
        existing_activities: List of existing activity dictionaries
        
    Returns:
        Page ID of the similar activity if found, None otherwise
    """
    if not existing_activities:
        return None
    
    try:
        # Create a list of existing activity names
        existing_names = [activity["properties"]["Name"]["title"][0]["text"]["content"] 
                          for activity in existing_activities 
                          if activity.get("properties", {}).get("Name", {}).get("title")]
        
        if not existing_names:
            return None
            
        # Format the names for the prompt
        existing_names_str = "\n".join([f"{i+1}. {name}" for i, name in enumerate(existing_names)])
        
        # Create the prompt for OpenAI
        prompt = f"""
        I have a new cruise ship activity named "{new_activity_name}" and a list of existing activities.
        Please determine if the new activity is very similar to any existing activity in the list.
        Consider similar activities as those likely to be the same activity with a slightly different name or description.
        
        Existing activities:
        {existing_names_str}
        
        If the new activity "{new_activity_name}" is very similar to an existing activity, respond with the number of the matching activity.
        If it's not similar to any existing activity, respond with "No match found".
        
        Your response should ONLY contain the number of the matching activity or "No match found".
        """
        
        # Query OpenAI for similarity check
        response = openai_client.chat.completions.create(
            model="gpt-4.5-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that determines if activities are similar based on their names."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=20,
            temperature=0.3
        )
        
        similarity_result = response.choices[0].message.content.strip()
        
        # Parse the result
        if similarity_result.lower() == "no match found":
            return None
        else:
            # Try to extract the number from the response
            import re
            match = re.search(r'\d+', similarity_result)
            if match:
                index = int(match.group()) - 1
                if 0 <= index < len(existing_activities):
                    return existing_activities[index]["id"]
        
        return None
    
    except Exception as e:
        logger.error(f"Error checking activity similarity: {e}")
        return None

def update_existing_activity(page_id: str, activity: Dict[str, Any], database_id: str) -> bool:
    """
    Update an existing activity record with new information.
    
    Args:
        page_id: ID of the existing page to update
        activity: New activity data dictionary
        database_id: The ID of the Notion database
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Create properties to update
        properties = {
            "Category": {
                "select": {
                    "name": activity["category"]
                }
            },
            "Summary": {
                "rich_text": [
                    {
                        "text": {
                            "content": activity["summary"]
                        }
                    }
                ]
            },
            "Activity Description": {
                "rich_text": [
                    {
                        "text": {
                            "content": activity["activity_description"]
                        }
                    }
                ]
            },
            "Insights": {
                "rich_text": [
                    {
                        "text": {
                            "content": activity["insights"]
                        }
                    }
                ]
            },
            "Link": {
                "url": activity.get("link", None)
            }
        }
        
        # Add Labels as multi-select
        if "labels" in activity and activity["labels"]:
            labels = activity["labels"]
            if isinstance(labels, str):
                # If labels came as comma-separated string
                labels = [label.strip() for label in labels.split(",")]
            
            properties["Labels"] = {
                "multi_select": [{"name": label} for label in labels]
            }
        
        # Update the page
        notion.pages.update(
            page_id=page_id,
            properties=properties
        )
        
        logger.info(f"Updated existing activity: {activity['name']}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating activity '{activity['name']}': {e}")
        return False

def create_ship_activity_records(activities: List[Dict[str, Any]], database_id: str) -> int:
    """
    Create records in the Ship Activities Notion database for each activity.
    If similar activities already exist, update them instead of creating duplicates.
    
    Args:
        activities: List of activity dictionaries
        database_id: The ID of the Notion database to create records in
        
    Returns:
        Number of activities successfully created or updated
    """
    if not database_id:
        logger.error("Ship Activities database ID not provided")
        return 0
    
    logger.info(f"Processing {len(activities)} ship activity records for Notion")
    created_or_updated_count = 0
    
    # First, get all existing activities from the database
    try:
        existing_activities = notion.databases.query(
            database_id=database_id,
            page_size=100  # Fetch up to 100 activities
        )["results"]
        logger.info(f"Found {len(existing_activities)} existing activities in database")
    except Exception as e:
        logger.error(f"Error fetching existing activities: {e}")
        existing_activities = []
    
    for activity in activities:
        try:
            # Validate activity format
            if not isinstance(activity, dict):
                logger.error(f"Invalid activity format: {activity}")
                continue
            
            # Ensure required fields exist
            required_fields = ["name", "category", "summary", "activity_description", "insights"]
            missing_fields = [field for field in required_fields if field not in activity]
            
            if missing_fields:
                logger.error(f"Activity missing required fields: {missing_fields}")
                # Try to create a more complete activity object if possible
                if isinstance(activity, str):
                    # If it's a string, use it as the name
                    activity = {
                        "name": activity,
                        "category": "Other",
                        "summary": "No summary provided",
                        "activity_description": "No description provided",
                        "insights": "No insights provided",
                        "link": None
                    }
                else:
                    # Skip this activity if we can't create a valid record
                    continue
            
            # Check if activity already exists by exact name
            query_results = notion.databases.query(
                database_id=database_id,
                filter={
                    "property": "Name",
                    "title": {
                        "equals": activity["name"]
                    }
                }
            )
            
            # If exact match found, skip it
            if query_results["results"]:
                logger.info(f"Activity '{activity['name']}' already exists with exact name, skipping")
                continue
            
            # Check for similar activities
            similar_page_id = check_activity_similarity(activity["name"], existing_activities)
            
            if similar_page_id:
                # Update the existing similar activity
                logger.info(f"Found similar activity for '{activity['name']}', updating existing record")
                if update_existing_activity(similar_page_id, activity, database_id):
                    created_or_updated_count += 1
                continue
            
            # No similar activity found, create a new one
            # Create properties for the new page
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": activity["name"]
                            }
                        }
                    ]
                },
                "Category": {
                    "select": {
                        "name": activity["category"]
                    }
                },
                "Summary": {
                    "rich_text": [
                        {
                            "text": {
                                "content": activity["summary"]
                            }
                        }
                    ]
                },
                "Activity Description": {
                    "rich_text": [
                        {
                            "text": {
                                "content": activity["activity_description"]
                            }
                        }
                    ]
                },
                "Insights": {
                    "rich_text": [
                        {
                            "text": {
                                "content": activity["insights"]
                            }
                        }
                    ]
                },
                "Link": {
                    "url": activity.get("link", None)
                }
            }
            
            # Add Labels as multi-select
            if "labels" in activity and activity["labels"]:
                labels = activity["labels"]
                if isinstance(labels, str):
                    # If labels came as comma-separated string
                    labels = [label.strip() for label in labels.split(",")]
                
                properties["Labels"] = {
                    "multi_select": [{"name": label} for label in labels]
                }
            
            # Create the page
            notion.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            
            created_or_updated_count += 1
            logger.info(f"Created new activity: {activity['name']}")
            
        except Exception as e:
            activity_name = activity.get("name", str(activity)) if isinstance(activity, dict) else str(activity)
            logger.error(f"Error processing activity '{activity_name}': {e}")
    
    return created_or_updated_count

def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Set up and return the argument parser for command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Process Notion Excursion data with OpenAI"
    )
    parser.add_argument(
        "--page-id", help="Process only a specific page (by ID)"
    )
    parser.add_argument(
        "--update-summary", action="store_true", help="Update the AI Summary field"
    )
    parser.add_argument(
        "--update-recommendation", action="store_true", help="Update the AI Recommendation field"
    )
    parser.add_argument(
        "--update-insights", action="store_true", help="Update the Guide Insights field"
    )
    parser.add_argument(
        "--update-all", action="store_true", help="Update all AI-generated fields"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--gather-ship-activities", action="store_true", 
        help="Gather activities from Royal Caribbean Explorer of the Seas and add to Notion"
    )
    return parser

def load_environment() -> Dict[str, str]:
    """
    Load and validate environment variables.
    Returns a dictionary of environment variables.
    """
    load_dotenv()
    env_vars = {
        "NOTION_API_KEY": os.getenv("NOTION_API_KEY"),
        "DATABASE_ID": os.getenv("NOTION_DATABASE_ID"),
        "PEOPLE_DATABASE_ID": os.getenv("NOTION_PEOPLE_DATABASE_ID"),
        "SHIP_ACTIVITIES_DATABASE_ID": os.getenv("NOTION_SHIP_ACTIVITIES_DATABASE_ID"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY")
    }
    
    # Validate required environment variables
    if not env_vars["NOTION_API_KEY"]:
        logger.error("NOTION_API_KEY not set in environment variables")
        sys.exit(1)
    
    # For ship activities, either OpenAI or Perplexity API key is required
    if not env_vars["OPENAI_API_KEY"] and not env_vars["PERPLEXITY_API_KEY"]:
        logger.error("Neither OPENAI_API_KEY nor PERPLEXITY_API_KEY set in environment variables")
        sys.exit(1)
        
    return env_vars

def initialize_clients(notion_api_key: str, openai_api_key: str) -> Tuple[Client, OpenAI, Optional[OpenAI]]:
    """
    Initialize and return the Notion, OpenAI, and Perplexity API clients.
    """
    notion_client = Client(auth=notion_api_key)
    openai_client_instance = OpenAI(api_key=openai_api_key) if openai_api_key else None
    
    # Initialize Perplexity client if API key is available
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    perplexity_client_instance = None
    if perplexity_api_key:
        perplexity_client_instance = OpenAI(api_key=perplexity_api_key, base_url="https://api.perplexity.ai")
    
    return notion_client, openai_client_instance, perplexity_client_instance

def process_ship_activities(ship_activities_db_id: str) -> None:
    """
    Process ship activities and create records in Notion.
    """
    if not ship_activities_db_id:
        logger.error("NOTION_SHIP_ACTIVITIES_DATABASE_ID not set in environment variables")
        sys.exit(1)
        
    # Gather ship activities and create records
    activities = get_ship_activities()
    if activities:
        created_count = create_ship_activity_records(activities, ship_activities_db_id)
        logger.info(f"Successfully created {created_count} ship activity records in Notion")
    else:
        logger.error("Failed to gather ship activities")

def determine_update_fields(args) -> Dict[str, bool]:
    """
    Determine which fields to update based on command line arguments.
    """
    update_fields = {
        "summary": args.update_summary,
        "recommendation": args.update_recommendation,
        "guide_insights": args.update_insights
    }
    
    # If --update-all is specified or no specific fields are requested, update all fields
    if args.update_all or not any(update_fields.values()):
        update_fields = {key: True for key in update_fields}
        
    return update_fields

def process_single_page(page_id: str, update_fields: Dict[str, bool]) -> None:
    """
    Process a single Notion page by ID.
    """
    try:
        # Get the page data
        page = notion.pages.retrieve(page_id=page_id)
        page_data = extract_page_data(page)
        
        if page_data["description"]:
            # Build family context only if we're updating the guide insights
            family_context = ""
            if update_fields["guide_insights"]:
                family_context = build_family_context()
            
            # Generate AI content based on which fields to update
            summary = None
            if update_fields["summary"]:
                summary = generate_ai_summary(page_data["description"])
            
            recommendation = None
            if update_fields["recommendation"]:
                # For single pages, we use a simplified recommendation
                recommendation = f"This is one of several options in {page_data['location']}. " \
                                 f"Consider your preferences and schedule when deciding."
            
            guide_insights = None
            if update_fields["guide_insights"]:
                guide_insights = generate_guide_insights(
                    page_data["description"],
                    page_data["location"],
                    family_context
                )
            
            # Update the page
            update_notion_page(
                page_id,
                summary=summary,
                recommendation=recommendation,
                guide_insights=guide_insights
            )
        else:
            logger.warning(f"No description found for page {page_id}")
    
    except Exception as e:
        logger.error(f"Error processing page {page_id}: {e}")
        if logger.level == logging.DEBUG:
            logger.exception("Detailed error:")

def process_all_pages(database_id: str, update_fields: Dict[str, bool]) -> None:
    """
    Process all pages in the Notion database.
    """
    # Get all pages from the database
    pages = get_database_pages(database_id)
    
    # Extract data from each page
    excursions_data = []
    for page in pages:
        page_data = extract_page_data(page)
        excursions_data.append(page_data)
    
    # Log the number of excursions found
    logger.info(f"Found {len(excursions_data)} excursions in the database")
    
    # Build family context only if we're updating the guide insights
    family_context = ""
    if update_fields["guide_insights"]:
        family_context = build_family_context()
    
    # Group excursions by location
    excursions_by_location = {}
    for exc in excursions_data:
        location = exc["location"]
        if location not in excursions_by_location:
            excursions_by_location[location] = []
        excursions_by_location[location].append(exc)
    
    # Generate recommendations for each location if needed
    recommendations = {}
    if update_fields["recommendation"]:
        recommendations = generate_recommendations(excursions_by_location)
    
    # Process each excursion
    for exc in excursions_data:
        try:
            if not exc["description"]:
                logger.warning(f"No description found for {exc['name']}")
                continue
            
            # Generate AI content based on which fields to update
            summary = None
            if update_fields["summary"]:
                summary = generate_ai_summary(exc["description"])
            
            recommendation = None
            if update_fields["recommendation"]:
                location = exc["location"]
                exc_id = exc["id"]
                if location in recommendations and exc_id in recommendations[location]:
                    recommendation = recommendations[location][exc_id]
            
            guide_insights = None
            if update_fields["guide_insights"]:
                guide_insights = generate_guide_insights(
                    exc["description"],
                    exc["location"],
                    family_context
                )
            
            # Update the Notion page
            update_notion_page(
                exc["id"],
                summary=summary,
                recommendation=recommendation,
                guide_insights=guide_insights
            )
        
        except Exception as e:
            logger.error(f"Error processing excursion {exc['name']}: {e}")
            if logger.level == logging.DEBUG:
                logger.exception("Detailed error:")

def main() -> None:
    """
    Main function to process Notion Excursion data with OpenAI.
    """
    # Set up argument parser and parse arguments
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Set logging level based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Load environment variables
    env_vars = load_environment()
    
    # Initialize global API clients
    global notion, openai_client, perplexity_client
    notion, openai_client, perplexity_client = initialize_clients(env_vars["NOTION_API_KEY"], env_vars["OPENAI_API_KEY"])

    # Special mode: gather ship activities
    if args.gather_ship_activities:
        process_ship_activities(env_vars["SHIP_ACTIVITIES_DATABASE_ID"])
        sys.exit(0)

    # For regular excursion processing, DATABASE_ID is required
    if not env_vars["DATABASE_ID"]:
        logger.error("NOTION_DATABASE_ID not set in environment variables")
        sys.exit(1)

    # Set global variables for backward compatibility
    global DATABASE_ID, PEOPLE_DATABASE_ID, SHIP_ACTIVITIES_DATABASE_ID
    DATABASE_ID = env_vars["DATABASE_ID"]
    PEOPLE_DATABASE_ID = env_vars["PEOPLE_DATABASE_ID"]
    SHIP_ACTIVITIES_DATABASE_ID = env_vars["SHIP_ACTIVITIES_DATABASE_ID"]

    # Determine which fields to update
    update_fields = determine_update_fields(args)
    
    # Process specific page or all pages
    if args.page_id:
        process_single_page(args.page_id, update_fields)
    else:
        process_all_pages(env_vars["DATABASE_ID"], update_fields)

if __name__ == "__main__":
    main() 