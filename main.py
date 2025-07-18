"""
Nitro-Powered AI nitro-ai-research-agent - Core Implementation (Gemini via GenAI SDK)

This module implements a two‑agent system for conducting research:
1. ResearchAgent: Groq Llama 3 + Tavily Search
2. AnalystAgent: Google Gemini via google‑generativeai SDK

Author: Google Software Engineer
"""

import os
import logging
from datetime import datetime
from typing import List

import streamlit as st
import google.generativeai as genai
from langchain.schema import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from tavily import TavilyClient
from dotenv import load_dotenv

# Load local .env for development
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)


# --- ResearchAgent Class ---

class ResearchAgent:
    """
    ResearchAgent uses Groq Llama 3 + Tavily to gather real-time web data
    and summarize it in chunks to avoid token limits.
    """

    def __init__(self):
        self.groq_api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
        self.tavily_api_key = st.secrets.get("TAVILY_API_KEY", os.getenv("TAVILY_API_KEY"))
        if not (self.groq_api_key and self.tavily_api_key):
            raise ValueError("Missing GROQ_API_KEY or TAVILY_API_KEY")

        self.llm = ChatGroq(
            temperature=0.1,
            groq_api_key=self.groq_api_key,
            model_name="llama3-70b-8192",
        )
        self.tavily = TavilyClient(api_key=self.tavily_api_key)
        logger.info("ResearchAgent initialized")

    def _search_web(self, query: str) -> str:
        """Performs a web search and returns concatenated results."""
        try:
            resp = self.tavily.search(query=query, search_depth="advanced", max_results=3)
            items = resp.get("results", [])
            if not items:
                return "No results."
            out = []
            for it in items:
                content = it.get('content', 'N/A')[:1500]
                out.append(
                    f"Title: {it.get('title', 'N/A')}\n"
                    f"Content: {content}\n"
                    f"URL: {it.get('url', 'N/A')}\n---"
                )
            return "\n".join(out)
        except Exception as e:
            logger.error("Search error", exc_info=True)
            return f"Search failed: {e}"

    def research_topic(self, topic: str) -> str:
        """Researches a topic by running multiple queries and summarizing each."""
        try:
            queries = [
                f"{topic} recent developments",
                f"{topic} key players and companies",
                f"{topic} major challenges and opportunities",
            ]
            summaries = []
            logger.info(f"Starting chunked research for topic: {topic}")
            for q in queries:
                logger.info(f"Running sub-query: {q}")
                web_data = self._search_web(q)
                if web_data == "No results.":
                    continue

                prompt = (
                    f"You are an expert researcher. Synthesize this data on '{topic}':\n\n"
                    f"Query: {q}\n{web_data}\n"
                    f"Provide a concise, factual summary based *only* on the provided data (max 250 words)."
                )
                messages = [
                    SystemMessage(content="You are an expert research analyst."),
                    HumanMessage(content=prompt)
                ]
                resp = self.llm.invoke(messages)
                summaries.append(resp.content)
                logger.info(f"Chunk for '{q}' summarized successfully.")

            if not summaries:
                return "Could not find sufficient information on the topic."

            logger.info("All research chunks summarized. Concatenating for final report.")
            return "\n\n---\n\n".join(summaries)
        except Exception as e:
            logger.error("Research error", exc_info=True)
            return f"Research failed: {e}"


# --- AnalystAgent Class ---

class AnalystAgent:
    """
    AnalystAgent uses Google Generative AI (Gemini) to create a polished report.
    """

    def __init__(self):
        self.gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
        if not self.gemini_key:
            raise ValueError("Missing GEMINI_API_KEY")

        genai.configure(api_key=self.gemini_key)
        self.model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")
        logger.info("AnalystAgent initialized with model: gemini-1.5-flash-latest")

    def create_report(self, research_data: str, topic: str) -> str:
        """Creates a final, detailed report from the summarized research data."""
        try:
            prompt = (
                f"You are a senior research analyst. Create a detailed, well-structured markdown report on '{topic}'.\n\n"
                f"Use the following research summaries to construct your report. Adhere strictly to the provided information.\n\n"
                f"Include the following sections:\n"
                f"- **Executive Summary**\n"
                f"- **Key Findings**\n"
                f"- **Detailed Analysis**\n"
                f"- **Conclusions & Recommendations**\n\n"
                f"--- RESEARCH DATA START ---\n{research_data}\n--- RESEARCH DATA END ---\n\n"
                f"Current date: {datetime.now().strftime('%Y-%m-%d')}"
            )
            gen_config = {"temperature": 0.3, "max_output_tokens": 4096}
            resp = self.model.generate_content(prompt, generation_config=gen_config)
            logger.info("Report generated successfully.")
            return resp.text
        except Exception as e:
            logger.error("Report creation error", exc_info=True)
            return f"Report generation failed: {e}"


# --- ResearchSystem Orchestrator ---

class ResearchSystem:
    """Orchestrates ResearchAgent and AnalystAgent into a full pipeline."""

    def __init__(self):
        self.researcher = ResearchAgent()
        self.analyst = AnalystAgent()
        logger.info("ResearchSystem initialized")


def run_full_research(topic: str) -> str:
    """Executes the complete research and reporting pipeline."""
    try:
        system = ResearchSystem()
        logger.info(f"Starting full research process for topic: {topic}")
        data = system.researcher.research_topic(topic)
        logger.info("Research data collection and summarization complete.")
        report = system.analyst.create_report(data, topic)
        logger.info("Full research process completed.")
        return report
    except Exception as e:
        logger.error("Full research pipeline failed", exc_info=True)
        return f"# Research Failed\n\nAn unexpected error occurred: {e}\n"


if __name__ == "__main__":
    topic_to_research = "The impact of 5G technology on IoT in 2025"
    print(f"--- Running full research for: '{topic_to_research}' ---")
    final_report = run_full_research(topic_to_research)
    print("\n--- FINAL REPORT ---")
    print(final_report)

