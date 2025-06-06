# Hướng Dẫn Sao lưu và Khôi phục Cơ sở dữ liệu Odoo

Hướng dẫn này chỉ cho bạn cách sao lưu và khôi phục cơ sở dữ liệu Odoo, cùng với các lưu ý quan trọng khi di chuyển **filestore**.

---

## 1. Sao lưu Cơ sở dữ liệu

Để tạo bản sao lưu của cơ sở dữ liệu Odoo, bạn sử dụng lệnh sau:

```bash
sudo -u odoo pg_dump -d odoo17 > sql_file.sql
```

Lệnh này sẽ tạo một bản sao lưu của cơ sở dữ liệu có tên `odoo17` và lưu nó vào tệp `sql_file.sql` trong thư mục hiện hành.

---

## 2. Khôi phục Cơ sở dữ liệu

Để khôi phục cơ sở dữ liệu từ tệp sao lưu, hãy thực hiện các bước sau:

1.  **Tạo cơ sở dữ liệu mới:**

    ```bash
    sudo -u odoo createdb odoo17
    ```

2.  **Khôi phục dữ liệu từ tệp SQL:**

    ```bash
    sudo -u odoo psql -d odoo17 -f sql_file.sql
    ```

---

## 3. Di chuyển Filestore

**Filestore** chứa tất cả các tệp đính kèm và tài liệu của Odoo. Nó thường nằm **ngang hàng với thư mục `addons`** hoặc được chỉ định trong tham số `data-dir` của cấu hình Odoo của bạn.

* **Tên thư mục filestore:** Thư mục filestore sẽ có tên trùng với tên cơ sở dữ liệu của bạn. Khi sao chép, hãy đảm bảo đổi tên thư mục filestore khớp chính xác với tên cơ sở dữ liệu hiện tại của bạn.

* **Lưu ý quan trọng khi sao chép filestore:**
    * **TUYỆT ĐỐI KHÔNG sao chép filestore khi cơ sở dữ liệu Odoo đã chạy lần đầu.**
    * Nếu bạn đã khởi động Odoo và cơ sở dữ liệu đã được tạo, bạn phải **DROP** cơ sở dữ liệu hiện có, sau đó **RESTORE** lại từ đầu cùng với filestore đã đổi tên.
    * Việc sao chép filestore sau khi cơ sở dữ liệu đã chạy có thể dẫn đến lỗi `500 backend js`.

### 3.1. Sao chép tệp sao lưu (tùy chọn)

Sau khi sao lưu, bạn có thể sao chép tệp `sql_file.sql` và thư mục filestore đến một vị trí khác (ví dụ: máy chủ dự phòng) bằng lệnh `scp`:

```bash
scp /đường/dẫn/tới/sql_file.sql user@remote_host:/đường/dẫn/đích
scp -r /đường/dẫn/tới/filestore user@remote_host:/đường/dẫn/đích
```
