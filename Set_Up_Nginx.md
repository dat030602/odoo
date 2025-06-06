---

# Hướng Dẫn Cài Đặt Nginx và Cấu Hình SSL với Certbot

Hướng dẫn này sẽ chỉ cho bạn cách cài đặt Nginx, cấu hình một server block cơ bản, và sau đó thiết lập SSL/TLS miễn phí bằng Certbot từ Let's Encrypt.

---

## 1. Cài đặt Nginx

Đầu tiên, hãy cập nhật danh sách gói và cài đặt Nginx:

1.  **Cập nhật hệ thống:**

    ```bash
    sudo apt update
    ```

2.  **Cài đặt Nginx:**

    ```bash
    sudo apt install nginx
    ```

3.  **Kiểm tra trạng thái Nginx:**
    Sau khi cài đặt, Nginx sẽ tự động khởi động. Bạn có thể kiểm tra trạng thái của nó:

    ```bash
    sudo systemctl status nginx
    ```
    Bạn sẽ thấy `active (running)` nếu Nginx đang chạy đúng cách.

---

## 2. Cấu hình Cơ bản Nginx và Tích hợp Odoo

Nginx quản lý các cấu hình trang web thông qua các thư mục `sites-available` (chứa tất cả các tệp cấu hình có sẵn) và `sites-enabled` (chứa các liên kết tượng trưng đến các cấu hình được kích hoạt).

1.  **Tạo tệp cấu hình Server Block mới:**
    Chúng ta sẽ tạo một server block mẫu cho Odoo. Thay thế `your_domain.conf` bằng tên miền hoặc tên mô tả của bạn.

    ```bash
    sudo nano /etc/nginx/sites-available/your_domain.conf
    ```

    Dán nội dung cấu hình sau vào tệp. Cấu hình này đã được cập nhật để phù hợp với việc **proxy Odoo** và hỗ trợ SSL thông qua Certbot.

    ```nginx
    # Định nghĩa các upstream servers cho Odoo backend và odoochat (Gevent)
    upstream odoo {
        server 127.0.0.1:7958; # Thay đổi cổng này nếu Odoo của bạn chạy trên cổng khác
    }

    upstream odoochat {
        server 127.0.0.1:8072; # Cổng longpolling của Odoo Gevent
    }

    # Ánh xạ cho websocket connections, quan trọng cho Odoo live chat
    map $http_upgrade $connection_upgrade {
        default upgrade;
        ''          close;
    }

    # Server Block cho HTTPS (cổng 443)
    server {
        server_name ccv.digital www.ccv.digital; # Thay thế bằng tên miền của bạn (ví dụ: yourdomain.com www.yourdomain.com)

        # Cấu hình SSL/TLS (được quản lý bởi Certbot)
        listen 443 ssl;
        ssl_certificate /etc/letsencrypt/live/ccv.digital/fullchain.pem; # Đường dẫn chứng chỉ
        ssl_certificate_key /etc/letsencrypt/live/ccv.digital/privkey.pem; # Đường dẫn khóa riêng
        include /etc/letsencrypt/options-ssl-nginx.conf; # Các tùy chọn bảo mật mặc định của Certbot
        ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # Tham số Diffie-Hellman

        # Tăng thời gian chờ cho các kết nối proxy (quan trọng cho các yêu cầu kéo dài của Odoo)
        proxy_read_timeout 720s;
        proxy_connect_timeout 720s;
        proxy_send_timeout 720s;

        # Cấu hình logging
        access_log /var/log/nginx/odoo.access.log;
        error_log /var/log/nginx/odoo.error.log;

        # Giới hạn kích thước tải lên (ví dụ: cho phép tải lên tệp lớn trong Odoo)
        client_max_body_size 1024m;

        # Tối ưu hóa cho header proxy
        proxy_headers_hash_max_size 512;
        proxy_headers_hash_bucket_size 128;

        # Thiết lập các HTTP headers cần thiết cho Odoo khi chạy ở chế độ proxy
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;

        # Chuyển hướng các yêu cầu websocket đến odoochat server (Gevent)
        location /websocket {
            proxy_pass http://odoochat;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Chuyển hướng các yêu cầu thông thường đến Odoo backend
        location / {
            proxy_pass http://odoo;
        }

        # Chuyển hướng các yêu cầu longpolling đến odoochat server
        location /longpolling {
            proxy_pass http://odoochat;
        }

        # Bật gzip để nén các loại nội dung phổ biến, cải thiện hiệu suất tải trang
        gzip_types text/css text/less text/plain text/xml application/xml application/json application/javascript;
        gzip on;
    }

    # Server Block cho HTTP (cổng 80) để chuyển hướng tất cả các yêu cầu sang HTTPS
    server {
        listen 80;
        listen [::]:80;
        server_name ccv.digital www.ccv.digital; # Thay thế bằng tên miền của bạn

        # Chuyển hướng vĩnh viễn (301) tất cả các yêu cầu HTTP đến phiên bản HTTPS
        return 301 https://$host$request_uri;
    }
    ```

    * **`upstream odoo` và `upstream odoochat`**: Định nghĩa các nhóm máy chủ mà Nginx sẽ proxy tới. Ở đây, chúng trỏ đến Odoo backend và Gevent longpolling server trên localhost.
    * **`map $http_upgrade $connection_upgrade`**: Cần thiết cho việc xử lý kết nối WebSocket (ví dụ: cho tính năng trò chuyện trực tiếp của Odoo).
    * **`server_name ccv.digital www.ccv.digital;`**: Đảm bảo rằng cấu hình này hoạt động cho cả tên miền gốc và tên miền `www`.
    * **`proxy_read_timeout`, `proxy_connect_timeout`, `proxy_send_timeout`**: Tăng thời gian chờ mặc định, rất quan trọng cho các ứng dụng như Odoo có thể có các yêu cầu dài hoặc tải dữ liệu lớn.
    * **`proxy_set_header`**: Đặt các header `X-Forwarded-*` để Odoo biết được địa chỉ IP thực của client và giao thức (HTTP/HTTPS) đã được sử dụng.
    * **`location /websocket`, `location /`, `location /longpolling`**: Định tuyến các yêu cầu khác nhau đến các upstream server Odoo hoặc odoochat tương ứng.
    * **`gzip on;`**: Bật nén Gzip để giảm kích thước dữ liệu truyền tải, giúp trang web tải nhanh hơn.
    * **Server block `listen 443 ssl`**: Cấu hình Nginx để lắng nghe trên cổng HTTPS và sử dụng chứng chỉ SSL được cung cấp bởi Certbot.
    * **Server block `listen 80`**: Đặt một server block riêng trên cổng 80 để bắt tất cả các yêu cầu HTTP và chuyển hướng chúng vĩnh viễn (301) sang HTTPS, đảm bảo trang web của bạn luôn được bảo mật.

