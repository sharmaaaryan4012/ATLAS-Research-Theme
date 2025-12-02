# ATLAS Research Theme

The ATLAS Research Theme project is an AI-assisted classification system designed to interpret free-form research descriptions and map them to **LAS-approved academic fields and subfields**.

This tool was developed as part of my internship with the **Applied Technologies for Learning in the Arts & Sciences (ATLAS)** at the University of Illinois Urbana-Champaign.

---

## Overview

The College of Liberal Arts & Sciences has **70+ majors**, with faculty whose research often spans multiple interdisciplinary areas. But there is no unified way for LAS staff to take a raw research description and translate it into the structured taxonomy the college uses.

The Research Theme project solves that.

It takes a plain-language query from a faculty member and returns:

* The most relevant **research fields**
* A refined list of **subfields** within each field
* Short descriptions for each selection
* A validated output that matches the **official LAS taxonomy**

This gives LAS staff a shared language for classification and helps with faculty placement, onboarding, and cross-college comparisons.

---

## Features

### 1. Free-form Query Intake

Users describe their research interest however they want. This becomes the starting point for the entire pipeline.

### 2. Field Classification

The system analyzes the text and identifies the most relevant high-level academic fields.

### 3. Subfield Classification

Within a chosen field, the system drills down into more granular subfields for a sharper classification.

### 4. Output Validation

Every result is checked against LAS’s official taxonomy to keep classifications consistent and accurate.

### 5. Extensible Knowledge Base

Field and subfield data live in editable JSON files so staff can update classifications as academic areas evolve.

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/sharmaaaryan4012/ATLAS-Research-Theme
cd ATLAS-Research-Theme
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your environment

- Create a file named `api.env` in the root directory.
- Add your Gemini API key to it in the following format:

```
GEMINI_API_KEY=your_api_key_here
```

- The app will detect this environment variable and use Gemini for LLM responses.

### 4. Run the pipeline

```bash
python3 main.py
```

You can pass any free-form research description to see the full classification flow.

---

## How It Works

1. **User Request**
   The system accepts a raw research description.

2. **Field Classification**
   An LLM ranks the most likely fields based on LAS mappings.

3. **Subfield Classification**
   For each field, another LLM ranks relevant subfields.

4. **Validation**
   Results are checked against the official taxonomy for accuracy.

---

## Future Directions
* Expand the tool to support **inter-college research classification** across the entire university.
* Enhance and maintain the knowledge base so it evolves with LAS academic priorities.
* Integrate deeper workflows for onboarding, cross-department matching, and faculty profile generation.

---

## Author

**Aaryan Sharma**
**Kirthi Shankar**
Developed during ATLAS Internship, Fall 2025
University of Illinois Urbana-Champaign
