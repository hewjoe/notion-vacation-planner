# Notion Integration Setup Guide

This guide will help you set up a Notion integration and get the necessary credentials to use with the Notion Vacation Planner.

## Step 1: Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click on "+ New integration"
3. Give your integration a name (e.g., "Vacation Planner")
4. Select the workspace where your excursion database is located
5. Under "Capabilities", ensure "Read content" and "Update content" are selected
6. Click "Submit" to create the integration
7. Copy the "Internal Integration Token" (this is your `NOTION_API_KEY`)

## Step 2: Share Your Database with the Integration

1. Open your Notion database with excursion information
2. Click the "..." menu in the top-right corner
3. Select "Add connections"
4. Find and select your integration (e.g., "Vacation Planner")
5. Click "Confirm" to give the integration access to your database

## Step 3: Get Your Database ID

1. Open your Notion database in a web browser
2. Look at the URL, which will be in this format:
   ```
   https://www.notion.so/workspace-name/1a2b3c4d5e6f7g8h9i0j?v=...
   ```
3. The database ID is the part after the workspace name and before the question mark:
   ```
   1a2b3c4d5e6f7g8h9i0j
   ```
4. Copy this ID (this is your `NOTION_DATABASE_ID`)

## Step 4: Set Up Your Database Properties

Ensure your Notion database has the following properties:

1. **Name** (title property) - The name of the excursion
2. **Description** (text property) - Detailed description of the excursion
3. **Location** (select property) - The location of the excursion
4. **AI Summary** (text property) - Will be populated by the program
5. **AI Recommendation** (text property) - Will be populated by the program

If any of these properties don't exist, add them to your database.

## Step 5: Get Your OpenAI API Key

1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in to your OpenAI account
3. Click "Create new secret key"
4. Give your key a name (e.g., "Vacation Planner")
5. Copy the API key (this is your `OPENAI_API_KEY`)

## Step 6: Update Your .env File

1. Open the `.env` file in this project
2. Add your Notion API key, database ID, and OpenAI API key to the appropriate fields
3. Save the file

## Step 7: Test Your Connection

Run the test script to verify your connection:

```
python test_notion_connection.py
```

If everything is set up correctly, you should see a success message and some sample records from your database. 