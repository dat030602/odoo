Kiến trúc tích hợp MISA meInvoice trên Odoo 19 được chia thành hai tầng độc lập gồm **Module Base** (xử lý hạ tầng kết nối, xác thực, hàng đợi tuần tự) và **Module Con** (ánh xạ dữ liệu nghiệp vụ Kế toán, POS, Kho) nhằm đảm bảo tính mở rộng và tuân thủ chuẩn OpenAPI của MISA.

## 1. Cấu trúc phân tầng hệ thống trên Odoo 19

Mô hình phân tách giúp cô lập tầng giao thức mạng khỏi tầng nghiệp vụ ERP, cho phép doanh nghiệp cài đặt linh hoạt từng phân hệ theo nhu cầu sử dụng thực tế:

* **Module Base (Core Connector)**: Quản lý cấu hình đa công ty, vòng đời Access Token, kiểm soát giới hạn gọi API (Rate Limit), hàng đợi tuần tự và bộ phân tích lỗi chung.
* **Module Con Kế toán (Accounting e-Invoice)**: Kế thừa model `account.move` để đồng bộ mẫu hóa đơn, ánh xạ dữ liệu hóa đơn GTGT/bán hàng, xử lý hóa đơn thay thế và điều chỉnh.
* **Module Con Máy tính tiền (POS e-Invoice)**: Kế thừa model `pos.order` phục vụ phát hành hóa đơn khởi tạo từ máy tính tiền theo cơ chế ký số sau.
* **Module Con Kho & Đặc thù (Stock & Verticals)**: Kế thừa model `stock.picking` cho Phiếu xuất kho điện tử hoặc mở rộng trường dữ liệu cho ngành xe, khách sạn, điện nước.



## 2. Phân tích quy trình tại Module Base (Hạ tầng & Giao thức)

**Quản lý cấu hình và Cơ chế Xác thực (Authentication Flow)**
Module Base mở rộng model `res.company` và `res.config.settings` để lưu trữ thông tin kết nối và tự động hóa quy trình cấp phát, làm mới Token trước mỗi phiên giao dịch:

1. **Khởi tạo kết nối**: Lưu Base URL (`[https://developer.misa.vn/apis/itg/meinvoice/](https://developer.misa.vn/apis/itg/meinvoice/)`), `ClientID`, `ClientSecret`, mã số thuế (`taxcode`), tài khoản (`username`, `password`) và mã thiết bị (`DeviceID`).
2. **Lấy Access Token**: Gọi `POST /invoice/token` để nhận chuỗi Token có thời hạn 14 ngày và lưu cache vào cơ sở dữ liệu Odoo để tái sử dụng cho các request phát hành.
3. **Tách biệt luồng Token**: Thiết lập cấu hình tách riêng hàm lấy Token cho luồng phát hành hóa đơn chính thức và hàm lấy Token riêng cho luồng tạo hóa đơn nháp.
4. **Xác thực hai lớp (2FA)**: Nếu tài khoản bật 2FA, hệ thống lấy `CustomData.Id` từ bước đăng nhập làm `UserID`, kết hợp mã OTP gọi `POST /invoice/2fa` với `Remember = true` để ghi nhớ thiết bị.
5. **Làm mới Token tự động**: Khi Token hết hạn, cronjob hoặc middleware tự động gọi `POST /invoice/token/refresh` kèm tham số `tokenExpriedDate` trước khi thực thi request nghiệp vụ.



**Điều phối Request Tuần tự và Kiểm soát Rate Limit**
Hệ thống MISA áp dụng các ràng buộc nghiêm ngặt về tần suất và thứ tự xử lý mà Module Base phải kiểm soát ở tầng ORM và Queue:

* **Xử lý tuần tự theo ký hiệu**: Bắt buộc khóa bản ghi (`SELECT ... FOR UPDATE`) theo từng `InvSeries` để chạy tuần tự vòng lặp: Gửi request -> Nhận response -> Xử lý response -> Lưu thông tin hóa đơn.
* **Kiểm soát giới hạn lô (Batch Limit)**: Giới hạn mỗi request phát hành tối đa 30 hóa đơn và mỗi hóa đơn tối đa 400 dòng hàng hóa.
* **Quản lý Rate Limit**: Giới hạn tối đa 10 request/60 giây cho các API xác thực và lấy mẫu; tự động tạm dừng và xếp lịch lại khi nhận HTTP Status 429 (`TooManyRequests`).



