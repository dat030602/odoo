# Web Side View

Module này mở rộng logic list view hiện tại và mở thêm hành vi cho form view trong phạm vi x2many, theo cùng tinh thần split/popup/default.

## Phạm vi xử lý

Chỉ xử lý trong ngữ cảnh x2many field khi đang ở form view.

Không mở rộng đại trà cho toàn bộ click trong form view.

## Hướng đề xuất

Ưu tiên inherit trực tiếp `web.FormView` thay vì chèn một wrapper chung vào `main > div` đầu tiên của `o_content`.

Lý do:
- `web.FormView` là điểm render gốc của form view trong Odoo 19.
- Cách này giới hạn ảnh hưởng trong phạm vi form view, giảm rủi ro làm lệch các view khác đang đi qua `web.Layout`.
- Có thể giữ logic hiện tại của list view và mở rộng form view theo cùng pattern, dễ debug hơn.

## Vì sao không ưu tiên wrapper chung trên `o_content`

Ý tưởng gắn logic vào `main.o_content > div:first-child` có thể chạy được trong một số trường hợp, nhưng đây là hướng rộng hơn cần thiết.

Rủi ro chính:
- Dễ tác động sang nhiều view cùng dùng `web.Layout`.
- Khó đảm bảo thứ tự DOM và selector ổn định trong mọi màn hình.
- Có thể làm phát sinh hành vi ngoài ý muốn ở các view đặc thù hoặc view trong dialog.

## Rule nghiệp vụ cần áp dụng

- many2one trong x2many list:
	Áp dụng theo mode đã chọn ở list view (default, split, popup).
- one2many và many2many:
	Chỉ áp dụng khi hiển thị dạng list view.
	Nếu widget làm thay đổi HTML theo kiểu đặc thù và không còn flow click chuẩn thì bỏ qua.
- Khi đang ở list của one2many hoặc many2many:
	Click vào cột many2one thì xử lý theo mode như trên.
	Click các cột còn lại (char, integer, many2many, ...) thì mở form view của chính record dòng hiện tại.

Điều kiện bắt buộc cho one2many/many2many:
- Chỉ áp dụng khi field đang readonly trên view.
- Hoặc field có edit = 0 / editable = 0 (tức là click sẽ theo flow popup/view record như chuẩn Odoo).

## Cách làm nếu chọn `web.FormView`

1. Inherit `web.FormView` trong XML.
2. Bổ sung patch xử lý click cho list renderer trong ngữ cảnh form view, nhưng chỉ kích hoạt khi renderer thuộc x2many readonly/editable=0.
3. Giữ nguyên logic list view hiện tại để tránh phá hành vi đang đúng.
4. Trong x2many list:
	many2one đi theo mode hiện tại.
	Các field còn lại mở form record hiện tại.
5. Bỏ qua các trường hợp widget tùy biến làm lệch flow click chuẩn.
6. Nếu chỉnh logic chạy list trong form view thì if (isFormView) là đoạn sẽ chèn vào đây, không viết ở ngoài ảnh hưởng đến logic trong list menu tôi đã build

## Ghi chú kỹ thuật

- `web.FormView` nằm trong `odoo/addons/web/static/src/views/form/form_controller.xml`.
- `web.Layout` là wrapper chung cho list/form, nhưng chỉ nên dùng khi muốn thay đổi hành vi ở mức toàn cục.
- Nếu mục tiêu chỉ là split view cho form, inherit `web.FormView` là phương án an toàn hơn.

## Kết luận

Hướng triển khai tiếp theo sẽ là inherit web.FormView và nối xử lý click cho x2many list trong form theo rule ở trên. Không can thiệp wrapper chung trên o_content.