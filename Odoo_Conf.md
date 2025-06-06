# Hướng Dẫn Cấu Hình File `odoo.conf`

File `odoo.conf` là trái tim của cấu hình Odoo server, nơi bạn định nghĩa các tham số quan trọng để kiểm soát hoạt động, hiệu suất và bảo mật của ứng dụng. Việc cấu hình đúng file này là yếu tố then chốt để Odoo hoạt động ổn định và hiệu quả trong môi trường production.

---

## 1. Vị trí File `odoo.conf`

File cấu hình Odoo thường nằm ở một trong các vị trí sau, tùy thuộc vào cách bạn cài đặt và cấu hình Odoo:

* `/etc/odoo/odoo.conf` (phổ biến cho cài đặt hệ thống)
* `~/.config/odoo/odoo.conf` (phổ biến cho cài đặt của người dùng cụ thể)
* Trong thư mục cài đặt Odoo (ví dụ: `/opt/odoo/odoo.conf`)

Nếu bạn đang sử dụng một dịch vụ `systemd` để chạy Odoo (khuyến nghị cho production), đường dẫn của file cấu hình sẽ được chỉ định trong tệp service của Odoo (ví dụ: `/etc/systemd/system/odoo.service`).

Để chỉnh sửa file này, bạn sẽ cần quyền `sudo` và một trình soạn thảo văn bản như `nano` hoặc `vi`:

```bash
sudo nano /path/to/your/odoo.conf
```
(Hãy thay thế `/path/to/your/odoo.conf` bằng đường dẫn thực tế của file `odoo.conf` trên server của bạn).

---

## 2. Cấu Trúc Cơ Bản của `odoo.conf`

File `odoo.conf` được tổ chức thành các phần, bắt đầu bằng `[options]`. Mỗi dòng trong phần này là một cặp `key = value`.

```ini
[options]
# Các biến cấu hình sẽ được định nghĩa ở đây
key_1 = value_1
key_2 = value_2
# ...
```

---

## 3. Các Biến Cấu Hình Chính và Chi tiết

Dưới đây là danh sách các biến cấu hình quan trọng và phổ biến, được nhóm theo chức năng, cùng với giải thích chi tiết và các giá trị khuyến nghị cho môi trường production.

### 3.1. Cấu Hình Cơ sở Dữ liệu (Database Configuration)

Các biến này thiết lập cách Odoo kết nối và quản lý cơ sở dữ liệu PostgreSQL.

* **`admin_passwd = <Mật khẩu Master được mã hóa>`**
    * **Giới thiệu:** Đây là "Master Password" của Odoo. Nó được sử dụng để truy cập giao diện quản lý cơ sở dữ liệu web (tại `/web/database/manager`), cho phép bạn tạo, xóa, sao lưu và khôi phục cơ sở dữ liệu.
    * **Cấu hình chi tiết:** Trong production, giá trị này **phải** là một chuỗi băm an toàn (như `pbkdf2-sha512` trong ví dụ của bạn) thay vì một mật khẩu văn bản thuần túy. Odoo tự động băm mật khẩu khi bạn thiết lập nó qua giao diện quản lý DB.
    * **Ví dụ:**
        ```ini
        admin_passwd = admin@412
        ```
    * **Khuyến nghị Production:** Luôn sử dụng mật khẩu master an toàn, băm mạnh.

* **`db_host = False`**
    * **Giới thiệu:** Địa chỉ IP hoặc hostname của server PostgreSQL.
    * **Cấu hình chi tiết:**
        * `False`: (Mặc định) Odoo sẽ cố gắng kết nối với PostgreSQL trên `localhost` bằng socket Unix hoặc các cấu hình mặc định khác.
        * `localhost` hoặc `127.0.0.1`: Kết nối cục bộ.
        * `your_db_server_ip`: Nếu PostgreSQL chạy trên một server riêng.
    * **Ví dụ:**
        ```ini
        db_host = False
        ```

