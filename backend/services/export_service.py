# backend/services/export_service.py
import json, csv, io
import openpyxl
from openpyxl.styles import Font, PatternFill

def _parse_extracted_payload(extraction_result):
    payload = json.loads(extraction_result.extracted_fields or '{}')
    payload = payload if isinstance(payload, dict) else {}
    if 'document' in payload:
        document_fields = payload.get('document') or {}
        page_results = payload.get('pages') or []
    else:
        document_fields = payload
        page_results = []
    if not isinstance(document_fields, dict):
        document_fields = {}
    if not isinstance(page_results, list):
        page_results = []
    return document_fields, page_results


def _split_field_entries(fields):
    scalar_entries = []
    table_entries = []
    for key, data in (fields or {}).items():
        if isinstance(data, dict):
            value = data.get('value')
            if isinstance(value, list):
                table_entries.append((key, value))
            else:
                scalar_entries.append((key, data))
        else:
            scalar_entries.append((key, {'value': data}))
    return scalar_entries, table_entries


def _write_csv_field_sections(writer, title, fields):
    scalar_entries, table_entries = _split_field_entries(fields)
    writer.writerow([title])
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

    for key, rows in table_entries:
        writer.writerow([])
        writer.writerow([f"{key.replace('_', ' ').title()} Table"])
        if not rows:
            writer.writerow(['No rows'])
            continue
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
            writer.writerow(['' if row.get(h) is None else row.get(h) for h in headers])


def _write_excel_field_sections(ws, title, fields, section_font, header_font, header_fill):
    scalar_entries, table_entries = _split_field_entries(fields)
    ws.append([title])
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
            ws.append(['' if row.get(h) is None else row.get(h) for h in headers])


def to_json(doc, extraction_result):
    fields, page_results = _parse_extracted_payload(extraction_result)
    return {
        'document_id': doc.id,
        'filename': doc.original_filename,
        'doc_type': doc.doc_type,
        'fields': fields,
        'pages': page_results
    }

def to_csv_string(doc, extraction_result):
    fields, page_results = _parse_extracted_payload(extraction_result)
    output = io.StringIO()
    writer = csv.writer(output)

    # Document metadata section
    writer.writerow(['document_id', doc.id])
    writer.writerow(['filename', doc.original_filename])
    writer.writerow(['doc_type', doc.doc_type or ''])
    writer.writerow([])

    _write_csv_field_sections(writer, 'Document-level Structured Fields', fields)

    if page_results:
        for page in sorted(page_results, key=lambda p: p.get('page_index', 0)):
            writer.writerow([])
            writer.writerow([f"Page {page.get('page_index', 0) + 1}"])
            page_fields = page.get('extracted_fields') or {}
            _write_csv_field_sections(writer, f"Page {page.get('page_index', 0) + 1} Structured Fields", page_fields)

            page_text = page.get('ocr_text')
            if page_text:
                writer.writerow([])
                writer.writerow([f"Page {page.get('page_index', 0) + 1} OCR Text"])
                writer.writerow([page_text])

    return output.getvalue()

def to_excel_bytes(doc, extraction_result):
    fields, page_results = _parse_extracted_payload(extraction_result)
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

    _write_excel_field_sections(
        ws,
        'Document-level Structured Fields',
        fields,
        section_font,
        header_font,
        header_fill
    )

    if page_results:
        for page in sorted(page_results, key=lambda p: p.get('page_index', 0)):
            ws.append([])
            ws.append([f"Page {page.get('page_index', 0) + 1}"])
            ws.cell(row=ws.max_row, column=1).font = section_font
            _write_excel_field_sections(
                ws,
                f"Page {page.get('page_index', 0) + 1} Structured Fields",
                page.get('extracted_fields') or {},
                section_font,
                header_font,
                header_fill
            )
            page_text = page.get('ocr_text')
            if page_text:
                ws.append([])
                ws.append([f"Page {page.get('page_index', 0) + 1} OCR Text"])
                ws.cell(row=ws.max_row, column=1).font = section_font
                ws.append([page_text])

    # Readability widths
    ws.column_dimensions['A'].width = 32
    ws.column_dimensions['B'].width = 52
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