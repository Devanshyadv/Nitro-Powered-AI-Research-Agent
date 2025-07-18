from pathlib import Path
import sys
import tempfile
import pytest
import os
from unittest.mock import Mock, patch

# Ensure project root is on the import path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# --- Streamlit secrets + .env fallback ---
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

os.environ['GROQ_API_KEY']   = st.secrets.get("GROQ_API_KEY",   os.getenv("GROQ_API_KEY",   ""))
os.environ['TAVILY_API_KEY'] = st.secrets.get("TAVILY_API_KEY", os.getenv("TAVILY_API_KEY", ""))
os.environ['GEMINI_API_KEY'] = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

# --- Now import the system under test ---
from main import ResearchAgent, AnalystAgent, ResearchSystem, run_full_research

class TestResearchAgent:
    """Test suite for ResearchAgent class."""

    def setup_method(self):
        self.mock_groq_key = "test_groq_key"
        self.mock_tavily_key = "test_tavily_key"

    @patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key", "TAVILY_API_KEY": "test_tavily_key"})
    @patch('main.ChatGroq')
    @patch('main.TavilyClient')
    def test_research_agent_initialization(self, mock_tavily, mock_groq):
        agent = ResearchAgent()
        assert agent.groq_api_key == self.mock_groq_key
        assert agent.tavily_api_key == self.mock_tavily_key
        mock_groq.assert_called_once()
        mock_tavily.assert_called_once()

    def test_research_agent_missing_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing GROQ_API_KEY or TAVILY_API_KEY"):
                ResearchAgent()

    @patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key", "TAVILY_API_KEY": "test_tavily_key"})
    @patch('main.ChatGroq')
    @patch('main.TavilyClient')
    def test_search_web_success(self, mock_tavily_client, mock_groq):
        mock_client = Mock()
        mock_tavily_client.return_value = mock_client
        mock_client.search.return_value = {"results": [{"title": "T", "content": "C", "url": "U"}]}

        agent = ResearchAgent()
        output = agent._search_web("query")

        assert "Title: T" in output
        assert "Content: C" in output
        assert "URL: U" in output
        mock_client.search.assert_called_once()

    @patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key", "TAVILY_API_KEY": "test_tavily_key"})
    @patch('main.ChatGroq')
    @patch('main.TavilyClient')
    def test_search_web_failure(self, mock_tavily_client, mock_groq):
        mock_client = Mock()
        mock_tavily_client.return_value = mock_client
        mock_client.search.side_effect = Exception("fail")

        agent = ResearchAgent()
        output = agent._search_web("query")
        assert "Search failed" in output
        assert "fail" in output

    @patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key", "TAVILY_API_KEY": "test_tavily_key"})
    @patch('main.ChatGroq')
    @patch('main.TavilyClient')
    def test_research_topic_flow(self, mock_tavily_client, mock_groq):
        mock_client = Mock(); mock_tavily_client.return_value = mock_client
        mock_client.search.return_value = {"results": [{"title": "T", "content": "C", "url": "U"}]}

        mock_llm = Mock(); mock_groq.return_value = mock_llm
        resp = Mock(); resp.content = "sum"
        mock_llm.invoke.return_value = resp

        agent = ResearchAgent()
        summary = agent.research_topic("Topic")
        assert summary == "sum"

class TestAnalystAgent:
    """Test suite for AnalystAgent class (Gemini via GenAI SDK)."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('google.generativeai.models.get')
    def test_initialization(self, mock_get):
        fake_model = Mock()
        mock_get.return_value = fake_model

        agent = AnalystAgent()

        mock_get.assert_called_once_with("gemini-1.5-flash-latest")
        assert agent.model is fake_model

    def test_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing GEMINI_API_KEY"):
                AnalystAgent()

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('google.generativeai.models.get')
    def test_create_report_success(self, mock_get):
        fake_model = Mock()
        fake_resp = Mock()
        fake_resp.text = "## Report"
        fake_model.generate_content.return_value = fake_resp
        mock_get.return_value = fake_model

        agent = AnalystAgent()
        report = agent.create_report("data", "Topic")

        fake_model.generate_content.assert_called_once()
        assert "## Report" in report

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch('google.generativeai.models.get')
    def test_create_report_failure(self, mock_get):
        fake_model = Mock()
        fake_model.generate_content.side_effect = Exception("API Error")
        mock_get.return_value = fake_model

        agent = AnalystAgent()
        result = agent.create_report("data", "Topic")
        assert "Report generation failed" in result
        assert "API Error" in result

class TestResearchSystem:
    @patch.dict(os.environ, {"GROQ_API_KEY": "gk", "TAVILY_API_KEY": "tk", "GEMINI_API_KEY": "gk2"})
    @patch('main.ResearchAgent')
    @patch('main.AnalystAgent')
    def test_init(self, mock_res, mock_ana):
        system = ResearchSystem()
        mock_res.assert_called_once(); mock_ana.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_init_fail(self):
        with pytest.raises(Exception):
            ResearchSystem()

class TestRunFullResearch:
    @patch.dict(os.environ, {"GROQ_API_KEY": "gk", "TAVILY_API_KEY": "tk", "GEMINI_API_KEY": "gk2"})
    @patch('main.ResearchSystem')
    def test_success(self, mock_sys):
        inst = Mock(); mock_sys.return_value = inst
        inst.researcher.research_topic.return_value = "d"
        inst.analyst.create_report.return_value = "r"
        assert run_full_research("T") == "r"

    @patch.dict(os.environ, {}, clear=True)
    def test_fail(self):
        assert "Research Failed" in run_full_research("T")
