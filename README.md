# Job Hunt Copilot (MCP server)

An MCP (Model Context Protocol) server that turns any MCP-capable AI app into a personal job-search assistant.
You paste your resume and job postings; the server stores them, matches skills, tracks applications, and
shows which skills the market asks for most.

Works with any MCP client: Claude Desktop, Cursor, VS Code, MCP Inspector, or the included multi-provider
client (Claude, OpenAI, Gemini).

## Architecture

```
You -> AI model (Claude / OpenAI / Gemini)
          | tool calls
          v
      MCP client (Claude Desktop, Cursor, or client/chat_client.py)
          | MCP over stdio
          v
      MCP server (jobhunt/server.py)  ->  core.py  ->  SQLite (data/jobhunt.db)
```

- `jobhunt/core.py` holds all the logic and has no MCP code, so it is unit tested on its own.
- `jobhunt/server.py` is a thin MCP layer exposing tools, resources and prompts.
- `client/chat_client.py` is a client showing how tool calling works with three model providers.

## What the server exposes

| Type | Name | Purpose |
|------|------|---------|
| Tool | `save_resume` | Store the resume and detect skills |
| Tool | `add_job_from_text` | Save a pasted job posting; returns required skills and work-pass hints |
| Tool | `list_jobs` | List saved jobs with status |
| Tool | `match_resume_to_job` | Score, matched skills, missing skills |
| Tool | `get_tailoring_context` | Resume + job + honesty rules for tailoring and cover letters |
| Tool | `track_application` | Set status and follow-up reminder |
| Tool | `get_followups_due` | Applications needing follow-up |
| Tool | `analyze_market_skills` | Most requested skills across saved jobs, and what to learn next |
| Resource | `resume://master`, `applications://all`, `jobs://{job_id}` | Read-only data |
| Prompt | `tailor_resume`, `cover_letter`, `weekly_review` | Reusable request templates |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # add your API key(s); never commit .env
python -m unittest discover -s tests -v   # core logic tests
```

## Try it three ways

**1. MCP Inspector (no AI needed; best for debugging)**
```bash
npx @modelcontextprotocol/inspector python -m jobhunt.server
```
Call `save_resume` with the text from `data/sample_resume.txt`, then `add_job_from_text` with `data/sample_job.txt`,
then `match_resume_to_job`.

**2. The included client (uses your API key)**
```bash
python client/chat_client.py --provider anthropic   # or openai / gemini
```
Then chat, for example: "Save this resume: ..." then "Save this job: ..." then "How well do I match job 1?"

**3. Claude Desktop** - add this to its MCP config file (use absolute paths, and the Python from your venv):
```json
{
  "mcpServers": {
    "job-hunt-copilot": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "jobhunt.server"],
      "cwd": "/absolute/path/to/job-hunt-copilot"
    }
  }
}
```
Restart the app. If your version ignores `cwd`, set `"env": {"PYTHONPATH": "/absolute/path/to/job-hunt-copilot"}` instead.

## Design decisions

- **Manual paste as the job source.** Big job sites restrict scraping and lack open search APIs, so the
  server takes text you paste. A future `JobSource` adapter can add official feeds.
- **Honest tailoring.** `get_tailoring_context` returns rules telling the model to reword real experience only.
- **Work-pass hints, not decisions.** Postings mentioning citizens, PR or work passes are flagged; you decide.
- **Rough matching.** The score uses a keyword skill list (`jobhunt/skills.py`). It is transparent and testable,
  but it misses skills outside the list. Semantic matching with embeddings is a planned upgrade.
- **Privacy.** Data stays in a local SQLite file, git-ignored. Use sample data in public demos.

## Roadmap

- [ ] Semantic matching with embeddings
- [ ] Email-alert import (parse JobStreet / LinkedIn / Indeed alert emails)
- [ ] `JobSource` adapters for open job feeds
- [ ] Streamable HTTP transport + auth, deployed remotely
- [ ] Evaluation: compare the match score with a human rating on 20 real postings

## Resume bullet

Built an MCP server (Python, SQLite) exposing 8 tools, 3 resources and 3 prompts for resume-to-job matching,
application tracking and market-skill analysis; wrote a multi-provider MCP client (Claude, OpenAI, Gemini)
and unit tests for the core logic.
