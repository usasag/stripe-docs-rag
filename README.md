# Stripe Docs RAG

Initial scaffold for Stripe docs RAG agent.

## Run
## Claude Desktop (MCP Server) Setup - Option C

To chat with the Stripe Docs agent natively inside **Claude Desktop**, you can connect it via our Model Context Protocol (MCP) Server.

1. Make sure you have the free **Claude Desktop** app installed.
2. Open your Claude Desktop config file, this can be found clicking on your name at the bottom left corner of the app and selecting "Settings", then going into Developer Settings. Click on "Open/Edit Config".
3. Add the following configuration (replace `YOUR_ABSOLUTE_PATH_TO_PROJECT` with the actual absolute path of this project, if the directory already exists, simply append the 'mcpServers' field to the JSON content):
```json
{
  "mcpServers": {
    "stripe-docs": {
      "command": "python",
      "args": [
        "app/mcp_server.py"
      ],
      "cwd": "YOUR_ABSOLUTE_PATH_TO_PROJECT",
      "env": {
        "SUPABASE_DB_URL": "postgresql://readonly_recruiter:temp_30_day_token_123@db.hxmpdytlsejvbkasrhlb.supabase.co:5432/postgres",
        "PYTHONPATH": "YOUR_ABSOLUTE_PATH_TO_PROJECT"
      }
    }
  }
}
```
4. Restart Claude Desktop. You will now see a 🔨 **Tools** icon indicating the `search_stripe_docs` tool is attached. You can now simply ask Claude: *"How do I confirm a PaymentIntent using Stripe?"* and it will use the knowledge base automatically!
- Install deps
- Start API with: `uvicorn app.main:app --reload`

## Health Check

`GET /health` returns `{"status": "ok"}`.
