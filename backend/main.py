import os
import json
import base64
import logging
import traceback
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import (
    SubmissionResponse,
    ApproveRequest,
    RejectRequest,
    RegenerateImageRequest,
    RegenerateImageResponse,
    GenerateVariationsResponse,
    SelectVariationRequest,
    SuccessResponse,
)
from database import (
    get_pending_submissions,
    get_submission_by_id,
    create_submission,
    update_submission,
)
from engines.writing_engine import draft_linkedin_post
from engines.image_router import generate_graphic, regenerate_with_feedback, generate_image_variations
from engines.web_research import process_research_urls

# Configure logging - use INFO level to reduce noise from matplotlib etc.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

load_dotenv()

app = FastAPI(
    title="Claris Writing API",
    description="AI-powered LinkedIn content creation for supply chain professionals",
    version="1.0.0",
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://*.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Claris Writing API"}


@app.post("/api/submit-idea", response_model=SuccessResponse)
async def submit_idea(
    author: str = Form(...),
    idea: Optional[str] = Form(None),
    graphic_description: Optional[str] = Form(None),
    graphic_type: Optional[str] = Form(None),
    chart_data: Optional[str] = Form(None),
    data_sources: Optional[str] = Form(None),
    research_urls: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
):
    """
    Submit a new content idea for AI processing.

    - Accepts form data with author and either idea or graphic_description (or both)
    - If idea provided, generates AI draft using Claude Sonnet 4
    - If graphic_description provided, generates graphics (chart, diagram, or concept)
    - If research_urls provided, fetches and extracts relevant facts
    - Saves to database with status='pending_review'
    """
    try:
        # Debug: Log all received parameters
        logger.info("=" * 50)
        logger.info("RECEIVED SUBMISSION - All Parameters:")
        logger.info(f"  author: '{author}'")
        logger.info(f"  idea: '{idea[:100] if idea else None}...'")
        logger.info(f"  graphic_description: '{graphic_description[:100] if graphic_description else None}...'")
        logger.info(f"  graphic_type: '{graphic_type}'")
        logger.info(f"  chart_data: '{chart_data}'")
        logger.info(f"  data_sources: '{data_sources}'")
        logger.info(f"  research_urls: '{research_urls}'")
        logger.info(f"  image_file: {image_file.filename if image_file else None}")
        logger.info("=" * 50)

        logger.info(f"Received submission from {author}")

        # Validate: must have either idea or graphic_description
        if not idea and not graphic_description and not image_file:
            raise HTTPException(
                status_code=400,
                detail="Must provide either an idea, a graphic description, or an uploaded image"
            )

        # Parse data sources if provided
        parsed_data_sources = None
        if data_sources:
            try:
                parsed_data_sources = json.loads(data_sources)
                logger.info(f"Parsed {len(parsed_data_sources)} data sources")
            except json.JSONDecodeError:
                logger.warning("Failed to parse data_sources JSON")

        # Process research URLs if provided
        research_results = None
        if research_urls:
            try:
                urls = json.loads(research_urls)
                if urls and len(urls) > 0:
                    logger.info(f"Processing {len(urls)} research URLs...")
                    topic = idea if idea else graphic_description if graphic_description else ""
                    research_results = process_research_urls(urls, topic)
                    logger.info(f"Extracted research from {len(research_results)} URLs")
            except json.JSONDecodeError:
                logger.warning("Failed to parse research_urls JSON")

        # Generate AI draft only if idea is provided
        ai_draft = None
        if idea and idea.strip():
            logger.info("Generating AI draft...")
            # Pass research results to the writing engine
            ai_draft = draft_linkedin_post(
                idea,
                author,
                research_data=research_results,
                data_sources=parsed_data_sources
            )
            logger.info(f"AI draft generated: {len(ai_draft)} chars")
        else:
            logger.info("No idea provided, skipping AI draft generation")

        # Handle graphic generation
        graphic_data = None

        if image_file:
            # User uploaded their own image
            logger.info("Processing uploaded image...")
            contents = await image_file.read()
            graphic_data = base64.b64encode(contents).decode("utf-8")
        elif graphic_description:
            # Generate graphic using AI
            print(f"\n[MAIN.PY] ========================================")
            print(f"[MAIN.PY] Graphic generation requested")
            print(f"[MAIN.PY] Description: {graphic_description}")
            print(f"[MAIN.PY] Type from form: '{graphic_type}'")
            print(f"[MAIN.PY] Chart data: {chart_data}")
            print(f"[MAIN.PY] Research results available: {bool(research_results)}")

            # Only pass research data to charts/diagrams, NOT to conceptual/DALL-E images
            # Charts can use real data; conceptual images should stay creative
            should_pass_research = graphic_type in ['chart', 'diagram'] and research_results
            print(f"[MAIN.PY] Will pass research to graphic generator: {should_pass_research}")
            print(f"[MAIN.PY] ========================================\n")

            logger.info(f"Generating graphic: {graphic_type}")
            # Pass chart_data and research_data to generate_graphic
            # research_data is only used for charts/diagrams (ignored for conceptual)
            graphic_data = generate_graphic(
                graphic_description,
                graphic_type,
                chart_data,
                research_data=research_results if should_pass_research else None
            )
            logger.info(f"Graphic generated: {len(graphic_data) if graphic_data else 0} chars")

        # Save to database
        logger.info("Saving to database...")
        submission_data = {
            "author": author,
            "raw_input": idea if idea else "",
            "ai_draft": ai_draft,
            "graphic_description": graphic_description,
            "graphic_type": graphic_type if graphic_type else None,
            "graphic_data": graphic_data,
            "data_sources": parsed_data_sources,
            "research_urls": research_results,
            "status": "pending_review",
        }

        result = create_submission(submission_data)
        logger.info(f"Submission saved: {result}")

        return SuccessResponse(
            success=True,
            message="Your idea has been submitted and is queued for review.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in submit_idea: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pending-submissions", response_model=list[SubmissionResponse])
async def get_pending():
    """
    Get all submissions pending review.

    Returns submissions ordered by created_at DESC.
    """
    try:
        submissions = get_pending_submissions()
        return [SubmissionResponse(**s) for s in submissions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approve-submission/{submission_id}", response_model=SuccessResponse)
async def approve_submission(submission_id: str, request: ApproveRequest):
    """
    Approve a submission with optional edits.

    Updates the submission status to 'approved' and saves any edits.
    """
    try:
        submission = get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        update_data = {
            "status": "approved",
            "ai_draft": request.edited_post,
            "reviewed_at": datetime.utcnow().isoformat(),
        }

        update_submission(submission_id, update_data)

        return SuccessResponse(
            success=True,
            message="Submission approved successfully.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reject-submission/{submission_id}", response_model=SuccessResponse)
async def reject_submission(submission_id: str, request: RejectRequest):
    """
    Reject a submission.

    Updates the submission status to 'rejected'.
    """
    try:
        submission = get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        update_data = {
            "status": "rejected",
            "reviewed_at": datetime.utcnow().isoformat(),
        }

        update_submission(submission_id, update_data)

        return SuccessResponse(
            success=True,
            message="Submission rejected.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/regenerate-image/{submission_id}", response_model=RegenerateImageResponse)
async def regenerate_image_endpoint(submission_id: str, request: RegenerateImageRequest):
    """
    Regenerate the image for a submission based on feedback.

    Returns the new base64-encoded image data.
    """
    try:
        logger.info(f"Regenerate image request for submission {submission_id}")
        logger.info(f"Feedback: {request.feedback}")

        submission = get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        if not submission.get("graphic_type") or not submission.get("graphic_description"):
            raise HTTPException(
                status_code=400,
                detail="This submission does not have graphic generation enabled",
            )

        logger.info(f"Regenerating {submission['graphic_type']} with description: {submission['graphic_description'][:100]}...")

        # Regenerate image with feedback - use correct function name and parameter order
        new_image_data = regenerate_with_feedback(
            original_description=submission["graphic_description"],
            feedback=request.feedback,
            graphic_type=submission["graphic_type"],
        )

        if not new_image_data:
            raise HTTPException(status_code=500, detail="Failed to regenerate image")

        logger.info(f"Image regenerated successfully, updating database...")

        # Update database with new image
        update_submission(submission_id, {"graphic_data": new_image_data})

        return RegenerateImageResponse(new_image_data=new_image_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating image: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-variations/{submission_id}", response_model=GenerateVariationsResponse)
async def generate_variations_endpoint(submission_id: str):
    """
    Generate multiple image variations for a submission.

    Returns an array of 3 base64-encoded images for the user to choose from.
    """
    try:
        logger.info(f"Generate variations request for submission {submission_id}")

        submission = get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        if not submission.get("graphic_type") or not submission.get("graphic_description"):
            raise HTTPException(
                status_code=400,
                detail="This submission does not have graphic generation enabled",
            )

        graphic_type = submission["graphic_type"]
        if graphic_type == "video":
            raise HTTPException(
                status_code=400,
                detail="Variations are not available for video content",
            )

        logger.info(f"Generating 3 variations for {graphic_type}: {submission['graphic_description'][:80]}...")

        variations = generate_image_variations(
            description=submission["graphic_description"],
            graphic_type=graphic_type,
            count=3,
        )

        if not variations:
            raise HTTPException(status_code=500, detail="Failed to generate variations")

        logger.info(f"Generated {len(variations)} variations successfully")

        return GenerateVariationsResponse(variations=variations)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating variations: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/select-variation/{submission_id}", response_model=SuccessResponse)
async def select_variation_endpoint(submission_id: str, request: SelectVariationRequest):
    """
    Select a variation as the main graphic for a submission.
    """
    try:
        logger.info(f"Select variation request for submission {submission_id}")

        submission = get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Update the submission with the selected image
        update_submission(submission_id, {"graphic_data": request.image_data})

        logger.info(f"Variation selected and saved for submission {submission_id}")

        return SuccessResponse(
            success=True,
            message="Selected variation has been set as the main graphic.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting variation: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
