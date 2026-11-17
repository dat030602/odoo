# Attachment Excel Editor (Odoo 19)

Click on any `.xlsx` / `.xlsm` file attached to a `many2many_binary` widget to open and edit it directly within Odoo using the built-in `o-spreadsheet` engine: formulas, cell styles, multiple sheets, merged cells, images, charts, undo/redo, and more.

> [!NOTE]
> VBA macros are not supported: macros are automatically removed upon saving, and `.xlsm` files are safely converted and saved as `.xlsx`.

---

## Features

- **Direct In-Browser Editing**: Open spreadsheets immediately from attachment preview widgets without manual download/re-upload.
- **Multiple Display Modes**: High-usability overlay popup or full-page client action (`dn_attachment_excel_editor`).
- **Flexible Save Options**:
  - **Overwrite original file**: Update the current attachment directly.
  - **Create a new version**: Keep the original intact and auto-increment versions (e.g. `report (v2).xlsx`, `report (v3).xlsx`), automatically linking the new attachment to the host record.
  - **User Preferences**: Configure default save behavior in **My Preferences** (Ask every time, Always overwrite, Always create new version).
- **Concurrency Protection**: Detects conflicting updates via `write_date` before saving.
- **Security & Integrity**:
  - Macro stripping for `.xlsm` files.
  - Server-side decompression with zip-bomb safeguards (max expansion factor check) and path traversal prevention.
  - Configurable max file size via `ir.config_parameter` (`dn_attachment_excel_editor.max_file_mb`).
  - Full respect of attachment read/write ACLs.

---

## Usage

1. Open any form with attachments (e.g. Contacts with the demo field).
2. Attach an Excel file (`.xlsx` or `.xlsm`).
3. Click on the attachment badge to launch the spreadsheet editor.
4. Make your edits and press `Ctrl+S` or click **Save**.
5. Choose whether to overwrite or create a new version (with the option to remember your choice).

---

## Configuration

- System Parameter `dn_attachment_excel_editor.max_file_mb` (default: `20`): Maximum allowed file size in megabytes.
