import { Handler } from '@netlify/functions';
import { Client } from '@notionhq/client';

interface FormData {
  fullName: string;
  email: string;
  currentStatus: string;
}

// Handle preflight OPTIONS request
export const handler: Handler = async (event, context) => {
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
      },
      body: '',
    };
  }

  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: JSON.stringify({ message: 'Method Not Allowed' }),
    };
  }

  try {
    // Parse the request body
    const formData: FormData = JSON.parse(event.body || '{}');

    // Validate required fields
    if (!formData.fullName || !formData.email) {
      return {
        statusCode: 400,
        body: JSON.stringify({ message: 'Full name and email are required' }),
      };
    }

    // Get Notion credentials from environment variables
    const notionToken = process.env.NOTION_API_KEY;
    const notionDatabaseId = process.env.NOTION_DATABASE_ID;

    if (!notionToken || !notionDatabaseId) {
      console.error('Missing Notion credentials');
      return {
        statusCode: 500,
        body: JSON.stringify({ message: 'Server configuration error' }),
      };
    }

    // Initialize Notion client
    const notion = new Client({
      auth: notionToken,
    });

    // Create a new page in the Notion database
    const response = await notion.pages.create({
      parent: {
        database_id: notionDatabaseId,
      },
      properties: {
        Name: {
          title: [
            {
              text: {
                content: formData.fullName,
              },
            },
          ],
        },
        Email: {
          email: formData.email,
        },
        Notes: {
          rich_text: [
            {
              text: {
                content: `Current Status: ${formData.currentStatus}`,
              },
            },
          ],
        },
      },
    });

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
      },
      body: JSON.stringify({
        message: 'Successfully added to waitlist',
        pageId: response.id,
      }),
    };
  } catch (error: any) {
    console.error('Error submitting to Notion:', error);
    
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({
        message: 'Failed to submit form. Please try again later.',
        error: process.env.NETLIFY_DEV ? error.message : undefined,
      }),
    };
  }
};