* **`db_port = False`**
    * **Giới thiệu:** Cổng mà PostgreSQL đang lắng nghe.
    * **Cấu hình chi tiết:**
        * `False`: (Mặc định) Odoo sẽ sử dụng cổng PostgreSQL mặc định (5432).
        * `<port_number>`: Nếu PostgreSQL của bạn chạy trên một cổng không chuẩn.
    * **Ví dụ:**
        ```ini
        db_port = False
        ```

* **`db_user = odoo`**
    * **Giới thiệu:** Tên người dùng mà Odoo sử dụng để kết nối với PostgreSQL. Người dùng này cần có quyền truy cập vào các cơ sở dữ liệu Odoo.
    * **Ví dụ:**
        ```ini
        db_user = odoo
        ```

* **`db_password = odoo`**
    * **Giới thiệu:** Mật khẩu của người dùng cơ sở dữ liệu.
    * **Cấu hình chi tiết:** Đây là một trong những thông tin quan trọng nhất. **Tuyệt đối không để mật khẩu mặc định như `odoo` trong production.** Hãy thay thế bằng một mật khẩu mạnh và duy nhất.
    * **Ví dụ:**
        ```ini
        db_password = your_strong_db_password
        ```
    * **Khuyến nghị Production:** Sử dụng mật khẩu mạnh và an toàn.

* **`db_max_retries = 3`**
    * **Giới thiệu:** Số lần Odoo sẽ thử lại kết nối đến cơ sở dữ liệu nếu kết nối bị mất.
    * **Cấu hình chi tiết:** Hữu ích trong môi trường mạng không ổn định hoặc khi DB có thể tạm thời không khả dụng.
    * **Ví dụ:**
        ```ini
        db_max_retries = 3
        ```

* **`list_db = True`**
    * **Giới thiệu:** Cho phép hiển thị danh sách các cơ sở dữ liệu có sẵn trên màn hình quản lý cơ sở dữ liệu web.
    * **Cấu hình chi tiết:**
        * `True`: (Mặc định) Cho phép người dùng xem và quản lý DB.
        * `False`: Tắt hiển thị danh sách DB.
    * **Khuyến nghị Production:** Đặt thành `False` để tăng cường bảo mật nếu bạn không cần truy cập giao diện quản lý DB thường xuyên, buộc người dùng phải biết tên DB để truy cập.
    * **Ví dụ:**
        ```ini
        list_db = False
        ```

### 3.2. Đường dẫn và Thư mục (Paths & Directories)

Các biến này xác định vị trí của các module, tệp log và dữ liệu của Odoo.

* **`addons_path = /opt/odoo/odoo/addons,/opt/odoo/odoo/develop,/opt/odoo/odoo/enterprise`**
    * **Giới thiệu:** Danh sách các thư mục chứa các module Odoo, được phân cách bởi dấu phẩy. Odoo sẽ tìm kiếm module trong các thư mục này theo thứ tự.
    * **Cấu hình chi tiết:**
        * `/opt/odoo/odoo/addons`: Chứa các module cộng đồng tiêu chuẩn.
        * `/opt/odoo/odoo/develop`: Thư mục cho các module tùy chỉnh hoặc phát triển.
        * `/opt/odoo/odoo/enterprise`: (Nếu bạn có Odoo Enterprise) Chứa các module Enterprise.
    * **Ví dụ:**
        ```ini
        addons_path = /opt/odoo/odoo/addons,/opt/odoo/custom_addons,/opt/odoo/enterprise
        ```

* **`data_dir = /opt/odoo/.local/share/Odoo`**
    * **Giới thiệu:** Đường dẫn đến thư mục mà Odoo sẽ lưu trữ các tệp đính kèm, hình ảnh, v.v. (được gọi là "filestore"). Đây là nơi chứa dữ liệu không phải trong DB.
    * **Cấu hình chi tiết:** Thư mục này rất quan trọng và cần được sao lưu thường xuyên cùng với cơ sở dữ liệu.
    * **Ví dụ:**
        ```ini
        data_dir = /opt/odoo/.local/share/Odoo
        ```

### 3.3. Cấu Hình Hiệu suất và Đa xử lý (Performance & Multiprocessing)

Các biến này ảnh hưởng trực tiếp đến khả năng xử lý và tài nguyên của Odoo.

