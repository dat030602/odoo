# SPEC: Excel Report Definition Builder
### Module kế thừa `dn_excel_report_base` — Odoo 19

**Trạng thái:** Chốt thiết kế (MVP) — sẵn sàng triển khai
**Phiên bản tài liệu:** 1.0

---

## 1. Mục tiêu

Cho phép người dùng nghiệp vụ (không cần dev) tự cấu hình một luồng:

> Nhập filter trên 1 wizard (transient model) → bấm nút → hệ thống gọi `ir.actions.server` (loại `excel_template` đã có sẵn trong `dn_excel_report_base`) → xuất file Excel theo template.

Toàn bộ Model, Field, View, Server Action, và cách trigger (Menu / Contextual Action) đều được cấu hình qua UI, không cần viết module Python riêng cho từng report.

---

## 2. Phạm vi (Scope)

### Trong phạm vi (MVP)
- Tạo `ir.model` (mặc định **transient = True**) từ UI.
- Tạo `ir.model.fields` gắn vào model đó.
- Auto-generate `ir.ui.view` (form) tối giản nếu model chưa có view nào, add field mặc định vào view.
- Liên kết tới `ir.actions.server` có sẵn (loại `excel_template`), hoặc cho phép tạo mới.
- Cho phép chỉnh **code** của server action ngay tại view `excel.report.definition` (không lưu bản sao — dùng related field).
- Chọn cách expose report: **Menu** hoặc **Contextual Action** (Action menu ⚙️ trên list/form).
- Smart button (button box) trên form `excel.report.definition` trỏ tới:
  - `ir.actions.server` liên quan
  - `ir.ui.view` đã generate

### Ngoài phạm vi (Non-goals, ghi nhận để làm sau nếu cần)
- Export cấu hình ra module Python thật (file trên disk, version-control được) — dữ liệu tạo qua tool này là **data**, không phải code, nên việc promote qua các môi trường (dev → staging → prod) cần làm thủ công hoặc qua cơ chế export riêng ở giai đoạn sau.
- Model không-transient (lưu trữ lâu dài) — không nằm trong MVP, có thể bổ sung sau bằng 1 checkbox nếu phát sinh nhu cầu.
- Tự động chèn `<button>` thật vào `<header>` của view có sẵn (VD `sale.order`) — **chủ động không làm**, vì rủi ro cao (view gốc có thể không có `<header>`/`<sheet>`, dễ gãy khi khác version). Nếu dev cần nút thật trong header, tự viết module riêng inherit view — nằm ngoài phạm vi tool.
- Loop lồng nhau, sinh nhiều field cùng lúc qua import hàng loạt — không có trong MVP.

---

## 3. Kiến trúc dữ liệu

### 3.1. Model `excel.report.definition`

| Field | Type | Ghi chú |
|---|---|---|
| `name` | Char | Tên gợi nhớ cho cấu hình |
| `target_model_id` | Many2one → `ir.model` | Model đích; nếu chưa tồn tại, cho phép nhập tên mới để tạo (technical name + display name) |
| `target_model_new` | Boolean (computed/UI helper) | Đánh dấu model vừa tạo bởi chính record này (dùng để kiểm soát quyền auto-gen view) |
| `field_ids` | One2many → `excel.report.definition.field` | Danh sách field cần tạo trên model đích |
| `server_action_id` | Many2one → `ir.actions.server` | Bắt buộc trước khi Confirm; có thể chọn action có sẵn hoặc tạo mới (domain lọc `state = 'excel_template'`) |
| `code` | Text, **related** = `server_action_id.code`, `readonly=False` | Cho phép sửa code ngay tại đây — ghi thẳng vào `ir.actions.server`, không có bước đồng bộ, không thể lệch dữ liệu |
| `trigger_type` | Selection: `menu`, `contextual` | Cách expose report ra UI |
| `menu_id` | Many2one → `ir.ui.menu`, readonly | Chỉ có giá trị khi `trigger_type = menu` sau khi Confirm |
| `generated_view_id` | Many2one → `ir.ui.view`, readonly | View form auto-generate (nếu có) |
| `state` | Selection: `draft`, `confirmed` | Khoá field cấu trúc (model/field) sau khi confirm, tránh sửa tuỳ tiện gây lệch giữa data thật và cấu hình |

