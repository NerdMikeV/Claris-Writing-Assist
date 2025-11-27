

from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
import os
import traceback
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import io
import base64

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Configure Google AI if API key is available
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

CLARIS_COLORS = {
    'primary': '#0077B5',
    'secondary': '#00A0DC',
    'dark': '#005582',
    'accent': '#FF6B35',
    'gray': '#666666'
}

def classify_graphic_type(description: str) -> str:
    """
    Auto-detect what type of graphic is needed.

    Priority:
    1. Check for video keywords -> 'video' (Veo 3.1)
    2. Check for infographic keywords -> 'infographic' (Nano Banana Pro)
    3. Check for explicit chart keywords -> 'chart' (Matplotlib)
    4. Check for explicit diagram keywords -> 'diagram' (Matplotlib)
    5. Default to 'conceptual' (DALL-E) for everything else

    IMPORTANT: Descriptions asking for "image of", "picture of", "rendering of",
    "view of", "scene of", etc. should go to DALL-E, NOT charts.
    """
    desc_lower = description.lower()

    # VIDEO keywords - route to Veo 3.1
    video_keywords = [
        'video', 'animation', 'animated', 'motion graphics',
        'moving', 'clip', 'footage', 'movie'
    ]

    if any(keyword in desc_lower for keyword in video_keywords):
        return 'video'

    # INFOGRAPHIC keywords - route to Nano Banana Pro (better for text-heavy images)
    infographic_keywords = [
        'infographic', 'stats', 'statistics visualization',
        'data visualization with text', 'text-heavy', 'diagram with text',
        'comparison chart with labels', 'data summary', 'key metrics',
        'stat card', 'data card', 'metrics dashboard'
    ]

    if any(keyword in desc_lower for keyword in infographic_keywords):
        return 'infographic'

    # EXPLICIT chart keywords - only route to chart if these are present
    # Must be specific chart types, not generic data words
    chart_keywords = [
        'bar chart', 'line chart', 'pie chart', 'area chart',
        'histogram', 'scatter plot', 'scatter chart',
        'column chart', 'stacked chart', 'donut chart',
        'bar graph', 'line graph', 'pie graph',
        'data visualization chart', 'chart showing data',
        'graph of', 'chart of'
    ]

    if any(keyword in desc_lower for keyword in chart_keywords):
        return 'chart'

    # EXPLICIT diagram keywords
    diagram_keywords = [
        'venn diagram', 'flowchart', 'flow chart', 'flow diagram',
        'process diagram', 'org chart', 'organization chart',
        'architecture diagram', 'network diagram', 'system diagram',
        'sequence diagram', 'state diagram', 'er diagram',
        'uml diagram', 'block diagram'
    ]

    if any(keyword in desc_lower for keyword in diagram_keywords):
        return 'diagram'

    # Everything else goes to DALL-E for conceptual/rendered images
    # This includes: "image of", "picture of", "rendering of", "view of",
    # "scene of", "illustration of", "warehouse", "interior", etc.
    return 'conceptual'