* **`workers = 17`**
    * **Giới thiệu:** Số lượng worker processes mà Odoo sẽ sử dụng để xử lý các yêu cầu. Mỗi worker là một tiến trình Python độc lập.
    * **Cấu hình chi tiết:** Đây là một thiết lập quan trọng để tối ưu hiệu suất cho môi trường production.
        * **Công thức ước tính (cho các worker HTTP):** `(Số lượng CPU * 2) + 1`.
        * **Ví dụ:** Server có 8 CPU -> `(8 * 2) + 1 = 17 workers`.
        * Một worker sẽ được dành riêng cho các tác vụ cron (xem `max_cron_threads`).
    * **Khuyến nghị Production:** Luôn cấu hình `workers > 0` (thường là >= 1) trong môi trường production.

* **`max_cron_threads = 1`**
    * **Giới thiệu:** Số lượng luồng (threads) tối đa dành riêng cho các tác vụ Cron (tác vụ định kỳ tự động của Odoo).
    * **Cấu hình chi tiết:**
        * `0`: Tắt tất cả các tác vụ cron.
        * `1`: (Khuyến nghị) Đảm bảo các tác vụ cron chạy tuần tự trên một worker riêng, tránh xung đột và chiếm dụng tài nguyên của các worker HTTP.
        * `>1`: Cho phép nhiều tác vụ cron chạy song song (cẩn thận với xung đột tài nguyên).
    * **Khuyến nghị Production:** Đặt là `1`.

* **`limit_memory_hard = 0`**
    * **Giới thiệu:** Giới hạn bộ nhớ cứng (tính bằng byte) cho mỗi worker process.
    * **Cấu hình chi tiết:** Nếu một worker vượt quá giới hạn này, nó sẽ bị kill ngay lập tức.
    * **Khuyến nghị Production:** Đặt một giá trị hợp lý (ví dụ: `2048MB = 2147483648 bytes`) để ngăn chặn các worker rò rỉ bộ nhớ gây ra sự cố cho toàn bộ server. Nếu để `0` (không giới hạn), một worker lỗi có thể chiếm hết RAM.
    * **Ví dụ:**
        ```ini
        limit_memory_hard = 2147483648
        ```

* **`limit_memory_soft = 0`**
    * **Giới thiệu:** Giới hạn bộ nhớ mềm (tính bằng byte) cho mỗi worker process.
    * **Cấu hình chi tiết:** Nếu một worker vượt quá giới hạn này, nó sẽ được khởi động lại sau khi hoàn thành request hiện tại.
    * **Khuyến nghị Production:** Nên đặt một giá trị nhỏ hơn `limit_memory_hard` (ví dụ: `1717986918 = 1.6GB`) để worker được làm mới định kỳ. Nếu để `0`, worker có thể tích lũy bộ nhớ thừa.
    * **Ví dụ:**
        ```ini
        limit_memory_soft = 1717986918
        ```

* **`limit_request = 8192`**
    * **Giới thiệu:** Số lượng request tối đa mà một worker sẽ xử lý trước khi được khởi động lại.
    * **Cấu hình chi tiết:** Giúp giải phóng bộ nhớ và tránh các vấn đề liên quan đến rò rỉ bộ nhớ nhỏ.
    * **Ví dụ:**
        ```ini
        limit_request = 8192
        ```

* **`limit_time_cpu = 7500`**
    * **Giới thiệu:** Giới hạn thời gian CPU (tính bằng giây) mà một worker có thể sử dụng để xử lý một request.
    * **Cấu hình chi tiết:** Ngăn chặn các request tốn CPU quá mức làm treo worker.
    * **Khuyến nghị Production:** Giá trị cao hơn trong production để cho phép các tác vụ phức tạp.
    * **Ví dụ:**
        ```ini
        limit_time_cpu = 7500
        ```

* **`limit_time_real = 8000`**
    * **Giới thiệu:** Giới hạn thời gian thực (tính bằng giây) mà một worker có thể mất để xử lý một request.
    * **Cấu hình chi tiết:** Ngăn chặn các request bị kẹt (ví dụ: chờ I/O) làm treo worker.
    * **Khuyến nghị Production:** Giá trị cao hơn trong production.
    * **Ví dụ:**
        ```ini
        limit_time_real = 8000
        ```

