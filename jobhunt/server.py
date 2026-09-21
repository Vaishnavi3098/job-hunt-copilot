"""Job Hunt Copilot MCP server.

Run locally (stdio):   python -m jobhunt.server
Inspect with the UI:   npx @modelcontextprotocol/inspector python -m jobhunt.server

IMPORTANT: with stdio transport, never print() to stdout. It would corrupt the protocol.
Log to stderr instead.
"""
import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from . import core

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("jobhunt")

mcp = FastMCP("job-hunt-copilot")


# ---------------- TOOLS: actions the model can take ----------------

@mcp.tool()
def save_resume(resume_text: str) -> dict:
    """Save or replace the user's master resume (plain text) and detect the skills in it."""
    log.info("save_resume (%d chars)", len(resume_text))
    return core.save_resume(resume_text)

@mcp.tool()
def save_resume_from_file(filename: str) -> dict:
    """Load the resume from a file in the project's data folder (.pdf, .docx, .txt or .md),
    for example 'my_resume.pdf'. Detects the skills in it and saves it."""
    log.info("save_resume_from_file %s", filename)
    return core.load_resume_file(filename)

@mcp.tool()
def add_job_from_text(title: str, company: str, description: str, url: str = "") -> dict:
    """Save a job posting the user pasted. Returns the job_id, the skills the job asks for,
    and any hints about nationality or work-pass requirements found in the text."""
    log.info("add_job_from_text %s @ %s", title, company)
    return core.add_job(title, company, description, url=url, source="manual")


@mcp.tool()
def list_jobs() -> list[dict]:
    """List all saved jobs with their id, company, status and follow-up date."""
    return core.list_jobs()

@mcp.tool()
def delete_job(job_id: int, confirm: bool = False) -> dict:
    """Permanently delete one saved job and its tracking record. Only use this when the user
    clearly asks to delete that job, and set confirm to true only after they agree."""
    log.info("delete_job %s confirm=%s", job_id, confirm)
    return core.delete_job(job_id, confirm)

@mcp.tool()
def match_resume_to_job(job_id: int) -> dict:
    """Compare the saved resume with a saved job. Returns a rough score, matched skills,
    missing skills, and work-pass hints."""
    return core.match_resume_to_job(job_id)


@mcp.tool()
def get_tailoring_context(job_id: int) -> dict:
    """Get the resume, the job description, matched and missing skills, and honesty rules.
    Use this before suggesting resume edits or writing a cover letter for a job."""
    return core.get_tailoring_context(job_id)


@mcp.tool()
def track_application(job_id: int, status: str, notes: str = "", followup_in_days: int = 7) -> dict:
    """Set the status of a job application. Status is one of: saved, applied, interviewing,
    offer, rejected, withdrawn. Applied and interviewing set a follow-up reminder date."""
    log.info("track_application job=%s status=%s", job_id, status)
    return core.track_application(job_id, status, notes, followup_in_days)


@mcp.tool()
def get_followups_due() -> list[dict]:
    """List applications whose follow-up date is today or earlier."""
    return core.get_followups_due()


@mcp.tool()
def analyze_market_skills(top_n: int = 15) -> dict:
    """Count which skills appear most across all saved jobs, mark which ones the resume has,
    and suggest the top skills to learn next."""
    return core.analyze_market_skills(top_n)


# ---------------- RESOURCES: data the client can read ----------------

@mcp.resource("resume://master")
def resume_resource() -> str:
    """The saved master resume text."""
    return core.get_resume()["text"]


@mcp.resource("applications://all")
def applications_resource() -> str:
    """Summary of all saved jobs and their application status, as JSON."""
    return json.dumps(core.applications_summary(), indent=2)


@mcp.resource("jobs://{job_id}")
def job_resource(job_id: int) -> str:
    """Full text of one saved job posting."""
    job = core.get_job(int(job_id))
    return f"{job['title']} at {job['company']}\n\n{job['description']}"


# ---------------- PROMPTS: reusable request templates ----------------

@mcp.prompt()
def tailor_resume(job_id: int) -> str:
    """Suggest honest resume improvements for one saved job."""
    return (
        f"Call get_tailoring_context for job {job_id}. Then suggest 5 improved resume bullets for this job. "
        "Follow the rules returned by the tool: only reword real experience, never invent skills. "
        "List which missing skills I should learn or build a small project for."
    )


@mcp.prompt()
def cover_letter(job_id: int) -> str:
    """Draft a short cover letter for one saved job."""
    return (
        f"Call get_tailoring_context for job {job_id}. Write a cover letter under 200 words using only "
        "facts from my resume. Mention two relevant projects. Do not claim skills I lack."
    )


@mcp.prompt()
def weekly_review() -> str:
    """Review the job search progress for the week."""
    return (
        "Call list_jobs, get_followups_due and analyze_market_skills. Summarize where my applications "
        "stand, tell me which follow-ups to send first, and name the 3 skills that would help most."
    )


def main() -> None:
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
