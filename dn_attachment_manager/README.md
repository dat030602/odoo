`Attachment Manager` là một module khá dễ làm nhưng có thể bán được vì hầu như khách hàng nào dùng Odoo lâu cũng gặp vấn đề **database phình to do attachment**.

Nếu mình làm để bán trên Odoo Apps, mình sẽ không chỉ làm màn hình xem attachment mà sẽ thêm các tính năng quản trị.

---

# Kiến trúc

Tạo module

```
attachment_manager/

├── models
│   ├── ir_attachment.py
│   ├── res_config.py
│
├── views
│   ├── attachment_views.xml
│   ├── menu.xml
│
├── wizard
│   ├── attachment_cleanup.py
│   ├── duplicate_merge.py
│
├── security
│   ├── ir.model.access.csv
│
└── static
```

---

# Menu

```
Settings

    Technical

        Attachment Manager

            All Attachments

            Large Files

            Duplicate Files

            Orphan Files

            Storage Statistic

            Cleanup Wizard
```

---

# Mở rộng ir.attachment

```python
class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    human_size = fields.Char(
        compute="_compute_size"
    )

    is_duplicate = fields.Boolean(
        compute="_compute_duplicate"
    )

    is_orphan = fields.Boolean(
        compute="_compute_orphan"
    )

    checksum_count = fields.Integer(
        compute="_compute_duplicate"
    )
```

---

# Human Size

Hiển thị

```
123 B

12 KB

5.3 MB

1.2 GB
```

```python
def sizeof_fmt(size):
    ...
```

Không phải xem

```
23564782
```

---

# Duplicate Detection

Odoo đã có field

```
checksum
```

=> cực tiện.

SQL

```sql
SELECT checksum,
COUNT(*)
FROM ir_attachment
GROUP BY checksum
HAVING COUNT(*) > 1;
```

Sau đó

```
Duplicate

YES

NO
```

---

# Orphan Detection

Ví dụ

```
res_model = sale.order

res_id = 100
```

Nhưng SO100 đã bị xóa.

=> orphan.

```python
if not env[res_model].browse(res_id).exists():
    orphan = True
```

---

# Large File

list View

```
Name

Model

Record

Size

Owner

Create Date
```

Sort theo

```
Size DESC
```

---

# Storage Statistic

Dashboard

```
Total Attachment

12,521
```

```
Total Size

8.3 GB
```

```
Average Size

650 KB
```

```
Largest File

420 MB
```

---

Theo model

```
Sale Order

1.5 GB
```

```
Invoice

2.3 GB
```

```
Product

700 MB
```

Có graph.

---

# Wizard Cleanup

Chọn

```
☑ Orphan

☑ Duplicate

☑ Larger than 20MB

☑ Before 2024
```

↓

Preview

↓

Delete

---

# Preview

```
Will delete

123 Files

2.5 GB
```

Không delete ngay.

---

# Duplicate Wizard

Nếu

```
A

B

C
```

checksum giống nhau.

Có thể

```
Keep oldest

Keep newest

Keep selected
```

Xóa phần còn lại.

---

# Smart Filter

Filter

```
Image

PDF

Excel

Video

XML

CSV

```

---

# MIME Icon

Hiển thị icon

📄 PDF

🖼 PNG

📊 XLSX

📹 MP4

---

# Download ZIP

Chọn

```
20 attachments
```

↓

Download ZIP

---

# Multi Delete

```
Action

Delete
```

---

# Search

```
File name

Extension

Owner

Model

Create Date

Checksum
```

---

# Statistics theo User

```
Admin

3.2 GB
```

```
John

1.1 GB
```

```
David

800 MB
```

---

# Statistics theo Module

```
sale.order

invoice

mrp.production

stock.picking
```

---

# Pie Chart

Theo loại file

```
Image 45%

PDF 30%

Excel 10%

Video 8%

Other
```

---

# Bar Chart

Top 20 model chiếm dung lượng.

---

# SQL tối ưu

Top file lớn

```sql
SELECT
id,
name,
file_size
FROM ir_attachment
ORDER BY file_size DESC;
```

---

Duplicate

```sql
SELECT
checksum,
count(*)
FROM ir_attachment
GROUP BY checksum
HAVING count(*) > 1;
```

---

Theo model

```sql
SELECT
res_model,
SUM(file_size)
FROM ir_attachment
GROUP BY res_model;
```

---

# Điểm cộng nếu muốn bán

Để module nổi bật hơn so với các module miễn phí, bạn có thể thêm một vài tính năng "Pro":

* **Cleanup theo lịch (Cron)**: tự động xóa attachment mồ côi hoặc quá cũ sau khi gửi email báo cáo.
* **Quota lưu trữ**: giới hạn dung lượng attachment theo người dùng hoặc theo model (ví dụ Sales chỉ được upload tối đa 500 MB).
* **Nén ảnh tự động**: giảm kích thước ảnh JPEG/PNG khi upload nhưng vẫn giữ chất lượng chấp nhận được.
* **Lưu trữ ngoài (S3/MinIO)**: hỗ trợ chuyển attachment sang object storage để giảm kích thước database.
* **Báo cáo PDF/Excel**: xuất thống kê dung lượng theo model, người dùng, loại file.
* **Xóa an toàn**: thay vì xóa ngay, chuyển vào "Recycle Bin" và cho phép khôi phục trong 30 ngày.