**Chuẩn hóa Xử lý Response, Bắt lỗi và Auto-Retry**
Module Base cung cấp hàm phân tích phản hồi JSON tập trung và điều hướng xử lý lỗi cho toàn bộ module con:

1. **Kiểm tra đa tầng**: Kiểm tra cờ `Success` cấp HTTP response trước, sau đó kiểm tra `ErrorCode` cấp request, rồi kiểm tra tiếp `publishInvoiceResult[i].ErrorCode` (hoặc `CreateInvoiceResult`) của từng hóa đơn.
2. **Xác nhận thành công**: Chỉ khi `Success = true` và `publishInvoiceResult[i].ErrorCode` rỗng, hệ thống mới cập nhật trạng thái đã phát hành và lưu `TransactionID` về Odoo.
3. **Cơ chế Auto-Retry**: Khi chạy luồng tự động, nếu gặp mã lỗi `InvoiceDuplicated` hoặc `InvoiceNumberNotCotinuous`, hàng đợi tự động kích hoạt phát hành lại hóa đơn đó.
4. **Đồng bộ làm tròn thập phân**: Cung cấp hàm ánh xạ cấu hình `decimal.precision` của Odoo vào tag `OptionUserDefined`, tuân thủ nguyên tắc làm tròn từng thành phần trước rồi mới cộng tổng.



## 3. Phân tích quy trình tại các Module Con (Nghiệp vụ ERP)

### 3.1. Module Con Kế toán: Phát hành Hóa đơn Chuẩn, Thay thế & Điều chỉnh

**Đồng bộ Danh mục Mẫu hóa đơn và Chứng thư số**
Trước khi phát hành, module con kế toán thực hiện đồng bộ dữ liệu danh mục từ MISA về Odoo để người dùng cấu hình trên Sổ nhật ký (`account.journal`):

* **Lấy mẫu hóa đơn**: Gọi `GET /invoice/templates` (truyền `invoiceWithCode`, `ticket`, `year`, `haveTempOld`) để lưu `IPTemplateID`, `InvSeries`, `InvTemplateNo`, `IsSendSummary` và `IsMoreVATRate`.
* **Nhận diện tự động qua ký hiệu**: Tự động bóc tách `InvSeries` để phân loại nghiệp vụ gồm ký tự đầu (1: GTGT, 2: Bán hàng, 5: Vé, 6: PXK), ký tự thứ 2 (C: Có mã, K: Không mã) và ký tự thứ 5 (T: Thường, M: Máy tính tiền).
* **Kiểm tra chữ ký số từ xa**: Gọi `GET /invoice/get-certificates` để xác minh danh sách chứng thư số HSM/eSign nâng cao; nếu rỗng sẽ chặn phát hành theo `SignType = 2`.



**Ánh xạ Dữ liệu từ `account.move` sang `InvoiceData**`
Khi kế toán xác nhận hóa đơn trên Odoo, module con chuyển đổi dữ liệu bản ghi sang cấu trúc JSON `InvoiceData` của MISA:

* **Định danh & Chung**: Sinh mã `RefID` dạng GUID duy nhất theo từng đơn hàng/hóa đơn để chống trùng, truyền `InvSeries`, `InvDate` (`yyyy-MM-dd`), `CurrencyCode`, `ExchangeRate` và `PaymentMethodName`.
* **Thông tin người mua**: Ánh xạ từ `res.partner`; bắt buộc truyền `BuyerLegalName` và `BuyerAddress` khi có `BuyerTaxCode` hoặc `BuyerBudgetCode` (7 ký tự), kiểm soát `BuyerIDNumber` (12 số) và chỉ truyền tối đa 1 `BuyerEmail`.
* **Chi tiết dòng hàng (`OriginalInvoiceDetail`)**: Phân loại `ItemType` (1: Hàng hóa thường, 2: Khuyến mại, 3: Chiết khấu thương mại, 4: Ghi chú, 5: Vận tải), đánh số `LineNumber` từ 1 và để `SortOrder = null` đối với `ItemType` 3 hoặc 4.
* **Tổng tiền & Thuế (`TaxRateInfo`)**: Tính toán chính xác các trường nguyên tệ (`OC`) và quy đổi theo công thức trừ dòng chiết khấu (`ItemType = 3`), đồng thời gom nhóm mảng `TaxRateInfo` bắt buộc đối với hóa đơn GTGT.



