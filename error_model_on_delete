# Khắc phục lỗi khi nâng cấp module bị lỗi do model không xóa được

## ❗ Mô tả lỗi

Khi nâng cấp module, Odoo có thể báo lỗi như sau:

```
KeyError: 'api.connector.requests'
````

Lỗi này xảy ra khi:

- Một model (ví dụ: `api.connector.requests`) đã bị xóa khỏi mã nguồn.
- Tuy nhiên các metadata như `ir.model.fields` hoặc `ir.model.fields.selection` vẫn còn trong cơ sở dữ liệu.
- Odoo cố gắng xử lý metadata đó và gặp lỗi vì không tìm thấy model tương ứng.

---

## ✅ Cách khắc phục

### Bước 1: Truy cập PostgreSQL

```bash
sudo -u postgres psql
````

### Bước 2: Kết nối database Odoo

```sql
\c your_odoo_database_name
```

> 🔁 Thay `your_odoo_database_name` bằng tên database thực tế của bạn.

---

### Bước 3: Xoá các lựa chọn bị lỗi

```sql
DELETE FROM ir_model_fields_selection
WHERE field_id IN (
    SELECT id FROM ir_model_fields
    WHERE model LIKE 'api.connector%'
);
```

---

### Bước 4 (tuỳ chọn): Xoá các trường liên quan

```sql
DELETE FROM ir_model_fields
WHERE model LIKE 'api.connector%';
```

---

### Bước 5: Thoát khỏi PostgreSQL

```sql
\q
```

---

### Bước 6: Khởi động lại Odoo và nâng cấp lại module

```bash
./odoo-bin -u your_module_name -d your_odoo_database_name
```

---

## 🧠 Ghi chú

* **Luôn backup database trước khi thao tác trực tiếp**.
* Nên sử dụng chức năng **uninstall module trong Odoo UI** nếu có thể, để tránh metadata dư thừa.
* Cách này áp dụng cho các module custom bị lỗi khi nâng cấp do model đã bị xóa khỏi mã nguồn.
