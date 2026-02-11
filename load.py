import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv  # <--- Added this to read .env file
from gemini_webapi import GeminiClient
from loguru import logger

# 1. Load the .env file
load_dotenv()

# --- Configuration ---
SECURE_1PSID = os.getenv("GEMINI_1PSID")
SECURE_1PSIDTS = os.getenv("GEMINI_1PSIDTS")

# Paths
INPUT_PRODUCT_IMAGE = "input/my_product.jpg"
OUTPUT_DIR = Path("output_product_set")

STYLE_PROMPT = """
STYLE GUIDELINES:
1. Lighting: Soft, diffused studio lighting mimicking natural daylight.
2. Background: Pure white (#FFFFFF) seamless background.
3. Product Focus: Perfectly sharp, centered, realistic geometry.
4. Quality: Ultra-high resolution, commercial-grade clarity.
"""

SHOT_LIST = [
    ("Front_View", "Generate a Front view of this product."),
    ("Side_View", "Generate a Side view of this product."),
    ("Lifestyle", "Generate a lifestyle image showing the product in realistic use on a table.")
]

async def get_client():
    # Check if cookies are loaded
    if not SECURE_1PSID or not SECURE_1PSIDTS:
        logger.error("❌ Error: Cookies missing. Please set GEMINI_1PSID and GEMINI_1PSIDTS in your .env file.")
        sys.exit(1)

    client = GeminiClient(SECURE_1PSID, SECURE_1PSIDTS)
    await client.init(timeout=60, auto_close=True, close_delay=300, auto_refresh=True)
    return client

async def generate_product_set():
    # Validation
    input_path = Path(INPUT_PRODUCT_IMAGE)
    if not input_path.exists():
        logger.error(f"❌ Input image not found at: {input_path}")
        logger.info("Please create a folder named 'input' and put 'my_product.jpg' inside it.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("🚀 Client initialized. Starting Studio Session...")
    client = await get_client()

    try:
        chat = client.start_chat()
        logger.info(f"📤 Uploading reference product: {input_path.name}...")
        
        # Initial handshake
        response = await chat.send_message(
            "I am uploading a reference product image. Analyze its geometry and materials. "
            "I will ask for variations.",
            files=[input_path]
        )
        logger.success("✅ Reference image analyzed.")

        # Loop through shots
        for shot_name, shot_instruction in SHOT_LIST:
            logger.info(f"🎨 Generating: {shot_name}...")
            
            full_prompt = f"{shot_instruction} Refer strictly to the uploaded image. {STYLE_PROMPT}"

            response = await chat.send_message(full_prompt)

            if response.images:
                for i, image in enumerate(response.images):
                    filename = f"{shot_name}_v{i+1}.png"
                    await image.save(path=str(OUTPUT_DIR), filename=filename, skip_invalid_filename=True)
                    logger.success(f"💾 Saved: {filename}")
            else:
                logger.warning(f"⚠️ No images generated for {shot_name}.")
            
            # Simple delay for stability
            await asyncio.sleep(5)

    except Exception as e:
        logger.exception(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(generate_product_set())