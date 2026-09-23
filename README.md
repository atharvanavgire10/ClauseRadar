# ClauseRadar

### From contract clauses to actions.

**ClauseRadar** is a contract obligation and risk operations platform that turns unstructured agreements into **trackable obligations, deadlines, risks, owners, evidence, and actionable workflows**.

Instead of stopping at *"summarize this contract"*, ClauseRadar transforms contract documents into an operational system where teams can discover what they are responsible for, verify the source evidence, track deadlines, review risks, and maintain an auditable history.

<p align="center">
  <a href="https://clause-radar-lcjfdq3yg-atharvas-projects-d1719307.vercel.app/">
    <strong>🚀 Live Demo</strong>
  </a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="https://github.com/atharvanavgire10/ClauseRadar">
    <strong>GitHub Repository</strong>
  </a>
</p>

---

## 🚀 Live Demo

**Production:**
https://clause-radar-lcjfdq3yg-atharvas-projects-d1719307.vercel.app/

The public evaluation workspace allows recruiters, judges, and reviewers to explore the platform without creating an account.

### Recommended demo flow

```text
Open ClauseRadar
      ↓
Explore Workspace
      ↓
Browse Contracts
      ↓
Open a Contract
      ↓
Inspect Clauses & Obligations
      ↓
View Source Evidence
      ↓
Inspect Risks & Deadlines
      ↓
Modify an Obligation
      ↓
Review Audit Trail
      ↓
Search / Compare Versions
      ↓
Upload & Process a Contract
```

---

# 🎯 The Problem

Contracts contain critical operational information:

* Payment obligations
* Renewal dates
* Notice periods
* Service-level commitments
* Deliverables
* Compliance requirements
* Termination conditions
* Reporting requirements
* Penalties
* Responsibilities assigned to specific parties

But this information is usually buried inside long PDF or DOCX documents.

Traditional contract workflows often leave teams asking:

> What exactly do we need to do?

> When is it due?

> Who owns it?

> What happens if we miss it?

> Where does the contract actually say that?

> Has this obligation changed between versions?

A contract summary can answer *"what does this document generally say?"*

It does not necessarily answer:

**"What actions do we need to take, and what evidence supports them?"**

---

# 💡 The Solution

ClauseRadar converts contracts into an operational layer.

```text
Contract Document
       │
       ▼
Document Processing
       │
       ▼
Clause Extraction
       │
       ▼
Obligation Extraction
       │
       ▼
Evidence & Source Mapping
       │
       ▼
Human Verification
       │
       ▼
Deadlines + Risks + Ownership
       │
       ▼
Operational Tracking
       │
       ▼
Audit Trail & Search
```

Every extracted item is designed to remain connected to its source evidence.

This makes the system useful not only for understanding contracts, but for **acting on them**.

---

# ✨ Core Features

## 📄 Contract Ingestion

Upload supported contract documents and process them into structured data.

Supported formats include:

* PDF
* DOCX

The ingestion pipeline includes:

* File validation
* Extension and magic-byte verification
* File-size validation
* Filename sanitization
* SHA-256 duplicate detection
* Secure document storage
* Document processing
* Extraction failure handling

---

## 🔍 Clause Extraction

Contracts are transformed into structured clauses that can be reviewed independently.

Each clause can retain:

* Clause text
* Clause type
* Source document
* Source page
* Evidence text
* Confidence
* Review status

---

## ✅ Obligation Extraction

ClauseRadar identifies actionable contractual obligations.

An obligation can contain:

* Description
* Responsible party
* Owner
* Reviewer
* Status
* Due date
* Recurrence
* Evidence
* Source clause
* Review state

This converts passive contract text into an actionable work queue.

---

## 📅 Deadline & Recurrence Tracking

Contractual dates are converted into operational deadlines.

Examples:

```text
Payment due → 30 days after invoice

Renewal → 90 days before contract expiry

Notice → 60 days before termination

Reporting → Monthly
```

Recurring obligations can also be represented as operational deadlines.

---

## ⚠️ Risk Analysis

ClauseRadar surfaces contract risks associated with extracted obligations and clauses.

