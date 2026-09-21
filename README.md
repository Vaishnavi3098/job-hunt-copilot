# Job Hunt Copilot (MCP server)

An MCP (Model Context Protocol) server that turns any MCP-capable AI app into a personal job-search assistant.
You paste your resume and job postings; the server stores them, matches skills, tracks applications, and
shows which skills the market asks for most.

Designed to work with any MCP client. Tested with MCP Inspector and the included client using OpenAI.
The Anthropic and Gemini adapters and the Claude Desktop config are included but not yet tested.

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
| Tool | `save_resume_from_file` | Load the resume from a PDF, Word, or text file in the `data/` folder |
| Tool | `delete_job` | Delete a saved job (needs `confirm=true` as a safety check) |
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
- **MCP SDK version.** The code targets the MCP Python SDK v1, so `requirements.txt` pins `mcp<2`.
  Version 2 renamed `FastMCP`, so a migration is needed before upgrading.

## Known limitations

- **Keyword matching only.** The score counts skills from a fixed list, so a posting that uses concepts
  instead of technology names can show a misleadingly high score (a 100% result on a role with few
  recognized skills). Semantic matching is planned.
- **AI output needs review.** Even with rules in `get_tailoring_context`, models sometimes stretch claims in
  suggested resume bullets and then report that they were unsure of nothing. Always check suggestions against
  your real resume.
- **No duplicate detection.** Saving the same posting twice creates two jobs; use `delete_job` to clean up.
- **Applied date is today's date.** `track_application` cannot record an earlier date yet.
- **Privacy.** When an AI client calls tools, your resume text is sent to that AI provider.


## Roadmap

- [ ] Semantic matching with embeddings
- [ ] Email-alert import (parse JobStreet / LinkedIn / Indeed alert emails)
- [ ] `JobSource` adapters for open job feeds
- [ ] Streamable HTTP transport + auth, deployed remotely
- [ ] Evaluation: compare the match score with a human rating on 20 real postings