def generate_graphic(description: str, graphic_type: str = None, chart_data: str = None, research_data: list = None) -> str:
    """Route to appropriate image generation engine. Returns base64 encoded image or video.

    Args:
        description: Text description of the graphic
        graphic_type: Type of graphic (chart, diagram, conceptual, infographic, video)
        chart_data: Optional JSON string with chart data points
        research_data: Optional list of research results with extracted facts (only used for charts/diagrams/infographics)
    """
    print(f"\n[IMAGE ROUTER] ========================================")
    print(f"[IMAGE ROUTER] Description: {description}")
    print(f"[IMAGE ROUTER] Requested type from form: {graphic_type}")
    print(f"[IMAGE ROUTER] Research data provided: {bool(research_data)}")
    if research_data:
        fact_count = sum(len(r.get('extracted_facts', [])) for r in research_data if r)
        print(f"[IMAGE ROUTER] Total extracted facts: {fact_count}")

    original_type = graphic_type

    if not graphic_type or graphic_type == 'auto' or graphic_type == 'none':
        graphic_type = classify_graphic_type(description)
        print(f"[IMAGE ROUTER] Auto-classified type: {graphic_type}")
    else:
        print(f"[IMAGE ROUTER] Using requested type: {graphic_type}")

    # Determine routing
    if graphic_type == 'video':
        print(f"[IMAGE ROUTER] Routing to: VEO 3.1 (video)")
        print(f"[IMAGE ROUTER] ========================================\n")
        return generate_veo_video(description)
    elif graphic_type == 'infographic':
        print(f"[IMAGE ROUTER] Routing to: NANO BANANA PRO (infographic)")
        print(f"[IMAGE ROUTER] ========================================\n")
        return generate_nano_banana_image(description, research_data)
    elif graphic_type == 'chart':
        print(f"[IMAGE ROUTER] Routing to: MATPLOTLIB (chart)")
        print(f"[IMAGE ROUTER] ========================================\n")
        return generate_chart(description, chart_data, research_data)
    elif graphic_type == 'conceptual' or graphic_type == 'concept':
        print(f"[IMAGE ROUTER] Routing to: DALL-E (conceptual)")
        print(f"[IMAGE ROUTER] NOTE: Research data NOT passed to DALL-E (keeping it creative)")
        print(f"[IMAGE ROUTER] ========================================\n")
        return generate_dalle_image(description)
    elif graphic_type == 'diagram':
        print(f"[IMAGE ROUTER] Routing to: MATPLOTLIB (diagram)")
        print(f"[IMAGE ROUTER] ========================================\n")
        return generate_chart(description, chart_data, research_data)
    else:
        print(f"[IMAGE ROUTER] Unknown type '{graphic_type}', defaulting to: DALL-E")
        print(f"[IMAGE ROUTER] ========================================\n")
        return generate_dalle_image(description)

def _format_research_for_chart(research_data: list) -> str:
    """Extract statistics and facts from research data for chart generation."""
    if not research_data:
        return ""

    facts_text = []
    for result in research_data:
        if not result or result.get('error'):
            continue

        source_name = result.get('source_name', 'Unknown')
        extracted_facts = result.get('extracted_facts', [])

        for fact in extracted_facts:
            fact_text = fact.get('fact', '')
            fact_type = fact.get('type', '')

            # Prioritize statistics and findings for charts
            if fact_type in ['statistic', 'finding', 'trend'] and fact_text:
                facts_text.append(f"- {fact_text} (Source: {source_name})")

    if facts_text:
        return "\n".join(facts_text)
    return ""


