# Xử lý Lỗi Frontend Odoo (Lỗi JS/CSS 500 hoặc Not Found)

Khi bạn gặp lỗi hiển thị frontend của Odoo, đặc biệt là các tệp JavaScript (JS) hoặc CSS báo lỗi 500 (Internal Server Error) hoặc Not Found khi tải lần đầu trang web, điều này thường xảy ra do các tệp tĩnh (static files) của Odoo bị hỏng hoặc không đồng bộ.

Odoo lưu trữ các tệp JS và CSS được tạo ra trong cơ sở dữ liệu (thường là trong bảng `ir_attachment`). Khi có lỗi, việc xóa các bản ghi này sẽ buộc Odoo Framework tự động tạo lại chúng khi cần thiết, giải quyết vấn đề.

Dưới đây là các câu lệnh SQL bạn có thể chạy để khắc phục lỗi này:

## Các Lệnh SQL Khắc phục

Bạn cần chạy các lệnh SQL này trực tiếp trên cơ sở dữ liệu Odoo của bạn. Hãy đảm bảo bạn chọn lệnh phù hợp với phiên bản Odoo bạn đang sử dụng.

### Đối với Odoo phiên bản 13 (v13)

Sử dụng lệnh này để xóa các tệp JS và CSS được lưu trữ dựa trên tên tệp dữ liệu:

```sql
DELETE FROM ir_attachment WHERE datas_fname SIMILAR TO '%.(js|css)';
```

### Đối với Odoo phiên bản 16 (v16) và các phiên bản mới hơn

Sử dụng lệnh này để xóa các tệp JS và CSS được lưu trữ dựa trên tên của bản ghi đính kèm:

```sql
DELETE FROM ir_attachment WHERE name SIMILAR TO '%.(js|css)';
```

### Lệnh chung (có thể sử dụng cho nhiều phiên bản)

Lệnh này sẽ xóa tất cả các tệp đính kèm có URL dạng `/web/content/%`, thường là nơi Odoo lưu trữ các tệp tĩnh đã được tạo:

```sql
DELETE FROM ir_attachment WHERE url LIKE '/web/content/%';
```

---

## Các bước thực hiện:

1.  **Kết nối đến cơ sở dữ liệu Odoo** bằng công cụ quản lý cơ sở dữ liệu như `psql` (nếu bạn dùng PostgreSQL).
2.  **Chọn cơ sở dữ liệu Odoo** mà bạn đang gặp lỗi.
3.  **Chạy một trong các lệnh SQL** trên (hoặc cả ba, tùy thuộc vào phiên bản Odoo và mức độ bạn muốn làm sạch).
4.  **Khởi động lại dịch vụ Odoo** sau khi chạy các lệnh SQL để đảm bảo Odoo tạo lại các tệp frontend cần thiết.

Sau khi thực hiện các bước này, hãy tải lại trang web Odoo của bạn. Các lỗi JS/CSS 500 hoặc Not Found sẽ được khắc phục, và giao diện frontend sẽ tải bình thường.