---

# Hướng Dẫn Cài Đặt Redis

Hướng dẫn này sẽ chỉ cho bạn cách cài đặt Redis trên hệ thống Ubuntu của bạn, sử dụng repository chính thức của Redis để đảm bảo bạn nhận được phiên bản mới nhất và ổn định.

---

## 1. Chuẩn bị Hệ thống và Thêm Redis Repository

Để cài đặt Redis từ repository chính thức, bạn cần thêm khóa GPG và repository Redis vào danh sách nguồn của hệ thống.

1.  **Cài đặt các gói cần thiết:**

    ```bash
    sudo apt-get install lsb-release curl gpg
    ```

    * `lsb-release`: Cung cấp thông tin về bản phân phối Linux.
    * `curl`: Công cụ để tải xuống dữ liệu từ internet.
    * `gpg`: Công cụ quản lý khóa GPG, dùng để xác thực các gói phần mềm.

2.  **Tải xuống và thêm khóa GPG của Redis:**

    ```bash
    curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    ```
    Lệnh này tải xuống khóa GPG của Redis và lưu nó vào thư mục `usr/share/keyrings`, đảm bảo tính toàn vẹn của các gói bạn sẽ cài đặt.

3.  **Thay đổi quyền cho khóa GPG:**

    ```bash
    sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
    ```
    Thiết lập quyền đọc cho tệp khóa GPG.

4.  **Thêm repository Redis vào danh sách nguồn:**

    ```bash
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
    ```
    Lệnh này thêm dòng repository chính thức của Redis vào một tệp mới trong `sources.list.d`, giúp hệ thống biết nơi tìm các gói Redis. `$(lsb_release -cs)` tự động lấy tên mã của bản phân phối Ubuntu của bạn (ví dụ: `jammy` cho Ubuntu 22.04).

---

## 2. Cài đặt Redis Server

Sau khi đã thêm repository, bạn có thể tiến hành cài đặt Redis.

1.  **Cập nhật danh sách gói:**

    ```bash
    sudo apt-get update
    ```
    Lệnh này làm mới danh sách các gói có sẵn từ các repository, bao gồm cả Redis repository mà bạn vừa thêm.

2.  **Cài đặt Redis:**

    ```bash
    sudo apt-get install redis
    ```
    Lệnh này sẽ cài đặt Redis server và các phụ thuộc của nó.

---

## 3. Quản lý Dịch vụ Redis

Sau khi cài đặt, Redis sẽ tự động được cấu hình để khởi động cùng hệ thống.

1.  **Kích hoạt Redis Server để tự khởi động cùng hệ thống (nếu chưa):**

    ```bash
    sudo systemctl enable redis-server
    ```

2.  **Khởi động Redis Server:**

    ```bash
    sudo systemctl start redis-server
    ```

3.  **Kiểm tra trạng thái của Redis Server:**

    ```bash
    sudo systemctl status redis-server
    ```
    Bạn sẽ thấy trạng thái `active (running)` nếu Redis đang chạy đúng cách.

Bạn đã cài đặt và cấu hình Redis thành công! Bây giờ bạn có thể sử dụng Redis cho các ứng dụng của mình.