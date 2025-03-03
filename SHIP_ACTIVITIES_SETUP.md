# Setting Up the Ship Activities Database in Notion

This guide will walk you through the process of setting up a "Ship Activities" database in Notion to work with the `notion_excursion_ai.py` script's `--gather-ship-activities` feature.

## Creating the Database

1. Log in to your Notion account.
2. Click the "+ New page" button in the sidebar.
3. Select "Table - Full page" from the options.
4. Name your database "Ship Activities" (or any other name you prefer).
5. Click "Create" to create the new database.

## Setting Up Properties

Once your database is created, you'll need to set up the required properties. By default, the database will have a "Name" property (title type), but you'll need to add several others:

1. **Name** (already exists as a Title property)
   - This will store the standardized name of each activity.

2. **Category** (Select)
   - Click "+ Add a property"
   - Name it "Category"
   - Select "Select" as the property type
   - Suggested options (you can add these later):
     - Dining
     - Entertainment
     - Recreation
     - Shopping
     - Wellness
     - Services
     - Kids & Teens

3. **Summary** (Text)
   - Click "+ Add a property"
   - Name it "Summary"
   - Select "Text" as the property type

4. **Activity Description** (Text)
   - Click "+ Add a property"
   - Name it "Activity Description"
   - Select "Text" as the property type

5. **Insights** (Text)
   - Click "+ Add a property"
   - Name it "Insights"
   - Select "Text" as the property type

6. **Labels** (Multi-select)
   - Click "+ Add a property"
   - Name it "Labels"
   - Select "Multi-select" as the property type
   - Suggested options (you can add these later):
     - Swimming
     - Fitness
     - Drinking
     - Dancing
     - Food
     - Music
     - Shows
     - Kids
     - Teens
     - Adults-Only
     - Relaxation
     - Adventure
     - Educational
     - Free
     - Paid
     - Indoor
     - Outdoor

7. **Link** (URL)
   - Click "+ Add a property"
   - Name it "Link"
   - Select "URL" as the property type

## Sharing the Database with Your Integration

For the script to access your database, you need to share it with your Notion integration:

1. Open your Ship Activities database.
2. Click the "Share" button in the top-right corner.
3. In the "Share" menu, click "Invite" at the bottom.
4. In the search field, find and select your integration (the one you created for this project).
5. Click "Invite".

## Getting the Database ID

To interact with this database, you'll need its ID:

1. Open your Ship Activities database in the browser.
2. Look at the URL. It will be in this format: `https://www.notion.so/[workspace-name]/[database-id]?v=[view-id]`
3. Copy the `[database-id]` part (it's a string of characters, usually 32 characters long with hyphens).
4. Add this ID to your `.env` file as `NOTION_SHIP_ACTIVITIES_DATABASE_ID=your_database_id_here`.

## Using the Feature

Once you've set up the database and added its ID to your `.env` file, you can use the feature:

```bash
python notion_excursion_ai.py --gather-ship-activities
```

This will:
1. Query OpenAI with web search to gather information about activities on the Royal Caribbean Explorer of the Seas cruise ship.
2. Create records in your Ship Activities database for each activity.
3. Skip any activities that already exist (based on name).

The script will automatically populate all the fields with appropriate values based on the information gathered. 