* **`max_http_workers = N`**
    * **Giới thiệu:** Giới hạn số lượng workers đồng thời xử lý các yêu cầu HTTP.
    * **Cấu hình chi tiết:** Hữu ích khi bạn có tổng số `workers` lớn nhưng muốn kiểm soát số lượng worker dành cho web.
    * **Ví dụ:**
        ```ini
        max_http_workers = 15
        ```

### 3.4. Cấu Hình Mạng và Proxy (Network & Proxy)

Các biến này liên quan đến cách Odoo tương tác với mạng và các proxy ngược (như Nginx).

* **`xmlrpc_port = 7958`**
    * **Giới thiệu:** Cổng mà Odoo sẽ lắng nghe cho các kết nối XML-RPC (cho giao diện web và API).
    * **Cấu hình chi tiết:** Đây là cổng mà proxy ngược (Nginx) sẽ chuyển tiếp các yêu cầu đến.
    * **Ví dụ:**
        ```ini
        xmlrpc_port = 7958
        ```

* **`gevent_port = 8072`**
    * **Giới thiệu:** Cổng mà Odoo Gevent server sẽ lắng nghe cho các kết nối longpolling (ví dụ: live chat, thông báo).
    * **Cấu hình chi tiết:** Proxy ngược (Nginx) sẽ chuyển tiếp các yêu cầu `/longpolling` và `/websocket` tới cổng này.
    * **Ví dụ:**
        ```ini
        gevent_port = 8072
        ```

* **`proxy_mode = True`**
    * **Giới thiệu:** Cho Odoo biết rằng nó đang chạy sau một proxy ngược.
    * **Cấu hình chi tiết:** Khi `True`, Odoo sẽ tin tưởng các header `X-Forwarded-*` từ proxy (ví dụ: Nginx), giúp Odoo nhận biết địa chỉ IP thực của client, tên host gốc và giao thức (HTTP/HTTPS) đã được sử dụng. Điều này rất quan trọng để đảm bảo Odoo tạo các URL chính xác và ghi log IP khách hàng đúng.
    * **Khuyến nghị Production:** Luôn đặt là `True` khi sử dụng proxy ngược.
    * **Ví dụ:**
        ```ini
        proxy_mode = True
        ```

### 3.5. Cấu Hình Log (Logging Configuration)

Các biến này kiểm soát cách Odoo ghi log các sự kiện và lỗi.

* **`log_file = /var/log/odoo/odoo.log`**
    * **Giới thiệu:** Đường dẫn tuyệt đối đến tệp log của Odoo.
    * **Cấu hình chi tiết:** Rất quan trọng để theo dõi lỗi, hoạt động và debug. Đảm bảo thư mục log có quyền ghi cho người dùng chạy Odoo.
    * **Ví dụ:**
        ```ini
        log_file = /var/log/odoo/odoo.log
        ```

* **`log_level = info`**
    * **Giới thiệu:** Mức độ chi tiết của log.
    * **Cấu hình chi tiết:**
        * `debug`: Rất chi tiết, thích hợp cho phát triển/debug.
        * `info`: (Mặc định) Thông tin chung về hoạt động của Odoo, thích hợp cho production để theo dõi.
        * `warning`, `error`, `critical`: Chỉ ghi lại các vấn đề nghiêm trọng.
    * **Khuyến nghị Production:** Đặt là `info`. Tăng lên `debug` tạm thời khi debug một vấn đề cụ thể.
    * **Ví dụ:**
        ```ini
        log_level = info
        ```

* **`log_handler = :INFO`**
    * **Giới thiệu:** Kiểm soát cách các tin nhắn log được xử lý và mức độ log cho từng handler hoặc module.
    * **Cấu hình chi tiết:**
        * `:INFO`: Tất cả các module sẽ ghi log ở mức `INFO` trở lên vào console/file log mặc định.
        * Bạn có thể chỉ định mức log cho từng module cụ thể, ví dụ: `odoo.addons.base:DEBUG` để module `base` ghi log ở mức `DEBUG`.
    * **Ví dụ:**
        ```ini
        log_handler = :INFO
        # log_handler = odoo.sql_db:DEBUG # Ví dụ: để debug các truy vấn SQL
        ```

