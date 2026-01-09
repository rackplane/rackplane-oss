# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Vendor Parser Registry

Auto-detects vendor from document text and routes to appropriate parser.
"""

from typing import Optional, List, Type
from .base_parser import VendorOrderParser, ParsedOrder
from .penguin_parser import PenguinComputingParser

# Register all available parsers
REGISTERED_PARSERS: List[Type[VendorOrderParser]] = [
    PenguinComputingParser,
    # FSParser,  # TODO: Add when migrated from fs_invoice.py
    # DellParser,  # TODO: Future
]


def get_available_parsers() -> List[str]:
    """Get list of available vendor parser names."""
    return [p.vendor_name for p in REGISTERED_PARSERS]


def detect_vendor(text: str) -> Optional[str]:
    """
    Detect vendor from document text.
    
    Args:
        text: Extracted document text
        
    Returns:
        Vendor name if detected, None otherwise
    """
    for parser_class in REGISTERED_PARSERS:
        parser = parser_class()
        if parser.can_parse(text):
            return parser.vendor_name
    return None


def parse_order(text: str, vendor_hint: Optional[str] = None) -> Optional[ParsedOrder]:
    """
    Parse order document text using appropriate vendor parser.
    
    Args:
        text: Extracted document text
        vendor_hint: Optional vendor name hint if auto-detection fails
        
    Returns:
        ParsedOrder if successful, None if no parser matched
    """
    # If vendor hint provided, try that parser first
    if vendor_hint:
        for parser_class in REGISTERED_PARSERS:
            if parser_class.vendor_name.lower() == vendor_hint.lower():
                parser = parser_class()
                return parser.parse(text)
    
    # Auto-detect vendor
    for parser_class in REGISTERED_PARSERS:
        parser = parser_class()
        if parser.can_parse(text):
            return parser.parse(text)
    
    return None


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF.
    
    Prefers pdftotext (from poppler-utils) as it produces better
    formatted text for table parsing. Falls back to PyPDF2.
    
    Args:
        file_content: Raw PDF bytes
        
    Returns:
        Extracted text string
    """
    import io
    
    # Try pdftotext first (better table formatting)
    try:
        import subprocess
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        result = subprocess.run(
            ['pdftotext', tmp_path, '-'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        os.unlink(tmp_path)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except FileNotFoundError:
        print("pdftotext not found, falling back to PyPDF2")
    except subprocess.TimeoutExpired:
        print("pdftotext timed out, falling back to PyPDF2")
    except Exception as e:
        print(f"pdftotext extraction failed: {e}")
    
    # Fallback to PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception as e:
        print(f"PyPDF2 extraction failed: {e}")
    
    raise ValueError("Could not extract text from PDF. Install poppler-utils or PyPDF2.")

