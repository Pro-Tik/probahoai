import asyncio
import os
import sys
from pathlib import Path
from gemini_webapi import GeminiClient
from loguru import logger

# --- Configuration ---
# Cookies: Get these from gemini.google.com > F12 > Network > Cookies
SECURE_1PSID = os.getenv("GEMINI_1PSID", "g.a0006ghXtGBRisMqgMH-aJTJwh-5buz9s7O3Uv_X9FJkpP3AreZzzRYNWiFLqVuL504QNlDQDAACgYKAcYSARUSFQHGX2MiTkh7BcVVJZYqYP-EPjlidRoVAUF8yKpRU01UfgilbUw13g0wgyr80076")
SECURE_1PSIDTS = os.getenv("GEMINI_1PSIDTS", "sidts-CjIB7I_69PNjXMBEM0K4TFDgxnQavMYQaJJXTrEnoJDDdgLoQUZeHXMPAc8gQq7ntFVg3BAA")

# Paths
INPUT_PRODUCT_IMAGE = "input/my_product.jpg"  # The reference photo
OUTPUT_DIR = Path("output_product_set")

# --- The Master Style Prompt (Based on your requirements) ---
STYLE_PROMPT = """
STYLE GUIDELINES:
1. Lighting: Soft, diffused studio lighting mimicking natural daylight. Balanced highlights, gentle shadows, no harsh reflections.
2. Background: Pure white (#FFFFFF) seamless background. Minimal and clean.
3. Product Focus: Perfectly sharp, centered, realistic geometry. No props.
4. Color: Accurate white balance, no oversaturation.
5. Quality: Ultra-high resolution, commercial-grade clarity, Amazon/Shopify ready.
6. Retouching: Remove dust/imperfections but keep authentic texture.
7. Shadow: Add a subtle, natural drop shadow for grounding.
"""

# --- The Shot List ---
# The script will generate a set for EACH of these angles.
SHOT_LIST = [
    ("Front_View", "Generate a Front view of this product."),
    ("Back_View", "Generate a Back view of this product."),
    ("Side_View", "Generate a Side view of this product."),
    ("Three_Quarter", "Generate a 45-degree three-quarter angle view of this product."),
    ("Detail_Shot", "Generate a Close-up detail shot highlighting texture and material."),
    ("Lifestyle", "Generate a lifestyle image showing the product in realistic use on a table.")
]

async def get_client():
    """Authenticates the Gemini Client."""
    if "YOUR_COOKIE" in SECURE_1PSID:
        logger.error("Please set your GEMINI_1PSID and GEMINI_1PSIDTS environment variables.")
        sys.exit(1)

    client = GeminiClient(SECURE_1PSID, SECURE_1PSIDTS)
    await client.init(timeout=60, auto_close=True, close_delay=300, auto_refresh=True)
    return client

async def generate_product_set():
    # 1. Validation
    input_path = Path(INPUT_PRODUCT_IMAGE)
    if not input_path.exists():
        logger.error(f"Input image not found at: {input_path}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Initialize Client
    client = await get_client()
    logger.info("Client initialized. Starting Studio Session...")

    try:
        # 3. Start Chat & Upload Reference
        # We start a chat so the model 'remembers' the product for subsequent angles
        chat = client.start_chat()
        
        logger.info(f"Uploading reference product: {input_path.name}...")
        
        # Initial handshake: Analyze the product
        response = await chat.send_message(
            "I am uploading a reference product image. Analyze its geometry, materials, and branding details. "
            "I will ask you to generate professional e-commerce variations of this exact product.",
            files=[input_path]
        )
        logger.success("Reference image analyzed by Gemini.")

        # 4. Loop through the Shot List
        for shot_name, shot_instruction in SHOT_LIST:
            logger.info(f"Generating: {shot_name}...")
            
            # Construct the full prompt
            full_prompt = (
                f"{shot_instruction}\n"
                f"Refer strictly to the uploaded image for product details.\n"
                f"{STYLE_PROMPT}"
            )

            # Send request
            response = await chat.send_message(full_prompt)

            if response.images:
                # Save the images
                for i, image in enumerate(response.images):
                    filename = f"{shot_name}_v{i+1}.png"
                    await image.save(path=str(OUTPUT_DIR), filename=filename, skip_invalid_filename=True)
                    logger.success(f"Saved: {filename}")
            else:
                logger.warning(f"No images generated for {shot_name}. (Model text: {response.text[:50]}...)")
            
            # Short pause to prevent rate limiting/spamming logic
            await asyncio.sleep(2)

    except Exception as e:
        logger.exception(f"An error occurred during generation: {e}")

if __name__ == "__main__":
    asyncio.run(generate_product_set())