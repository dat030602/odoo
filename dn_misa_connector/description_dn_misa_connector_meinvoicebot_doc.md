Kiến trúc tích hợp MISA meInvoice Bot (INBOT - Quản lý hóa đơn đầu vào và đầu ra) trên Odoo 19 được thiết kế theo mô hình phân tầng gồm **Module Base** (quản lý xác thực 2 bước, cơ cấu tổ chức, phân trang đồng bộ và hàng đợi tải tệp) và các **Module Con** (ánh xạ hóa đơn mua hàng, hóa đơn bán hàng, đối chiếu rủi ro thuế và đồng bộ trạng thái hạch toán/thanh toán).

## 1. Cấu trúc phân tầng Module trên Odoo 19

Việc tách biệt tầng giao thức kết nối và tầng nghiệp vụ kế toán giúp hệ thống dễ bảo trì, tái sử dụng kết nối chung với hệ sinh thái MISA và kiểm soát chặt chẽ dữ liệu đầu vào trước khi ghi sổ:

* **Module Base (`dn_misa_meinvoicebot_base`)**: Quản lý cấu hình kết nối Base URL (`[https://developer.misa.vn/apis](https://developer.misa.vn/apis)`), luồng xác thực 2 bước (`ValidateUser` và `GetToken`), đồng bộ cơ cấu tổ chức (`Subscribers` và `Organizations`), quản lý hạn mức gói dịch vụ (`Other`) và tiến trình nền tải tệp ZIP (`xml`/`pdf`).
* **Module Con Hóa đơn Đầu vào (`dn_misa_meinvoicebot_in_invoice`)**: Kế thừa `account.move` (`move_type = 'in_invoice'`, `'in_refund'`), tự động kéo hóa đơn đầu vào, kiểm tra tính hợp lệ/rủi ro của nhà cung cấp (`CheckingResult`, `SellerRiskStatus`) và đẩy ngược thông tin hạch toán, thanh toán lên INBOT.
* **Module Con Hóa đơn Đầu ra (`dn_misa_meinvoicebot_out_invoice`)**: Đồng bộ và đối soát dữ liệu hóa đơn đầu ra từ INBOT (`OutInvoices`) với hóa đơn bán hàng phát sinh trên Odoo (`move_type = 'out_invoice'`, `'out_refund'`).
* **Module Con Mở rộng Nghị định 70 & Ngành đặc thù (`dn_misa_meinvoicebot_nd70`)**: Ánh xạ các trường dữ liệu đặc thù theo Nghị định 70 như kinh doanh xe, vận tải, thương mại điện tử và biên lai vào chi tiết dòng hạch toán.



## 2. Phân tích quy trình tại Module Base (Hạ tầng & Đồng bộ nền)

**Quản lý Xác thực 2 bước (Two-Step Authentication)**
Khác với luồng phát hành hóa đơn thông thường, hệ thống MISA INBOT bắt buộc thực hiện quy trình xác thực qua 2 bước nối tiếp để cấp phát JWT Token:

1. **Bước 1 - Xác thực người dùng (`ValidateUser`)**: Gọi `POST /meinvoicebot/v1/validateuser` với Header chứa `ClientID`, `CompanyTaxCode`, `UserName` và Body JSON chứa `PassWord` để nhận chuỗi phản hồi dạng `{CompanyID};{securetoken}` trong trường `Data`.
2. **Bước 2 - Lấy JWT Token (`GetToken`)**: Tách lấy `securetoken` từ bước 1 và truyền vào Header cùng `ClientID`, `companytaxcode`, `username` qua `POST /meinvoicebot/v1/auth/jwttoken` để nhận `AccessToken` (JWT).
3. **Đính kèm Header chuẩn**: Mọi request nghiệp vụ sau đó đều được Module Base tự động gắn Header `Authorization: Bearer {jwt_token}` và `ClientID`.
4. **Cơ chế tự động xác thực lại**: Khi gặp mã lỗi `TokenExpiredCode`, `InvalidTokenCode` hoặc `INVALIDTOKEN`, middleware trên Odoo tự động kích hoạt lại luồng xác thực từ Bước 1 để làm mới phiên làm việc.



**Đồng bộ Cơ cấu Tổ chức và Giám sát Tài nguyên (`Subscribers` & `Organizations`)**
Trước khi truy xuất hóa đơn, Module Base phải định danh được mã thuê bao và đơn vị tổ chức tương ứng với từng công ty (`res.company`) hoặc chi nhánh trên Odoo:

1. **Lấy mã định danh thuê bao (`SubscribersId`)**: Gọi `GET /meinvoicebot/v1/subscribers/code/{taxcode}` (hỗ trợ cả mã số thuế chi nhánh như `0101243143-008`) để lưu trường `Id` làm `SubscribersId` (CompanyID) trên `res.company`.
2. **Lấy danh sách phòng ban/tổ chức (`OrganizationID`)**: Gọi `GET /meinvoicebot/v1/{SubscribersId}/organizations` để đồng bộ danh sách đơn vị về Odoo, cho phép phân quyền truy xuất hóa đơn theo từng phòng ban/chi nhánh.
3. **Theo dõi hạn mức gói dịch vụ (`Other`)**: Đọc đối tượng `Other` trả về trong API danh sách hóa đơn để lưu thông tin gói (`ProductPackCode`), ngày hết hạn (`ExpiredDate`), tổng số hóa đơn (`NumberOfInvoice`), số đã dùng (`NumberInvUsed`) và số còn lại (`NumberInvStill`) nhằm cảnh báo sớm trên Dashboard Odoo.



