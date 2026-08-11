# Excel Template Engine — Design Spec

> **Mục tiêu:** Loại bỏ hoàn toàn `_write_table_data()`, `_get_header_footer_data()` viết tay.
> Child module chỉ cần trả về **1 JSON** (dict lồng nhau, hỗ trợ list/object tuỳ ý).
> Template `.xlsx` tự khai báo vòng lặp, điều kiện, tổng, ảnh bằng cú pháp nhúng — không cần marker `<TABLE_START>`, không cần `insert_rows` thủ công trong code Python child.
> Lấy cảm hứng cú pháp từ `report_py3o` (Genshi trên ODF) nhưng chạy **native trên openpyxl**, không phụ thuộc LibreOffice.

---

## 1. Cú pháp template

### 1.1 Placeholder giá trị — `{{ path }}`

```
{{ company.name }}
{{ line.date }}
{{ line.partner.city }}
```

- Dot-path resolve bằng `getattr` (object/recordset) hoặc `dict.get` (dict) — tự động thử cả hai theo thứ tự: `dict-like` trước, `attr` sau.
- Cho phép filter nối bằng `|`: `{{ line.amount | fmt:'#,##0.00' }}`, `{{ line.date | fmt:'DD/MM/YYYY' }}`.
- Nếu giá trị resolve ra bắt đầu bằng `=` → gán làm formula Excel sống (giữ hành vi cũ).

### 1.2 Block lặp — `{% for x in path %}` ... `{% endfor %}`

Đặt trong **cột đầu tiên của dòng mở block** và **cột đầu tiên của dòng đóng block**:

```
Row 4  A4: {% for line in lines %}
Row 5  A5: {{ line.name }}   B5: {{ line.date }}   C5: {{ line.amount }}
Row 6  A6: {% endfor %}
```

- Vùng lặp = các dòng **giữa** dòng mở và dòng đóng (không bao gồm 2 dòng marker — 2 dòng này bị xoá sau khi expand).
- Hỗ trợ **nhiều dòng / 1 item** (record chiếm 2-3 dòng vẫn được, engine nhân bản cả cụm).
- Hỗ trợ **nested for** (group/subtotal tự nhiên, không cần flatten JSON thủ công):

```
A4: {% for g in groups %}
A5:   {% for l in g.lines %}
B5:      {{ l.name }}   C5: {{ l.amount }}
A6:   {% endfor %}
A7:   Subtotal {{ g.name }}   C7: {{ g.lines | sum:'amount' }}
A8: {% endfor %}
```

### 1.3 Điều kiện — `{% if cond %}` ... `{% endif %}`

```
A9: {% if line.amount > 1000000 %}
B9: {{ line.name }}  (VIP)
A10: {% endif %}
```

- Cùng cơ chế marker-row như `for`. Điều kiện eval bằng `eval()` trên context an toàn (whitelist toán tử so sánh, không cho gọi hàm tuỳ ý — xem mục 4.4 Bảo mật).

### 1.4 Filter `sum` — tổng cột không double-count

```
{{ lines | sum:'amount' }}
```

- Chỉ hợp lệ khi đặt **ngoài** block `for` tương ứng, tham chiếu đúng list vừa lặp.
- Engine tự biết `start_row`/`end_row` thực tế của block đó **sau khi expand** (runtime), tự sinh:

```
=SUBTOTAL(9, C{start_row}:C{end_row})
```

- Nested `for` → nested `SUBTOTAL` tự động bỏ qua subtotal con (đúng cơ chế Excel `SUBTOTAL`, giữ nguyên từ framework cũ mục 9.2).
- Filter khác cùng họ: `count`, `avg`, `max`, `min` → map sang code `SUBTOTAL(2/1/4/5, ...)`.

### 1.5 Ảnh embed — filter `image`

```
{{ line.photo_base64 | image }}
{{ company.logo_url | image:width=120,height=60 }}
```

- Engine phát hiện filter `image` → **không gán `.value`**, thay vào đó:
  1. Decode base64 hoặc tải URL → `PIL.Image` / `openpyxl.drawing.image.Image`.
  2. Resize theo `width/height` nếu chỉ định (đơn vị px), mặc định fit theo kích thước ô.
  3. `ws.add_image(img, anchor=cell_coordinate)`.
- Trong block `for`, mỗi item lặp có ảnh riêng theo đúng dòng nhân bản.
- Dòng chứa ảnh nên **không merge cell** trừ khi đã test kỹ (xem mục 4.2).

