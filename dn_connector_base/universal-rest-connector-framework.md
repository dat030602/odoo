# Universal REST Connector Framework cho Odoo

*Tài liệu thiết kế tổng hợp — bản review*

---

## 1. Mục tiêu

Xây dựng **Universal REST Connector Framework** cho Odoo — không phải connector Shopify/Woo riêng lẻ, mà là framework kết nối được bất kỳ REST API nào.

**Triết lý:** *Raw Data First – Business Later*

Framework chỉ chịu trách nhiệm: Request API → Sinh schema → Import raw data. **Không xử lý business logic.**

---

## 2. Kiến trúc 2 lớp

```
Lớp 1: Data Acquisition (dùng chung cho mọi hệ thống)
  REST API · Raw models · Auto schema · Auto import

Lớp 2: Business Transformer (viết riêng theo từng connector)
  Shopify → sale.order
  Woo     → product.product
  Kiot    → res.partner
  Haravan → stock.move
```

Đây là điểm mạnh nhất của thiết kế: connector cụ thể (Shopify, Woo, KiotViet...) chỉ còn là **adapter + transformer**, không phải viết lại toàn bộ engine.

```
Request → Response JSON → Target Path → Discover Schema
   → Create Models → Create Fields → Create Relations
   → Generate Views → Import Raw Data
```

---

## 3. Quy tắc sinh Schema

| # | Quy tắc |
|---|---|
| Model gốc | Người dùng đặt tên, bắt buộc prefix `x_`, chỉ lowercase + `_`, không chứa `.` |
| Model con | Chỉ sinh khi gặp **Array**. Không dùng path dài, không dùng tên array để đặt tên model. |
| **Đặt tên model con** | ⚠️ Điều chỉnh so với bản gốc: khoá theo **JSON path cố định** (vd. `lines`, `lines_taxes`), **không** đánh số theo thứ tự duyệt JSON — tránh drift khi API đổi thứ tự field. |
| Object (`{}` không phải array) | Không sinh model. Tạo field kiểu Text, lưu nguyên JSON. |
| Primitive (int/float/bool/date...) | Không quan tâm type gốc, luôn tạo `fields.Text`. Business xử lý convert sau. |
| Quan hệ | Tự tạo One2many / Many2one giữa model cha–con. |
| Field | Mỗi key JSON → 1 field, đặt tên `x_<key>`, tạo nếu chưa có. |

### Discovery & Apply tách rời
- **Discovery**: scan JSON trước, thu thập Missing Models / Fields / Relations — không tạo gì cả.
- **Apply Schema**: tạo Model → Field → Relation → View, **xong hết mới Import**. Không tạo schema giữa lúc import.
- Có checkbox **Auto Create Schema**: bật → scan + tạo tự động; tắt → field thiếu chỉ log (`Model / Field / JSON Path`), skip, tiếp tục import, không raise lỗi.
- ⚠️ **Bổ sung quan trọng**: dù bật Auto Create Schema, khuyến nghị **chỉ tự sinh field mới ở lần discovery đầu tiên** của mỗi endpoint; các lần sync sau schema nên "đóng băng" trừ khi user chủ động re-run discovery. Lý do: tạo `ir.model`/`ir.model.fields` runtime kéo theo registry reload — chạy liên tục trên production nhiều worker sẽ gây lag toàn hệ thống, không chỉ riêng connector.

### Cache & Logging
- Cache Models/Fields/Relations trong phạm vi 1 request, tránh query lặp `ir.model` / `ir.model.fields`.
- Missing field log gộp theo request (vd. `discount` thiếu ở 10,000 record → log 1 dòng duy nhất cuối request), không log lặp.

### View tự sinh
- **Form**: Notebook, mỗi model con → 1 page (Lines, Taxes, Payments...).
- **Tree**: hiện toàn bộ field; 5 field đầu `optional="show"`, còn lại `optional="hide"`.
- **Lưu ý UX**: view tự sinh (toàn Text/JSON thô) phù hợp cho dev/debug, **không** nên coi là UI bán cho end-user không kỹ thuật. UI thật cho khách hàng nằm ở Business Layer, nơi field đã có ý nghĩa nghiệp vụ.

### Payload
- Ngoài các field đã map, luôn giữ field `payload` (Text/JSON) lưu nguyên response gốc — phục vụ debug và làm nguồn cho Business Layer xử lý lại.

---

## 4. Code Execution Engine (bổ sung mới)

Hai điểm phát sinh từ thực tế: config tĩnh (key-value mapping) không đủ xử lý logic đặc thù của từng API. Cần cho phép viết code trực tiếp ở 2 điểm:

