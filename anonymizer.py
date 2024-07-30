import streamlit as st
import os
import tempfile
import zipfile
import pandas as pd
import re
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
import pytesseract
import random
import string
from PIL import Image, ImageDraw, ImageFont

st.set_option('client.showErrorDetails', True)

@st.cache_resource
def load_nlp_model():
    import spacy
    return spacy.load("en_core_web_sm")

nlp = load_nlp_model()

def get_default_font(size=30):
    return ImageFont.load_default().font_variant(size=size)

def get_full_name(text):
    # Look for the full name after "Name:" in both formats
    match = re.search(r'Name:\s*([\w\s,]+?)(?=\s\s|\n|$)', text)
    if match:
        full_name = match.group(1).strip()
        # Check if the name is in "Last, First" format
        if ',' in full_name:
            last_name, first_name = full_name.split(',', 1)
            return f"{first_name.strip()} {last_name.strip()}"
        else:
            return full_name
    
    # If not found, try looking for "Name:" with single space
    match = re.search(r'Name:\s*([\w\s,\.]+)(?=\sApplicant|\s\s|\n|$)', text)
    if match:
        full_name = match.group(1).strip()
        # Check if the name is in "Last, First" format
        if ',' in full_name:
            last_name, first_name = full_name.split(',', 1)
            return f"{first_name.strip()} {last_name.strip()}"
        else:
            return full_name
    
    return None

def get_email(text):
    # Look for the email after "Email:"
    match = re.search(r'Email:\s*([\w\.-]+@[\w\.-]+)', text)
    if match:
        return match.group(1)
    return None

def generate_name_variations(full_name):
    parts = full_name.split()
    if len(parts) < 2:
        return [full_name]
    
    first_name, last_name = parts[0], parts[-1]
    middle_names = parts[1:-1]
    middle_initials = ''.join([name[0] for name in middle_names]) if middle_names else ''
    
    variations = [
        full_name,
        f"{full_name},",
        f"{full_name}*,",
        f"{last_name} {first_name}",
        f"{last_name}, {first_name}",
        f"{first_name[0]}. {last_name}",
        f"{first_name[0]}.{last_name}",
        first_name,
        f"{last_name},",
        f"{last_name}*",    
        last_name,
        f"{last_name} {first_name[0]}",
        f"{last_name} {first_name[0]}*,",
        f"{last_name} {first_name[0]},",
        f"{last_name} {first_name[0]}A,",
        f"{last_name} {first_name[0]}B,",
        f"{last_name} {first_name[0]}C,",
        f"{last_name} {first_name[0]}D,",
        f"{last_name} {first_name[0]}E,",
        f"{last_name} {first_name[0]}F,",
        f"{last_name} {first_name[0]}G,",
        f"{last_name} {first_name[0]}H,",
        f"{last_name} {first_name[0]}I,",
        f"{last_name} {first_name[0]}J,",
        f"{last_name} {first_name[0]}K,",
        f"{last_name} {first_name[0]}L,",
        f"{last_name} {first_name[0]}M,",
        f"{last_name} {first_name[0]}N,",
        f"{last_name} {first_name[0]}O,",
        f"{last_name} {first_name[0]}P,",
        f"{last_name} {first_name[0]}Q,",
        f"{last_name} {first_name[0]}R,",
        f"{last_name} {first_name[0]}S,",
        f"{last_name} {first_name[0]}T,",
        f"{last_name} {first_name[0]}U,",
        f"{last_name} {first_name[0]}V,",
        f"{last_name} {first_name[0]}W,",
        f"{last_name} {first_name[0]}X,",
        f"{last_name} {first_name[0]}Y,",
        f"{last_name} {first_name[0]}Z,",
        f"{re.escape(last_name)} {re.escape(first_name[0])}\\w*",
        f"{first_name[0]} {last_name}",
        f"{first_name[0]}. {last_name}",
    ]
    
    # Add variations with middle initials only if they exist
    if middle_initials:
        variations.extend([
            f"{last_name} {first_name[0]}{middle_initials}",
            f"{last_name} {first_name[0]}{middle_initials},",
            f"{last_name} {first_name[0]}{middle_initials}*,",
            f"{last_name} {first_name[0]}{middle_initials[0]}",
            f"{last_name} {first_name[0]}{middle_initials[0]},",
            f"{last_name} {first_name[0]}{middle_initials[0]}*,",
            f"{first_name[0]}{middle_initials} {last_name}",
            f"{first_name[0]}.{middle_initials}. {last_name}"
        ])
    
    # Add variations without spaces
    variations.extend([v.replace(" ", "") for v in variations])
    
    # Add lowercase variations
    variations.extend([v.lower() for v in variations])
    
    return list(set(variations))  # Remove duplicates

