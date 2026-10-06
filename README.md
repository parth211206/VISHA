# VISHA — India Snakebite AI Decision-Support & Surveillance System

An AI-assisted clinical decision-support and epidemiological surveillance system for snakebite management in India.

## Overview

Snakebite envenoming is a major public-health problem in India, where rapid identification of the likely snake, assessment of clinical symptoms, and timely treatment decisions can be critical.

**VISHA** aims to provide a unified AI-assisted system that can support clinicians and healthcare professionals by combining:

- Snake species identification from images
- Clinical symptom and syndrome analysis
- Envenomation risk assessment
- Antivenom-related decision support
- Geographic and epidemiological intelligence
- Snake occurrence and distribution data
- Evidence-based clinical information
- Surveillance and reporting capabilities

> **Important:** This project is a research/prototype system and is not intended to replace qualified medical professionals or established clinical protocols.

---

## Project Objectives

The project focuses on developing an integrated pipeline that can:

1. Analyze snake images and identify the most likely species.
2. Process clinical signs and symptoms associated with snakebite.
3. Estimate potential envenomation risk.
4. Combine visual, clinical, geographic, and epidemiological evidence.
5. Provide structured decision-support information for healthcare professionals.
6. Support epidemiological surveillance and analysis.
7. Maintain traceable evidence and reasoning wherever possible.

---

## System Concept

```text
                 ┌─────────────────────┐
                 │   Patient / Case    │
                 │      Input          │
                 └──────────┬──────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
      ┌────────────┐ ┌────────────┐ ┌────────────┐
      │ Snake      │ │ Clinical   │ │ Geographic │
      │ Image      │ │ Symptoms   │ │ Information│
      └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
            │              │              │
            ▼              ▼              ▼
      ┌─────────────────────────────────────────┐
      │          AI / Evidence Pipeline          │
      └────────────────────┬────────────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Risk & Clinical      │
                │ Decision Support     │
                └──────────┬───────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       Clinical Support          Epidemiological
                                  Surveillance
