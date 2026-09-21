import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RESUME = (
    "Generative AI engineer. Built a RAG chatbot with LangChain, ChromaDB and FastAPI. "
    "Python, SQL, Docker, Git. Fine-tuned a model with LoRA using Hugging Face."
)
JOB = (
    "We need an AI Engineer with Python, RAG, LangChain, Kubernetes and AWS experience. "
    "Experience with MCP and vector databases is a plus. Singapore Citizens and PRs only."
)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["JOBHUNT_DB"] = str(Path(self.tmp.name) / "test.db")
        from jobhunt import core
        self.core = core

    def tearDown(self):
        self.tmp.cleanup()

    def test_resume_skill_extraction(self):
        out = self.core.save_resume(RESUME)
        for s in ["python", "rag", "langchain", "vector database", "fastapi", "fine-tuning", "hugging face"]:
            self.assertIn(s, out["skills_found"])
        self.assertNotIn("kubernetes", out["skills_found"])

    def test_plural_forms_match(self):
        from jobhunt.skills import extract_skills
        self.assertIn("vector database", extract_skills("Experience with vector databases required"))
        self.assertIn("agents", extract_skills("Build AI agents for customers"))
        self.assertNotIn("git", extract_skills("digital transformation"))

    def test_short_input_rejected(self):
        with self.assertRaises(ValueError):
            self.core.save_resume("hi")
        with self.assertRaises(ValueError):
            self.core.add_job("x", "y", "short")

    def test_add_job_and_match(self):
        self.core.save_resume(RESUME)
        job = self.core.add_job("AI Engineer", "Acme", JOB)
        self.assertIn("kubernetes", job["skills_required"])
        self.assertTrue(job["work_pass_signals"])
        m = self.core.match_resume_to_job(job["job_id"])
        self.assertIn("python", m["matched_skills"])
        self.assertIn("kubernetes", m["missing_skills"])
        self.assertIn("aws", m["missing_skills"])
        self.assertIn("mcp", m["missing_skills"])
        self.assertTrue(0 < m["match_score_percent"] < 100)

    def test_match_needs_resume(self):
        job = self.core.add_job("AI Engineer", "Acme", JOB)
        with self.assertRaises(ValueError):
            self.core.match_resume_to_job(job["job_id"])

    def test_tracking_and_followups(self):
        job = self.core.add_job("AI Engineer", "Acme", JOB)
        r = self.core.track_application(job["job_id"], "applied", "via portal", followup_in_days=7)
        self.assertEqual(r["applied_date"], date.today().isoformat())
        self.assertEqual(self.core.get_followups_due(), [])
        future = date.today() + timedelta(days=8)
        with mock.patch.object(self.core, "_today", return_value=future):
            due = self.core.get_followups_due()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["company"], "Acme")

    def test_invalid_status(self):
        job = self.core.add_job("AI Engineer", "Acme", JOB)
        with self.assertRaises(ValueError):
            self.core.track_application(job["job_id"], "ghosted")

    def test_notes_accumulate(self):
        job = self.core.add_job("AI Engineer", "Acme", JOB)
        self.core.track_application(job["job_id"], "applied", "first note")
        self.core.track_application(job["job_id"], "interviewing", "second note")
        with self.core._conn() as c:
            notes = c.execute("SELECT notes FROM applications").fetchone()["notes"]
        self.assertEqual(notes, "first note\nsecond note")

    def test_market_analysis(self):
        self.core.save_resume(RESUME)
        self.core.add_job("AI Engineer", "A", JOB)
        self.core.add_job("ML Engineer", "B", "Python, Kubernetes, AWS and Docker experience required for this role.")
        out = self.core.analyze_market_skills()
        top = {s["skill"]: s for s in out["top_skills"]}
        self.assertEqual(top["python"]["jobs"], 2)
        self.assertTrue(top["python"]["you_have_it"])
        self.assertFalse(top["kubernetes"]["you_have_it"])
        self.assertIn("kubernetes", out["skills_to_learn_next"])

    def test_tailoring_context_has_rules(self):
        self.core.save_resume(RESUME)
        job = self.core.add_job("AI Engineer", "Acme", JOB)
        ctx = self.core.get_tailoring_context(job["job_id"])
        self.assertTrue(ctx["rules"])
        self.assertIn("kubernetes", ctx["missing_skills"])


if __name__ == "__main__":
    unittest.main()
