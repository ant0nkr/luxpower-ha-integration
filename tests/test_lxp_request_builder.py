"""Tests for LxpRequestBuilder."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.lxp_modbus.classes.lxp_request_builder import LxpRequestBuilder


def test_prepare_packet_for_write_accepts_register_values_above_signed_range():
    """Register writes should preserve the full 16-bit word."""
    packet = LxpRequestBuilder.prepare_packet_for_write(
        b"DG44302247",
        b"4434280298",
        21,
        62404,
    )

    assert packet[-4:-2] == bytes([0xC4, 0xF3])


def test_prepare_packet_for_write_masks_values_to_unsigned_16_bit():
    """Values should be encoded as unsigned 16-bit register contents."""
    packet = LxpRequestBuilder.prepare_packet_for_write(
        b"DG44302247",
        b"4434280298",
        21,
        0x1FFFF,
    )

    assert packet[-4:-2] == bytes([0xFF, 0xFF])