1. **Signature (sinh schema)** — logic riêng để quyết định model/field sinh ra từ raw JSON (vd. Shopify flatten `variants` thay vì sinh model con, Woo thì có).
2. **Prepare Request** — build request body, cần truy cập `records` của bản ghi Odoo hiện tại khi bấm nút execute từ view (vd. push `sale.order` lên Shopify).

### Quyết định: tự build execute bằng `safe_eval`, không dùng thẳng `ir.actions.server`

**Về mặt kỹ thuật thuần túy**, `ir.actions.server` thực ra cũng làm được cả hai việc: trả về arbitrary data (qua biến `action` khi gọi `.run()` bằng code, không phải qua UI), và nhận thêm biến vào context (qua `.with_context(...)` trước khi `.run()`). Đây không phải điểm yếu quyết định của nó.

**Lý do chọn tự build (dùng thẳng `safe_eval`) vẫn đứng vững:**

| Lý do | Chi tiết |
|---|---|
| UX nhúng inline | `code` là 1 field `Text` nằm thẳng trên model connector/endpoint của bạn → nhúng ngay trong tab của view, bấm Execute tại chỗ. Dùng `ir.actions.server` cần thêm Many2one sang model khác, kéo theo field/state không liên quan (`binding_model_id`, `crud_model_id`, `child_ids`...) nếu không ẩn kỹ. |
| Model gọn cho mục đích đóng gói bán | Khách mua Connector Pack là dev/implementer, không phải lúc nào cũng quen thuộc Server Actions menu. Model riêng, tên đúng chức năng, dễ export theo module (XML data ít, ít phụ thuộc ngoài phạm vi connector). |
| Semantic rõ ràng | `ir.actions.server` ngầm định nghĩa là "hành động user bấm mở UI"; dùng nó làm data transformer/pipeline step dễ gây hiểu nhầm mục đích cho người maintain sau. |
| Validate riêng | Dễ thêm `@api.constrains` bắt buộc code phải gán biến `result`, việc này khó làm trên model core của Odoo. |

**Đánh đổi:** phải tự lo logging/audit và security group — nhưng chỉ vài dòng, không đáng kể so với lợi ích tách bạch.

### Thiết kế: `connector.code.mixin`

```python
class ConnectorCodeMixin(models.AbstractModel):
    _name = "connector.code.mixin"

    code = fields.Text(
        string="Python Code",
        help="Biến có sẵn: env, record, records, context, log(message). "
             "Code bắt buộc phải gán biến `result`.",
        groups="base.group_system",  # hạn chế quyền sửa, giống ir.actions.server
    )

    def _get_eval_context(self, extra_context=None):
        self.ensure_one()
        ctx = {
            "env": self.env,
            "record": self.env.context.get("active_record"),
            "records": self.env.context.get("active_records"),
            "context": self.env.context,
            "log": lambda msg: _logger.info("[%s] %s", self.display_name, msg),
            "datetime": datetime,
            "dateutil": dateutil,
            "json": json,
        }
        if extra_context:
            ctx.update(extra_context)
        return ctx

    def execute_code(self, extra_context=None):
        eval_context = self._get_eval_context(extra_context)
        safe_eval(self.code, eval_context, mode="exec", nocopy=True)
        result = eval_context.get("result")
        self.env["connector.code.execution.log"].sudo().create({
            "model_id": self._name,
            "record_id": self.id,
            "code_snapshot": self.code,
            "result_summary": str(result)[:500],
        })
        return result
```

### Use case 1 — Signature (Discovery)

```python
class ConnectorModelSignature(models.Model):
    _name = "connector.model.signature"
    _inherit = ["connector.code.mixin"]

    connector_id = fields.Many2one("connector.config")
    target_model = fields.Char()

    def run_discovery(self, raw_json):
        return self.execute_code(extra_context={
            "raw_json": raw_json,
            "target_model": self.target_model,
        })
        # convention: code gán result = {"fields": [...], "models": [...], "relations": [...]}
```

### Use case 2 — Prepare Request (từ view, có `records`)

```python
class ConnectorEndpoint(models.Model):
    _name = "connector.endpoint"
    _inherit = ["connector.code.mixin"]

    def button_prepare_request(self):
        records = self.env[self.env.context["active_model"]].browse(
            self.env.context.get("active_ids", [])
        )
        payload = self.execute_code(extra_context={"records": records})
        return self.target_connector_id.sync(endpoint=self.endpoint, payload=payload)
```