**Quy trình Hóa đơn Thay thế và Điều chỉnh (Cập nhật theo Phụ lục XVII từ 15/12/2026)**
Đối với nghiệp vụ lập hóa đơn điều chỉnh (`ReferenceType = 2`) hoặc thay thế (`ReferenceType = 1`) từ hóa đơn gốc trên Odoo, module con bổ sung quy tắc bắt buộc mới của cơ quan thuế:

* **Tách thông tin hóa đơn gốc**: Truyền `OrgInvoiceType = 1` (hóa đơn NĐ 123), `OrgInvNo`, `OrgInvDate`, và tách ký hiệu gốc (ví dụ `1C24MAA`) thành `OrgInvTemplateNo = "1"` (ký tự đầu) cùng `OrgInvSeries = "C24MAA"` (phần còn lại).
* **Truyền mã lý do bắt buộc**: Bắt buộc truyền trường `AdjustReplaceReasonCode` (kiểu `int`, giá trị từ 1 đến 14 theo Phụ lục XVII Thông tư 91) bên cạnh `InvoiceNote` để MISA sinh thẻ XML `<LDDCTThe>` trong `<TTHDLQuan>`.



### 3.2. Module Con Phương thức Ký số: HSM, USB Token và Hóa đơn Nháp

Tùy theo hạ tầng chữ ký số của doanh nghiệp, module con điều hướng quy trình phát hành qua 3 luồng xử lý khác nhau:

1. **Luồng Ký số HSM (`SignType = 2`)**: Odoo gọi trực tiếp `POST /invoice/publishing` kèm mảng `InvoiceData`, hệ thống MISA tự động ký số trên Cloud và trả về kết quả ngay trong một lần gọi.
2. **Luồng Ký số USB Token (`SignType = 1`) - Bước 1**: Odoo gọi API lên Cloud MISA để tạo dữ liệu XML thô và nhận chuỗi XML trả về trong thuộc tính `CreateInvoiceResult`.
3. **Luồng Ký số USB Token (`SignType = 1`) - Bước 2**: JavaScript (OWL Component) trên trình duyệt người dùng gọi API Local của phần mềm MISA SignedService đang chạy dưới máy trạm để ký số vào XML thô.
4. **Luồng Ký số USB Token (`SignType = 1`) - Bước 3**: Trình duyệt gửi XML đã ký về Odoo Server để gọi API phát hành lên hệ thống Cloud MISA và Cơ quan Thuế.
5. **Luồng Xem trước & Hóa đơn nháp**: Hỗ trợ gọi `POST /invoice/unpublishview` để lấy đường dẫn xem trước hóa đơn (tồn tại 5 phút) hoặc đẩy hóa đơn nháp lên cổng web `app3.meinvoice.vn`.



### 3.3. Module Con POS (Máy tính tiền), Kho (PXK) và Ngành đặc thù

Các module con mở rộng kế thừa trực tiếp từ Module Con Kế toán để ghi đè hàm chuẩn bị dữ liệu (`_prepare_misa_invoice_data`) cho từng nghiệp vụ chuyên biệt:

* **Module POS Máy tính tiền (`pos.order`)**: Sử dụng mẫu ký hiệu có ký tự thứ 5 là `M` (như `1C25MYY`), truyền `SignType = 5` (ký số sau, không hiển thị CKS), và tự động gán `AdjustReplaceReasonCode = 14` khi thay thế hóa đơn MTT lập sai.
* **Module Phiếu xuất kho (`stock.picking`)**: Áp dụng cho mẫu có ký tự đầu là `6`, bổ sung nhóm trường lệnh điều động (`InternalCommandNo`, `InternalCommandOwner`, `InternalCommandDate`), vận chuyển (`TransporterName`, `Transport`) và kho xuất/nhập (`StockOut...`, `StockIn...`).
* **Module Ngành đặc thù**: Mở rộng dòng hàng cho kinh doanh xe (`ChassisNumber`, `EngineNumber`, `LicensePlate` khi `ItemType = 5`), hóa đơn khách sạn (`CheckIn`, `CheckOut`, `RoomNo`, `ServiceFeeRate`, `ExciseTaxRate`), hoặc điện nước (`ClockInfos`, `OldIndex`, `NewIndex`).


