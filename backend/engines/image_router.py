

from openai import OpenAI
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import io
import base64

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
    1. Check for explicit chart keywords -> 'chart'
    2. Check for explicit diagram keywords -> 'diagram'
    3. Default to 'conceptual' (DALL-E) for everything else

    IMPORTANT: Descriptions asking for "image of", "picture of", "rendering of",
    "view of", "scene of", etc. should go to DALL-E, NOT charts.
    """
    desc_lower = description.lower()

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
    """Route to appropriate image generation engine. Returns base64 encoded image.

    Args:
        description: Text description of the graphic
        graphic_type: Type of graphic (chart, diagram, conceptual)
        chart_data: Optional JSON string with chart data points
        research_data: Optional list of research results with extracted facts (only used for charts/diagrams)
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
    # For charts/diagrams: pass research data so they can use real numbers
    # For conceptual: do NOT pass research data - keep DALL-E creative
    if graphic_type == 'chart':
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

def regenerate_with_feedback(original_description: str, feedback: str, graphic_type: str) -> str:
    """Regenerate image with user feedback"""
    
    enhanced_description = f"{original_description}\n\nAdjustments requested: {feedback}"
    
    return generate_graphic(enhanced_description, graphic_type)