Risk information can be connected to:

* Contract
* Clause
* Obligation
* Evidence
* Severity
* Status
* Review state

The goal is to provide **traceable risk information**, rather than unexplained AI-generated conclusions.

---

## 👤 Ownership & Review

Responsibilities can be assigned to people or roles.

Teams can track:

* Who owns an obligation
* Who reviews it
* Current status
* Review state
* Completion state

This creates a clear operational responsibility chain.

---

## 🔎 Evidence-First Design

One of ClauseRadar's core design principles is:

> **AI/extracted information should be traceable back to the source document.**

Instead of showing an isolated generated statement, ClauseRadar can associate information with:

```text
Contract
   ↓
Document
   ↓
Page
   ↓
Clause
   ↓
Obligation
   ↓
Evidence
```

This allows users to verify where an extracted obligation or risk came from.

---

## 🧾 Audit Trail

Important changes are recorded through an audit trail.

This allows users to understand:

* What changed
* Which object changed
* Who performed the action
* Previous state
* New state
* When the change occurred

This is particularly important for operational contract management.

---

## 🔄 Contract Version Comparison

Contracts can have multiple versions.

ClauseRadar supports version-aware workflows so teams can inspect how contracts evolve over time.

This makes it possible to investigate changes to:

* Clauses
* Obligations
* Contract terms
* Deadlines
* Operational requirements

---

## 🤖 Evidence-Grounded Q&A

ClauseRadar provides contract-oriented Q&A using the structured contract data and source evidence.

The objective is not simply to generate an answer.

The system is designed around:

```text
Question
   ↓
Relevant Contract Data
   ↓
Relevant Evidence
   ↓
Answer
   ↓
Source Citations
```

This keeps contract questions connected to the underlying data.

---

# 🧠 AI Architecture

ClauseRadar uses an AI-provider abstraction rather than tightly coupling the application to one model provider.

Conceptually:

```text
                 ┌──────────────────┐
                 │   ClauseRadar UI  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │   Django / DRF   │
                 └────────┬─────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      ┌────────────────┐      ┌────────────────┐
      │ Deterministic  │      │ AI Provider    │
      │ Processing     │      │ Abstraction    │
      └───────┬────────┘      └───────┬────────┘
              │                       │
              └───────────┬───────────┘
                          ▼
                 ┌──────────────────┐
                 │ Structured Data  │
                 └──────────────────┘
```

The application is designed so that core workflows remain useful without requiring an external AI provider.

---

# 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────┐
│                    React Frontend                   │
│                                                     │
│  Dashboard • Contracts • Obligations • Risks       │
│  Search • Evidence • Audit • Version Comparison    │
└────────────────────────┬────────────────────────────┘
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────┐
│                 Django + DRF Backend                │
│                                                     │
│  Authentication                                     │
│  Contract Management                                │
│  Clause Extraction                                  │
│  Obligation Management                              │
│  Risk Analysis                                      │
│  Evidence                                           │
│  Audit Logging                                      │
│  Evaluation Workspace                               │
└───────────────┬──────────────────┬──────────────────┘
                │                  │
                ▼                  ▼
       ┌────────────────┐   ┌────────────────────┐
       │ PostgreSQL     │   │ Document Storage   │
       │                │   │                    │
       │ Contracts      │   │ Vercel Blob        │
       │ Clauses        │   │ Private Files      │
       │ Obligations    │   │                    │
       │ Risks          │   └────────────────────┘
       │ Audit Events   │
       └────────────────┘

                ┌────────────────────┐
                │ Document Processing│
                │                    │
                │ PyMuPDF            │
                │ python-docx        │
                │ OCR fallback       │
                └────────────────────┘