def generate_chart(description: str, chart_data: str = None, research_data: list = None) -> str:
    """Generate chart using Claude to write matplotlib code, then execute it.

    Args:
        description: Text description of the chart
        chart_data: Optional JSON string with data like:
            {"startValue": "100", "endValue": "150", "timePeriod": "6 months", "dataPoints": ""}
            or {"dataPoints": "Q1: 100, Q2: 120, Q3: 145, Q4: 180"}
        research_data: Optional list of research results with extracted facts/statistics
    """
    import json

    print(f"\n[CHART] ========================================")
    print(f"[CHART] Generating chart for: {description[:100]}...")
    print(f"[CHART] Chart data provided: {bool(chart_data)}")
    print(f"[CHART] Research data provided: {bool(research_data)}")

    # Parse chart data if provided
    data_instruction = ""
    has_real_data = False

    # First, check for research data with extracted facts
    if research_data:
        research_facts = _format_research_for_chart(research_data)
        if research_facts:
            data_instruction = f"\n\nIMPORTANT - USE REAL DATA FROM RESEARCH SOURCES:\nThe following statistics were extracted from research URLs. Use these EXACT values in your chart:\n{research_facts}\n\nExtract the relevant numbers from these facts and use them as your data points. Cite the source in a small footnote or caption.\n"
            has_real_data = True
            print(f"[CHART] Using research data with {len(research_facts.split(chr(10)))} facts")

    # Then check for manually entered chart data (takes priority if both exist)
    if chart_data:
        try:
            data = json.loads(chart_data)

            # Check if user provided actual data
            if data.get('dataPoints') and data['dataPoints'].strip():
                data_instruction = f"\n\nIMPORTANT - USE THESE EXACT DATA POINTS (user-provided):\n{data['dataPoints']}\n"
                has_real_data = True
                print(f"[CHART] Using user-provided data points")
            elif data.get('startValue') and data.get('endValue'):
                data_instruction = f"\n\nIMPORTANT - USE THESE EXACT VALUES (user-provided):\n- Start value: {data['startValue']}\n- End value: {data['endValue']}"
                if data.get('timePeriod'):
                    data_instruction += f"\n- Time period: {data['timePeriod']}"
                data_instruction += "\n"
                has_real_data = True
                print(f"[CHART] Using user-provided start/end values")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[CHART] Warning: Failed to parse chart_data: {e}")

    # Add subtitle note if using illustrative data
    subtitle_instruction = ""
    if not has_real_data:
        subtitle_instruction = "\n8. Add a small italic subtitle under the title: '(Illustrative example data)'"
        print(f"[CHART] No real data - will add illustrative disclaimer")
    else:
        print(f"[CHART] Has real data - no illustrative disclaimer needed")

    print(f"[CHART] ========================================")

    prompt = f"""Write Python matplotlib code to create this chart:

"{description}"{data_instruction}

REQUIREMENTS:
1. Use Claris AI brand colors: primary blue #0077B5, light blue #00A0DC, dark blue #005582
2. Figure size: (12, 6.75) for LinkedIn (1200x675px)
3. DPI: 150
4. Professional styling: remove top and right spines, add light grid on y-axis, clear title (16pt bold), axis labels (12pt), white background
5. {"Use the exact data values provided above" if has_real_data else "Use realistic example data since no specific numbers were provided"}
6. DO NOT call plt.show()
7. Return complete runnable code{subtitle_instruction}

Output ONLY the Python code, no markdown, no explanations.

Example:
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(12, 6.75), dpi=150)
x = [1, 2, 3, 4, 5, 6]
y = [100, 120, 140, 160, 180, 200]
ax.bar(x, y, color='#0077B5', width=0.6)
ax.set_xlabel('Month', fontsize=12)
ax.set_ylabel('Value', fontsize=12)
ax.set_title('Chart Title', fontsize=16, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
"""

    response = anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    code = response.content[0].text
    code = code.replace("```python", "").replace("```", "").strip()
    
    exec_globals = {'plt': plt, 'np': np, 'mpatches': mpatches}
    
    try:
        exec(code, exec_globals)
        
        fig = plt.gcf()
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
    
    except Exception as e:
        print(f"Error executing chart code: {e}")
        return generate_dalle_image(description)

def generate_dalle_image(description: str) -> str:
    """Generate conceptual image using DALL-E 3"""
    import traceback

    print(f"\n[DALL-E] ========================================")
    print(f"[DALL-E] Generating image for: {description}")

    enhanced_prompt = f"""Professional LinkedIn graphic for a B2B AI consulting firm specializing in retail supply chain.

Create: {description}

Style requirements:
- Clean, modern, professional corporate aesthetic
- Color palette: Blues (#0077B5, #00A0DC, #005582) with white and gray accents
- Suitable for B2B audience (executives, VPs, directors)
- Landscape orientation for LinkedIn (16:9 ratio)
- No cartoon or playful elements
- Minimal or no text in the image
- Focus on clarity and visual impact
- Photorealistic or clean illustration style
- Professional business environment"""

    print(f"[DALL-E] Enhanced prompt length: {len(enhanced_prompt)} chars")

    try:
        print(f"[DALL-E] Calling OpenAI DALL-E 3 API...")
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size="1792x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        print(f"[DALL-E] Got image URL: {image_url[:100]}...")

        import requests
        print(f"[DALL-E] Downloading image from URL...")
        image_data = requests.get(image_url).content
        image_base64 = base64.b64encode(image_data).decode()

        print(f"[DALL-E] SUCCESS - Image generated, base64 length: {len(image_base64)} chars")
        print(f"[DALL-E] ========================================\n")

        return f"data:image/png;base64,{image_base64}"

    except Exception as e:
        print(f"[DALL-E] ERROR: {str(e)}")
        print(f"[DALL-E] Full traceback:\n{traceback.format_exc()}")
        print(f"[DALL-E] ========================================\n")
        return None

