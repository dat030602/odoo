# Hướng dẫn sử dụng Office Approval Process

## 1. Mục đích

Office Approval Process cho phép tạo quy trình phê duyệt động cho nhiều model Odoo. Một quy trình có thể gồm nhiều bước, điều kiện áp dụng và người được phép phê duyệt.

Các đối tượng chính:

- **Process**: quy trình phê duyệt gắn với một model.
- **Step**: từng bước trong quy trình.
- **Rule**: điều kiện xác định người được phép xử lý một bước.
- **Execution**: trạng thái chạy thực tế của một quy trình trên một record.

## 2. Quyền sử dụng

Người dùng cần có quyền đọc các model của module để xem cấu hình và execution.

Việc tạo hoặc chỉnh sửa Process, Step và Rule cần quyền quản trị hệ thống theo cấu hình quyền hiện tại.

Không nên cho người dùng thông thường chỉnh trực tiếp Execution. Execution phải được thay đổi thông qua luồng approval hoặc method ORM được kiểm soát.

## 3. Tạo filter trước khi tạo Process

Process và Rule sử dụng `ir.filters` để xác định record nào được áp dụng.

### Tạo filter

1. Mở menu **Filters**.
2. Tạo một filter mới.
3. Chọn đúng model nghiệp vụ, ví dụ `Sales Order`.
4. Nhập domain điều kiện.
5. Đặt tên dễ nhận biết.
6. Lưu filter.

Nên tạo ít nhất hai filter:

- **Trigger**: điều kiện bắt đầu quy trình.
- **Process-wide filter**: điều kiện chung mà record phải thỏa trong toàn bộ quy trình.

Ví dụ:

```text
Trigger: trạng thái đơn hàng là quotation
Process-wide filter: đơn hàng có tổng tiền lớn hơn 10.000
```

Nếu một Rule có điều kiện riêng, tạo thêm filter cho Rule đó.

## 4. Tạo Process

1. Mở menu **Validation Process > Validation Process**.
2. Nhấn **New**.
3. Nhập tên quy trình.
4. Chọn **Model**, ví dụ `Sales Order`.
5. Chọn **Trigger**.
6. Chọn **Process-wide filter**.
7. Đánh dấu **Active**.
8. Cấu hình các tùy chọn bên phải.
9. Lưu lại.

### Các tùy chọn chính

- **Disable Edition**: khóa chỉnh sửa record khi đang chờ phê duyệt.
- **Allow restart after approved if triggered**: cho phép chạy lại sau khi đã hoàn tất nếu record vẫn thỏa điều kiện.
- **Allow restart after cancelled if triggered**: cho phép chạy lại sau khi bị hủy nếu record vẫn thỏa điều kiện.
- **Log messages to object**: ghi lịch sử thao tác vào chatter của record nghiệp vụ.
- **Activity type**: loại activity dùng khi tạo việc cần xử lý cho người phê duyệt.

Một Process chỉ nên có một bản active cho mỗi model. Nếu có nhiều Process active cùng model, việc xác định quy trình sẽ bị từ chối để tránh xử lý không xác định.

## 5. Tạo Step

Có thể tạo Step ngay trong tab **Steps** của Process hoặc mở menu **Validation Process > Steps**.

1. Mở Process.
2. Vào tab **Steps**.
3. Nhấn **Add a line**.
4. Nhập tên bước.
5. Nhập **Sequence**.
6. Lưu Process.

Các Step được xử lý theo `Sequence` tăng dần.

### Tùy chọn Step

- **Allow anyone if no conditions**: cho phép mọi người xử lý nếu bước không có Rule phù hợp.
- **Auto confirm if no conditions**: tự động xác nhận khi bước không có điều kiện.
- **Auto confirm if no active rules**: tự động xác nhận khi không có Rule active phù hợp.
- **Allow back button**: cho phép quay lại bước trước.
- **Back To Step**: chỉ định bước quay lại cụ thể.
- **Allow reset button**: cho phép khởi động lại theo cấu hình.
- **Enable activity**: tạo activity cho người xử lý bước tiếp theo.
- **Disable Edition**: khóa chỉnh sửa record trong bước này.

### Cấu hình action

Các trường action nhận danh sách tên method, phân tách bằng dấu phẩy:

```text
method_one,method_two
```

Các action hiện có:

- **Action on confirm**
- **Action on cancel**
- **Action on back**
- **Action on reset**

Chỉ sử dụng method nghiệp vụ đã được cho phép trên server. Không nhập method private, method không tồn tại hoặc method có thể gây thay đổi ngoài phạm vi approval.

### Cấu hình cập nhật field

Các trường field dùng định dạng:

```text
field_name=value,another_field=another_value
```

