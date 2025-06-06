# Hướng Dẫn Cài đặt IP Tĩnh và Động với Netplan

Netplan là một tiện ích cấu hình mạng cho Linux, được sử dụng trên các bản phân phối như Ubuntu. Bạn có thể cấu hình địa chỉ IP động (DHCP) hoặc tĩnh bằng cách chỉnh sửa tệp cấu hình Netplan và sau đó áp dụng các thay đổi.

---

## 1. Chỉnh sửa tệp cấu hình Netplan

Bạn sẽ cần chỉnh sửa tệp cấu hình Netplan chính, thường là `/etc/netplan/00-installer-config.yaml`. Sử dụng lệnh sau để mở tệp bằng trình soạn thảo `nano`:

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

---

## 2. Cấu hình IP động (Dynamic IP)

Để cấu hình địa chỉ IP tự động thông qua DHCP, hãy đảm bảo tệp cấu hình của bạn trông giống như sau:

```yaml
# dynamic IP
network:
  ethernets:
    ens33:
      dhcp4: true
  version: 2
```

---

## 3. Cấu hình IP tĩnh (Static IP)

Để thiết lập một địa chỉ IP cố định cho máy chủ của bạn, hãy sử dụng cấu hình sau. Thay thế `ens33` bằng tên giao diện mạng của bạn nếu nó khác, và cập nhật địa chỉ IP, gateway, và nameserver cho phù hợp với mạng của bạn.

```yaml
# static IP
network:
  ethernets:
    ens33:
      dhcp4: no
      addresses: [192.168.1.11/24]
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4] # Có thể thêm nhiều địa chỉ DNS
  version: 2
```

---

## 4. Áp dụng thay đổi

Sau khi đã chỉnh sửa tệp cấu hình Netplan, bạn cần áp dụng các thay đổi để chúng có hiệu lực:

```bash
sudo netplan apply
```

Lệnh này sẽ đọc cấu hình mới và thiết lập lại các dịch vụ mạng tương ứng. Sau khi thực hiện, bạn có thể kiểm tra địa chỉ IP của mình bằng lệnh như `ip a` hoặc `ifconfig`.