2.  **Kích hoạt Server Block:**
    Tạo một liên kết tượng trưng (symlink) từ `sites-available` sang `sites-enabled` để kích hoạt cấu hình:

    ```bash
    sudo ln -s /etc/nginx/sites-available/your_domain.conf /etc/nginx/sites-enabled/
    ```

3.  **Kiểm tra cấu hình Nginx:**
    Luôn kiểm tra lỗi cú pháp trước khi khởi động lại Nginx:

    ```bash
    sudo nginx -t
    ```
    Bạn sẽ thấy `syntax is ok` và `test is successful` nếu không có lỗi.

4.  **Tải lại Nginx:**
    Áp dụng các thay đổi cấu hình:

    ```bash
    sudo systemctl reload nginx
    ```
    Hoặc khởi động lại hoàn toàn nếu cần:
    ```bash
    sudo systemctl restart nginx
    ```

---

## 3. Cài đặt và Cấu hình SSL với Certbot

Để bảo mật trang web của bạn bằng HTTPS, chúng ta sẽ sử dụng Certbot để cài đặt chứng chỉ SSL/TLS miễn phí từ Let's Encrypt.

1.  **Cài đặt Certbot và plugin Nginx:**

    ```bash
    sudo apt install certbot python3-certbot-nginx
    ```

2.  **Chạy Certbot để lấy chứng chỉ SSL:**
    Sử dụng lệnh sau, thay thế `ccv.digital` và `www.ccv.digital` bằng tên miền thực tế của bạn. Certbot sẽ tự động tìm cấu hình Nginx và thực hiện các bước cần thiết để cấp chứng chỉ.

    ```bash
    sudo certbot --nginx -d ccv.digital -d www.ccv.digital
    ```
    Certbot sẽ hỏi bạn một số thông tin (email, đồng ý điều khoản dịch vụ) và sau đó sẽ tự động cấu hình Nginx để sử dụng chứng chỉ SSL và thiết lập chuyển hướng HTTP sang HTTPS (như bạn đã thấy trong cấu hình đã cập nhật ở mục 2).

3.  **Kiểm tra tự động gia hạn:**
    Certbot tự động thiết lập một tác vụ cron hoặc systemd timer để gia hạn chứng chỉ của bạn trước khi chúng hết hạn. Bạn có thể kiểm tra quá trình gia hạn bằng cách chạy thử:

    ```bash
    sudo certbot renew --dry-run
    ```

---

## 4. Kiểm tra Trạng thái Nginx

Bạn có thể kiểm tra trạng thái dịch vụ Nginx bất cứ lúc nào:

```bash
sudo systemctl status nginx
```

Nếu mọi thứ đã được thiết lập đúng cách, trang web Odoo của bạn sẽ được phục vụ bởi Nginx và được bảo mật bằng SSL từ Let's Encrypt!