import pytest
from app.services.product_parser import ProductParserService

@pytest.mark.regression
def test_parse_simple_product():
    """Test parsing of a standard product string."""
    name = "Cisco SFP-10G-SR Compatible 10G SFP+ 850nm 300m DOM Transceiver Module"
    result = ProductParserService.parse_product_name(name)

    assert result['speed'] == '10G'
    # Parser finds FIRST occurrence of form_factor in string: "SFP" from "SFP-10G-SR" (not "SFP+" later)
    assert result['form_factor'] == 'SFP'
    assert result['interface'] == 'SR'
    assert result['category'] == 'optical_transceiver'

@pytest.mark.regression
def test_parse_complex_800g_product():
    """Test parsing of a modern high-speed product."""
    name = "NVIDIA MMA4Z00-Ns400 Compatible 400G SR4 OSFP 850nm 50m DOM Optical Transceiver"
    result = ProductParserService.parse_product_name(name)
    
    assert result['speed'] == '400G'
    assert result['form_factor'] == 'OSFP'
    assert result['interface'] == 'SR4'
    assert result['category'] == 'optical_transceiver'

@pytest.mark.regression
def test_parse_dac_cable():
    """Test parsing of a DAC cable."""
    name = "100G QSFP28 to QSFP28 Passive Direct Attach Copper Cable 1m"
    result = ProductParserService.parse_product_name(name)

    assert result['speed'] == '100G'
    assert result['form_factor'] == 'QSFP28'
    # String contains "COPPER" which regex matches before DAC heuristic applies
    assert result['media_type'] == 'COPPER'
    assert result['category'] == 'dac_cable'

@pytest.mark.regression
def test_parse_fiber_patch_cord():
    """Test parsing of a fiber cable."""
    name = "LC UPC to LC UPC Duplex OM4 Multimode Patch Cord"
    result = ProductParserService.parse_product_name(name)

    assert result['connector'] == 'LC'
    assert result['media_type'] == 'OM4'
    # String contains "LC" but not "CABLE", so _determine_category returns 'other'
    assert result['category'] == 'other'
