#!/usr/bin/env python3
"""
Utility script to find the page ID of a Notion page by its name
"""

import os
import sys
import argparse
from notion_client import Client
from dotenv import load_dotenv

def extract_text_content(rich_text_list):
    """Extract plain text from a rich text object list."""
    if not rich_text_list:
        return ""
    return "".join([text.get("plain_text", "") for text in rich_text_list])

def main():
    parser = argparse.ArgumentParser(description="Find the page ID of a Notion page by its name")
    parser.add_argument("search_term", help="Name (or part of the name) to search for")
    parser.add_argument("--database", choices=["excursions", "people"], default="excursions", 
                        help="Which database to search (default: excursions)")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get Notion API key and database IDs from environment
    notion_api_key = os.environ.get("NOTION_API_KEY")
    excursions_database_id = os.environ.get("NOTION_DATABASE_ID")
    people_database_id = os.environ.get("NOTION_PEOPLE_DATABASE_ID")
    
    if not notion_api_key:
        print("ERROR: NOTION_API_KEY not found in environment variables.")
        print("Please create a .env file with your NOTION_API_KEY.")
        sys.exit(1)
    
    # Determine which database to search
    if args.database == "excursions":
        if not excursions_database_id:
            print("ERROR: NOTION_DATABASE_ID not found in environment variables.")
            sys.exit(1)
        database_id = excursions_database_id
        print(f"Searching in Excursions database for: {args.search_term}")
    else:  # people
        if not people_database_id:
            print("ERROR: NOTION_PEOPLE_DATABASE_ID not found in environment variables.")
            sys.exit(1)
        database_id = people_database_id
        print(f"Searching in People database for: {args.search_term}")
    
    # Initialize the Notion client
    notion = Client(auth=notion_api_key)
    
    try:
        # Query the database
        query_result = notion.databases.query(database_id=database_id)
        
        # Extract pages and their names
        pages = []
        for page in query_result.get("results", []):
            page_id = page.get("id", "")
            properties = page.get("properties", {})
            
            # Find the title property
            name = "Unknown"
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    name = extract_text_content(prop_value.get("title", []))
                    break
            
            pages.append({"id": page_id, "name": name})
        
        # Handle pagination if there are more results
        while query_result.get("has_more", False):
            query_result = notion.databases.query(
                database_id=database_id,
                start_cursor=query_result["next_cursor"]
            )
            
            for page in query_result.get("results", []):
                page_id = page.get("id", "")
                properties = page.get("properties", {})
                
                # Find the title property
                name = "Unknown"
                for prop_name, prop_value in properties.items():
                    if prop_value.get("type") == "title":
                        name = extract_text_content(prop_value.get("title", []))
                        break
                
                pages.append({"id": page_id, "name": name})
        
        # Filter pages by search term
        search_term_lower = args.search_term.lower()
        matching_pages = [page for page in pages if search_term_lower in page["name"].lower()]
        
        # Display results
        if matching_pages:
            print(f"\nFound {len(matching_pages)} matching page(s):")
            for i, page in enumerate(matching_pages, 1):
                print(f"{i}. {page['name']}")
                print(f"   ID: {page['id']}")
                print()
            
            print("To update a specific page, use the --page-id parameter with notion_excursion_ai.py:")
            print(f"python notion_excursion_ai.py --page-id PAGE_ID [other options]")
        else:
            print(f"\nNo pages found matching '{args.search_term}'.")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 