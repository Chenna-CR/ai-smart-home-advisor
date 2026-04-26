# Project Status: Smart Home Appliance Buyer Guide (v3.1.0) - Hybrid AI Edition

This document provides a comprehensive overview of the **Smart Home Appliance Buyer Guide** project, currently featuring a **Hybrid AI Architecture**.

## 🚀 1. Overview
Version 3.1.0 transitions from a pure LLM-based approach to a **Hybrid Academic Architecture**. It integrates core AI concepts like **State Space Search (Unit II)**, **Feature Engineering (Unit III)**, and **Local NLP (Unit IV)** directly into the Python backend, using the LLM exclusively for high-level reasoning and natural language generation.

---

## 🏗️ 2. System Architecture (Hybrid Edition)

The project follows a **Multi-Stage AI Pipeline**:

1.  **Stage 1: Intent Extraction (NLP)**
    - Uses Groq (Llama-3) to parse user queries into structured requirements.
2.  **Stage 2: Search Space Generation**
    - Real-time product discovery via SerpAPI (Google Shopping).
3.  **Stage 3: Heuristic State Space Search (Unit II)**
    - **Algorithmic Selection**: Implements a local `HeuristicSearchEngine` using **A* logic**.
    - **Cost Function $f(n) = g(n) + h(n)$**: 
        - $g(n)$: Path cost (Normalized Price).
        - $h(n)$: Heuristic score (Euclidean distance between product features and user intent).
4.  **Stage 4: Data-Centric Feature Engineering (Unit III)**
    - **Normalization**: Numerical specs (Price, Ratings) are scaled using `MinMaxScaler`.
5.  **Stage 5: Local Sentiment Analysis (Unit IV)**
    - Uses standard Python libraries (`TextBlob`) to perform sentiment analysis on product snippets.
    - **Penalty Multiplier**: If sentiment is negative ($< 0$), a 20% penalty is applied to the final score.
6.  **Stage 6: Final Reasoning (Chain-of-Thought)**
    - Groq AI explains the mathematical "Ground Truth" calculated by the Python engine using prompt engineering patterns.

---

## 🛠️ 3. Technology Stack (v3.1.0)

| Layer | Technology | Academic Unit |
| :--- | :--- | :--- |
| **Backend Core** | FastAPI (Python) | - |
| **Logic & ML** | NumPy, Scikit-learn | Unit III (ML Concepts) |
| **Local NLP** | TextBlob | Unit IV (NLP) |
| **Search Engine** | SerpAPI + Custom A* Search Subsystem | Unit II (Search) |
| **LLM Interface** | Groq (Llama-3.3) | Unit V (Prompts) |
| **Visualization** | Chart.js | - |

---

## 🌟 4. Mathematical Foundation

### **1. Heuristic Distance Calculation**
The system treats users as a **Target Vector $T = [Price=0, Rating=1, Features=1]$**. For each product $P$, the heuristic $h(n)$ is:
$$h(n) = \sqrt{(P_{price} - T_{price})^2 + (P_{rating} - T_{rating})^2 + (P_{features} - T_{features})^2}$$

### **2. Natural Language Preprocessing**
Products are penalized based on local NLP analysis:
- **Polarity $>$ 0**: High Confidence (Multiplier 1.0)
- **Polarity $<$ 0**: Low Confidence (Multiplier 0.8)

---

## 📁 5. Deployment & Execution
- **Main App**: [main.py](file:///c:/Users/chenn/Documents/Smart%20Home%20Appliance%20Buyer%20Guide/backend/app/main.py)
- **Heuristic Engine**: [shopping_service.py](file:///c:/Users/chenn/Documents/Smart%20Home%20Appliance%20Buyer%20Guide/backend/app/shopping_service.py)
- **CoT Reasoning**: [ai_service.py](file:///c:/Users/chenn/Documents/Smart%20Home%20Appliance%20Buyer%20Guide/backend/app/ai_service.py)
- **Frontend**: [advisor.html](file:///c:/Users/chenn/Documents/Smart%20Home%20Appliance%20Buyer%20Guide/backend/app/templates/advisor.html)

**Run Command**:
```bash
uvicorn app.main:app --reload
```
