# backend/services/export_service.py
import json, csv, io
import openpyxl
from openpyxl.styles import Font, PatternFill

def to_json(doc, extraction_result):
    payload = json.loads(extraction_result.extracted_fields or '{}')
    fields = payload.get('document', payload) if isinstance(payload, dict) else {}
    return {
        'document_id': doc.id,
        'filename': doc.original_filename,
        'doc_type': doc.doc_type,
        'fields': fields
    }

def to_csv_string(doc, extraction_result):
    payload = json.loads(extraction_result.extracted_fields or '{}')
    payload = payload if isinstance(payload, dict) else {}
    fields = payload.get('document', payload) if isinstance(payload, dict) else {}
    fields = fields if isinstance(fields, dict) else {}
    output = io.StringIO()
    writer = csv.writer(output)

    # Document metadata section
    writer.writerow(['document_id', doc.id])
    writer.writerow(['filename', doc.original_filename])
    writer.writerow(['doc_type', doc.doc_type or ''])
    writer.writerow([])

    # Split fields similarly to UI:
    # - scalar fields: value is not a list
    # - table fields: value is a list of row objects
    scalar_entries = []
    table_entries = []
    for key, data in fields.items():
        if isinstance(data, dict):
            value = data.get('value')
            if isinstance(value, list):
                table_entries.append((key, value))
            else:
                scalar_entries.append((key, data))
        else:
            scalar_entries.append((key, {'value': data}))

    # Scalar fields section (human-readable key/value table)
    writer.writerow(['Structured Fields'])
    writer.writerow(['field', 'value', 'confidence', 'manually_corrected'])
    for key, data in scalar_entries:
        value = data.get('value', '')
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        writer.writerow([
            key.replace('_', ' '),
            '' if value is None else value,
            data.get('confidence', ''),
            data.get('manually_corrected', '')
        ])

    # Table fields sections (one table per list field)
    for key, rows in table_entries:
        writer.writerow([])
        writer.writerow([f"{key.replace('_', ' ').title()} Table"])
        if not rows:
            writer.writerow(['No rows'])
            continue

        # Preserve first-row key order, then append any extra keys seen later.
        headers = list(rows[0].keys()) if isinstance(rows[0], dict) else []
        for row in rows[1:]:
            if isinstance(row, dict):
                for col in row.keys():
                    if col not in headers:
                        headers.append(col)

        if not headers:
            writer.writerow(['value'])
            for row in rows:
                writer.writerow([json.dumps(row, ensure_ascii=False)])
            continue

        writer.writerow(headers)
        for row in rows:
            if not isinstance(row, dict):
                writer.writerow([json.dumps(row, ensure_ascii=False)] + [''] * (len(headers) - 1))
                continue
            writer.writerow([
                '' if row.get(h) is None else row.get(h)
                for h in headers
            ])

    return output.getvalue()

def to_excel_bytes(doc, extraction_result):
    payload = json.loads(extraction_result.extracted_fields or '{}')
    payload = payload if isinstance(payload, dict) else {}
    fields = payload.get('document', payload) if isinstance(payload, dict) else {}
    fields = fields if isinstance(fields, dict) else {}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = doc.doc_type or 'Extraction'

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', fgColor='2563EB')
    section_font = Font(bold=True)

    # Document metadata section
    ws.append(['document_id', doc.id])
    ws.append(['filename', doc.original_filename])
    ws.append(['doc_type', doc.doc_type or ''])
    ws.append([])

    # Split fields similarly to UI
    scalar_entries = []
    table_entries = []
    for key, data in fields.items():
        if isinstance(data, dict):
            value = data.get('value')
            if isinstance(value, list):
                table_entries.append((key, value))
            else:
                scalar_entries.append((key, data))
        else:
            scalar_entries.append((key, {'value': data}))

    # Scalar fields section
    ws.append(['Structured Fields'])
    ws.cell(row=ws.max_row, column=1).font = section_font

    ws.append(['field', 'value', 'confidence', 'manually_corrected'])
    for cell in ws[ws.max_row]:
        cell.font = header_font
        cell.fill = header_fill

    for key, data in scalar_entries:
        value = data.get('value', '')
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        ws.append([
            key.replace('_', ' '),
            '' if value is None else value,
            data.get('confidence', ''),
            data.get('manually_corrected', '')
        ])

    # Table fields sections
    for key, rows in table_entries:
        ws.append([])
        ws.append([f"{key.replace('_', ' ').title()} Table"])
        ws.cell(row=ws.max_row, column=1).font = section_font

        if not rows:
            ws.append(['No rows'])
            continue

        headers = list(rows[0].keys()) if isinstance(rows[0], dict) else []
        for row in rows[1:]:
            if isinstance(row, dict):
                for col in row.keys():
                    if col not in headers:
                        headers.append(col)

        if not headers:
            ws.append(['value'])
            for row in rows:
                ws.append([json.dumps(row, ensure_ascii=False)])
            continue

        ws.append(headers)
        for cell in ws[ws.max_row]:
            cell.font = header_font
            cell.fill = header_fill

        for row in rows:
            if not isinstance(row, dict):
                ws.append([json.dumps(row, ensure_ascii=False)] + [''] * (len(headers) - 1))
                continue
            ws.append([
                '' if row.get(h) is None else row.get(h)
                for h in headers
            ])

    # Readability widths
    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 48
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 20

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