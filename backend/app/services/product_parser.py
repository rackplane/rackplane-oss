# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Product Parser Service
Extracts structured attributes (speed, form_factor, etc.) from product names/descriptions.
Generalized for use with FS.com, NVIDIA, and other vendor data.
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ProductParserService:
    """
    Parses unstructured product strings into structured attributes.
    """
    
    # Regex patterns for extraction
    PATTERNS = {
        'speed': r'(800G|400G|200G|100G|50G|40G|25G|10G|1G)',
        'form_factor': r'(OSFP|QSFP-DD|QSFP56|QSFP28|QSFP\+|QSFP|SFP28|SFP\+|SFP|DSFP)',
        'interface': r'\b(SR4|SR8|DR4|DR8|FR4|LR4|ER4|ZR4|SR|LR|ER|ZR|PLR4|PSM4|CWDM4|SWDM4|BiDi|LX|SX|EX|ZX)\b',
        'connector': r'\b(LC|SC|MTP|MPO|MPO-12|MPO-16|MPO-24|RJ45)\b',
        'media_type': r'\b(MMF|SMF|OM3|OM4|OM5|OS2|DAC|AOC|COPPER)\b',
        'wavelength': r'(\d{3,4})nm'
    }
    
    @classmethod
    def parse_product_name(cls, name: str, description: str = "") -> Dict[str, Any]:
        """
        Extract attributes from product name and description.
        
        Args:
            name: Product name/title
            description: Detailed product description (optional)
            
        Returns:
            Dict of extracted attributes
        """
        full_text = f"{name} {description}".upper()
        attributes = {}
        
        for key, pattern in cls.PATTERNS.items():
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                value = match.group(1).upper()
                # Normalize specific values
                if key == 'form_factor':
                    value = value.replace('QSFP+', 'QSFP_PLUS').replace('SFP+', 'SFP_PLUS')
                attributes[key] = value

        # Post-processing heuristics
        if 'DIRECT ATTACH' in full_text and 'media_type' not in attributes:
             attributes['media_type'] = 'DAC'
             
        # Heuristics for determining category
        attributes['category'] = cls._determine_category(full_text, attributes)
        
        return attributes
    
    @classmethod
    def extract_manufacturer_from_name(cls, name: str) -> Optional[str]:
        """
        Extract manufacturer/brand from product name.
        
        Usually the manufacturer is the first word or hyphenated phrase.
        Examples:
        - "FiberCablesDirect LC-LC OS2..." -> "FiberCablesDirect"  
        - "Celestica DS10000 Switch" -> "Celestica"
        - "NVIDIA MCP4Y10-N002 DAC" -> "NVIDIA"
        
        Args:
            name: Product name
            
        Returns:
            Extracted manufacturer name or None
        """
        if not name:
            return None
            
        # Remove leading/trailing spaces
        name = name.strip()
        
        # Common patterns to skip (not manufacturers)
        skip_words = {
            'new', 'used', 'refurbished', 'genuine', 'original', 'oem',
            'compatible', 'replacement', 'premium', 'professional'
        }
        
        # Split on spaces
        words = name.split()
        if not words:
            return None
            
        # Get first word (or hyphenated phrase)
        first_word = words[0]
        
        # Skip if it's a common prefix
        if first_word.lower() in skip_words:
            if len(words) > 1:
                first_word = words[ 1]
            else:
                return None
                
        # Clean up - remove special chars except hyphens
        manufacturer = re.sub(r'[^\w\-]', '', first_word)
        
        # Capitalize properly
        manufacturer = manufacturer.strip()
        
        return manufacturer if manufacturer else None
    
    @staticmethod
    def _determine_category(text: str, attrs: Dict[str, Any]) -> str:
        """Determine overarching category based on attributes and text."""
        if 'TRANSCEIVER' in text or 'MODULE' in text:
            return 'optical_transceiver'
        if 'DAC' in text or 'DIRECT ATTACH' in text or attrs.get('media_type') == 'DAC':
            return 'dac_cable'
        if 'AOC' in text or 'ACTIVE OPTICAL' in text:
            return 'aoc_cable'
        if 'CABLE' in text and ('MTP' in text or 'MPO' in text or 'LC' in text):
            return 'fiber_cable'
        if 'SWITCH' in text:
            return 'switch'
        return 'other'
