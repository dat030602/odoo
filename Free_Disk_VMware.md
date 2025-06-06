# Hướng Dẫn Giải phóng Dung lượng Đĩa trên VMware

Nếu bạn đã mở rộng dung lượng đĩa ảo (VMDK) trong VMware và muốn hệ điều hành khách (guest OS) sử dụng toàn bộ không gian trống đó, bạn cần thực hiện các bước sau để mở rộng phân vùng và hệ thống tệp.

---

## 1. Mở rộng Logical Volume (LVM)

Lệnh này sẽ mở rộng Logical Volume (LV) của bạn để sử dụng toàn bộ không gian trống có sẵn trong Volume Group (VG):

```bash
sudo lvextend -l +100%FREE /dev/mapper/ubuntu--vg-ubuntu--lv
```

* `sudo lvextend`: Lệnh dùng để thay đổi kích thước của Logical Volume.
* `-l +100%FREE`: Chỉ định rằng bạn muốn mở rộng LV để sử dụng toàn bộ (100%) không gian trống còn lại trong Volume Group.
* `/dev/mapper/ubuntu--vg-ubuntu--lv`: Đây là đường dẫn đến Logical Volume cụ thể của bạn. Hãy đảm bảo bạn thay thế nó bằng đường dẫn LV chính xác trên hệ thống của mình nếu khác.

---

## 2. Thay đổi Kích thước Hệ thống Tệp

Sau khi Logical Volume được mở rộng, bạn cần thay đổi kích thước hệ thống tệp (thường là ext4) để nó lấp đầy không gian mới được cấp phát:

```bash
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
```

* `sudo resize2fs`: Lệnh dùng để thay đổi kích thước hệ thống tệp ext2, ext3 hoặc ext4.
* `/dev/mapper/ubuntu--vg-ubuntu--lv`: Đây là đường dẫn đến thiết bị mà hệ thống tệp được gắn trên đó.

Sau khi thực hiện hai lệnh này, hệ điều hành của bạn sẽ nhận và sử dụng toàn bộ dung lượng đĩa đã được mở rộng trong VMware.