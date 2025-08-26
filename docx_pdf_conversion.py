
from fastapi import UploadFile, File, APIRouter, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import os
import uuid

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter()

@router.get("/docx-pdf-health")
async def docx_pdf_health():
	return {"status": "DOCX to PDF endpoint is alive"}




@router.post("/convert-docx-to-pdf")
async def convert_docx_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
	try:
		# Save uploaded DOCX file
		temp_docx_filename = f"temp_{uuid.uuid4().hex}.docx"
		temp_pdf_filename = f"temp_{uuid.uuid4().hex}.pdf"
		with open(temp_docx_filename, "wb") as f:
			f.write(await file.read())

		# Extract text from DOCX
		doc = Document(temp_docx_filename)
		text = []
		for para in doc.paragraphs:
			text.append(para.text)

		# Create PDF with extracted text
		c = canvas.Canvas(temp_pdf_filename, pagesize=letter)
		width, height = letter
		y = height - 40
		for line in text:
			c.drawString(40, y, line)
			y -= 15
			if y < 40:
				c.showPage()
				y = height - 40
		c.save()

		# Schedule cleanup of temp files after response is sent
		def cleanup():
			if os.path.exists(temp_docx_filename):
				os.remove(temp_docx_filename)
			if os.path.exists(temp_pdf_filename):
				os.remove(temp_pdf_filename)
		background_tasks.add_task(cleanup)

		# Return PDF file
		return FileResponse(
			temp_pdf_filename,
			media_type="application/pdf",
			filename="converted.pdf"
		)
	except Exception as e:
		return JSONResponse(content={"error": str(e)}, status_code=500)