> **Lưu ý:** `target_model_id` mặc định luôn tạo với `transient = True`. Không có field `is_wizard` — bỏ hẳn theo quyết định đã chốt để giảm nhánh rẽ không cần thiết.

### 3.2. Model `excel.report.definition.field`

| Field | Type | Ghi chú |
|---|---|---|
| `definition_id` | Many2one → `excel.report.definition` | |
| `field_label` | Char | Display name của field |
| `field_technical_name` | Char | Tự thêm prefix `x_` nếu user không nhập (bắt buộc theo convention field custom của Odoo) |
| `field_type` | Selection | Giới hạn tập con an toàn cho MVP: `char`, `text`, `integer`, `float`, `boolean`, `date`, `datetime`, `many2one`, `selection` |
| `relation_model_id` | Many2one → `ir.model` | Chỉ hiện/required khi `field_type = many2one` |
| `selection_value_ids` | One2many (hoặc Text nhập dạng `key:label` mỗi dòng) | Chỉ hiện khi `field_type = selection` |
| `required` | Boolean | |

---

## 4. Quy trình xử lý (`action_confirm`)

```
1. Validate:
   - Có ít nhất tên model, tên report
   - server_action_id đã được set (bắt buộc, vì đây là nơi xuất Excel)
   - trigger_type đã chọn

2. target_model_id:
   - Nếu là model mới → tạo ir.model (transient=True)
   - Nếu là model có sẵn → dùng luôn, KHÔNG tạo view mới (xem bước 4)

3. Loop field_ids → tạo ir.model.fields tương ứng
   (bỏ qua field đã tồn tại trùng technical name, cảnh báo thay vì lỗi cứng)

4. Generate view:
   - CHỈ generate khi model là model MỚI tạo ở bước 2 và chưa có view form nào
   - Sinh arch tối giản: <form><sheet><group>{tất cả field_ids vừa tạo}</group></sheet></form>
   - Lưu vào generated_view_id
   - Nếu model có sẵn (đã có view) → KHÔNG đụng vào, để nguyên,
     yêu cầu user tự thêm field vào view nếu cần

5. Trigger:
   - trigger_type = 'menu':
       Tạo ir.ui.menu, action = server_action_id (Reference field,
       ir.ui.menu chấp nhận action trỏ thẳng ir.actions.server)
       → lưu vào menu_id
   - trigger_type = 'contextual':
       Set trên server_action_id:
         binding_model_id = target_model_id
         binding_type = 'action'
         binding_view_types = 'list,form'
       (server action tự xuất hiện ở menu Action ⚙️ của model đích,
        không đụng view gốc)

6. state = 'confirmed'
   (khoá field_ids, target_model_id để tránh sửa cấu trúc gây lệch dữ liệu
    thật đã phát sinh — muốn sửa thì phải qua flow riêng, ngoài MVP)
```

---

## 5. UI/UX — Form view `excel.report.definition`

```
┌────────────────────────────────────────────────────────┐
│  [Smart Button: Server Action]   [Smart Button: View]   │  ← button box
├────────────────────────────────────────────────────────┤
│  Name: __________                                       │
│  Target Model: [__________▼]  (m2o, có thể gõ tạo mới)  │
│                                                          │
│  Tab "Fields"                                            │
│    field_ids (list editable inline)                     │
│                                                          │
│  Tab "Server Action"                                     │
│    Server Action: [__________▼]                          │
│    Code: [textarea — related, readonly=False]            │
│                                                          │
│  Tab "Trigger"                                            │
│    Trigger Type: ( ) Menu   ( ) Contextual Action         │
│                                                          │
│  [Confirm]                                                │
└────────────────────────────────────────────────────────┘
```