def generate_nano_banana_image(description: str, research_data: list = None) -> str:
    """Generate image using Google's Imagen 3 - best for infographics and text-heavy images.

    Imagen 3 is optimized for generating images with text, data visualizations,
    and infographic-style content where DALL-E often struggles with text rendering.

    Uses the google-genai SDK with the correct image generation pattern.
    """
    from google import genai
    from google.genai import types

    print(f"\n[IMAGEN 3] ========================================")
    print(f"[IMAGEN 3] Generating infographic for: {description[:100]}...")
    print(f"[IMAGEN 3] Research data provided: {bool(research_data)}")

    try:
        # Check if Google AI is configured
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print(f"[IMAGEN 3] ERROR: GOOGLE_API_KEY not set, falling back to DALL-E")
            print(f"[IMAGEN 3] ========================================\n")
            return generate_dalle_image(description)

        # Initialize the google-genai client
        client = genai.Client(api_key=api_key)

        # Build enhanced prompt for infographic
        research_context = ""
        if research_data:
            facts = _format_research_for_chart(research_data)
            if facts:
                research_context = f"\n\nUse these real statistics and facts:\n{facts}"

        enhanced_prompt = f"""Create a professional infographic for LinkedIn:

{description}{research_context}

Style requirements:
- Clean, modern corporate design
- Color palette: Blues (#0077B5, #00A0DC, #005582) with white and gray accents
- Clear, readable text and labels
- Professional B2B aesthetic suitable for supply chain executives
- Landscape orientation (16:9 ratio)
- Data should be prominently displayed with clear visual hierarchy
- Minimal but effective use of icons and visual elements"""

        print(f"[IMAGEN 3] Enhanced prompt length: {len(enhanced_prompt)} chars")
        print(f"[IMAGEN 3] Calling Google Imagen 3 API...")

        # Use Imagen 3 for image generation
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=enhanced_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
            ),
        )

        # Extract image from response
        if response.generated_images and len(response.generated_images) > 0:
            image = response.generated_images[0].image

            # Get image bytes
            if hasattr(image, 'image_bytes') and image.image_bytes:
                image_base64 = base64.b64encode(image.image_bytes).decode()
                print(f"[IMAGEN 3] SUCCESS - Image generated, {len(image_base64)} base64 chars")
                print(f"[IMAGEN 3] ========================================\n")
                return f"data:image/png;base64,{image_base64}"

        print(f"[IMAGEN 3] ERROR: No image in response, falling back to DALL-E")
        print(f"[IMAGEN 3] ========================================\n")
        return generate_dalle_image(description)

    except Exception as e:
        print(f"[IMAGEN 3] ERROR: {str(e)}")
        print(f"[IMAGEN 3] Full traceback:\n{traceback.format_exc()}")
        print(f"[IMAGEN 3] Falling back to DALL-E...")
        print(f"[IMAGEN 3] ========================================\n")
        return generate_dalle_image(description)


