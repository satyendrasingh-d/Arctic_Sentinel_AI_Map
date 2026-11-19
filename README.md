# Arctic_Sentinel_AI_Map
Live Data Project : https://arctic-sentinel-ai-map-vdt3.onrender.com

🏔️ Arctic Sentinel AI: Route Risk Analysis & Intelligence Model
📌 Project Overview
This model is an AI-Powered Route Intelligence System specifically designed for the Arctic and extreme-weather regions (such as Yakutsk, Magadan, and Svalbard). Its primary objective is to analyze safe routes for travelers and communities, providing critical alerts about potential hazards in extreme conditions.

The system calculates the optimal path between Start and End locations and computes real-time risk probabilities for various coordinates along the journey.

🚀 Core Capabilities & Features
Dynamic Route Generation: Utilizes OSRM (Open Source Routing Machine) to generate a continuous and highly accurate path from origin to destination.
Risk Assessment Engine: Analyzes weather APIs and geographical parameters to assign a precise Risk Percentage to individual points along the route.
Zone Categorization: Smartly classifies risk into 3 distinct tiers:
🟢 Low Risk (0-35%)
🟡 Medium Risk (36-55%)
🔴 High Risk (56-100%)
Interactive Geo-Visualization: Plots the processed data onto a full-screen interactive map using Leaflet.js and OpenStreetMap, complete with real-time user device location (GPS) tracking.
🛠️ Technology Stack
Backend Engine: FastAPI (Python) for high-performance, rapid API responses.
Routing & Data: OSRM, OpenWeather API, and SQLite (for administrative search logging).
Frontend Visualization: HTML5, CSS3, Vanilla JavaScript, and Leaflet.js.
Data Flow: Browser Render Clouds for instant, zero-latency state transfer between the main dashboard and the full-screen map view.
🎯 Objective of this Notebook
This notebook demonstrates the core logic, data processing pipelines, API integrations, and overall backend architecture of the route-risk assessment model, providing a comprehensive deep dive into how the system engine operates.