**Smart buttons (button box):**
- **"Server Action"** — hiện box_icon dạng con số/link, `invisible` khi `server_action_id` rỗng, bấm vào mở form `ir.actions.server` tương ứng (dùng chung màn hình chuẩn của Odoo, không cần build view riêng).
- **"View"** — tương tự, trỏ tới `generated_view_id`; `invisible` khi rỗng (tức model dùng view có sẵn, không phải view tự sinh).

**State machine đơn giản:**
- `draft`: mọi field ở trên đều sửa được.
- `confirmed`: `target_model_id` và `field_ids` readonly; `code`, `trigger_type` vẫn có thể sửa lại (vì không ảnh hưởng cấu trúc dữ liệu đã phát sinh) — có nút "Reset to Draft" nếu cần mở lại cấu trúc (cân nhắc thêm cảnh báo dữ liệu record cũ có thể mất field nếu xoá).

---

## 6. Rủi ro & giới hạn đã biết (đưa vào tài liệu để thống nhất kỳ vọng)

| # | Rủi ro | Mức độ | Ghi chú |
|---|---|---|---|
| 1 | Model/Field là **data**, không phải code | Trung bình | Không nằm trong version control; promote giữa môi trường phải làm thủ công hoặc để dành cho phase export module sau này |
| 2 | Field `binding_view_types`, cách `ir.ui.menu.action` nhận thẳng `ir.actions.server` | Thấp — cần verify 1 lần | Hành vi chuẩn của Odoo qua nhiều version, nhưng nên test tay trên instance Odoo 19 thật trước khi code cứng, vì có thể có khác biệt nhỏ giữa các minor version |
| 3 | Transient record tự bị xoá theo `_transient_max_hours` | Thấp | Đúng theo thiết kế — model chỉ dùng làm form nhập filter tạm thời, không phải nơi lưu trữ |
| 4 | Không tự thêm field mới vào view đã tồn tại (model có sẵn hoặc từ lần 2 trở đi) | Chấp nhận được | Tránh phá layout người dùng đã tự chỉnh; đánh đổi là user phải tự thêm field vào view thủ công trong các trường hợp này |
| 5 | Phân quyền tạo `ir.model`/`ir.model.fields`/`ir.actions.server` | Cần xử lý | Nên giới hạn nhóm quyền chặt (tương tự `base.group_system` đã áp dụng cho `ir.actions.server` gốc), không mở cho user thường |

---

## 7. Định nghĩa "Hoàn thành" (Definition of Done — MVP)

- [ ] Tạo được `excel.report.definition` với model mới (transient) + ít nhất 1 field, Confirm thành công.
- [ ] View form được auto-generate đúng, hiện đủ field vừa khai báo.
- [ ] Smart button "Server Action" và "View" hoạt động, ẩn/hiện đúng theo dữ liệu.
- [ ] Sửa `code` tại tab "Server Action" → xác nhận `ir.actions.server.code` thay đổi ngay (không có field trung gian lưu bản sao).
- [ ] Trigger = Menu → menu mới xuất hiện, bấm vào mở đúng wizard, generate Excel thành công qua `_run_action_excel_template_multi`.
- [ ] Trigger = Contextual → server action xuất hiện trong menu Action (⚙️) của model đích (kể cả model có sẵn như `sale.order`), chạy đúng, không có thay đổi nào trên view gốc của model đó.
- [ ] Chọn model đích là model **có sẵn** (không phải model mới tạo) → hệ thống không tự sinh view, không lỗi.

---

## 8. Việc cần làm tiếp theo

1. Verify trên Odoo 19 shell: field `binding_view_types` (giá trị hợp lệ), khả năng `ir.ui.menu.action` trỏ thẳng `ir.actions.server`.
2. Code `excel.report.definition` + `excel.report.definition.field` theo spec mục 3.
3. Code `action_confirm()` theo pipeline mục 4.
4. Build view XML cho `excel.report.definition` (mục 5), gồm button box.
5. Viết `ir.model.access.csv` với group quyền hạn chế (mục 6, rủi ro #5).