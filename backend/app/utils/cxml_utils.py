"""
cXML Utilities for Punchout Integration

This module provides utilities for generating and parsing cXML messages
for Amazon Business Punchout integration.

cXML (Commerce eXtensible Markup Language) is a protocol for B2B e-commerce
transactions, standardized by Ariba.

References:
- cXML User's Guide: https://cxml.org/
- Amazon Business Punchout: Uses standard cXML 1.2
"""

import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from defusedxml.ElementTree import fromstring as safe_fromstring

# cXML DTD version
CXML_VERSION = "1.2.050"


def generate_payload_id() -> str:
    """Generate a unique PayloadID for cXML messages.
    
    Format: timestamp.random@rackplane.io
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    unique_part = uuid.uuid4().hex[:8]
    return f"{timestamp}.{unique_part}@rackplane.io"


def build_punchout_setup_request(
    from_identity: str,
    to_identity: str,
    shared_secret: str,
    buyer_cookie: str,
    callback_url: str,
    user_email: Optional[str] = None,
    operation: str = "create",
) -> str:
    """
    Build a PunchOutSetupRequest cXML message.
    
    Args:
        from_identity: The buyer's identity (your DUNS or Network ID)
        to_identity: Amazon Business identity (usually 'Amazon' or provided by Amazon)
        shared_secret: The shared secret for authentication
        buyer_cookie: A unique identifier for this session (used to correlate the response)
        callback_url: The URL where Amazon will POST the PunchOutOrderMessage
        user_email: User's email address (REQUIRED by Amazon Business)
        operation: 'create' for new session, 'edit' or 'inspect' for existing carts
        
    Returns:
        cXML document as a string
    """
    payload_id = generate_payload_id()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    
    # Build the cXML structure
    cxml = Element("cXML", {
        "payloadID": payload_id,
        "timestamp": timestamp,
        "version": CXML_VERSION,
    })
    
    # Header
    header = SubElement(cxml, "Header")
    
    # From (Buyer)
    from_elem = SubElement(header, "From")
    from_cred = SubElement(from_elem, "Credential", {"domain": "NetworkId"})
    SubElement(from_cred, "Identity").text = from_identity
    
    # To (Supplier - Amazon)
    to_elem = SubElement(header, "To")
    to_cred = SubElement(to_elem, "Credential", {"domain": "NetworkId"})
    SubElement(to_cred, "Identity").text = to_identity
    
    # Sender (same as From, but includes SharedSecret)
    sender = SubElement(header, "Sender")
    sender_cred = SubElement(sender, "Credential", {"domain": "NetworkId"})
    SubElement(sender_cred, "Identity").text = from_identity
    SubElement(sender_cred, "SharedSecret").text = shared_secret
    SubElement(sender, "UserAgent").text = "RackPlane Punchout/1.0"
    
    # Request
    request = SubElement(cxml, "Request")
    punchout_setup = SubElement(request, "PunchOutSetupRequest", {"operation": operation})
    
    # BuyerCookie - THIS IS CRITICAL for correlating the response
    SubElement(punchout_setup, "BuyerCookie").text = buyer_cookie
    
    # Extrinsic UserEmail - REQUIRED by Amazon Business
    if user_email:
        extrinsic_email = SubElement(punchout_setup, "Extrinsic", {"name": "UserEmail"})
        extrinsic_email.text = user_email
    
    # BrowserFormPost - where Amazon sends the user back with the cart
    browser_post = SubElement(punchout_setup, "BrowserFormPost")
    SubElement(browser_post, "URL").text = callback_url
    
    # Generate XML string with declaration
    xml_bytes = tostring(cxml, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE cXML SYSTEM "http://xml.cxml.org/schemas/cXML/{CXML_VERSION}/cXML.dtd">\n{xml_bytes}'


class PunchoutOrderItem:
    """Represents an item from a PunchOutOrderMessage."""
    
    def __init__(
        self,
        supplier_part_id: str,
        quantity: float,
        unit_price: float,
        currency: str,
        description: str,
        unit_of_measure: str = "EA",
        manufacturer_part_id: Optional[str] = None,
        manufacturer_name: Optional[str] = None,
        classification: Optional[dict] = None,
    ):
        self.supplier_part_id = supplier_part_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.currency = currency
        self.description = description
        self.unit_of_measure = unit_of_measure
        self.manufacturer_part_id = manufacturer_part_id
        self.manufacturer_name = manufacturer_name
        self.classification = classification or {}
    
    def __repr__(self):
        return f"<PunchoutOrderItem sku={self.supplier_part_id} qty={self.quantity} price={self.unit_price}>"


class PunchoutOrderParseResult:
    """Result of parsing a PunchOutOrderMessage."""
    
    def __init__(
        self,
        buyer_cookie: str,
        items: list[PunchoutOrderItem],
        total: Optional[float] = None,
        currency: Optional[str] = None,
        raw_xml: Optional[str] = None,
    ):
        self.buyer_cookie = buyer_cookie
        self.items = items
        self.total = total
        self.currency = currency
        self.raw_xml = raw_xml
    
    def __repr__(self):
        return f"<PunchoutOrderParseResult cookie={self.buyer_cookie} items={len(self.items)}>"


def parse_punchout_order_message(xml_content: str) -> PunchoutOrderParseResult:
    """
    Parse a PunchOutOrderMessage cXML from Amazon.
    
    This message contains the items the user added to their cart on Amazon
    and is POSTed to our BrowserFormPost URL when they checkout.
    
    Args:
        xml_content: The raw cXML content (from the cxml-urlencoded form field)
        
    Returns:
        PunchoutOrderParseResult with extracted items
        
    Raises:
        ValueError: If the XML is malformed or missing required elements
    """
    # Use defusedxml for safe parsing
    root = safe_fromstring(xml_content)
    
    # Navigate to PunchOutOrderMessage
    # Structure: cXML/Message/PunchOutOrderMessage
    message = root.find(".//Message")
    if message is None:
        raise ValueError("No Message element found in cXML")
    
    punchout_order = message.find("PunchOutOrderMessage")
    if punchout_order is None:
        raise ValueError("No PunchOutOrderMessage element found")
    
    # Extract BuyerCookie
    buyer_cookie_elem = punchout_order.find("BuyerCookie")
    if buyer_cookie_elem is None or buyer_cookie_elem.text is None:
        raise ValueError("BuyerCookie is required but not found")
    buyer_cookie = buyer_cookie_elem.text
    
    # Extract items from PunchOutOrderMessageHeader/ItemIn elements
    items = []
    
    for item_in in punchout_order.findall(".//ItemIn"):
        # Get quantity
        quantity_elem = item_in.get("quantity", "1")
        try:
            quantity = float(quantity_elem)
        except ValueError:
            quantity = 1.0
        
        # ItemID contains SupplierPartID
        item_id = item_in.find("ItemID")
        supplier_part_id = ""
        if item_id is not None:
            supplier_part_id_elem = item_id.find("SupplierPartID")
            if supplier_part_id_elem is not None and supplier_part_id_elem.text:
                supplier_part_id = supplier_part_id_elem.text
        
        # ItemDetail contains description and price
        item_detail = item_in.find("ItemDetail")
        unit_price = 0.0
        currency = "USD"
        description = ""
        unit_of_measure = "EA"
        manufacturer_part_id = None
        manufacturer_name = None
        classification = {}
        
        if item_detail is not None:
            # UnitPrice
            unit_price_elem = item_detail.find("UnitPrice")
            if unit_price_elem is not None:
                money = unit_price_elem.find("Money")
                if money is not None:
                    currency = money.get("currency", "USD")
                    try:
                        unit_price = float(money.text or "0")
                    except ValueError:
                        unit_price = 0.0
            
            # Description
            desc_elem = item_detail.find("Description")
            if desc_elem is not None and desc_elem.text:
                description = desc_elem.text
            
            # UnitOfMeasure
            uom_elem = item_detail.find("UnitOfMeasure")
            if uom_elem is not None and uom_elem.text:
                unit_of_measure = uom_elem.text
            
            # ManufacturerPartID
            mfr_part_elem = item_detail.find("ManufacturerPartID")
            if mfr_part_elem is not None and mfr_part_elem.text:
                manufacturer_part_id = mfr_part_elem.text
            
            # ManufacturerName
            mfr_name_elem = item_detail.find("ManufacturerName")
            if mfr_name_elem is not None and mfr_name_elem.text:
                manufacturer_name = mfr_name_elem.text
            
            # Classification (UNSPSC codes, etc.)
            for class_elem in item_detail.findall("Classification"):
                domain = class_elem.get("domain", "unknown")
                if class_elem.text:
                    classification[domain] = class_elem.text
        
        items.append(PunchoutOrderItem(
            supplier_part_id=supplier_part_id,
            quantity=quantity,
            unit_price=unit_price,
            currency=currency,
            description=description,
            unit_of_measure=unit_of_measure,
            manufacturer_part_id=manufacturer_part_id,
            manufacturer_name=manufacturer_name,
            classification=classification,
        ))
    
    # Calculate total from items
    total = sum(item.unit_price * item.quantity for item in items)
    currency_final = items[0].currency if items else "USD"
    
    return PunchoutOrderParseResult(
        buyer_cookie=buyer_cookie,
        items=items,
        total=total,
        currency=currency_final,
        raw_xml=xml_content,
    )


def build_punchout_setup_response(
    payload_id: str,
    status_code: str = "200",
    status_text: str = "OK",
    start_page_url: Optional[str] = None,
) -> str:
    """
    Build a PunchOutSetupResponse cXML message.
    
    This is used to simulate Amazon's response for testing purposes.
    In production, Amazon generates this response.
    
    Args:
        payload_id: The PayloadID to use
        status_code: HTTP-like status code ("200" for success)
        status_text: Status text description
        start_page_url: The URL to redirect the user to (Amazon's shopping page)
        
    Returns:
        cXML document as a string
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    
    cxml = Element("cXML", {
        "payloadID": payload_id,
        "timestamp": timestamp,
        "version": CXML_VERSION,
    })
    
    response = SubElement(cxml, "Response")
    
    # Status
    status = SubElement(response, "Status", {"code": status_code, "text": status_text})
    
    if status_code == "200" and start_page_url:
        # PunchOutSetupResponse
        punchout_response = SubElement(response, "PunchOutSetupResponse")
        SubElement(punchout_response, "StartPage").append(
            Element("URL")
        )
        punchout_response.find("StartPage/URL").text = start_page_url
    
    xml_bytes = tostring(cxml, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_bytes}'


class OrderRequestItem:
    """Represents an item for an OrderRequest."""
    
    def __init__(
        self,
        line_number: int,
        supplier_part_id: str,
        quantity: int,
        unit_price: float,
        currency: str = "USD",
        description: str = "",
        unit_of_measure: str = "EA",
        supplier_part_auxiliary_id: Optional[str] = None,
    ):
        self.line_number = line_number
        self.supplier_part_id = supplier_part_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.currency = currency
        self.description = description
        self.unit_of_measure = unit_of_measure
        self.supplier_part_auxiliary_id = supplier_part_auxiliary_id


def build_order_request(
    from_identity: str,
    to_identity: str,
    shared_secret: str,
    order_id: str,
    order_date: Optional[str] = None,
    items: list[OrderRequestItem] = None,
    ship_to_name: str = "",
    ship_to_address: Optional[dict] = None,
    bill_to_name: str = "",
    bill_to_address: Optional[dict] = None,
    total: Optional[float] = None,
    currency: str = "USD",
    mode: str = "test",
) -> str:
    """
    Build a cXML OrderRequest message for Amazon Business.
    
    Args:
        from_identity: The buyer's identity (Network ID)
        to_identity: Amazon Business identity
        shared_secret: The shared secret for authentication
        order_id: Unique order/PO number
        order_date: Order date in ISO format (defaults to now)
        items: List of OrderRequestItem objects
        ship_to_name: Ship-to contact name
        ship_to_address: Dict with street, city, state, postal_code, country
        bill_to_name: Bill-to contact name
        bill_to_address: Dict with street, city, state, postal_code, country
        total: Order total (calculated from items if not provided)
        currency: Currency code (default USD)
        
    Returns:
        cXML OrderRequest document as a string
    """
    def validate_field(value: Optional[str], max_length: int = 255) -> str:
        """Sanitize and truncate fields to prevent issues and meet limits."""
        if not value:
            return ""
        # Remove control characters (except allowed whitespace)
        sanitized = "".join(ch for ch in str(value) if ch.isprintable())
        return sanitized[:max_length]
    if items is None:
        items = []
    
    payload_id = generate_payload_id()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    
    if order_date is None:
        order_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    
    # Calculate total if not provided
    if total is None:
        total = sum(item.unit_price * item.quantity for item in items)
    
    # Build the cXML structure
    # Build the cXML structure
    cxml = Element("cXML", {
        "payloadID": payload_id,
        "timestamp": timestamp,
        "version": CXML_VERSION,
    })
    
    if mode == "test":
        cxml.set("deploymentMode", "test")
    elif mode == "production":
        cxml.set("deploymentMode", "production")
    
    # Header (same structure as PunchOutSetupRequest)
    header = SubElement(cxml, "Header")
    
    # From (Buyer)
    from_elem = SubElement(header, "From")
    from_cred = SubElement(from_elem, "Credential", {"domain": "NetworkId"})
    SubElement(from_cred, "Identity").text = from_identity
    
    # To (Supplier - Amazon)
    to_elem = SubElement(header, "To")
    to_cred = SubElement(to_elem, "Credential", {"domain": "NetworkId"})
    SubElement(to_cred, "Identity").text = to_identity
    
    # Sender (same as From, with SharedSecret)
    sender = SubElement(header, "Sender")
    sender_cred = SubElement(sender, "Credential", {"domain": "NetworkId"})
    SubElement(sender_cred, "Identity").text = from_identity
    SubElement(sender_cred, "SharedSecret").text = shared_secret
    SubElement(sender, "UserAgent").text = "RackPlane Punchout/1.0"
    
    # Request
    request = SubElement(cxml, "Request")
    order_request = SubElement(request, "OrderRequest")
    
    # OrderRequestHeader
    order_header = SubElement(order_request, "OrderRequestHeader", {
        "orderID": order_id,
        "orderDate": order_date,
        "type": "new",
    })
    
    # Total
    total_elem = SubElement(order_header, "Total")
    money_elem = SubElement(total_elem, "Money", {"currency": currency})
    money_elem.text = f"{total:.2f}"
    
    # ShipTo (if provided)
    if ship_to_address:
        ship_to = SubElement(order_header, "ShipTo")
        address = SubElement(ship_to, "Address")
        if ship_to_name:
            SubElement(address, "Name").text = validate_field(ship_to_name)
        postal = SubElement(address, "PostalAddress")
        if ship_to_address.get("street"):
            SubElement(postal, "Street").text = validate_field(ship_to_address["street"])
        if ship_to_address.get("city"):
            SubElement(postal, "City").text = validate_field(ship_to_address["city"], 50)
        if ship_to_address.get("state"):
            SubElement(postal, "State").text = validate_field(ship_to_address["state"], 50)
        if ship_to_address.get("postal_code"):
            SubElement(postal, "PostalCode").text = validate_field(ship_to_address["postal_code"], 20)
        if ship_to_address.get("country"):
            country_code = validate_field(ship_to_address["country"], 2).upper()
            country_elem = SubElement(postal, "Country", {"isoCountryCode": country_code})
            country_elem.text = country_code
    
    # BillTo (if provided)
    if bill_to_address:
        bill_to = SubElement(order_header, "BillTo")
        address = SubElement(bill_to, "Address")
        if bill_to_name:
            SubElement(address, "Name").text = validate_field(bill_to_name)
        postal = SubElement(address, "PostalAddress")
        if bill_to_address.get("street"):
            SubElement(postal, "Street").text = validate_field(bill_to_address["street"])
        if bill_to_address.get("city"):
            SubElement(postal, "City").text = validate_field(bill_to_address["city"], 50)
        if bill_to_address.get("state"):
            SubElement(postal, "State").text = validate_field(bill_to_address["state"], 50)
        if bill_to_address.get("postal_code"):
            SubElement(postal, "PostalCode").text = validate_field(bill_to_address["postal_code"], 20)
        if bill_to_address.get("country"):
            country_code = validate_field(bill_to_address["country"], 2).upper()
            country_elem = SubElement(postal, "Country", {"isoCountryCode": country_code})
            country_elem.text = country_code
    
    # ItemOut elements
    for item in items:
        item_out = SubElement(order_request, "ItemOut", {
            "lineNumber": str(item.line_number),
            "quantity": str(item.quantity),
        })
        
        # ItemID
        item_id = SubElement(item_out, "ItemID")
        SubElement(item_id, "SupplierPartID").text = item.supplier_part_id
        if item.supplier_part_auxiliary_id:
            SubElement(item_id, "SupplierPartAuxiliaryID").text = item.supplier_part_auxiliary_id
        
        # ItemDetail
        item_detail = SubElement(item_out, "ItemDetail")
        
        # UnitPrice
        unit_price_elem = SubElement(item_detail, "UnitPrice")
        money = SubElement(unit_price_elem, "Money", {"currency": item.currency})
        money.text = f"{item.unit_price:.2f}"
        
        # Description
        if item.description:
            SubElement(item_detail, "Description").text = item.description
        
        # UnitOfMeasure
        SubElement(item_detail, "UnitOfMeasure").text = item.unit_of_measure
    
    # Generate XML string with declaration
    xml_bytes = tostring(cxml, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE cXML SYSTEM "http://xml.cxml.org/schemas/cXML/{CXML_VERSION}/cXML.dtd">\n{xml_bytes}'