Ví dụ:

```text
approval_status='approved',approval_note='Manager approved'
```

Chỉ cập nhật field tồn tại, có thể ghi và không phải field kỹ thuật. Giá trị cần phù hợp với kiểu dữ liệu của field.

## 6. Tạo Rule

Rule xác định người nào được phép xử lý Step khi record thỏa điều kiện.

1. Mở Process.
2. Mở Step cần cấu hình.
3. Trong phần **Rules**, nhấn **Add a line**.
4. Nhập tên Rule.
5. Chọn **Applies on**.
6. Chọn cách xác định người dùng.
7. Lưu lại.

### Các cách xác định người dùng

#### Custom

Chọn trực tiếp người dùng trong **Authorized users**.

Danh sách rỗng được xử lý theo cấu hình của Step, đặc biệt là tùy chọn **Allow anyone if no conditions**.

#### Domain

Nhập domain cho model `res.users`. Những user thỏa domain sẽ được xem là người được phép.

Ví dụ:

```python
[('department_id.name', '=', 'Sales')]
```

#### Server Action

Chọn một Server Action đã được chuẩn bị để trả về user hoặc danh sách user. Server Action phải được kiểm tra kỹ vì nó chạy trong quá trình xác định quyền phê duyệt.

## 7. Luồng nghiệp vụ

Về mặt ORM, luồng xử lý dự kiến là:

```text
Mở record
    -> kiểm tra Process, Trigger và Process-wide filter
    -> tạo hoặc lấy Execution
    -> xác định Step và Rule
    -> kiểm tra quyền user
    -> thực hiện confirm/cancel/back/restart
    -> cập nhật record và Execution
```

Các method ORM chính:

```text
fal.vprocess.get_approval_state(model_name, record_id)
fal.vprocess.render_approval_bar(model_name, record_id)
fal.vprocess.execute_approval_action(model_name, record_id, action)
```

Action hợp lệ:

```text
confirm
cancel
back
restart
```

## 8. Theo dõi Execution

Mở menu **Validation Process > Executions** để xem các lần chạy.

Các thông tin quan trọng:

- **Process**: Process được sử dụng.
- **Process Model**: model nghiệp vụ.
- **Target**: ID record nghiệp vụ.
- **Step**: bước hiện tại.
- **Previous Step**: bước trước đó.
- **Last Action**: thao tác gần nhất.
- **Finished**: đã hoàn tất.
- **Cancelled**: đã hủy.

Không nên sửa trực tiếp các trường trạng thái của Execution vì có thể làm sai lịch sử và bỏ qua kiểm tra quyền.

## 9. Xử lý các trường hợp thường gặp

### Không thấy quy trình trên record

Kiểm tra:

1. Process có Active không.
2. Model của Process có đúng model của record không.
3. Record có thỏa Trigger không.
4. Record có thỏa Process-wide filter không.
5. Process có Step active không.
6. Có nhiều Process active cùng model không.

### User không thấy nút hoặc không thể phê duyệt

Kiểm tra:

1. User có nằm trong Rule Custom không.
2. User có thỏa domain user không.
3. Server Action có trả đúng user không.
4. Rule có Active không.
5. Record có thỏa filter của Rule không.
6. Step có cho phép mọi người khi không có điều kiện không.

### Không thể quay lại

Kiểm tra **Allow back button**, **Back To Step** và Sequence của các Step.

### Action không chạy

Kiểm tra method đã tồn tại trên model nghiệp vụ, có được whitelist trên server và user có quyền thực thi method đó hay chưa.

## 10. Trạng thái triển khai hiện tại

Hai file JavaScript giao diện cũ đã được loại bỏ:

- `Falinwa.validationProcess.js`
- `Falinwa.formControllerPatch.js`

Vì vậy module hiện không còn tự động chèn action bar vào form nghiệp vụ bằng JavaScript. Phần ORM và QWeb server-rendered đã có sẵn để tích hợp, nhưng cần một cơ chế giao diện Odoo khác gọi `render_approval_bar()` và `execute_approval_action()` nếu muốn hiển thị và thao tác trực tiếp trên form.

## 11. Khuyến nghị vận hành

- Tạo filter và Rule có tên rõ ràng.
- Chỉ để một Process active cho mỗi model.
- Kiểm thử trên bản sao dữ liệu trước khi bật Active.
- Không dùng method hoặc field cập nhật không được kiểm soát.
- Kiểm tra execution sau mỗi thay đổi cấu hình.
- Dùng user thử nghiệm để kiểm tra cả trường hợp được phép và không được phép phê duyệt.
- Sao lưu database trước khi thay đổi nhiều Process hoặc Step đang chạy.
