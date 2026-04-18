# backend/services/export_service.py
import json, csv, io
import openpyxl
from openpyxl.styles import Font, PatternFill

def to_json(doc, extraction_result):
    fields = json.loads(extraction_result.extracted_fields or '{}')
    return {
        'document_id': doc.id,
        'filename': doc.original_filename,
        'doc_type': doc.doc_type,
        'fields': fields
    }

def to_csv_string(doc, extraction_result):
    fields = json.loads(extraction_result.extracted_fields or '{}')
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['field', 'value', 'confidence'])
    for key, data in fields.items():
        if isinstance(data, dict) and not isinstance(data.get('value'), list):
            writer.writerow([key, data.get('value', ''), data.get('confidence', '')])
    return output.getvalue()

def to_excel_bytes(doc, extraction_result):
    fields = json.loads(extraction_result.extracted_fields or '{}')
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = doc.doc_type or 'Extraction'

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', fgColor='2563EB')

    # Header
    ws.append(['Field', 'Value', 'Confidence'])
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill

    # Rows
    for key, data in fields.items():
        if isinstance(data, dict):
            val = data.get('value', '')
            if isinstance(val, list):
                val = json.dumps(val)
            ws.append([key, str(val) if val else '', data.get('confidence', '')])

    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['C'].width = 12

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def bulk_to_csv(documents_with_results):
    """One row per document, key fields as columns."""
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'filename', 'doc_type', 'status', 'uploaded_at', 'extracted_fields_json'])
    for item in documents_with_results:
        writer.writerow([
            item.get('id'), item.get('original_filename'),
            item.get('doc_type'), item.get('status'),
            item.get('uploaded_at'),
            str(item.get('extracted_fields', {}))
        ])
    return output.getvalue()    