### Bảo mật — bắt buộc

- `code` field giới hạn `base.group_system` (hoặc nhóm riêng "Connector Developer") — giống cách Odoo core giới hạn ai sửa server action.
- Lõi thực thi luôn qua `odoo.tools.safe_eval.safe_eval()` — không tự viết sandbox riêng, không expose `import` trong context. Thư viện ngoài cần dùng (`requests`, `json`...) chủ động import sẵn ở server và đưa vào `eval_context`, không cho code tự `import`.
- Có model log riêng `connector.code.execution.log`: ai, model nào, code snapshot, kết quả/lỗi, thời điểm — phục vụ audit và debug khi client báo sync sai.
- Cân nhắc mức độ expose `env`: cho phép `env` đầy đủ (full ORM access) phù hợp với đối tượng dev/implementer đã trust, nhưng **luôn log lại mọi lần execute** để có thể truy vết.

---

## 5. Vận hành khác (không đổi so với bản gốc)

- **Missing field khi Auto Schema OFF**: không raise, log rồi skip, tiếp tục import.
- **Discovery → Apply → Import**: luôn tách 3 bước, không tạo schema giữa chừng lúc import.
- **Business Layer làm sau, tách khỏi Framework**: Framework không convert type, không map product/partner. Ví dụ: `x_price` → `sale.order.amount_total` là việc của Transformer, không phải của base.

### Bổ sung nên có ngay từ Phase 1 (rút ra từ đánh giá trước)
- **Upsert key / idempotent sync**: bắt buộc có external_id + unique constraint để tránh tạo record trùng khi sync lại nhiều lần — nếu thiếu, Incremental Sync ở mục roadmap gần như vô nghĩa.
- **`ir.model.access` cho model tự sinh**: mỗi model runtime cần access rights tương ứng, nếu không sẽ chặn ngay ở bước demo.

---

## 6. Hướng mở rộng tương lai (không thay đổi lõi)

- Scheduler/Cron Sync
- Pagination (page, offset, cursor, next token)
- Webhook (nhận đẩy dữ liệu)
- Incremental Sync (theo `updated_at`, `last_sync`)
- Retry Queue
- Request/Response Log
- Transformer (raw model → business model)
- REST API Generator (sinh API ngược từ Odoo dựa trên schema động)

---

## 7. Roadmap

| Phase | Nội dung |
|---|---|
| **Phase 1 — Base Framework** | Request engine, Target path, Auto schema, Auto model/field/view, Raw import, Pagination, Scheduler, Logging, **Code Execution Engine (mixin)**, **Upsert/idempotent sync**, **Access rights cho model runtime** |
| **Phase 2 — Shopify Pack** | Auth, Orders, Products, Customers, Transformer |
| **Phase 3 — Woo Pack** | Reuse base, đổi auth, đổi endpoint, viết transformer |
| **Phase 4 — Kiot/Sapo/Haravan** | Scale — tái sử dụng toàn bộ engine, chỉ bổ sung adapter + transformer |

**Khuyến nghị trước khi build full Phase 1**: làm 1 spike nhỏ — lấy dữ liệu Shopify orders thật (có nested line items, refunds, discounts, càng bẩn càng tốt) chạy qua discovery engine dự kiến, xác nhận model/field sinh ra thực sự dùng được, rồi mới đầu tư toàn bộ framework. Rủi ro lớn nhất không nằm ở kiến trúc mà ở việc JSON thực tế luôn bẩn hơn JSON mẫu.

---

## 8. Mô hình kinh doanh

**Tầng 1 — Framework**: Universal REST Connector Base (Auto schema, Auto model, Auto view, Raw import) — ví dụ 199–299 USD.

**Tầng 2 — Connector Pack** (mua thêm nếu muốn đồng bộ chuẩn vào Odoo):
- Shopify Pack: $79–149 — Auth + endpoints, Pagination, Webhook (optional), Transformer → sale.order
- WooCommerce Pack: $79–149 — Auth + endpoints, Pagination, Transformer → sale.order, Product/customer sync
- KiotViet Pack: $99–179 — OAuth2, Products/customers/invoices, Transformer → Odoo, Delta sync

**Lưu ý cạnh tranh**: Odoo Apps Store đã có một số app "Generic REST Connector". Điểm khác biệt thật sự khó copy là **auto schema discovery + code execution engine linh hoạt**, không phải bản thân việc kết nối Shopify/Woo — nên định vị marketing và tài liệu bán hàng cần nhấn vào đúng chỗ này.
