# Claris Writing - LinkedIn Content Automation

AI-powered LinkedIn content creation system for supply chain professionals.

## Overview

This system allows partners (Tony, Wade, Michael) to submit raw ideas via a web form. AI then:
1. Drafts a professional LinkedIn post (using Claude Sonnet 4)
2. Generates graphics (charts via Python/matplotlib, concepts via DALL-E 3)
3. Queues everything for review
4. Michael reviews/edits/approves via dashboard

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.11+
- **Database**: Supabase (PostgreSQL)
- **AI**: Claude Sonnet 4 (writing), DALL-E 3 (concept images)

## Project Structure

```
claris-writing/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx (submission form)
│   │   └── review/page.tsx (review dashboard)
│   ├── components/
│   │   ├── ContentSubmissionForm.tsx
│   │   └── ReviewDashboard.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── .env.local
├── backend/
│   ├── main.py (FastAPI app)
│   ├── database.py (Supabase connection)
│   ├── models.py (Pydantic models)
│   ├── engines/
│   │   ├── writing_engine.py (Claude AI)
│   │   ├── image_router.py (DALL-E 3)
│   │   └── chart_generator.py (Matplotlib)
│   ├── requirements.txt
│   └── .env
└── README.md
```

## Local Development Setup

### Prerequisites

- Node.js 18+
- Python 3.11+
- Supabase account with "submissions" table

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs at: http://localhost:3000

### Environment Variables

**Backend (.env)**:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
```

**Frontend (.env.local)**:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/submit-idea` | Submit new content idea |
| GET | `/api/pending-submissions` | Get all pending submissions |
| POST | `/api/approve-submission/{id}` | Approve a submission |
| POST | `/api/reject-submission/{id}` | Reject a submission |
| POST | `/api/regenerate-image/{id}` | Regenerate image with feedback |

## Database Schema

The `submissions` table in Supabase:

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| author | VARCHAR | Author name (Tony, Wade, Michael) |
| raw_input | TEXT | Original idea text |
| ai_draft | TEXT | AI-generated LinkedIn post |
| graphic_description | TEXT | Description for image generation |
| graphic_type | VARCHAR | chart, diagram, or concept |
| graphic_data | TEXT | Base64-encoded image |
| status | VARCHAR | pending_review, approved, rejected |
| created_at | TIMESTAMP | Submission timestamp |
| reviewed_at | TIMESTAMP | Review timestamp |

## Deployment

### Frontend (Vercel)

1. Push code to GitHub
2. Import project in Vercel
3. Set environment variables:
   - `NEXT_PUBLIC_API_URL`: Your Railway backend URL

### Backend (Railway)

1. Push code to GitHub
2. Create new project in Railway
3. Connect GitHub repo (backend folder)
4. Set environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`

## TODO: Implementing AI Engines

The engine files contain placeholder logic. To complete the implementation:

### Writing Engine (`engines/writing_engine.py`)

Uncomment and configure the Anthropic client:
```python
from anthropic import Anthropic
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### Image Router (`engines/image_router.py`)

Uncomment and configure the OpenAI client for DALL-E 3:
```python
from openai import OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

### Chart Generator (`engines/chart_generator.py`)

Add AI-powered data extraction using Claude to parse chart descriptions and generate appropriate visualizations.

## Usage

1. **Submit Ideas**: Navigate to http://localhost:3000
   - Select author
   - Enter raw idea
   - Optionally request a graphic
   - Submit

2. **Review Dashboard**: Navigate to http://localhost:3000/review
   - View pending submissions
   - Edit AI drafts
   - Preview LinkedIn post
   - Regenerate images
   - Approve or reject

## License

Proprietary - Claris Consulting