def generate_veo_video(description: str, duration_seconds: int = 8) -> str:
    """Generate video using Google's Veo 3.1 Fast.

    Veo 3.1 is Google's video generation model, ideal for creating
    motion graphics, animations, and video content for social media.

    Uses the google-genai SDK with the correct async polling pattern.
    Video generation typically takes 1-3 minutes.

    Returns a base64-encoded video with metadata prefix for frontend handling.
    """
    import time
    from google import genai
    from google.genai import types

    print(f"\n[VEO 3.1] ========================================")
    print(f"[VEO 3.1] Generating video for: {description[:100]}...")
    print(f"[VEO 3.1] Duration: {duration_seconds} seconds")

    try:
        # Check if Google AI is configured
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print(f"[VEO 3.1] ERROR: GOOGLE_API_KEY not set")
            print(f"[VEO 3.1] ========================================\n")
            return None

        # Initialize the google-genai client
        client = genai.Client(api_key=api_key)

        enhanced_prompt = f"""Professional B2B video for LinkedIn.
Topic: {description}
Style: Clean, corporate aesthetic with blue color tones (#0077B5, #00A0DC).
Professional lighting, smooth camera movements.
Suitable for supply chain and logistics consulting content.
Duration: {duration_seconds} seconds."""

        print(f"[VEO 3.1] Enhanced prompt length: {len(enhanced_prompt)} chars")
        print(f"[VEO 3.1] Calling Veo 3.1 Fast API (this may take 1-3 minutes)...")

        # Create video generation operation
        operation = client.models.generate_videos(
            model="veo-3.1-fast-generate-preview",
            prompt=enhanced_prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=duration_seconds,
                aspect_ratio="16:9",
            ),
        )

        # Poll until complete (video generation takes time)
        poll_count = 0
        max_polls = 30  # 5 minutes max (30 * 10 seconds)
        while not operation.done and poll_count < max_polls:
            print(f"[VEO 3.1] Waiting for video generation... (poll {poll_count + 1}/{max_polls})")
            time.sleep(10)
            operation = client.operations.get(operation)
            poll_count += 1

        if not operation.done:
            print(f"[VEO 3.1] ERROR: Video generation timed out after 5 minutes")
            print(f"[VEO 3.1] ========================================\n")
            return None

        # Get the generated video
        if operation.response and operation.response.generated_videos:
            video = operation.response.generated_videos[0].video

            # Get video bytes and convert to base64
            if hasattr(video, 'video_bytes') and video.video_bytes:
                video_base64 = base64.b64encode(video.video_bytes).decode()
                print(f"[VEO 3.1] SUCCESS - Video generated, {len(video_base64)} base64 chars")
                print(f"[VEO 3.1] ========================================\n")
                return f"data:video/mp4;base64,{video_base64}"

            # If video is at a URI, download it with authentication
            if hasattr(video, 'uri') and video.uri:
                print(f"[VEO 3.1] Video at URI: {video.uri}")
                try:
                    import requests

                    # The URI requires authentication with the API key
                    download_url = video.uri
                    if "?" in download_url:
                        download_url += f"&key={api_key}"
                    else:
                        download_url += f"?key={api_key}"

                    print(f"[VEO 3.1] Downloading video...")
                    response = requests.get(download_url, timeout=120)

                    if response.status_code == 200:
                        video_bytes = response.content
                        video_base64 = base64.b64encode(video_bytes).decode()
                        print(f"[VEO 3.1] SUCCESS - Video downloaded, {len(video_base64)} base64 chars")
                        print(f"[VEO 3.1] ========================================\n")
                        return f"data:video/mp4;base64,{video_base64}"
                    else:
                        print(f"[VEO 3.1] ERROR: Download failed with status {response.status_code}")
                        print(f"[VEO 3.1] Response: {response.text[:500]}")
                except Exception as download_error:
                    print(f"[VEO 3.1] ERROR: Failed to download video from URI: {download_error}")

        print(f"[VEO 3.1] ERROR: No video in response")
        print(f"[VEO 3.1] ========================================\n")
        return None

    except Exception as e:
        print(f"[VEO 3.1] ERROR: {str(e)}")
        print(f"[VEO 3.1] Full traceback:\n{traceback.format_exc()}")
        print(f"[VEO 3.1] ========================================\n")
        return None


def regenerate_with_feedback(original_description: str, feedback: str, graphic_type: str) -> str:
    """Regenerate image with user feedback"""

    enhanced_description = f"{original_description}\n\nAdjustments requested: {feedback}"

    return generate_graphic(enhanced_description, graphic_type)
