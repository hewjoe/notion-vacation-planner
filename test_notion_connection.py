#!/usr/bin/env python3
"""
Test script to verify Notion API connection
"""

import os
import sys
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Notion API key from environment
notion_api_key = os.environ.get("NOTION_API_KEY")
excursions_database_id = os.environ.get("NOTION_DATABASE_ID")
people_database_id = os.environ.get("NOTION_PEOPLE_DATABASE_ID")

if not notion_api_key:
    print("ERROR: NOTION_API_KEY not found in environment variables.")
    print("Please create a .env file with your NOTION_API_KEY.")
    sys.exit(1)

if not excursions_database_id:
    print("WARNING: NOTION_DATABASE_ID not found in environment variables.")
    print("Will only test API authentication, not excursions database access.")

if not people_database_id:
    print("WARNING: NOTION_PEOPLE_DATABASE_ID not found in environment variables.")
    print("Will not test people database access.")

# Print masked API key for verification
masked_key = notion_api_key[:4] + "..." + notion_api_key[-4:] if len(notion_api_key) > 8 else "***"
print(f"Using Notion API key: {masked_key}")

def extract_text_content(rich_text_list):
    """Extract plain text from a rich text object list."""
    if not rich_text_list:
        return ""
    return "".join([text.get("plain_text", "") for text in rich_text_list])

def get_related_page_title(notion_client, page_id):
    """Get the title of a related page."""
    try:
        page = notion_client.pages.retrieve(page_id)
        properties = page.get("properties", {})
        
        # Find the title property
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                return extract_text_content(prop_value.get("title", []))
        
        return f"[Untitled Page: {page_id}]"
    except Exception as e:
        return f"[Error: {str(e)}]"

def test_database_connection(notion_client, database_id, database_name):
    """Test connection to a specific database and print its properties."""
    try:
        # Try to query the database
        query_result = notion_client.databases.query(database_id=database_id)
        print(f"\n✅ Successfully accessed {database_name} database!")
        print(f"Database contains {len(query_result.get('results', []))} records.")
        
        # Get database schema
        db_info = notion_client.databases.retrieve(database_id=database_id)
        db_properties = db_info.get("properties", {})
        print(f"\n{database_name} Database Properties:")
        for prop_name, prop_info in db_properties.items():
            prop_type = prop_info.get("type", "unknown")
            print(f"  - {prop_name} ({prop_type})")
        
        # Print the first few records to verify content
        results = query_result.get('results', [])
        if results:
            print(f"\nSample {database_name} records:")
            for i, page in enumerate(results[:3], 1):
                page_id = page.get("id", "Unknown ID")
                properties = page.get("properties", {})
                
                # Try to extract the title/name property
                title = "Unknown"
                for prop_name, prop_value in properties.items():
                    if prop_value.get("type") == "title" and prop_value.get("title"):
                        title_parts = [text.get("plain_text", "") for text in prop_value.get("title", [])]
                        title = "".join(title_parts)
                        break
                
                print(f"\n  {i}. {title} (ID: {page_id})")
                
                # Print some key properties
                print("     Properties:")
                for prop_name, prop_value in properties.items():
                    prop_type = prop_value.get("type", "unknown")
                    value_display = "Empty"
                    
                    if prop_type == "title":
                        value_display = extract_text_content(prop_value.get("title", []))
                    elif prop_type == "rich_text":
                        value_display = extract_text_content(prop_value.get("rich_text", []))
                    elif prop_type == "select" and prop_value.get("select"):
                        value_display = prop_value.get("select", {}).get("name", "")
                    elif prop_type == "number":
                        value_display = str(prop_value.get("number", ""))
                    elif prop_type == "relation":
                        relation_ids = [rel.get("id") for rel in prop_value.get("relation", [])]
                        if relation_ids:
                            related_titles = []
                            for rel_id in relation_ids[:2]:  # Limit to first 2 relations
                                related_titles.append(get_related_page_title(notion_client, rel_id))
                            value_display = ", ".join(related_titles)
                            if len(relation_ids) > 2:
                                value_display += f" (+ {len(relation_ids) - 2} more)"
                        else:
                            value_display = "No relations"
                    
                    print(f"     - {prop_name} ({prop_type}): {value_display}")
            
            print(f"\nVerify these records match what you expect to see in your {database_name} database.")
        
        return True
    except Exception as e:
        print(f"\n❌ Error accessing {database_name} database: {e}")
        print(f"Please check your {database_name} database ID and make sure you have access to this database.")
        return False

try:
    # Initialize the Notion client
    notion = Client(auth=notion_api_key)
    
    # Test API connection by listing users
    users = notion.users.list()
    print("\n✅ Successfully connected to Notion API!")
    print(f"Found {len(users.get('results', []))} users.")
    
    # Test excursions database connection
    if excursions_database_id:
        excursions_success = test_database_connection(notion, excursions_database_id, "Excursions")
    
    # Test people database connection
    if people_database_id:
        people_success = test_database_connection(notion, people_database_id, "People")
    
except Exception as e:
    print(f"\n❌ Error connecting to Notion API: {e}")
    print("Please check your NOTION_API_KEY and make sure it's valid.")

print("\nTroubleshooting tips:")
print("1. Ensure your Notion integration has been added to your databases")
print("2. Verify your API key is correct and has the necessary permissions")
print("3. Check that your database IDs are correct")
print("4. Make sure your integration has 'Read content' and 'Update content' capabilities") 