```

---

# 🛠️ Tech Stack

## Frontend

* React
* Vite
* JavaScript
* CSS
* Playwright

## Backend

* Python
* Django
* Django REST Framework
* PostgreSQL

## Document Processing

* PyMuPDF
* python-docx
* Optional OCR processing
* SHA-256 document deduplication

## Infrastructure

* Vercel
* Vercel Blob
* Vercel Cron
* WhiteNoise

## Development & Testing

* Git
* GitHub
* Pytest / Django test suite
* Vitest
* Playwright
* ESLint / TypeScript type checking where applicable

---

# 🔐 Security

Security was treated as a first-class part of the implementation.

### CSRF Protection

Browser mutations are protected with Django CSRF validation.

The production browser flow explicitly verifies:

```text
GET application
      ↓
CSRF cookie
      ↓
Browser mutation
      ↓
X-CSRFToken
      ↓
Django validation
```

The production E2E test also verifies the previously discovered session-cookie CSRF scenario.

### Tenant Isolation

Private workspace data is permission checked so users cannot access another workspace's contracts or documents.

### Public Evaluation Isolation

The recruiter evaluation environment is deliberately isolated from private workspace data.

### File Security

Uploads include:

* File type validation
* Magic-byte validation
* Extension validation
* Filename sanitization
* Size limits
* Duplicate detection
* Permission-checked downloads

### Private Document Storage

Production documents use private storage rather than exposing public storage URLs.

### Cron Security

Internal scheduled endpoints require the configured cron secret.

### Secrets

Sensitive configuration is supplied through environment variables rather than committed source code.

---

# 🚀 Running Locally

## 1. Clone

```bash
git clone https://github.com/atharvanavgire10/ClauseRadar.git

cd ClauseRadar
```

---

## 2. Backend setup

Create and activate a Python virtual environment:

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 3. Environment variables

Create a `.env` file based on the project's environment configuration.

Typical configuration includes:

```env
DEBUG=True

SECRET_KEY=your-secret-key

DATABASE_URL=your-postgresql-url

ALLOWED_HOSTS=localhost,127.0.0.1

CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Do not commit `.env` files or production secrets.

---

## 4. Database

Run migrations:

```bash
python manage.py migrate
```

Create an administrator if required:

```bash
python manage.py createsuperuser
```

---

## 5. Start Django

```bash
python manage.py runserver
```

Backend:

```text
http://127.0.0.1:8000
```

---

## 6. Start frontend

From the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 🧪 Testing

ClauseRadar has automated backend, frontend, and production browser coverage.

### Backend

```bash
pytest
```

Current release verification:

```text
171 passed
4 skipped
```

### Frontend

```bash
npm test
```

Current release verification:

```text
9 passed
```

### Type checking

```bash
npm run typecheck
```

### Production build

```bash
npm run build
```

### Django checks

```bash
python manage.py check
python manage.py makemigrations --check
```

### Production E2E

The repository includes a permanent Playwright regression test covering the production CSRF/session flow.

The release was verified against the live Vercel deployment using real Chromium.

```text
1 passed
```

The production E2E flow covers:

* CSRF bootstrap
* Public evaluation session
* Contract browsing
* Contract details
* Obligations
* Source evidence
* Mutations
* Direct SPA routes
* Refresh
* Back/forward navigation
* Session-cookie browser flow
* Register
* Login
* Logout
* Unexpected 403 detection
* Console error detection

---

# ☁️ Vercel Deployment

ClauseRadar is designed to run as a Vercel-native Django deployment.

Production architecture avoids requiring a continuously running worker process.

The production deployment uses:

```text
Vercel
├── Django application
├── React/Vite frontend
├── PostgreSQL
├── Vercel Blob
└── Vercel Cron
```

### Production build flow

```text
Vercel Build
     │
     ├── Install Python dependencies
     ├── Run production migrations
     ├── Seed evaluation workspace
     ├── Build React frontend
     ├── Synchronize SPA assets
     └── Deploy Django application
```

### Production health endpoint

```text
/api/ready/
```

Expected response:

```json
{
  "ready": true,
  "checks": {
    "database": "ok"
  },
  "ai_provider": "none"
}
```

---

# 📊 Evaluation Workspace

ClauseRadar includes a public evaluation workspace designed for recruiters, judges, and reviewers.

The evaluation environment contains seeded contract data so the product can be explored immediately without requiring an external account.

Current seeded dataset:

