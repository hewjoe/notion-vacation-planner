# Troubleshooting Guide

This guide addresses common issues you might encounter when using the Notion Vacation Planner.

## Connection Issues

### Error: "NOTION_API_KEY not found in environment variables"

**Solution:**
1. Make sure you've created a `.env` file in the project directory
2. Ensure the file contains the line `NOTION_API_KEY=your_actual_api_key`
3. Check that there are no spaces around the equals sign
4. Verify that the API key is correct and not expired

### Error: "Error connecting to Notion API"

**Solution:**
1. Verify your API key is correct
2. Check your internet connection
3. Ensure you're not using a VPN that might block the Notion API
4. Try creating a new integration and using the new API key

## Database Access Issues

### Error: "Error accessing database"

**Solution:**
1. Verify your database ID is correct
2. Make sure you've shared the database with your integration
3. Check that your integration has both "Read content" and "Update content" capabilities
4. Try opening the database in your browser to confirm you have access

### Error: "Object reference not found"

**Solution:**
1. Make sure your database ID is correct
2. Verify that the database still exists and hasn't been deleted
3. Check that your integration still has access to the database

## Property Issues

### Error: "Cannot read properties of undefined"

**Solution:**
1. Verify that your database has all the required properties:
   - Name (title)
   - Description (text)
   - Location (select)
   - AI Summary (text)
   - AI Recommendation (text)
2. Make sure the property names match exactly (case-sensitive)
3. Check that the property types are correct

## OpenAI Issues

### Error: "Error generating AI summary" or "Error generating recommendations"

**Solution:**
1. Verify your OpenAI API key is correct
2. Check that your OpenAI account has available credits
3. Ensure you're not exceeding OpenAI's rate limits
4. Try using a different OpenAI model (modify the code to use "gpt-3.5-turbo" instead of "gpt-4" if needed)

## General Troubleshooting Steps

1. **Check the logs:** Look for specific error messages in the console output
2. **Verify credentials:** Double-check all API keys and IDs
3. **Test basic connectivity:** Run `test_notion_connection.py` to verify basic connectivity
4. **Update dependencies:** Run `pip install -r requirements.txt` to ensure you have the latest versions
5. **Check Notion status:** Visit [Notion Status](https://status.notion.so/) to see if there are any ongoing service issues

If you continue to experience issues, try the following:

1. Delete and recreate your Notion integration
2. Create a new test database and try connecting to that instead
3. Check if your firewall or security software is blocking the connections 