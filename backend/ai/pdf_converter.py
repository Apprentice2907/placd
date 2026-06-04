import subprocess
from pathlib import Path

def docx_to_pdf(docx_path: str) -> str:
    """
    Converts a DOCX file to PDF using LibreOffice headless.
    """
    docx_file = Path(docx_path)
    if not docx_file.exists():
        raise FileNotFoundError(f"DOCX file not found at {docx_path}")
        
    pdf_path = str(docx_file.with_suffix('.pdf'))
    
    # Run LibreOffice conversion
    subprocess.run([
        'libreoffice', '--headless', '--convert-to', 'pdf',
        '--outdir', str(docx_file.parent),
        str(docx_file)
    ], check=True, timeout=30)
    
    return pdf_path
