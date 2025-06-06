---

# Mở Rộng Ổ Đĩa Ubuntu khi Đã có Không Gian Trống

Khi bạn đã mở rộng ổ đĩa vật lý (ví dụ: trong VMware, VirtualBox, hoặc trên server vật lý) và hệ thống Ubuntu của bạn có không gian trống chưa được phân bổ, bạn cần thực hiện các bước sau để mở rộng phân vùng và hệ thống tệp để sử dụng toàn bộ dung lượng đó. Hướng dẫn này áp dụng cho các hệ thống sử dụng Logical Volume Management (LVM), một cấu hình phổ biến trên Ubuntu server.

---

## 1. Mở Rộng Phân Vùng Gốc với `parted`

Chúng ta sẽ sử dụng công cụ `parted` để thay đổi kích thước phân vùng. Trong ví dụ này, chúng ta giả định phân vùng bạn muốn mở rộng là `/dev/sda3`. **Hãy đảm bảo bạn thay thế `/dev/sda` và số phân vùng (ví dụ: `3`) cho phù hợp với hệ thống của mình.**

1.  **Chạy `parted` trên thiết bị đĩa:**

    ```bash
    sudo parted /dev/sda
    ```
    (Thay `/dev/sda` bằng ổ đĩa vật lý chính của bạn).

2.  **Mở rộng phân vùng:**
    Trong giao diện `parted`, sử dụng lệnh `resizepart` để mở rộng phân vùng. Bạn cần chỉ định số phân vùng và kích thước cuối cùng. Ví dụ `2147GB` có thể là kích thước tối đa của đĩa đã mở rộng.

    ```parted
    (parted) resizepart 3 2147GB
    ```
    * `resizepart`: Lệnh thay đổi kích thước phân vùng.
    * `3`: Số của phân vùng bạn muốn mở rộng (kiểm tra bằng `print` trước).
    * `2147GB`: Kích thước MỚI của phân vùng. Bạn có thể sử dụng `100%` để điền toàn bộ không gian trống còn lại. Ví dụ: `resizepart 3 100%`.

3.  **Kiểm tra không gian trống (tùy chọn):**
    Bạn có thể dùng lệnh `print free` để xem các phân vùng và không gian trống.

    ```parted
    (parted) print free
    ```

4.  **Thoát `parted`:**

    ```parted
    (parted) quit
    ```

---

## 2. Thông báo Thay đổi Bảng Phân Vùng với `partprobe`

Sau khi thay đổi phân vùng bằng `parted`, bạn cần thông báo cho kernel về những thay đổi này.

```bash
sudo partprobe /dev/sda
```
Lệnh này sẽ quét lại bảng phân vùng trên `/dev/sda` và cập nhật thông tin cho kernel.

---

## 3. Mở Rộng Physical Volume (PV) trong LVM

Bây giờ, bạn cần mở rộng Physical Volume (PV) để LVM nhận ra không gian mới đã được thêm vào phân vùng.

```bash
sudo pvresize /dev/sda3
```
* `pvresize`: Lệnh thay đổi kích thước Physical Volume.
* `/dev/sda3`: Đường dẫn đến phân vùng đã được mở rộng mà trên đó Physical Volume của bạn được tạo.

---

## 4. Mở Rộng Logical Volume (LV)

Tiếp theo, mở rộng Logical Volume (LV) để nó sử dụng toàn bộ không gian trống có sẵn trong Volume Group (VG) đã được mở rộng.

```bash
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
```
* `lvextend`: Lệnh dùng để thay đổi kích thước của Logical Volume.
* `-l +100%FREE`: Chỉ định rằng bạn muốn mở rộng LV để sử dụng toàn bộ (100%) không gian trống còn lại trong Volume Group.
* `/dev/ubuntu-vg/ubuntu-lv`: Đây là đường dẫn đến Logical Volume chính của bạn (thường là `/dev/mapper/ubuntu--vg-ubuntu--lv` hoặc tương tự). **Hãy thay thế nó bằng đường dẫn LV chính xác trên hệ thống của bạn.**

---

## 5. Thay đổi Kích thước Hệ thống Tệp

Cuối cùng, sau khi Logical Volume được mở rộng, bạn cần thay đổi kích thước hệ thống tệp (thường là `ext4`) để nó lấp đầy không gian mới được cấp phát.

```bash
sudo resize2fs /dev/ubuntu-vg/ubuntu-lv
```
* `resize2fs`: Lệnh dùng để thay đổi kích thước hệ thống tệp ext2, ext3 hoặc ext4.
* `/dev/ubuntu-vg/ubuntu-lv`: Đây là đường dẫn đến thiết bị mà hệ thống tệp được gắn trên đó (phải khớp với đường dẫn LV ở bước trước).

Sau khi hoàn tất các bước này, hệ điều hành của bạn sẽ nhận và sử dụng toàn bộ dung lượng đĩa đã được mở rộng. Bạn có thể kiểm tra dung lượng bằng lệnh `df -h` để xác nhận.