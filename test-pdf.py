from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import traceback

def create_pdf_with_reportlab(content, filename):
    try:
        # Save the file in /tmp directory for compatibility with Cloud Run or local testing
        save_path = os.path.join('/tmp', filename)
        doc = SimpleDocTemplate(save_path, pagesize=letter)
        # Get a sample stylesheet
        styles = getSampleStyleSheet()
        story = []

        # Add the title to the first page
        title_style = styles['Title']
        title_style.textColor = colors.darkblue
        title_style.fontSize = 24
        title = Paragraph("Eco-Friendly Luxury Travels", title_style)
        story.append(title)
        story.append(Spacer(1, 0.5 * inch))  # Add space after the title

        # Split the content into lines and add paragraphs
        for line in content.split('\n'):
            paragraph = Paragraph(line, styles['Normal'])
            story.append(paragraph)
            story.append(Spacer(1, 0.2 * inch))  # Adds space between paragraphs

        # Build the PDF
        doc.build(story)

        # Verify file creation
        if os.path.exists(save_path):
            print(f"PDF successfully created at: {save_path}")
            file_size = os.path.getsize(save_path)
            print(f"PDF file size: {file_size} bytes")
        else:
            print("PDF creation failed.")
        
        return save_path  # Return the path of the created PDF
    except Exception as e:
        print(f"Error creating PDF: {e}")
        traceback.print_exc()
        return None

# Test the function
if __name__ == "__main__":
    content = "Here is a test itinerary for creating a PDF.\n\nDestination:\n- Paris\n\nNumber of days:\n- 7\n\nBudget:\n- $25000\n\nFamily size:\n- 6."
    filename = "5 day Altanta itinerary.pdf"
    create_pdf_with_reportlab(content, filename)