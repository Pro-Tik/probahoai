import { GoogleGenerativeAI } from "@google/generative-ai";
import fs from "fs";

// --- CONFIGURATION ---
const API_KEY = "AIzaSyBHLP_PI9-OcOmCxMHGFZzMjbUGiauJndM"; // Replace with your key
const INPUT_IMAGE = "test.jpg"; // Your product image
const OUTPUT_DIR = "./ecommerce_set";

// Initialize Google AI
const genAI = new GoogleGenerativeAI(API_KEY);

// We use the Imagen 3 model for high-fidelity image generation
// Note: In some regions, this might be 'imagen-3.0-generate-001' or similar.
const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash-image" });

// --- THE MASTER PROMPT (Your Specs) ---
const BASE_PROMPT = `
Using the reference image as the absolute truth for the product's identity, generate a high-end professional product photography shot.

VISUAL STYLE:
- Lighting: Soft, diffused studio lighting mimicking natural daylight. Balanced highlights, no harsh reflections.
- Background: Clean, seamless, non-textured. Pure white (#FFFFFF) or subtle professional neutral tone.
- Product Focus: Perfectly sharp, centered, accurate proportions.
- Retouching: Commercial grade. Remove dust/scratches but keep authentic texture.
- Shadow: Subtle, natural drop shadow for grounding.

CRITICAL: The product must look EXACTLY like the reference image in terms of branding, text, and material.
`;

// --- THE 6 ANGLES ---
const shots = [
    {
        name: "01_front_view",
        details: "ANGLE: Front view. The product is facing the camera directly. Symmetrical and commanding."
    },
    {
        name: "02_back_view",
        details: "ANGLE: Back view. Show the rear of the product clearly. Maintain the same lighting setup."
    },
    {
        name: "03_side_view",
        details: "ANGLE: Side profile view. 90-degree turn. Highlight the silhouette and thickness."
    },
    {
        name: "04_three_quarter",
        details: "ANGLE: 45-degree three-quarter angle. This is the 'hero' shot. Show depth and dimension."
    },
    {
        name: "05_detail_macro",
        details: "ANGLE: Extreme close-up macro shot. Focus on the material texture, logo, or key feature. Shallow depth of field (bokeh)."
    },
    {
        name: "06_lifestyle",
        details: "STYLE: Lifestyle image. The product is placed in a realistic, premium environment (e.g., a modern desk, marble counter, or clean shelf) suitable for its category. Product remains the main focus."
    }
];

// --- HELPER FUNCTIONS ---
function loadReferenceImage(path) {
    if (!fs.existsSync(path)) {
        throw new Error(`❌ File not found: ${path}`);
    }
    return {
        inlineData: {
            data: fs.readFileSync(path).toString("base64"),
            mimeType: "image/jpeg", // Adjust if using PNG
        },
    };
}

async function generateShots() {
    console.log("🚀 Starting Professional Product Photography Session...");
    
    // Create output folder
    if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR);

    const referenceImage = loadReferenceImage(INPUT_IMAGE);

    for (const shot of shots) {
        console.log(`📸 Shooting: ${shot.name}...`);
        
        // Combine Base Prompt + Specific Angle
        const fullPrompt = `${BASE_PROMPT}\n\n${shot.details}`;

        try {
            const result = await model.generateContent([
                referenceImage, // Pass the reference image to lock identity
                fullPrompt
            ]);

            const response = await result.response;
            
            // Check for valid image output
            if (!response.candidates || !response.candidates[0].content.parts) {
                console.error(`⚠️ No image generated for ${shot.name}. Check safety filters.`);
                continue;
            }

            const imagePart = response.candidates[0].content.parts.find(p => p.inlineData);

            if (imagePart) {
                const buffer = Buffer.from(imagePart.inlineData.data, "base64");
                const outputPath = `${OUTPUT_DIR}/${shot.name}.png`;
                fs.writeFileSync(outputPath, buffer);
                console.log(`✅ Saved: ${outputPath}`);
            } else {
                console.log(`⚠️ API returned text instead of image for ${shot.name}:`, response.text());
            }

            // Rate Limit Safety (Wait 5 seconds between shots)
            await new Promise(r => setTimeout(r, 5000));

        } catch (error) {
            console.error(`❌ Failed ${shot.name}:`, error.message);
        }
    }
    console.log("\n✨ Session Complete. Check the 'ecommerce_set' folder.");
}

// Run the script
generateShots();