def anonymize_pdf(pdf_path, output_path, unique_number, progress_bar):
    # Convert PDF to images
    images = convert_from_path(pdf_path)
    
    # Get full name and email from the first page
    first_page_text = pytesseract.image_to_string(images[0])
    full_name = get_full_name(first_page_text)
    email = get_email(first_page_text)
    
    if full_name:
        name_variations = generate_name_variations(full_name)
    else:
        name_variations = []
    
    # Get default font
    font = get_default_font(size=30)
    
    # Process each page
    for i, image in enumerate(images):
        # Perform OCR
        text = pytesseract.image_to_string(image)
        
        # Draw black boxes over names and emails
        draw = ImageDraw.Draw(image)
        words = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Check for name variations
        for j in range(len(words['text'])):
            for variation in name_variations:
                # Check if the variation matches starting from this word
                if ' '.join(words['text'][j:j+len(variation.split())]).lower() == variation.lower():
                    # Calculate bounding box for the entire variation
                    x1 = min(words['left'][k] for k in range(j, j+len(variation.split())))
                    y1 = min(words['top'][k] for k in range(j, j+len(variation.split())))
                    x2 = max(words['left'][k] + words['width'][k] for k in range(j, j+len(variation.split())))
                    y2 = max(words['top'][k] + words['height'][k] for k in range(j, j+len(variation.split())))
                    
                    # Draw black rectangle over the entire variation
                    draw.rectangle([x1, y1, x2, y2], fill="black")
        
        # Check for email
        if email:
            for j in range(len(words['text'])):
                if ' '.join(words['text'][j:j+len(email.split())]).lower() == email.lower():
                    # Calculate bounding box for the entire email
                    x1 = min(words['left'][k] for k in range(j, j+len(email.split())))
                    y1 = min(words['top'][k] for k in range(j, j+len(email.split())))
                    x2 = max(words['left'][k] + words['width'][k] for k in range(j, j+len(email.split())))
                    y2 = max(words['top'][k] + words['height'][k] for k in range(j, j+len(email.split())))
                    
                    # Draw black rectangle over the entire email
                    draw.rectangle([x1, y1, x2, y2], fill="black")
        
        # Add "ID: [unique_number]" to the top center of the first page
        if i == 0:
            # Prepare the text
            text = f"ID: {unique_number}"
            
            # Calculate text size and position
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            x = (image.width - text_width) / 2
            y = 20  # 20 pixels from the top
            
            # Draw the text
            draw.text((x, y), text, font=font, fill="black")
        
        # Save the anonymized image
        image.save(f"{output_path}_page_{i+1}.pdf")
        
        # Update progress
        progress_bar.progress((i + 1) / len(images))
    
    # Merge all pages back into a single PDF
    merger = PdfWriter()
    for i in range(len(images)):
        merger.append(f"{output_path}_page_{i+1}.pdf")
    merger.write(f"{output_path}.pdf")
    merger.close()
    
    # Clean up temporary files
    for i in range(len(images)):
        os.remove(f"{output_path}_page_{i+1}.pdf")
    
    return full_name, email

def main():
    st.title("ERAS Application Anonymizer")
    
    uploaded_files = st.file_uploader("Upload ERAS application PDFs", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        if 'processing_complete' not in st.session_state:
            st.session_state.processing_complete = False
        
        if not st.session_state.processing_complete:
            # Create a temporary directory to store processed files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Process each uploaded file
                applicant_data = []
                
                progress_text = "Overall Progress"
                overall_progress_bar = st.progress(0, text=progress_text)
                
                for i, file in enumerate(uploaded_files):
                    unique_number = f"{i+1:04d}"  # Unique 4-digit number
                    
                    # Save uploaded file temporarily
                    temp_pdf_path = os.path.join(temp_dir, f"temp_{unique_number}.pdf")
                    with open(temp_pdf_path, "wb") as f:
                        f.write(file.getbuffer())
                    
                    # Anonymize PDF
                    output_path = os.path.join(temp_dir, f"anonymized_{unique_number}")
                    st.write(f"Processing file {i+1} of {len(uploaded_files)}: {file.name}")
                    file_progress_bar = st.progress(0)
                    full_name, email = anonymize_pdf(temp_pdf_path, output_path, unique_number, file_progress_bar)
                    
                    applicant_data.append({"ID": unique_number, "Applicant Name": full_name or "Unknown"})
                    
                    # Update overall progress
                    overall_progress_bar.progress((i + 1) / len(uploaded_files), text=f"{progress_text} {i+1}/{len(uploaded_files)}")
                
                # Create Excel file with applicant data
                df = pd.DataFrame(applicant_data)
                excel_path = os.path.join(temp_dir, "applicant_key.xlsx")
                df.to_excel(excel_path, index=False)
                
                # Create zip file containing anonymized PDFs and Excel key
                zip_path = os.path.join(os.getcwd(), "anonymized_applications.zip")
                with zipfile.ZipFile(zip_path, "w") as zip_file:
                    for file in os.listdir(temp_dir):
                        if file.startswith("anonymized_") or file == "applicant_key.xlsx":
                            zip_file.write(os.path.join(temp_dir, file), file)
                
                # Save the zip file path to session state
                st.session_state.zip_path = zip_path
                st.session_state.processing_complete = True
                st.success("Processing complete! Click below to download the anonymized applications.")
                st.rerun()
        
        else:
            # Offer zip file for download
            try:
                with open(st.session_state.zip_path, "rb") as f:
                    st.download_button(
                        label="Download Anonymized Applications",
                        data=f.read(),
                        file_name="anonymized_applications.zip",
                        mime="application/zip"
                    )
            except Exception as e:
                st.error(f"An error occurred while preparing the download: {str(e)}")
                st.error("Please try processing the files again.")
            
            # Add a button to reset the app state
            if st.button("Process more files"):
                if os.path.exists(st.session_state.zip_path):
                    os.remove(st.session_state.zip_path)
                del st.session_state.processing_complete
                del st.session_state.zip_path
                st.rerun()

if __name__ == "__main__":
    main()