**Cơ chế Phân trang (`Pagination`) và Hàng đợi Tải tệp (`Download Queue`)**
Module Base cung cấp dịch vụ Cronjob xử lý phân trang dữ liệu lớn và cơ chế chờ bất đồng bộ khi tải file đính kèm từ máy chủ MISA:

* **Đồng bộ phân trang theo thời gian**: Sử dụng bộ tham số `take` (tối đa 100 bản ghi/lần, mặc định 20), `skip` (vị trí bản ghi), `from` và `to` (`yyyy-MM-dd`), kết hợp cờ `IsFilterInvDate = false` để chỉ quét các hóa đơn có thay đổi (`ModifiedDate`) từ lần đồng bộ gần nhất.
* **Tạo Key tải tệp nén (`POST .../download/zip`)**: Gửi danh sách ID hóa đơn (`LstInvID`), loại tệp `FileType` (`1`: XML+PDF, `2`: PDF, `3`: XML) và cờ `IsInbot` (`true`: đầu vào, `false`: đầu ra) để nhận `Key` tải có hiệu lực đến 24h cuối ngày.
* **Cơ chế trễ khi tải tệp (`GET .../download/{Key}/download`)**: Do máy chủ INBOT cần thời gian nén dữ liệu, Odoo Queue Job phải đặt lịch gọi API tải file sau tối thiểu `(10 x số lượng hóa đơn)` giây hoặc gom tải vào cuối ngày trước 24h, sau đó giải nén chuỗi Base64 và lưu vào `ir.attachment`.



## 3. Phân tích quy trình tại các Module Con (Nghiệp vụ ERP)

### 3.1. Module Con Hóa đơn Đầu vào: Kiểm tra Rủi ro & Tạo Hóa đơn Mua hàng

**Quy tắc Nguồn dữ liệu và Kiểm soát Hóa đơn Trùng**
Khi đồng bộ qua `GET /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/v2/modified` và lấy chi tiết qua `GET .../invoices/{InvoiceId}`, module con cần áp dụng quy tắc quản lý nguồn hóa đơn:

* **Thiết lập chính sách nguồn nhận (`TypeInvoiceReceive`)**: Cấu hình rõ trên Odoo việc chỉ nhận hóa đơn tự động từ CQT (`3`) hay nhận từ nhiều nguồn gồm upload (`1`), email (`2`), nhập tay (`4`), hoặc từ tool (`5`).
* **Bảo toàn dữ liệu XML gốc**: Tuân thủ quy tắc của INBOT là khi người dùng đã tự tải XML lên trước đó và hệ thống kéo dữ liệu trùng từ CQT về, hệ thống không ghi đè file XML đã tải lên mà chỉ cập nhật các trạng thái kiểm tra chưa xử lý.
* **Đối chiếu và tự động tạo Nhà cung cấp (`res.partner`)**: Dựa vào `SellerTaxCode`, hệ thống tìm kiếm nhà cung cấp trên Odoo; nếu chưa tồn tại sẽ tự động khởi tạo mới kèm `SellerName`, `SellerAddress` và `SellerPhoneNumber`.



**Phân tích Trạng thái Kiểm tra (`CheckingResult`) và Cảnh báo Rủi ro Thuế**
Trước khi chuyển hóa đơn từ vùng đệm (Staging) sang chứng từ kế toán (`account.move`), module con phân tích sâu các cờ trạng thái để bảo vệ doanh nghiệp khỏi hóa đơn bất hợp pháp:

* **Kiểm tra trạng thái rủi ro người bán (`SellerRiskStatus` / `RiskStatus`)**: Cảnh báo đỏ và chặn xác nhận tự động nếu nhà cung cấp thuộc diện rủi ro theo công văn danh sách đen của Thuế (`2`) hoặc trạng thái hoạt động 06 - không hoạt động tại địa chỉ đăng ký (`4`).
* **Xác minh chữ ký số và thông báo phát hành (`CheckingResult`)**: Kiểm tra chi tiết đối tượng `SellerSignatureStatus` (chứng thư số hợp lệ, đúng chủ sở hữu, ngày ký trùng ngày hóa đơn), `TaxaxionSignature` (chữ ký số CQT, dữ liệu không bị sửa đổi sau khi ký) và `PublishedInvoiceStatus`.
* **Phân loại tính chất hóa đơn (`TinhChatEnum` & `TThaiHDonEnum`)**: Nhận diện hóa đơn gốc (`1`), thay thế (`2`), điều chỉnh (`3`), hoặc hóa đơn đã bị thay thế/điều chỉnh/xóa bỏ (`4`, `5`, `6`) dựa vào mảng `InvoiceRelateds` và `InfoND123` để tự động liên kết hoặc tạo bút toán điều chỉnh giảm/thay thế trên Odoo.