```text
6 contracts
8 contract versions
8 documents
41 clauses
41 obligations
82 deadlines
43 risks
```

The evaluation workspace can be reset through the application's controlled reset mechanism.

---

# 🗂️ Project Structure

```text
ClauseRadar/
│
├── backend/
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── contracts/
│   ├── documents/
│   ├── obligations/
│   ├── risks/
│   ├── audit/
│   ├── eval/
│   └── cron/
│
├── frontend/
│   ├── src/
│   ├── e2e/
│   └── package.json
│
├── scripts/
│   └── vercel-build.sh
│
├── tests/
│
├── vercel.json
├── requirements.txt
├── .python-version
└── README.md
```

---

# 🔄 Core Data Model

At a high level:

```text
Workspace
   │
   └── Contract
          │
          ├── Contract Version
          │       │
          │       └── Document
          │
          ├── Clauses
          │       │
          │       └── Evidence
          │
          ├── Obligations
          │       │
          │       ├── Owner
          │       ├── Reviewer
          │       ├── Deadlines
          │       └── Evidence
          │
          ├── Risks
          │
          └── Audit Events
```

This structure allows contract information to remain connected from the original document through to the operational action.

---

# 🎬 Recruiter / Judge Demo

If you have only 2–3 minutes to demonstrate ClauseRadar, use this sequence:

### 1. Start with the problem

> Contracts contain important obligations, but those obligations are buried inside documents and are difficult to operationalize.

### 2. Open the live demo

Show the public evaluation workspace.

### 3. Open a contract

Show:

* Contract metadata
* Clauses
* Obligations
* Risks
* Deadlines

### 4. Click an obligation

Demonstrate:

```text
Obligation
   ↓
Owner
   ↓
Deadline
   ↓
Risk
   ↓
Source evidence
```

### 5. Show source evidence

Open the original source text and demonstrate that the extracted information can be traced back to the contract.

### 6. Change an obligation

Modify its operational state and show the audit trail.

### 7. Show version comparison

Demonstrate that different contract versions can be investigated.

### 8. Finish with the key message

> **ClauseRadar doesn't just summarize contracts. It turns contract language into operational actions.**

---

# 🧭 Design Principles

ClauseRadar is built around several principles:

### Evidence over unsupported claims

Important extracted information should remain traceable to source material.

### Operations over summaries

The goal is not merely understanding a contract.

The goal is knowing:

```text
What?
Who?
When?
Why?
Where does it say that?
What changed?
What happened?
```

### Human verification

Extracted information can be reviewed rather than blindly trusted.

### Deterministic fallback

Core product workflows should remain useful when an external AI provider is unavailable.

### Security by default

Tenant boundaries, CSRF protection, upload validation, private storage, and authenticated mutations are treated as product requirements.

---

# 🗺️ Roadmap

Potential future extensions include:

* Advanced semantic contract search
* More sophisticated obligation extraction
* Multi-document cross-contract analysis
* Email/calendar integrations
* Deadline notifications
* Advanced approval workflows
* Contract policy enforcement
* More powerful version-diff analysis
* On-premise deployment
* Additional document formats
* Enterprise SSO
* Advanced analytics and reporting

---

# 📌 Project Status

**Status: Production Ready**

ClauseRadar has been deployed to Vercel and verified using:

* Automated backend tests
* Frontend tests
* Type checking
* Production build checks
* Django security checks
* Database migration checks
* Live API smoke tests
* Real Chromium Playwright testing against production

The production evaluation workspace has also been reset to a clean seeded state.

---

# 👨‍💻 Author

**Atharva Navgire**

Full Stack Developer | AI & Backend Engineering

GitHub:
https://github.com/atharvanavgire10

---

# ⭐ Why ClauseRadar?

Most contract tools stop at:

```text
Upload → Extract → Summarize
```

ClauseRadar is designed around:

```text
Upload
   ↓
Understand
   ↓
Verify
   ↓
Assign
   ↓
Track
   ↓
Act
   ↓
Audit
```

### **From contract clauses to actions.**

If you find the project useful, consider giving the repository a ⭐.