---

## 2. Kiến trúc xử lý (thay Section 6 của tài liệu cũ)

```
action_generate_excel()
  │
  ├─ 1. _load_template()                (giữ nguyên — decode attachment)
  ├─ 2. _get_report_context() [HOOK]     ← child chỉ override HÀM NÀY
  │        return { 'company': {...}, 'groups': [...], 'lines': [...] }
  ├─ 3. TemplateEngine.render(sheet, context)
  │        3a. parse_blocks(sheet)        → tìm mọi cặp for/if, kể cả nested
  │        3b. expand(sheet, blocks, context)  (đệ quy, sâu nhất trước)
  │        3c. resolve_placeholders(sheet, context)  → {{ }} còn lại (ngoài block)
  │        3d. resolve_sum_filters()      → cần chạy SAU 3b vì cần start/end row thật
  │        3e. embed_images()
  ├─ 4. _autofit_columns()               (giữ nguyên, optional theo Fast Mode)
  └─ 5. _export_file()                   (giữ nguyên)
```

**Child module chỉ còn 1 hook bắt buộc:**

```python
def _get_report_context(self):
    orders = self.env['sale.order'].search([...], order='partner_id, date_order')
    groups = {}
    for o in orders:
        groups.setdefault(o.partner_id, []).append(o)

    return {
        'company': {'name': self.env.company.name},
        'print_date': fields.Date.today().strftime('%d/%m/%Y'),
        'groups': [
            {
                'name': partner.name,
                'lines': [
                    {'name': o.name, 'date': o.date_order.date(), 'amount': o.amount_total}
                    for o in orders
                ],
            }
            for partner, orders in groups.items()
        ],
    }
```

So với hook cũ (`_get_report_data` + `_write_table_data` + `_get_header_footer_data` ≈ 30-50 dòng), hook mới chỉ là 1 hàm build dict — **không đụng openpyxl, không biết row/column là gì**.

---

## 3. Thuật toán `parse_blocks` — điểm kỹ thuật quan trọng nhất

1. Quét toàn sheet theo thứ tự **hàng tăng dần**, cột A (hoặc cột đầu tiên có nội dung) tìm regex `^\{%\s*(for|if)\s+.*%\}$` và `^\{%\s*end(for|if)\s*%\}$`.
2. Dùng **stack** để khớp cặp mở/đóng — cho phép nested tuỳ ý độ sâu:
   ```
   push khi gặp {% for/if %}
   pop khi gặp {% endfor/endif %} → tạo Block(start_row, end_row, kind, expr)
   ```
3. Sort các block theo **độ sâu giảm dần** (block trong cùng expand trước) — bắt buộc, vì expand block ngoài trước sẽ làm lệch row index của block trong.
4. Với mỗi block:
   - `for x in path`: resolve `path` từ context hiện tại (context được truyền theo ngữ cảnh cha khi đệ quy vào nested block) → list.
   - Với mỗi item: copy toàn bộ vùng `(start_row+1 .. end_row-1)` bằng `copy.copy()` style + value pattern (dùng lại `_copy_row_styles()` logic cũ), chèn xuống dưới bằng `insert_rows` tại đúng vị trí, rồi resolve `{{ }}` trong vùng đó với context = item.
   - Sau khi expand xong toàn bộ item, **xoá 2 dòng marker** (`{% for %}` và `{% endfor %}`).
   - Ghi lại `(actual_start_row, actual_end_row)` của block này vào 1 registry — để bước `resolve_sum_filters` dùng.
5. `if`: eval điều kiện, nếu False thì **xoá nguyên vùng** (`delete_rows`), nếu True thì chỉ xoá 2 dòng marker.

**Độ phức tạp:** O(số cell) cho parse, O(tổng số dòng sau expand) cho ghi — tương đương chi phí `insert_rows` cũ, không phát sinh thêm bậc phức tạp.

---

## 4. Rủi ro kỹ thuật cần xử lý (khác với bản `<TABLE_START>` cũ)

### 4.1 Merged cells trong vùng lặp
`insert_rows()` của openpyxl **không tự dịch chuyển merged cell ranges** một cách an toàn khi vùng đó nằm giữa sheet có merge phức tạp. Cần:
- Trước khi insert: lưu danh sách `MergedCellRange` giao với vùng bị đẩy.
- Sau khi insert: `ws.unmerge_cells()` cũ rồi `ws.merge_cells()` lại theo offset mới.
- Test riêng: block `for` có 1 ô merge ngang (ví dụ tên sản phẩm dài merge B:C) trên dòng lặp.

