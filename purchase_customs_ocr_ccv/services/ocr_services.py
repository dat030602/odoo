from odoo import models, api, _
from odoo.exceptions import UserError
import google.generativeai as genai
from google.generativeai.types import content_types
import fitz  # PyMuPDF
import base64
import csv
import json
import logging
import os
import re
from io import BytesIO, StringIO
import pandas as pd

_logger = logging.getLogger(__name__)

class OCRService(models.TransientModel):
    _name = 'ocr.service'
    _description = 'OCR Service for EDO, B/L and Custom Declaration Processing'

    def _get_gemini_api_key(self):
        """Get Gemini API key from system parameters"""
        api_key = self.env['ir.config_parameter'].sudo().get_param('purchase_customs_ocr_ccv.gemini_api_key')
        if not api_key:
            raise UserError("Gemini API key not configured. Please contact administrator.")
        
        return api_key

    def _configure_gemini(self):
        """Configure Gemini AI with API key"""
        api_key = self._get_gemini_api_key()
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-flash-latest')

    def process_file_with_gemini(self, file_b64_list):
        """Main OCR processing method with comprehensive error handling
        
        Args:
            file_b64_list: List of dictionaries with 'content' (base64) and 'name' (filename)
            
        Returns:
            dict: Combined extracted data from all files
        """
        if not file_b64_list:
            return {}
            
        try:
            # Classify files
            pdf_files, excel_files = self._classify_files(file_b64_list)
            
            # Always use combined processing for all file types
            return self._process_combined_files(pdf_files, excel_files)
            
        except Exception as e:
            _logger.error("Error in process_file_with_gemini: %s", str(e), exc_info=True)
            return {"error": "An error occurred while processing the files"}

    def _classify_files(self, file_b64_list):
        """Classify files into PDF and Excel categories"""
        pdf_files = []
        excel_files = []
        
        for content in file_b64_list:
            try:
                file_type = self._detect_file_type(content)
                if file_type == 'pdf':
                    pdf_files.append(content)
                elif file_type in ('xlsx', 'xls'):
                    excel_files.append(content)
                else:
                    pdf_files.append(content)
            except Exception:
                pdf_files.append(content)
        
        return pdf_files, excel_files

    def _detect_file_type(self, content):
        """Detect file type from base64 content or dict with 'content' key
        
        Args:
            content: Either a base64 string or a dict with 'content' key containing base64 string
            
        Returns:
            str: 'pdf', 'xlsx', 'xls', or 'unknown'
        """
        try:
            # Handle case where content is a dict with 'content' key
            if isinstance(content, dict) and 'content' in content:
                content = content['content']
                
            # Ensure content is a string before slicing
            if not isinstance(content, (str, bytes)):
                _logger.warning("Invalid content type for file detection: %s", type(content))
                return 'unknown'
                
            # Decode first 1024 bytes to check file signature (needed for XLSX detection)
            content_str = content.decode('utf-8') if isinstance(content, bytes) else content
            header_bytes = base64.b64decode(content_str[:1024]) if content_str else b''
            
            # Check for PDF (PDF files start with %PDF)
            if header_bytes.startswith(b'%PDF'):
                return 'pdf'
                
            # Check for XLSX (Office Open XML - ZIP-based format)
            if header_bytes.startswith(b'PK\x03\x04'):
                # Look for XLSX-specific markers in the ZIP structure
                xlsx_markers = [
                    b'[Content_Types].xml',
                    b'_rels/.rels',
                    b'xl/workbook.xml',
                    b'xl/worksheets/',
                    b'xl/sharedStrings.xml'
                ]
                # Check for any XLSX marker in the first 1024 bytes
                if any(marker in header_bytes for marker in xlsx_markers):
                    return 'xlsx'
                # If no specific markers found but has ZIP header, check for Excel MIME type
                if b'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in header_bytes:
                    return 'xlsx'
            
            # Check for XLS (BIFF format)
            if len(header_bytes) >= 8:  # Make sure we have enough bytes for the signature
                # Check for Compound File Binary Format (most modern XLS files)
                if header_bytes.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'):
                    return 'xls'
                # Check for older Excel 95/97-2003 format
                if len(header_bytes) >= 8 and header_bytes.startswith(b'\x09\x08\x10\x00\x00\x06\x05\x00'):
                    return 'xls'
                
            return 'unknown'
                
        except Exception as e:
            _logger.warning("Error detecting file type: %s", e)
            return 'unknown'

    def _process_combined_files(self, pdf_files, excel_files):
        """Process both PDF and Excel files together in a single request
        
        Args:
            pdf_files: List of PDF file info dicts with 'content' and 'name'
            excel_files: List of Excel file info dicts with 'content' and 'name'
            
        Returns:
            dict: Combined extracted data
        """
        if not pdf_files and not excel_files:
            return {}
            
        model = self._configure_gemini()
        documents = []
        
        # Process PDF files
        for idx, file_info in enumerate(pdf_files, 1):
            try:
                binary_data = base64.b64decode(file_info.get('content', b''))
                documents.append({
                    'mime_type': 'application/pdf',
                    'data': binary_data,
                    'file_index': idx,
                    'file_name': file_info.get('name', 'Document_{0}.pdf'.format(idx))
                })
            except Exception:
                continue
        
        # Process Excel files (convert to text)
        for idx, file_info in enumerate(excel_files, len(pdf_files) + 1):
            try:
                excel_data = base64.b64decode(file_info.get('content', b''))
                text_content = self._excel_to_text(excel_data, file_info.get('name', ''))
                
                max_size = 2 * 1024 * 1024
                if len(text_content) > max_size:
                    text_content = text_content[:max_size] + "\n[...truncated due to size...]"
                
                file_name = file_info.get('name', 'Document_{0}'.format(idx))
                base_name = os.path.splitext(file_name)[0]
                
                documents.append({
                    'mime_type': 'text/plain',
                    'data': text_content.encode('utf-8'),
                    'file_index': idx,
                    'file_name': '{0}.txt'.format(base_name)
                })
            except Exception:
                continue
        
        if not documents:
            return {}
        
        prompt = self._build_combined_prompt(documents)

        request_content = [prompt]
        
        for doc in documents:
            request_content.append({
                'mime_type': doc['mime_type'],
                'data': doc['data']
            })
        
        response = model.generate_content(request_content)
        
        _logger.info("=== RESPONSE ===")
        _logger.info(response.text)
        _logger.info("=== END RESPONSE ===")
        
        if not response or not response.text:
            return {}
            
        return self._parse_combined_response(response.text)

    def _build_combined_prompt(self, documents):
        """
        Build a highly optimized Gemini OCR prompt for extracting structured shipping and container data
        from Vietnamese EDOs, Bills of Lading, and Customs documents.

        Args:
            documents (list): List of document info dicts, each containing at least `file_name` and `mime_type`.

        Returns:
            str: Well-formatted prompt string tailored for maximum OCR accuracy.
        """

        file_list = ", ".join([doc['file_name'] for doc in documents])

        return f"""
            ROLE:
            You are a specialized OCR and information extraction expert, trained to interpret Vietnamese shipping documents including:
            - Electronic Delivery Orders (EDO)
            - Bills of Lading (B/L)
            - Customs declarations

            OBJECTIVE:
            Extract accurate shipping and container-level data from the provided documents. The layout may vary across different carriers or templates, including multi-page formats and embedded tables.

            DOCUMENTS TO PROCESS: {file_list}

            INSTRUCTIONS – SHIPPING INFO:
            Extract the following high-level fields:
            - "carrier_name": Name of the shipping line (e.g., "Maersk", "Yang Ming", "SITC")
            - "bl_number": Bill of Lading number or No. Bill or "Số Bill" (e.g., "SITGJNSGHB0038", "BL123456789")
            - "vessel_name": Full name of the vessel (e.g., "OOCL NEW YORK", "HONG AN")
            - "voyage_number": Voyage or trip number (e.g., "2511S", "VN1234")
            - "arrival_date_estimated": Estimated time of arrival, in YYYY-MM-DD format
            - "custom_declaration_number": Extract if available (format: numeric)
            - "custom_declaration_date": Date of customs declaration registration. Look for the label "Ngày đăng ký" in the customs declaration. Input may include time (e.g. "18/10/2025 10:23:42"); convert the date to ISO format YYYY-MM-DD and drop the time portion. If multiple registration dates appear, choose the primary "Ngày đăng ký" of the declaration.

            INSTRUCTIONS – CONTAINER DETAILS:   
            Return a list of all containers and their associated seals. Use the following rules:

            1. container_number and seal_number:
                - Format usually be 3 or 4 uppercase letters + 6 or 7 digits (e.g., "TGCU0086030", "SITF512841")
                - Remove hyphens or spaces (e.g., "TGHU-1234567" → "TGHU1234567")

            2. Common formats to look for:
                - Combined: "TGCU0086030/SITF512841"
                - Split table format: separate container and seal columns
                - Spaced: "TGCU0086030 / SITF512841"

            3. Container and Seal Number Awareness:
                - If tabular, match container numbers with their respective seal numbers
                - Cross-check attachments or footnotes for full container lists
                - Container number and seal number always come in pairs, never leave any container number without a seal number

            RESPONSE FORMAT (JSON):
            ```json
            {{
              "carrier_name": "string",
              "bl_number": "string",
              "vessel_name": "string",
              "voyage_number": "string",
              "arrival_date_estimated": "YYYY-MM-DD",
              "custom_declaration_number": "string",
              "custom_declaration_date": "YYYY-MM-DD",
              "containers": [
                {{
                    "container_number": "string",
                    "seal_number": "string"
                }}
              ]
            }}
            """


    def _excel_to_text(self, excel_data, filename):
        """Convert Excel file data to a structured text representation.
        
        Args:
            excel_data (bytes): Binary Excel file data
            filename (str): Original filename (for error messages)
            
        Returns:
            str: Text representation of the Excel file
        """
        try:
            # Try reading as XLSX first, then XLS
            try:
                df = pd.read_excel(BytesIO(excel_data), engine='openpyxl')
            except Exception:
                df = pd.read_excel(BytesIO(excel_data), engine='xlrd')
            
            # Convert to CSV-like text representation
            output = StringIO()
            df.to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
            text_content = f"Excel File: {filename}\n\n"
            text_content += output.getvalue()
            return text_content
            
        except Exception as e:
            _logger.error(f"Error converting Excel file {filename} to text: {str(e)}")
            # Fallback: return basic file info if conversion fails
            return f"[Excel File: {filename} - Could not convert to text: {str(e)}]"

    def _parse_combined_response(self, response_text):
        """Parse the combined response from Gemini AI into a structured format
        
        Args:
            response_text (str): Raw text response from Gemini AI
            
        Returns:
            dict: Parsed data in the format expected by the purchase order
        """
        try:
            # Clean the response text to handle any markdown code blocks
            clean_text = response_text.strip()
            if '```json' in clean_text:
                clean_text = clean_text.split('```json', 1)[1].split('```', 1)[0].strip()
            elif '```' in clean_text:
                clean_text = clean_text.split('```', 1)[1].rsplit('```', 1)[0].strip()
            
            # Parse the JSON response
            data = json.loads(clean_text)
            
            # Initialize the result structure
            result = {
                'carrier_name': (data.get('carrier_name') or "").strip(),
                'bl_number': (data.get('bl_number') or "").strip().upper(),
                'vessel_name': (data.get('vessel_name') or "").strip(),
                'voyage_number': (data.get('voyage_number') or "").strip().upper(),
                'arrival_date_estimated': (data.get('arrival_date_estimated') or "").strip(),
                'custom_declaration_number': (data.get('custom_declaration_number') or "").strip(),
                'custom_declaration_date': (data.get('custom_declaration_date') or "").strip(),
                'stock_input_ids': []
            }
            
            # Process containers
            for container in data.get('containers', []):
                container_num = container.get('container_number', '').strip().upper()
                seal_num = container.get('seal_number', '').strip().upper()
                
                # Clean container number (remove non-alphanumeric characters)
                container_num = re.sub(r'[^A-Z0-9]', '', container_num)
                
                # Skip if no container number
                if not container_num:
                    continue
                    
                result['stock_input_ids'].append({
                    'container_number': container_num,
                    'seal_number': seal_num if seal_num else ''
                })
            
            return result
            
        except json.JSONDecodeError as e:
            _logger.error("Failed to parse JSON response: %s\nResponse: %s", str(e), response_text)
            return {}
        except Exception as e:
            _logger.error("Error parsing combined response: %s", str(e), exc_info=True)
            return {}
