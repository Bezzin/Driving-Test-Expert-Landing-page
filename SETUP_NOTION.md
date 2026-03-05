# Notion Waitlist Form Setup

This guide explains how to set up the Notion integration for the waitlist form.

## Prerequisites

1. A Notion account
2. Access to the "DTE Waitlist Signups" database
3. A Notion integration (API key)

## Step 1: Create a Notion Integration

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Give it a name (e.g., "DTE Waitlist Form")
4. Select your workspace
5. Click **"Submit"**
6. Copy the **"Internal Integration Token"** (starts with `secret_`) - this is your `NOTION_API_KEY`

## Step 2: Share Database with Integration

1. Open the "DTE Waitlist Signups" database in Notion
2. Click the **"..."** menu in the top right
3. Click **"Connections"** → **"Add connections"**
4. Select your integration (e.g., "DTE Waitlist Form")
5. Click **"Confirm"**

## Step 3: Get Database ID

1. Open the "DTE Waitlist Signups" database in Notion
2. Copy the URL - it should look like: `https://www.notion.so/e5df5c44abbd45d2969ca6b3c0b7635c`
3. Extract the database ID from the URL (the part after the last `/`)
   - Database ID: `e5df5c44abbd45d2969ca6b3c0b7635c`

## Step 4: Set Environment Variables

### ⚠️ Important: Choose ONE Platform

**This project uses Netlify Functions** (the serverless function is in `netlify/functions/`), so you should deploy to **Netlify**.

If you want to use Vercel instead, the function structure would need to be changed to use Vercel's API routes.

### For Local Development

Create a `.env` file in the root directory with your credentials:

```env
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_database_id_here
```

**Important:** The `.env` file is already in `.gitignore` to protect your credentials.

### For Netlify Deployment (Recommended for this project)

1. Go to your Netlify site dashboard
2. Navigate to **Site settings** → **Environment variables**
3. Add the following variables:
   - `NOTION_API_KEY` = your Notion integration token (starts with `ntn_` or `secret_`)
   - `NOTION_DATABASE_ID` = your database ID from Step 3
4. Click **"Save"**
5. Redeploy your site

### For Vercel Deployment (Requires function migration)

If you want to use Vercel instead of Netlify, the serverless function structure needs to be changed. Contact the developer to migrate the function to Vercel's API routes format.

## Database Schema

The form submits the following fields to Notion:

- **Name** (Title field) → Maps to "Full Name" from form
- **Email** (Email field) → Maps to "Email Address" from form
- **Notes** (Rich text field) → Contains "Current Status" from form dropdown
- **Signup Date** (Created time) → Automatically set by Notion

## Testing

1. Fill out the form on your site
2. Submit the form
3. Check the "DTE Waitlist Signups" database in Notion
4. You should see a new entry with the submitted data

## Troubleshooting

### "Server configuration error"
- Check that `NOTION_API_KEY` and `NOTION_DATABASE_ID` are set correctly
- Ensure the integration has access to the database

### "Failed to submit form"
- Check Netlify function logs for detailed error messages
- Verify the database ID is correct (no extra spaces/characters)
- Ensure the integration token is valid and not expired

### Form submission works locally but not in production
- Double-check environment variables are set in your hosting platform
- Redeploy after adding environment variables
- Check that the function is deployed (should be at `/.netlify/functions/submit-waitlist`)

