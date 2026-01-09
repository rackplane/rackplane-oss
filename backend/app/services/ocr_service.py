# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
OCR Service - Extract text from images
Process inventory images to extract asset information
"""

import re
import logging
from typing import Dict, List, Optional
from io import BytesIO
from PIL import Image
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Vendor-specific part number patterns
# Based on manufacturer documentation and common formats
VENDOR_PART_NUMBER_PATTERNS = {
    'Dell': [
        re.compile(r'\b(?:DP/N|Dell\s+Part)[:\s]*([A-Z0-9]{3,}-[A-Z0-9]{4,})\b', re.IGNORECASE),  # 400-AXSD, 450-AIQX
        re.compile(r'\b([A-Z0-9]{3,}-[A-Z0-9]{4,})\b'),  # Generic Dell format: XXX-XXXX
    ],
    'HP': [
        re.compile(r'\b(?:FRU|Spare\s+Part|Part\s+No|P/N)[:\s]*([0-9]{6}-[0-9]{3})\b', re.IGNORECASE),  # 708046-001
        re.compile(r'\b([0-9]{6}-[0-9]{3})\b'),  # Generic HP format: ######-###
    ],
    'HPE': [
        re.compile(r'\b(?:FRU|Spare\s+Part|Part\s+No|P/N)[:\s]*([0-9]{6}-[0-9]{3})\b', re.IGNORECASE),  # 708046-001
        re.compile(r'\b([0-9]{6}-[0-9]{3})\b'),  # Generic HPE format: ######-###
    ],
    'Aruba': [
        re.compile(r'\b([A-Z][0-9][A-Z][0-9]{2,}[A-Z]?)\b'),  # R0M46A, R0M46A-001
        re.compile(r'\b([A-Z][0-9][A-Z][0-9]{2,}[A-Z]?)(?:[-][A-Z0-9]+)?\b'),  # With optional suffix
    ],
    'Lenovo': [
        re.compile(r'\b(?:FRU\s+P/N|P/N)[:\s]*([0-9]{2}[A-Z]{2}[0-9]{3})\b', re.IGNORECASE),  # 00YK016, 01KR355
        re.compile(r'\b([0-9]{2}[A-Z]{2}[0-9]{3})\b'),  # Generic Lenovo format: ##XX###
    ],
    'Cisco': [
        re.compile(r'\b(?:P/N|Part\s+Number)[:\s]*([A-Z0-9-]{8,})\b', re.IGNORECASE),  # Various formats
        re.compile(r'\b([A-Z]{2,}[0-9]{4,}[A-Z0-9-]*)\b'),  # Generic Cisco format
    ],
    'Juniper': [
        re.compile(r'\b(?:P/N|Part\s+Number)[:\s]*([A-Z0-9-]{8,})\b', re.IGNORECASE),
    ],
    'Arista': [
        re.compile(r'\b(?:P/N|Part\s+Number)[:\s]*([A-Z0-9-]{8,})\b', re.IGNORECASE),
    ],
}


class OCRService:
    """Service for OCR processing of inventory images"""

    def __init__(self):
        self.has_tesseract = False
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.has_tesseract = True
        except ImportError:
            print("Warning: pytesseract not installed. OCR functionality will be limited.")
            self.pytesseract = None

    def extract_text_from_image(self, image_data: bytes) -> str:
        """Extract text from image using OCR with enhanced preprocessing"""
        if not self.has_tesseract:
            return ""

        try:
            # Open image from bytes
            image = Image.open(BytesIO(image_data))
            print(f"Image opened successfully - Format: {image.format}, Mode: {image.mode}, Size: {image.size}")

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                print(f"Converting image from {image.mode} to RGB")
                image = image.convert('RGB')

            # Handle unsupported formats (like MPO) by converting to PIL Image without format metadata
            # This ensures pytesseract can process any image type
            if image.format not in ['JPEG', 'PNG', 'TIFF', 'BMP', 'GIF']:
                print(f"Converting from {image.format} to standard format for OCR processing")
                # Create a new image in RGB mode (removes format metadata)
                temp_buffer = BytesIO()
                image.save(temp_buffer, format='PNG')
                temp_buffer.seek(0)
                image = Image.open(temp_buffer)
                print(f"Converted to: Format: {image.format}, Mode: {image.mode}")

            # Enhanced preprocessing for better OCR accuracy
            image = self._preprocess_image(image)

            # Tesseract configuration for better accuracy
            # Try multiple PSM modes for different label layouts
            configs = [
                # PSM 6: Assume uniform block of text (good for labels)
                r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:.- ',
                # PSM 3: Fully automatic (fallback)
                r'--oem 3 --psm 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:.- ',
                # PSM 11: Sparse text (for labels with gaps)
                r'--oem 3 --psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:.- ',
                # PSM 8: Single word (for product codes)
                r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:.- ',
                # No whitelist, auto PSM (most permissive)
                '--oem 3 --psm 3'
            ]
            
            text = ""
            for i, config in enumerate(configs):
                try:
                    result = self.pytesseract.image_to_string(image, config=config)
                    if result.strip():
                        text = result
                        print(f"OCR succeeded with config {i+1}/{len(configs)}")
                        break
                except Exception as e:
                    print(f"Config {i+1} failed: {e}")
                    continue
            
            # If still no text, try without any config (default)
            if not text.strip():
                print("Trying default Tesseract config")
                text = self.pytesseract.image_to_string(image)
            
            print(f"OCR completed - Extracted {len(text)} characters")
            return text.strip()
        except Exception as e:
            import traceback
            print(f"OCR extraction failed: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return ""

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        from PIL import ImageEnhance, ImageFilter, ImageOps
        try:
            import numpy as np
            HAS_NUMPY = True
        except ImportError:
            HAS_NUMPY = False
        
        # Resize if image is too small (Tesseract works better with larger images)
        width, height = image.size
        if width < 600 or height < 600:
            scale_factor = max(600 / width, 600 / height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"Resized image from {width}x{height} to {new_size[0]}x{new_size[1]}")
        
        # Convert to RGB if needed for color analysis
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Detect if this is a dark background with light text (common on asset labels)
        # Check average brightness
        gray = image.convert('L')
        if HAS_NUMPY:
            pixels = np.array(gray)
            avg_brightness = np.mean(pixels)
            
            # If image is mostly dark (like red label on dark background), invert it
            # Tesseract works better with dark text on light background
            if avg_brightness < 100:  # Threshold for "dark" image
                print(f"Detected dark image (avg brightness: {avg_brightness:.1f}), inverting colors")
                image = ImageOps.invert(image)
                gray = image.convert('L')
        else:
            # Fallback: sample a few pixels to estimate brightness
            sample_pixels = [gray.getpixel((i, j)) for i in range(0, min(100, gray.width), 10) 
                           for j in range(0, min(100, gray.height), 10)]
            avg_brightness = sum(sample_pixels) / len(sample_pixels) if sample_pixels else 128
            if avg_brightness < 100:
                print(f"Detected dark image (estimated brightness: {avg_brightness:.1f}), inverting colors")
                image = ImageOps.invert(image)
                gray = image.convert('L')
        
        # Enhance contrast aggressively (helps with red labels on dark backgrounds)
        enhancer = ImageEnhance.Contrast(gray)
        image = enhancer.enhance(2.0)  # Increase contrast by 100%
        
        # Enhance brightness if needed
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.2)  # Increase brightness by 20%
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)  # Increase sharpness by 50%
        
        # Apply unsharp mask to improve text clarity
        image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=3))
        
        # Apply threshold to create pure black/white (binarization)
        # This helps with colored text on colored backgrounds
        threshold = 128
        image = image.point(lambda p: p > threshold and 255)
        
        return image

    def parse_asset_information(self, ocr_text: str) -> Dict[str, Optional[str]]:
        """Parse OCR text to extract asset information"""
        info = {
            "serial_number": None,
            "model": None,
            "manufacturer": None,
            "asset_tag": None,
            "part_number": None,
            "mac_address": None,
            "hostname": None,
        }

        if not ocr_text:
            return info

        lines = ocr_text.split('\n')

        # Common manufacturer names
        manufacturers = [
            'dell', 'hp', 'hpe', 'aruba', 'cisco', 'juniper', 'arista', 'supermicro',
            'lenovo', 'ibm', 'oracle', 'nvidia', 'intel', 'amd',
            'mellanox', 'netapp', 'emc', 'seagate', 'western digital'
        ]

        for line in lines:
            line_lower = line.lower().strip()

            # Serial Number patterns - improved to catch "S/N: C2504422334" or "S/N: CN19KSFXXP"
            if any(keyword in line_lower for keyword in ['serial', 's/n', 'sn:', 'serial number', 'service tag']):
                # Extract alphanumeric sequence after keyword (including colons/spaces)
                # Pattern: S/N: C2504422334 or S/N: CN19KSFXXP or S/N CN19KSFXXP
                serial_match = re.search(r'(?:S/N|SN|Serial)[:\s]*([A-Z0-9]{6,})', line.upper())
                if serial_match and not info["serial_number"]:
                    serial = serial_match.group(1)
                    # Filter out obvious OCR errors
                    if not serial.startswith('AGETETSTLASED') and len(serial) >= 6:
                        info["serial_number"] = serial
                # Fallback: look for Aruba-style serials (CN followed by alphanumeric)
                if not info["serial_number"]:
                    aruba_serial = re.search(r'CN[A-Z0-9]{7,}', line.upper())
                    if aruba_serial:
                        info["serial_number"] = aruba_serial.group()
                # Fallback: any long alphanumeric sequence (but avoid OCR errors)
                if not info["serial_number"]:
                    serial_match = re.search(r'[A-Z0-9]{7,}', line.upper())
                    if serial_match:
                        serial = serial_match.group()
                        # Filter out obvious OCR errors
                        if not serial.startswith('AGETETSTLASED') and len(serial) >= 7:
                            info["serial_number"] = serial

            # Part Number patterns - vendor-aware detection
            # First, try to identify vendor from manufacturer field or context
            detected_vendor = None
            if info.get("manufacturer"):
                manufacturer_lower = info["manufacturer"].lower()
                if 'dell' in manufacturer_lower:
                    detected_vendor = 'Dell'
                elif 'aruba' in manufacturer_lower:
                    detected_vendor = 'Aruba'
                elif 'hp' in manufacturer_lower or 'hpe' in manufacturer_lower or 'hewlett' in manufacturer_lower:
                    detected_vendor = 'HPE' if 'enterprise' in manufacturer_lower or 'hpe' in manufacturer_lower else 'HP'
                elif 'lenovo' in manufacturer_lower:
                    detected_vendor = 'Lenovo'
                elif 'cisco' in manufacturer_lower:
                    detected_vendor = 'Cisco'
                elif 'juniper' in manufacturer_lower:
                    detected_vendor = 'Juniper'
                elif 'arista' in manufacturer_lower:
                    detected_vendor = 'Arista'
            
            # Try vendor-specific patterns first
            if detected_vendor and detected_vendor in VENDOR_PART_NUMBER_PATTERNS:
                for pattern in VENDOR_PART_NUMBER_PATTERNS[detected_vendor]:
                    part_match = pattern.search(line)
                    if part_match and not info["part_number"]:
                        part_text = part_match.group(1) if part_match.groups() else part_match.group(0)
                        part_text = part_text.strip()
                        # Filter out obvious errors
                        if part_text and not part_text.startswith('AGETETSTLASED') and len(part_text) >= 4:
                            # Make sure it's not a serial number
                            if not any(keyword in line_lower for keyword in ['s/n', 'sn:', 'serial']):
                                info["part_number"] = part_text
                                break
            
            # Generic part number detection (if vendor-specific didn't work)
            if not info["part_number"]:
                # Look for labeled part numbers
                if any(keyword in line_lower for keyword in ['part', 'p/n', 'pn:', 'part number', 'part#', 'dell part', 'fru', 'spare part']):
                    # Extract part number pattern - alphanumeric codes
                    part_match = re.search(r'(?:Part|P/N|PN|Dell\s+Part|FRU|Spare\s+Part)[:\s]*([A-Z0-9][A-Z0-9\-]{3,})', line.upper())
                    if part_match:
                        part_text = part_match.group(1).strip()
                        if len(part_text) >= 4 and not part_text.startswith('AGETETSTLASED'):
                            # Make sure it's not a serial number
                            if not any(keyword in line_lower for keyword in ['s/n', 'sn:', 'serial']):
                                info["part_number"] = part_text
            
            # Also check for standalone part numbers on lines without labels
            # Try Aruba pattern first (R0M46A)
            if not info["part_number"] and len(line.strip()) > 0:
                # Aruba/HPE pattern: Letter-Number-Letter-Number-Letter (e.g., R0M46A)
                aruba_part = re.search(r'\b([A-Z][0-9][A-Z][0-9]{2,}[A-Z]?)(?:[-][A-Z0-9]+)?\b', line.upper())
                if aruba_part:
                    part_candidate = aruba_part.group(1)
                    # Make sure it's not a serial number (CN prefix) or other field
                    if not part_candidate.startswith('CN') and len(part_candidate) >= 5 and len(part_candidate) <= 10:
                        # Don't use if line contains serial number markers
                        if not any(keyword in line_lower for keyword in ['s/n', 'sn:', 'serial', 'sid:']):
                            info["part_number"] = part_candidate
            
            # Model Number patterns - improved for various products
            # Look for patterns like "OSFP-800G-2OPC015" or "800G OSFP to 20SFP DAC 1.5m"
            # Or Aruba model like "50G SFP56 0.65m DAC"
            # Don't use R0M46A as model - that's a part number
            if any(keyword in line_lower for keyword in ['model', 'model no', 'model#', 'type']):
                # Extract model pattern - look for alphanumeric codes
                # Pattern: OSFP-800G-2OPC015, etc. (but not R0M46A which is a part number)
                model_match = re.search(r'([A-Z0-9][A-Z0-9\-]{2,})', line.upper())
                if model_match and not info["model"]:
                    model_text = model_match.group(1).strip()
                    # Avoid very short matches and common OCR errors
                    # Also avoid if it's the same as part_number (R0M46A should be part_number, not model)
                    # Don't use part number patterns (Letter-Number-Letter-Number pattern)
                    if len(model_text) > 2 and not model_text.startswith('AGETETSTLASED'):
                        # Check if it's a part number pattern (R0M46A style)
                        is_part_number_pattern = re.match(r'^[A-Z][0-9][A-Z][0-9]{2,}[A-Z]?$', model_text)
                        if not is_part_number_pattern:
                            if not info["part_number"] or model_text != info["part_number"]:
                                info["model"] = model_text
            
            # Also look for product descriptions (e.g., "800G OSFP to 20SFP DAC 1.5m", "50G SFP56 0.65m DAC")
            # These often contain model info even without "model" keyword
            # But be careful not to combine multiple fields
            if not info["model"] and len(line.strip()) > 5:
                # Look for patterns like "800G OSFP", "DAC", "SFP56", product codes
                # Aruba patterns: "50G SFP56 0.65m DAC", "R0M46A"
                # But don't match if it contains "S/N:" or "Serial:" (that's a different field)
                if any(keyword in line_lower for keyword in ['osfp', 'qsfp', 'sfp', 'sfp56', 'dac', 'aoc', 'g', 'gb', 'm ']):
                    # Skip if this line contains serial number markers (don't combine fields)
                    if not any(keyword in line_lower for keyword in ['s/n', 'sn:', 'serial']):
                        # Extract the line but clean it up
                        model_text = line.strip()
                        # Remove common OCR artifacts at the start
                        model_text = re.sub(r'^[^A-Z0-9]+', '', model_text)  # Remove leading non-alphanumeric
                        # Remove trailing colons/spaces
                        model_text = re.sub(r'[:;]+$', '', model_text).strip()
                        # Don't use if it looks like a part number (R0M46A pattern)
                        if not re.match(r'^[A-Z][0-9][A-Z][0-9]{2,}[A-Z]?$', model_text.upper()):
                            if len(model_text) > 3 and len(model_text) < 100:
                                # Avoid obvious OCR errors
                                if not model_text.startswith('AGETETSTLASED'):
                                    info["model"] = model_text

            # Part Number patterns - moved above to check before model
            # (Already handled in the section above)

            # Asset Tag patterns
            if any(keyword in line_lower for keyword in ['asset tag', 'asset', 'tag']):
                asset_match = re.search(r'(?:SRV|SW|STR|NET|PDU|UPS)?[-]?[0-9]{3,}', line.upper())
                if asset_match and not info["asset_tag"]:
                    info["asset_tag"] = asset_match.group()

            # MAC Address pattern
            mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
            if re.search(mac_pattern, line):
                mac_match = re.search(mac_pattern, line)
                if mac_match and not info["mac_address"]:
                    info["mac_address"] = mac_match.group().upper()

            # Manufacturer detection - add FS.com, Aruba, HPE
            manufacturers_extended = manufacturers + ['fs', 'fs.com', 'fs com']
            for manufacturer in manufacturers_extended:
                if manufacturer in line_lower and not info["manufacturer"]:
                    if manufacturer in ['fs', 'fs.com', 'fs com']:
                        info["manufacturer"] = "FS.com"
                    elif manufacturer in ['aruba']:
                        info["manufacturer"] = "Aruba"
                    elif manufacturer in ['hp', 'hpe']:
                        info["manufacturer"] = "HPE"
                    else:
                        info["manufacturer"] = manufacturer.title()
                    break
            
            # Also check for FS in the raw text (might be vertical text)
            if 'fs' in ocr_text.lower() and not info["manufacturer"]:
                info["manufacturer"] = "FS.com"
            
            # Check for Aruba/HPE in raw text
            if ('aruba' in ocr_text.lower() or 'hpe' in ocr_text.lower()) and not info["manufacturer"]:
                if 'aruba' in ocr_text.lower():
                    info["manufacturer"] = "Aruba"
                else:
                    info["manufacturer"] = "HPE"

            # Hostname patterns (common datacenter naming conventions)
            # Only match if it looks like a real hostname (has a dot, not product codes)
            # Exclude product descriptions like "P800G0SFPT020SFPDAC1.5"
            hostname_pattern = r'^[a-z0-9\-]+\.[a-z0-9\-\.]+$'
            if re.search(hostname_pattern, line_lower):
                # Don't match if it looks like a product code (has numbers followed by letters like "800G", "SFP", "DAC")
                if not re.search(r'\d+[A-Z]{2,}', line.upper()):  # Avoid "800G", "SFP", "DAC" patterns
                    if not info["hostname"]:
                        info["hostname"] = line.strip()

        # Post-processing: Clean up extracted data
        # Common OCR garbage patterns to filter out
        garbage_patterns = [
            r'^AGETETSTLASED.*',  # Common OCR error
            r'^[A-Z]{10,}$',  # All caps long strings (often OCR errors)
            r'^[^A-Z0-9]+$',  # Only special characters
        ]
        
        for key in info:
            if info[key]:
                # Remove common OCR artifacts
                info[key] = info[key].replace('|', 'I').replace('O', '0').strip()
                # Remove trailing colons, semicolons, spaces
                info[key] = re.sub(r'[:;]+$', '', info[key]).strip()
                # Remove leading/trailing whitespace
                info[key] = info[key].strip()
                
                # Filter out garbage patterns
                is_garbage = False
                for pattern in garbage_patterns:
                    if re.match(pattern, info[key], re.IGNORECASE):
                        is_garbage = True
                        break
                
                if is_garbage:
                    info[key] = None
                    continue
                
                # Special cleanup for model field
                if key == "model":
                    # Remove common OCR error patterns
                    if info[key] and info[key].startswith('AGETETSTLASED'):
                        info[key] = None
                    # If model looks like a hostname (has dots and numbers), might be wrong
                    elif info[key] and '.' in info[key] and re.search(r'\d+[A-Z]{2,}', info[key]):
                        # Could be a product code, but if it has multiple dots it's probably a hostname
                        if info[key].count('.') > 1:
                            info[key] = None
                
                # Special cleanup for hostname field
                if key == "hostname":
                    # If hostname looks like a product code (has patterns like "800G", "SFP", "DAC")
                    if info[key] and re.search(r'\d+[A-Z]{2,}', info[key]):
                        # It's probably not a hostname, clear it
                        info[key] = None

        return info

    async def process_image(
        self, 
        image_data: bytes, 
        use_cloud_ocr: bool = False, 
        force_cloud_ocr: bool = False,
        db: Optional[Session] = None
    ) -> Dict:
        """
        Process image and return OCR results with parsed information.
        
        Now uses RackPlane Services API for all OCR processing (Tesseract or Cloud).
        All OCR happens on YOUR servers - this just makes a simple HTTP call.
        
        Args:
            image_data: Image bytes
            use_cloud_ocr: If True, use cloud OCR (requires subscription). If False, use Tesseract.
            force_cloud_ocr: If True, skip Tesseract and use cloud OCR directly
            db: Optional database session (needed for RackPlane Services client)
        """
        try:
            from app.bridges.rackplane_services import RackPlaneServicesClient
            has_rpc_client = True
        except ImportError:
            RackPlaneServicesClient = None
            has_rpc_client = False
            
        from fastapi import HTTPException
        
        ocr_text = ""
        ocr_source = "none"
        confidence = "none"
        
        
        # Use RackPlane Services API for OCR (Tesseract or Cloud)
        if db and has_rpc_client:
            try:
                client = RackPlaneServicesClient(db)
                
                # Determine which OCR to use
                use_cloud = force_cloud_ocr or use_cloud_ocr
                
                # Make boring API call - YOUR backend does all the OCR work
                ocr_result = await client.ocr(
                    image_data=image_data,
                    use_cloud=use_cloud
                )
                
                ocr_text = ocr_result.get('text', '')
                ocr_source = ocr_result.get('service_used', 'tesseract')
                confidence = ocr_result.get('confidence', 'medium')
                
                logger.info(f"OCR via RackPlane Services: {ocr_source} (confidence: {confidence})")
                
            except HTTPException as e:
                if e.status_code == 402:
                    # Subscription required - fall back to Tesseract if cloud was requested
                    if use_cloud and not force_cloud_ocr:
                        logger.info(f"Cloud OCR requires subscription, falling back to Tesseract: {e.detail}")
                        try:
                            ocr_result = await client.ocr(image_data, use_cloud=False)
                            ocr_text = ocr_result.get('text', '')
                            ocr_source = ocr_result.get('service_used', 'tesseract')
                            confidence = ocr_result.get('confidence', 'medium')
                        except Exception as fallback_error:
                            logger.error(f"Tesseract fallback failed: {fallback_error}")
                    else:
                        raise
                elif e.status_code == 401:
                    # API key not configured - log but don't fail
                    logger.warning(f"RackPlane Services API key not configured: {e.detail}")
                    # Fall back to local Tesseract if available
                    if self.has_tesseract:
                        logger.info("Falling back to local Tesseract")
                        ocr_text = self.extract_text_from_image(image_data)
                        ocr_source = "tesseract" if ocr_text else "none"
                        confidence = "medium" if ocr_text else "none"
                else:
                    raise
            except Exception as e:
                logger.error(f"RackPlane Services OCR failed: {e}")
                # Fall back to local Tesseract if available
                if self.has_tesseract:
                    logger.info("Falling back to local Tesseract")
                    ocr_text = self.extract_text_from_image(image_data)
                    ocr_source = "tesseract" if ocr_text else "none"
                    confidence = "medium" if ocr_text else "none"
        else:
            # No database session - fall back to local Tesseract
            if self.has_tesseract:
                logger.info("No DB session, using local Tesseract")
                ocr_text = self.extract_text_from_image(image_data)
                ocr_source = "tesseract" if ocr_text else "none"
                confidence = "medium" if ocr_text else "none"
            else:
                logger.warning("No OCR available - neither RackPlane Services nor local Tesseract")
        
        parsed_info = self.parse_asset_information(ocr_text)
        
        return {
            "raw_text": ocr_text,
            "parsed_data": parsed_info,
            "confidence": confidence,
            "ocr_source": ocr_source,
            "suggestions": self._generate_suggestions(parsed_info)
        }

    def _generate_suggestions(self, parsed_info: Dict) -> List[str]:
        """Generate helpful suggestions based on parsed data"""
        suggestions = []

        if parsed_info.get("serial_number"):
            suggestions.append(f"Serial Number detected: {parsed_info['serial_number']}")

        if parsed_info.get("model"):
            suggestions.append(f"Model detected: {parsed_info['model']}")

        if parsed_info.get("manufacturer"):
            suggestions.append(f"Manufacturer detected: {parsed_info['manufacturer']}")

        if parsed_info.get("asset_tag"):
            suggestions.append(f"Asset Tag detected: {parsed_info['asset_tag']}")

        if parsed_info.get("mac_address"):
            suggestions.append(f"MAC Address detected: {parsed_info['mac_address']}")

        if not suggestions:
            suggestions.append("No asset information detected. You may need to take a clearer photo.")

        return suggestions