### 3.6. Các Biến Khác (Miscellaneous Options)

* **`default_productivity_apps = True`**
    * **Giới thiệu:** Nếu `True`, Odoo sẽ tự động cài đặt một số ứng dụng năng suất mặc định (như Discuss, Calendar, Contacts) khi tạo một cơ sở dữ liệu mới.
    * **Ví dụ:**
        ```ini
        default_productivity_apps = True
        ```

* **`without_demo = True`**
    * **Giới thiệu:** Khi tạo một cơ sở dữ liệu mới, nếu `True`, dữ liệu demo sẽ không được tải.
    * **Khuyến nghị Production:** Rất nên đặt là `True` trong môi trường production để tránh cài đặt dữ liệu không cần thiết.
    * **Ví dụ:**
        ```ini
        without_demo = True
        ```

* **`auth_timeout = 604800`**
    * **Giới thiệu:** Thời gian (tính bằng giây) mà một phiên đăng nhập sẽ tồn tại nếu không có hoạt động.
    * **Cấu hình chi tiết:** `604800` giây tương đương 7 ngày.
    * **Ví dụ:**
        ```ini
        auth_timeout = 604800
        ```

* **`import_enable = True`**
    * **Giới thiệu:** Cho phép chức năng import dữ liệu thông qua giao diện người dùng Odoo.
    * **Cấu hình chi tiết:**
        * `True`: (Mặc định) Cho phép import.
        * `False`: Vô hiệu hóa chức năng import, có thể tăng cường bảo mật nếu không cần thiết.
    * **Ví dụ:**
        ```ini
        import_enable = True
        ```

---

## 4. Các Bước Hoàn Thiện Cấu Hình

1.  **Chỉnh sửa file `odoo.conf`**:
    * Mở file bằng lệnh `sudo nano /path/to/your/odoo.conf`.
    * Cập nhật hoặc thêm các giá trị theo nhu cầu cụ thể của môi trường production của bạn.
    * Đặc biệt chú ý đến:
        * `admin_passwd`: Đảm bảo mật khẩu này là mạnh và an toàn.
        * `db_password`: Mật khẩu người dùng cơ sở dữ liệu.
        * `addons_path`: Kiểm tra lại các đường dẫn có chính xác không.
        * `xmlrpc_port` và `gevent_port`: Phải khớp với cấu hình proxy ngược (Nginx).
        * `data_dir`: Ghi nhớ đường dẫn này để sao lưu filestore.
        * `workers`, `limit_memory_hard`, `limit_memory_soft`: Điều chỉnh để tối ưu hiệu suất dựa trên tài nguyên server.
        * `proxy_mode = True`: Quan trọng khi sử dụng Nginx.
        * `without_demo = True`: Khuyến nghị cho production.

2.  **Lưu file và thoát**:
    * Nhấn `Ctrl + O`, `Enter` để lưu.
    * Nhấn `Ctrl + X` để thoát trình soạn thảo `nano`.

3.  **Khởi động lại dịch vụ Odoo**:
    Sau khi thay đổi file cấu hình, bạn cần khởi động lại dịch vụ Odoo để các thay đổi có hiệu lực.

    ```bash
    sudo systemctl restart odoo.service # Thay odoo.service bằng tên service Odoo của bạn nếu khác
    ```

4.  **Kiểm tra log Odoo**:
    Sau khi khởi động lại, kiểm tra file log Odoo (`/var/log/odoo/odoo.log`) để đảm bảo không có lỗi nào xảy ra và các cấu hình mới đã được áp dụng.

    ```bash
    sudo tail -f /var/log/odoo/odoo.log
    ```

Việc nắm vững và cấu hình đúng các biến trong file `odoo.conf` là chìa khóa để Odoo hoạt động ổn định, hiệu quả và an toàn trong môi trường production của bạn.