**Ánh xạ Chi tiết Hóa đơn (`InvoiceInbot` & `Items`) sang `account.move**`
Khi hóa đơn đầu vào đạt trạng thái hợp lệ (`CheckingResultStatusInvoice = 1` và `Status = 2`), hệ thống ánh xạ dữ liệu sang Vendor Bill:

* **Thông tin chung & Tiền tệ**: Ánh xạ `InvoiceNo`, `Series`, `TemplateNo`, `InvoiceDate`, `IssueDate`, `MCCQT` (Mã CQT cấp), tỷ giá `ExchangeRate`, và các trường tổng tiền nguyên tệ (`...CC`) cùng tiền quy đổi.
* **Ánh xạ dòng hàng (`Items`) và Tính chất (`KindND123`)**: Xử lý từng dòng theo `Kind` gồm hàng hóa dịch vụ (`1`), khuyến mãi (`2`), chiết khấu thương mại theo dòng (`3`), ghi chú diễn giải (`4` -> ánh xạ thành `display_type = 'line_note'` trên Odoo) và hàng hóa đặc trưng NĐ70 (`5`).
* **Xử lý Thuế suất (`VatRate`) và Giảm thuế**: Ánh xạ chính xác các mức thuế `0%`, `5%`, `8%`, `10%`, Không chịu thuế (`-1`), Không kê khai nộp thuế (`-2`) và các khoản giảm thuế theo Nghị quyết 43/406 (`TotalTaxReductionAmount43`, `IsTaxReduction`) cùng danh sách phí (`Fees` / `SumTPhi`).



### 3.2. Luồng Đồng bộ Ngược từ Odoo lên MISA INBOT (Two-Way Sync)

Sau khi kế toán xử lý chứng từ trên Odoo 19, module con tự động đẩy trạng thái hạch toán và thanh toán ngược lên MISA INBOT để đồng bộ dữ liệu hai chiều:

1. **Cập nhật trạng thái hạch toán đơn lẻ**: Khi một Vendor Bill được vào sổ (`action_post`), Odoo gọi `POST /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoiceaccountingdateV2` truyền tên kế toán (`Accountant`), ngày hạch toán (`AccountingDate` định dạng `yyyy-MM-dd`), `InvoiceId` và số chứng từ Odoo (`RefNo`).
2. **Cập nhật hạch toán hàng loạt**: Khi kế toán xác nhận nhiều hóa đơn cùng lúc trên giao diện danh sách Odoo, hệ thống gọi `POST .../invoices/invoiceaccountingdatemultiV2` với tham số `InvoiceId` là mảng danh sách ID hóa đơn (`string[]`).
3. **Đồng bộ trạng thái thanh toán (`account.payment` / Reconcile)**: Khi hóa đơn được đối soát thanh toán trên Odoo, hệ thống gọi `POST /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoicepayment` truyền `PaymentDate` (định dạng `yyyy/MM/dd`), `PaymentPair`, số tiền đã trả (`TotalAmountPayment`), số tiền còn nợ (`TotalAmountNotPayment`) và trạng thái `AmountPayment` (`1`: Chưa thanh toán, `2`: Thanh toán toàn phần, `5`: Thanh toán một phần).



### 3.3. Module Con Hóa đơn Đầu ra (`OutInvoices`) & Mở rộng Nghị định 70

* **Đối soát Hóa đơn Đầu ra (`OutInvoices`)**: Sử dụng `GET /meinvoicebot/v1/{subscriberId}/{organizationId}/OutInvoices/modified` và `GET .../OutInvoices/{invoiceID}` để kéo toàn bộ hóa đơn đầu ra (bao gồm các hóa đơn phát hành từ máy tính tiền hoặc phần mềm thứ ba) về đối chiếu số liệu doanh thu và thuế đầu ra trên Odoo.
* **Ánh xạ dữ liệu Nghị định 70 cấp độ Hóa đơn**: Lưu trữ các trường định danh mới gồm Mã số đơn vị có quan hệ với ngân sách (`BuyerMSDVCQHVNS`, `SellerMSDVCQHVNS`), Căn cước công dân (`BuyerNoCitizenIdentityCard`), Số hộ chiếu (`BuyerPassportNumber`), hợp đồng vận chuyển (`NumberAgreement`, `AgreementDate`), hành trình (`From`, `Destination`, `LicensePlate`) và cờ biên lai/chiết khấu (`IsReceiptDecree70`, `IsDiscountDecree70`).
* **Ánh xạ dữ liệu Nghị định 70 cấp độ Dòng hàng (`Items`)**: Phân loại `SpecificProductType` (`1`: Kinh doanh xe máy, ô tô; `2`: Dịch vụ vận chuyển; `3`: Vận chuyển trên nền tảng số/TMĐT) để lưu thông tin Số khung (`VehicleFrameNumber`), Số máy (`VehicleEngineNumber`), Biển kiểm soát (`TransportLicensePlate`) và thông tin người gửi hàng (`ShipperName`, `ShipperTaxCode`, `ShipperIdentifier`, `ShipperAddress`).


