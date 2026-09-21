"""A small MCP client that works with Claude, OpenAI or Gemini.

Usage:
    python client/chat_client.py --provider anthropic
    python client/chat_client.py --provider openai
    python client/chat_client.py --provider gemini

The client starts the MCP server itself (stdio), asks it for its tools, and runs the loop:
model asks for a tool -> client calls the MCP server -> result goes back to the model.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SYSTEM = (
    "You are a job-search assistant. Use the available tools to save the resume and jobs, "
    "match them, track applications and analyze the market. Ask the user to paste any text you need. "
    "Never invent experience the resume does not contain."
)


def result_text(result) -> str:
    """Turn an MCP tool result into plain text for the model."""
    parts = [getattr(block, "text", "") for block in result.content]
    return "\n".join(p for p in parts if p) or "(no output)"


async def run_tool(session: ClientSession, name: str, args: dict):
    print(f"  [tool] {name}({json.dumps(args)[:120]})")
    return await session.call_tool(name, args)


class AnthropicAgent:
    def __init__(self, session: ClientSession, tools):
        import anthropic

        self.client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
        self.session = session
        self.tools = [
            {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema} for t in tools
        ]
        self.messages: list = []

    async def turn(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        while True:
            resp = await self.client.messages.create(
                model=self.model, max_tokens=1500, system=SYSTEM, tools=self.tools, messages=self.messages
            )
            self.messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text")
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    out = await run_tool(self.session, block.name, block.input)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text(out),
                            "is_error": bool(out.isError),
                        }
                    )
            self.messages.append({"role": "user", "content": results})


class OpenAIAgent:
    def __init__(self, session: ClientSession, tools):
        import openai

        self.client = openai.AsyncOpenAI()  # reads OPENAI_API_KEY
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")  # any tool-calling model works
        self.session = session
        self.tools = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema},
            }
            for t in tools
        ]
        self.messages: list = [{"role": "system", "content": SYSTEM}]

    async def turn(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        while True:
            resp = await self.client.chat.completions.create(
                model=self.model, messages=self.messages, tools=self.tools
            )
            msg = resp.choices[0].message
            self.messages.append(msg.model_dump(exclude_none=True))
            if not msg.tool_calls:
                return msg.content or ""
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                out = await run_tool(self.session, call.function.name, args)
                self.messages.append({"role": "tool", "tool_call_id": call.id, "content": result_text(out)})


class GeminiAgent:
    """Uses the google-genai SDK's built-in support for passing an MCP session as a tool."""

    def __init__(self, session: ClientSession, tools):
        from google import genai
        from google.genai import types

        self.types = types
        self.client = genai.Client()  # reads GEMINI_API_KEY or GOOGLE_API_KEY
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.session = session
        self.history: list = []

    async def turn(self, user_text: str) -> str:
        t = self.types
        self.history.append(t.Content(role="user", parts=[t.Part(text=user_text)]))
        resp = await self.client.aio.models.generate_content(
            model=self.model,
            contents=self.history,
            config=t.GenerateContentConfig(system_instruction=SYSTEM, tools=[self.session]),
        )
        text = resp.text or ""
        self.history.append(t.Content(role="model", parts=[t.Part(text=text)]))
        return text


AGENTS = {"anthropic": AnthropicAgent, "openai": OpenAIAgent, "gemini": GeminiAgent}


async def main(provider: str) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "jobhunt.server"],
        cwd=str(ROOT),
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print(f"Connected. Server tools: {', '.join(t.name for t in tools)}")
            agent = AGENTS[provider](session, tools)
            print(f"Provider: {provider}. Type 'quit' to exit.\n")
            while True:
                user_text = await asyncio.to_thread(input, "you> ")
                if user_text.strip().lower() in {"quit", "exit"}:
                    break
                if not user_text.strip():
                    continue
                try:
                    print(f"\nassistant> {await agent.turn(user_text)}\n")
                except Exception as exc:  # keep the chat alive on API errors
                    print(f"\n[error] {exc}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=AGENTS, default="anthropic")
    asyncio.run(main(parser.parse_args().provider))
