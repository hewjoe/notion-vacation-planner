#!/usr/bin/env python3
"""
Test script to verify OpenAI API connection
"""

import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key from environment
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    print("ERROR: OPENAI_API_KEY not found in environment variables.")
    print("Please create a .env file with your OPENAI_API_KEY.")
    sys.exit(1)

# Print masked API key for verification
masked_key = openai_api_key[:4] + "..." + openai_api_key[-4:] if len(openai_api_key) > 8 else "***"
print(f"Using OpenAI API key: {masked_key}")

# Initialize the OpenAI client
client = OpenAI(api_key=openai_api_key)

try:
    # Test API connection with a simple completion
    print("Testing OpenAI API connection...")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Using a less expensive model for testing
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Please respond with a short greeting."}
        ],
        max_tokens=20
    )
    
    # Extract and print the response
    message = response.choices[0].message.content.strip()
    print(f"\n✅ Successfully connected to OpenAI API!")
    print(f"Response: \"{message}\"")
    
    # Print available models (optional)
    print("\nChecking available models...")
    models = client.models.list()
    print(f"Found {len(models.data)} models available to your account.")
    
    # Print a few model IDs
    print("Some available models:")
    for model in models.data[:5]:  # Show first 5 models
        print(f"- {model.id}")
    
except Exception as e:
    print(f"\n❌ Error connecting to OpenAI API: {e}")
    print("Please check your OPENAI_API_KEY and make sure it's valid.")

print("\nTroubleshooting tips:")
print("1. Verify your API key is correct")
print("2. Check that your OpenAI account has available credits")
print("3. Ensure you're not exceeding OpenAI's rate limits")
print("4. Check if your account has access to the requested model") 