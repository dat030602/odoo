# -*- coding: utf-8 -*-

import hashlib
import xmltodict
from odoo import _
from odoo.exceptions import UserError


class VietnameseInvoiceParser:
    """Parser for Vietnamese electronic invoice XML files."""

    # Common format mapping for Vietnamese invoice XML structure
    COMMON_KEYS = {
        "TTChung",
        "NBan",
        "NMua",
        "HHDVu",
        "TToan",
    }

    @classmethod
    def safe_float(cls, value, default=0.0):
        """Safely convert value to float."""
        if value is None:
            return default
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return default

    @classmethod
    def find_key_dynamic(cls, data, target_key):
        if isinstance(data, dict):
            if target_key in data:
                return data[target_key]
            for key, value in data.items():
                result = cls.find_key_dynamic(value, target_key)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = cls.find_key_dynamic(item, target_key)
                if result is not None:
                    return result
        return None

    @classmethod
    def parse_xml_content(cls, xml_content):
        """
        Parse XML content and return structured invoice data.

        Args:
            xml_content (str or bytes): XML content as string or bytes

        Returns:
            dict: Parsed invoice data with keys matching COMMON_FORMAT

        Raises:
            UserError: If XML parsing fails
        """
        try:
            # Handle different encodings
            if isinstance(xml_content, bytes):
                # Try UTF-8 first
                try:
                    xml_content = xml_content.decode("utf-8")
                except UnicodeDecodeError:
                    # Try UTF-8 with BOM
                    try:
                        xml_content = xml_content.decode("utf-8-sig")
                    except UnicodeDecodeError:
                        # Try windows-1258 (Vietnamese encoding)
                        try:
                            xml_content = xml_content.decode("windows-1258")
                        except UnicodeDecodeError:
                            raise UserError(
                                _(
                                    "Unable to decode XML file. Supported encodings: UTF-8, UTF-8-SIG, Windows-1258"
                                )
                            )

            # Parse XML to dict
            data = xmltodict.parse(xml_content)

            # Parse according to common format
            parsed_data = {}
            for key in cls.COMMON_KEYS:
                parsed_data[key] = cls.find_key_dynamic(data, key)

            return parsed_data

        except Exception as e:
            if isinstance(e, UserError):
                raise
            raise UserError(_("Failed to parse XML file: %s") % str(e))

    @classmethod
    def compute_raw_file_checksum(cls, xml_content):
        """
        Compute SHA256 checksum of raw XML file content.

        Args:
            xml_content (str or bytes): XML content

        Returns:
            str: SHA256 hex digest
        """
        if isinstance(xml_content, str):
            xml_content = xml_content.encode("utf-8")
        return hashlib.sha256(xml_content).hexdigest()

    @classmethod
    def compute_business_checksum(
        cls,
        invoice_series,
        invoice_number,
        invoice_date,
    ):
        """
        Compute business-level checksum to prevent duplicate invoices.

        Args:
            invoice_series (str): Invoice series
            invoice_number (str): Invoice number
            invoice_date (str): Invoice date

        Returns:
            str: SHA256 hex digest
        """
        key = f"{invoice_series}|{invoice_number}|{invoice_date}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
