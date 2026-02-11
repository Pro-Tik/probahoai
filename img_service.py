import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from gemini_webapi import GeminiClient
from loguru import logger

# Load .env file
load_dotenv()

# --- Configuration (Defaults) ---
SECURE_1PSID = os.getenv("GEMINI_1PSID") or os.getenv("1PSID") or os.getenv("SECURE_1PSID")
SECURE_1PSIDTS = os.getenv("GEMINI_1PSIDTS") or os.getenv("1PSIDTS") or os.getenv("SECURE_1PSIDTS")
GEMINI_PROXY = os.getenv("GEMINI_PROXY")

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

SHOT_LIST = [
    ("Front_View", "Generate a Front view of this product."),
    ("Back_View", "Generate a Back view of this product."),
    ("Side_View", "Generate a Side view of this product."),
    ("Three_Quarter", "Generate a 45-degree three-quarter angle view of this product."),
    ("Detail_Shot", "Generate a Close-up detail shot highlighting texture and material."),
    ("Lifestyle", "Generate a lifestyle image showing the product in realistic use on a table.")
]

class GeminiImageGenerator:
    def __init__(self, psid=None, psidts=None, proxy=None):
        self.psid = psid or SECURE_1PSID
        self.psidts = psidts or SECURE_1PSIDTS
        self.proxy = proxy or GEMINI_PROXY
        self.client = None

    async def init_client(self):
        if not self.psid or not self.psidts:
            logger.error("Missing cookies: GEMINI_1PSID or GEMINI_1PSIDTS not provided.")
            raise ValueError("GEMINI_1PSID and GEMINI_1PSIDTS must be set.")
        
        logger.info(f"Initializing GeminiClient with Proxy: {self.proxy if self.proxy else 'None'}")
        try:
            self.client = GeminiClient(self.psid, self.psidts, proxy=self.proxy)
            await self.client.init(timeout=60, auto_close=True, close_delay=300, auto_refresh=True)
            logger.success("GeminiClient initialized successfully.")
            return self.client
        except Exception as e:
            logger.error(f"GeminiClient initialization FAILED: {str(e)}")
            if "expired" in str(e).lower():
                logger.warning("Cookie expiration detected. Please refresh Gemini in your browser and sync.")
            raise e

    async def generate_for_image(self, input_image_path: Path, output_dir: Path, progress_callback=None):
        """Generates all shots for a single input image."""
        if not self.client:
            await self.init_client()

        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            chat = self.client.start_chat()
            
            if progress_callback:
                await progress_callback({"status": "uploading", "message": f"Uploading reference: {input_image_path.name}"})

            # Initial handshake: Upload the reference image ONCE
            if progress_callback:
                await progress_callback({"status": "uploading", "message": "Analyzing reference product image..."})

            response = await chat.send_message(
                "You are a professional e-commerce product photographer/AI. "
                "I am uploading ONE reference image of a product. Your job is to generate variations of THIS EXACT product from different angles. "
                "CRITICAL: Maintain the exact geometry, branding, and materials of the product in the image. Do NOT invent a new product.",
                files=[input_image_path]
            )
            
            generated_files = []

            for shot_name, shot_instruction in SHOT_LIST:
                if progress_callback:
                    await progress_callback({"status": "generating", "shot": shot_name, "message": f"Generating {shot_name} angle..."})

                # Stricter prompt referring to the initial context
                full_prompt = (
                    f"Task: Generate the '{shot_name}' variant.\n"
                    f"Instruction: {shot_instruction}\n"
                    f"Reference: Use the product from the uploaded image ONLY.\n\n"
                    f"{STYLE_PROMPT}\n"
                    f"IMPORTANT: The generated output MUST be an image of the exact same product as shown in our first message."
                )

                response = await chat.send_message(full_prompt)

                if response.images:
                    for i, image in enumerate(response.images):
                        filename = f"{input_image_path.stem}_{shot_name}_v{i+1}.png"
                        
                        # Retry logic for saving (mitigates transient network/timeout issues)
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                # We add a small delay before saving to ensure Google's CDN is ready
                                await asyncio.sleep(2)
                                await image.save(path=str(output_dir), filename=filename, skip_invalid_filename=True)
                                generated_files.append(str(output_dir / filename))
                                logger.success(f"Saved: {filename}")
                                break
                            except Exception as e:
                                if attempt == max_retries - 1:
                                    logger.error(f"Failed to download/save {filename} after attempts: {e}")
                                    # We don't want to crash the whole job if one image fails to download
                                    # but we log it clearly.
                                    break
                                logger.warning(f"Save attempt {attempt + 1} failed for {filename}. Retrying...")
                                await asyncio.sleep(3)
                else:
                    logger.warning(f"Gemini returned no images for {shot_name}. Text response: {response.text[:100]}...")
                
                # Small pause between messages
                await asyncio.sleep(3)

            return generated_files

        except Exception as e:
            logger.exception(f"Error generating shots for {input_image_path}: {e}")
            raise e
