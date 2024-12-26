from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from g4f.client import Client
import re
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Input model
class BlogRequest(BaseModel):
    title: str

@app.post("/generate-blog")
async def generate_blog(request: BlogRequest):
    try:
        client = Client()

        # Request blog content
        blog_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Write a detailed seo blog about: {request.title} with headings, subheadings, and sections."}]
        )
        if not blog_response.choices:
            raise HTTPException(status_code=500, detail="No content generated for the blog.")

        # Clean and format blog content
        blog_content = blog_response.choices[0].message.content
        blog_content = re.sub(r"[*#]", "", blog_content)  # Remove unwanted `*` and `#`
        blog_sections = blog_content.split("\n\n")  # Split paragraphs into sections

        # Request related images
        image_response = client.images.generate(
            model="flux",
            prompt=request.title,
            response_format="url"
        )
        if not image_response.data:
            raise HTTPException(status_code=500, detail="No images generated for the blog.")

        # Prepare images
        image_urls = [image.url for image in image_response.data]

        # Structure response
        blog_with_images = []
        for i, section in enumerate(blog_sections):
            if i == 0:
                blog_with_images.append({"type": "title", "content": section.strip()})
            elif any(word in section.lower() for word in ["introduction", "conclusion", "overview", "summary"]):
                blog_with_images.append({"type": "subtitle", "content": section.strip()})
            else:
                blog_with_images.append({"type": "text", "content": section.strip()})

            if i > 0 and i % 2 == 0 and image_urls:  # Add an image every 2 sections
                blog_with_images.append({"type": "image", "content": image_urls.pop(0)})

        return {"title": request.title, "sections": blog_with_images}

    except Exception as e:
        logging.error(f"Error generating blog: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating blog: {str(e)}")

# For cloud-based deployment, run with gunicorn (example: Render, AWS, etc.)
if __name__ == "__main__":
    import os
    host = os.getenv("HOST", "0.0.0.0")  # Host is set by cloud platform
    port = int(os.getenv("PORT", 8000))  # Port is dynamically assigned by cloud platform
    uvicorn.run(app, host=host, port=port)