### 4.2 Ảnh (Image anchor) khi insert/delete rows
openpyxl **không tự dịch chuyển anchor của ảnh đã có sẵn** trong template khi `insert_rows`/`delete_rows` chạy. Ảnh tĩnh (logo công ty) nên đặt **ngoài mọi block for/if**. Ảnh động (`{{ x | image }}`) do engine tự add sau khi đã biết vị trí cuối cùng nên không bị ảnh hưởng — nhưng nếu logo nằm phía dưới 1 block `for` có nhiều dòng, logo sẽ **không tự trôi xuống theo** trừ khi engine cũng track và re-anchor nó. → khuyến nghị layout: mọi ảnh tĩnh đặt phía trên block đầu tiên hoặc dùng "Footer-above-data" pattern (giữ nguyên tip Fast Mode ở tài liệu cũ, mục 8.2).

### 4.3 Formula tham chiếu ra ngoài block
Nếu 1 formula trong template trỏ đến cell nằm ngoài vùng lặp (ví dụ tham chiếu 1 hằng số ở A1), sau `insert_rows` openpyxl **có tự dịch reference** cho formula nội bộ sheet trong nhiều trường hợp, nhưng **không đảm bảo 100%** với formula 3D hoặc tham chiếu sang sheet khác. Cần test riêng, không giả định an toàn tuyệt đối như tài liệu cũ ngụ ý.

### 4.4 Bảo mật khi eval điều kiện `{% if %}`
Không dùng `eval()` trần trên chuỗi lấy từ file `.xlsx` do người dùng khác upload — dùng thư viện expression an toàn (`simpleeval`, hoặc tự viết parser whitelist chỉ cho phép so sánh `== != > < >= <=`, `and/or/not`, truy cập attribute theo whitelist path đã biết trong context). Không expose `__import__`, không cho gọi hàm Python tuỳ ý.

### 4.5 Performance / Fast Mode
Logic Fast Mode (bỏ `_copy_row_styles`, bỏ `_autofit_columns` khi ≥ `FAST_MODE_THRESHOLD`) vẫn áp dụng được, nhưng cần đo lại ngưỡng vì engine mới làm **nhiều việc hơn mỗi row** (parse path, resolve filter) so với vòng `for idx, rec in enumerate(data)` thuần cũ — nên benchmark lại threshold mặc định 1000, có thể cần hạ xuống hoặc tối ưu bằng cách compile path 1 lần (parse `{{ }}` thành list token, không regex lại mỗi row).

---

## 5. So sánh nhanh với `report_py3o`

| | `report_py3o` (OCA) | Engine đề xuất |
|---|---|---|
| File nguồn | `.odt`/`.ods` | `.xlsx` trực tiếp |
| Runtime phụ thuộc | LibreOffice headless (subprocess) | chỉ `openpyxl` (+ `simpleeval` cho `if`) |
| Cú pháp | Genshi (`for=`, `${}`) — chuẩn, đã test nhiều năm | tự định nghĩa, cần viết test suite riêng |
| Merge cell / ảnh khi convert | LO tự lo lúc convert ODF→xlsx | phải tự xử lý thủ công (mục 4.1, 4.2) |
| Tốc độ | chậm hơn (spawn subprocess LO) | nhanh hơn, thuần Python |
| Độ trưởng thành | production-ready, nhiều năm dùng ở OCA | phải tự kiểm thử từ đầu |

**Khuyến nghị triển khai:** làm engine theo 3 giai đoạn để giảm rủi ro:
1. **Giai đoạn 1:** chỉ hỗ trợ `for` phẳng (không nested) + `{{ }}` + `sum` filter — thay thế được 80% report hiện có, rủi ro merge/ảnh thấp nhất.
2. **Giai đoạn 2:** thêm `if` + nested `for` (group/subtotal).
3. **Giai đoạn 3:** thêm `image` filter + xử lý merge cell tự động.

Việc chia giai đoạn giúp bạn có bản dùng được sớm, đồng thời cô lập rủi ro (mục 4) vào từng giai đoạn cụ thể thay vì phải giải hết trước khi ra bản đầu tiên.