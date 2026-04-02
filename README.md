# 🧠 SemantiCite.ai

> **An Agentic System for Semantic Citation Analysis using Graph RAG**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-AuraDB-008CC1.svg)](https://neo4j.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)

---

## 📖 Overview

SemantiCite.ai is an AI-driven research assistant that goes beyond traditional citation search. Instead of treating citations as simple binary links, it **semantically classifies** the relationships between research papers — distinguishing whether a paper *supports*, *critiques*, *extends*, or *uses the methods* of prior work.

The system autonomously crawls academic literature via the **Semantic Scholar API**, uses **Large Language Models (Google Gemini)** to classify citation intent, stores relationships in a **Neo4j Knowledge Graph**, and presents an interactive visualization through a **React dashboard**.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 React + Cytoscape.js                │
│              Interactive Graph Dashboard             │
└────────────────────────┬────────────────────────────┘
                         │ REST + SSE
┌────────────────────────┴────────────────────────────┐
│              FastAPI + LangGraph Agent              │
│   ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│   │ Semantic  │ │ Citation │ │  LLM Classifier   │  │
│   │ Scholar   │ │ Context  │ │  (Gemini Flash)   │  │
│   │ API Tool  │ │Extractor │ │                   │  │
│   └──────────┘ └──────────┘ └───────────────────┘  │
└────────────────────────┬────────────────────────────┘
                         │ Cypher / Bolt
┌────────────────────────┴────────────────────────────┐
│                   Neo4j AuraDB                      │
│          Papers (Nodes) ↔ Relations (Edges)         │
└─────────────────────────────────────────────────────┘
```

## 🚀 Features

- **Autonomous Citation Crawler** — Agent-based paper discovery via Semantic Scholar API
- **Semantic Relationship Classification** — LLM-powered intent detection (Supports, Critiques, Extends, Uses Method, Basis, Background)
- **Interactive Knowledge Graph** — Cytoscape.js visualization with color-coded edges
- **Context-Aware Search** — Filter citations by intent (e.g., "Show me only critiques of Transformers")
- **Real-time Processing** — SSE-based live updates as the agent discovers papers

## 📁 Project Structure

```
SemantiCite.ai/
├── backend/                  # FastAPI + LangGraph
│   ├── main.py               # App entry point
│   ├── config.py             # Environment config
│   ├── api/                  # REST endpoints
│   ├── agent/                # LangGraph agent + tools
│   └── db/                   # Neo4j client
├── frontend/                 # React + Vite
│   ├── src/
│   │   ├── components/       # UI components
│   │   ├── hooks/            # Custom React hooks
│   │   └── services/         # API client
│   └── index.html
├── docs/                     # Documentation & assets
└── README.md
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Cytoscape.js, Framer Motion |
| Backend | FastAPI, LangGraph, LangChain |
| LLM | Google Gemini Flash |
| Database | Neo4j AuraDB |
| External API | Semantic Scholar Academic Graph API |

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Neo4j AuraDB account (free tier)
- Google AI Studio API key

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # Add your API keys
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 📄 License

This project is developed as part of the MCA IV Semester Major Project at the Department of Computer Science, Jamia Millia Islamia (Feb–May 2026).

## 👤 Author

**Zaki Nafees** — 24MCA058
Supervisor: **Dr. Mansaf Alam**, Professor (DCS)
