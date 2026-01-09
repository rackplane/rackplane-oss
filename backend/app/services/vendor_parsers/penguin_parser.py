# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Penguin Computing / Penguin Solutions Order Parser

Parses order forms and quotes from Penguin Computing (penguinsolutions.com).

Sample format (Q254331):
    Order Form ID: Q254331
    Order Form Date: 12/08/2025
    
    Description                     Qty    Unit Price    Ext. Price
    Altus XE8318GTSv2-AIR Server    8      $415,000.00   $3,320,000.00
    ...
    TOTAL                                                $3,830,281.75
"""

import re
from typing import List, Optional
from .base_parser import VendorOrderParser, ParsedOrder, ParsedOrderItem


class PenguinComputingParser(VendorOrderParser):
    """Parser for Penguin Computing/Solutions order forms."""
    
    vendor_name = "Penguin Computing"
    vendor_patterns = [
        "penguinsolutions.com",
        "Penguin Computing",
        "Penguin Solutions",
        "PENGUIN",
        "888-PENGUIN"
    ]
    
    def can_parse(self, text: str) -> bool:
        """Check if text contains Penguin Computing markers."""
        text_upper = text.upper()
        return any(
            pattern.upper() in text_upper 
            for pattern in self.vendor_patterns
        )
    
    def parse(self, text: str) -> ParsedOrder:
        """Parse Penguin Computing order form text."""
        order = ParsedOrder(
            vendor=self.vendor_name,
            raw_text=text
        )
        
        # Extract Order Form ID (e.g., "Q254331")
        order_id_match = re.search(r'Order Form ID\s*[:\n]?\s*([A-Z0-9]+)', text)
        if order_id_match:
            order.order_number = order_id_match.group(1)
        
        # Extract Order Form Date
        date_match = re.search(r'Order Form Date\s*[:\n]?\s*(\d{1,2}/\d{1,2}/\d{4})', text)
        if date_match:
            order.order_date = date_match.group(1)
        
        # Extract Customer name (after "Customer:")
        customer_match = re.search(r'Customer:\s*([A-Za-z0-9\s]+?)(?:\n|Billing)', text)
        if customer_match:
            order.customer_name = customer_match.group(1).strip()
        
        # Extract TOTAL
        total_match = re.search(r'TOTAL\s*\$?([\d,]+\.?\d*)', text)
        if total_match:
            order.total = self.parse_price(total_match.group(1))
        
        # Extract Subtotal
        subtotal_match = re.search(r'Subtotal\s*\$?([\d,]+\.?\d*)', text)
        if subtotal_match:
            order.subtotal = self.parse_price(subtotal_match.group(1))
        
        # Parse line items
        order.items = self._parse_line_items(text)
        
        return order
    
    def _parse_line_items(self, text: str) -> List[ParsedOrderItem]:
        """
        Parse line items from Penguin order form.
        
        PDF format has:
        - "Description" header line (marks start of items section)
        - Item description on one or MORE lines (includes specs like CPU, RAM)
        - Column headers (Qty, Unit Price, Ext. Price) on separate lines
        - Values (number, $price, $price) for each column
        
        We accumulate ALL description lines until we hit qty/price.
        """
        items = []
        lines = text.split('\n')
        
        qty_pattern = re.compile(r'^(\d+)$')  # Just a number alone
        
        description_lines = []  # Accumulate multi-line descriptions
        pending_qty = None
        pending_unit = None
        in_items_section = False
        
        column_headers = {'Qty', 'Unit Price', 'Ext. Price'}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Start after "Description" header
            if line == 'Description':
                in_items_section = True
                continue
            
            # Skip column headers
            if line in column_headers:
                continue
            
            # Stop at TOTAL
            if line.startswith('TOTAL'):
                break
            
            if not in_items_section:
                continue
            
            # Match qty (number alone like "8" or "32")
            qty_match = qty_pattern.match(line)
            if qty_match and description_lines:
                pending_qty = int(qty_match.group(1))
                continue
            
            # Match price (starts with $)
            if line.startswith('$') and pending_qty is not None:
                price_val = self.parse_price(line)
                if price_val is not None:
                    if pending_unit is None:
                        pending_unit = price_val
                    else:
                        # We have both prices - create item
                        ext_price = price_val
                        
                        # Join all description lines with newline for full specs
                        full_description = '\n'.join(description_lines)
                        
                        if full_description and pending_qty:
                            category = self.detect_category(full_description)
                            
                            item = ParsedOrderItem(
                                description=full_description,
                                quantity=pending_qty,
                                unit_price=pending_unit,
                                extended_price=ext_price,
                                category=category,
                                manufacturer=self._extract_manufacturer(full_description),
                                part_number=self._extract_part_number(full_description)
                            )
                            items.append(item)
                        
                        # Reset for next item
                        description_lines = []
                        pending_qty = None
                        pending_unit = None
                continue
            
            # Otherwise this is a description line - accumulate it
            if len(line) > 3 and not line.startswith('$') and pending_qty is None:
                description_lines.append(line)
        
        return items


    
    def _extract_manufacturer(self, description: str) -> Optional[str]:
        """Extract manufacturer from description if mentioned."""
        desc_lower = description.lower()
        
        # Known manufacturers
        manufacturers = {
            "nvidia": "NVIDIA",
            "amd": "AMD",
            "intel": "Intel",
            "mellanox": "NVIDIA",  # Mellanox is now NVIDIA
            "netshelter": "APC",
            "supermicro": "Supermicro",
        }
        
        for key, value in manufacturers.items():
            if key in desc_lower:
                return value
        
        # Default to Penguin for servers
        if any(kw in desc_lower for kw in ["altus", "relion", "penguin"]):
            return "Penguin Computing"
        
        return None
    
    def _extract_part_number(self, description: str) -> Optional[str]:
        """Extract part number patterns from description."""
        # Common patterns:
        # - SN5610, SN2201, AR3350B2
        # - XE8318GTSv2
        # - NDR 800G
        
        patterns = [
            r'\b(SN\d{4})\b',           # Nvidia switches: SN5610
            r'\b(AR\d+[A-Z0-9]*)\b',     # APC racks: AR3350B2
            r'\b(XE\d+[A-Z0-9]*)\b',     # Penguin servers: XE8318GTSv2
            r'\b([A-Z]{2,4}-[A-Z0-9-]+)\b',  # Generic part numbers
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)
        
        return None


# Convenience function
def parse_penguin_order(text: str) -> Optional[ParsedOrder]:
    """Parse text as a Penguin Computing order, or return None if not parseable."""
    parser = PenguinComputingParser()
    if parser.can_parse(text):
        return parser.parse(text)
    return None
