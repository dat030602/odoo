Đọc kỹ 2 tài liệu đặc tả OpenAPI đính kèm (`dn_misa_connector_meinvoice_doc.md` và `dn_misa_connector_meinvoicebot_doc.md`) (mô tả description_*.md) và file summary.md là mô tả chung và triển khai hệ thống tích hợp MISA trên Odoo 19 theo kiến trúc **Decoupled Document Models** (Tách bảng độc lập):

- **Nguyên tắc cốt lõi**: Tuyệt đối KHÔNG nhồi nhét các trường dữ liệu đặc thù của MISA vào bảng `account.move`, `account.move.line`, `pos.order` hay `stock.picking`. Toàn bộ dữ liệu nghiệp vụ, trạng thái, JSON/XML, kết quả kiểm tra rủi ro và trường mở rộng (NĐ123, NĐ70, Phụ lục XVII, PXK) phải được lưu trên các **Model trung gian độc lập**. Các chứng từ gốc của Odoo chỉ giữ trường liên kết (`Many2one` / `One2many`) sang các model này.

---

# 1. KIẾN TRÚC PHÂN TẦNG 3 MODULE & SƠ ĐỒ MODEL

1. **`dn_misa_connector_base`**:
   - Hạ tầng kết nối, cấu hình đa công ty (`res.company`), xác thực kép (meInvoice & INBOT), đồng bộ cơ cấu tổ chức (`misa.organization`), kiểm soát Rate Limit, hàng đợi tuần tự (`misa.queue.job`) và lịch sử gọi API (`misa.api.log`).
2. **`dn_misa_connector_meinvoice`** (Phát hành Hóa đơn/Biên lai/PXK đầu ra):
   - Model trung tâm: **`misa.einvoice.document`** (Header hóa đơn phát hành), **`misa.einvoice.document.line`** (Chi tiết dòng hàng `OriginalInvoiceDetail`), **`misa.einvoice.tax.line`** (Tổng hợp thuế `TaxRateInfo`).
   - Liên kết mỏng (Thin Link): `account.move`, `pos.order`, `stock.picking` chỉ khai báo `misa_einvoice_ids = fields.One2many('misa.einvoice.document', ...)` và `misa_einvoice_id = fields.Many2one('misa.einvoice.document')` (chứng từ MISA hiện hành).
3. **`dn_misa_connector_meinvoicebot`** (Đồng bộ Hóa đơn Đầu vào/Đầu ra INBOT):
   - Model trung tâm: **`misa.inbot.document`** (Lưu toàn bộ dữ liệu `InvoiceInbot`, `CheckingResult`, `InfoND123`, Nghị định 70), **`misa.inbot.document.line`** (`Items`), **`misa.inbot.related.line`** (`InvoiceRelateds`), **`misa.inbot.fee.line`** (`Fees`).
   - Liên kết mỏng (Thin Link): `account.move` chỉ khai báo `misa_inbot_id = fields.Many2one('misa.inbot.document')`. Mọi thao tác tạo hóa đơn mua hàng, đối soát hoặc đẩy ngược trạng thái hạch toán/thanh toán đều thông qua liên kết này.

---

# 2. PHÂN TÍCH QUY TRÌNH MODULE BASE (`dn_misa_connector_base`)

### 2.1. Quản lý Cấu hình & Luồng Xác thực Kép (Dual Authentication)
- **Thông tin cấu hình (`res.company`)**: Lưu `ClientID`, `ClientSecret`, `taxcode`, `username`, `password`, `DeviceID` và 2 nhánh Base URL độc lập.
- **Nhánh 1 - Xác thực meInvoice (`https://developer.misa.vn/apis/itg/meinvoice/`)**:
  + Gọi `POST /invoice/token` (Headers: `ClientID`, `ClientSecret`; Body: `taxcode`, `username`, `password`) để lấy Bearer Token (thời hạn 14 ngày, lưu cache tái sử dụng). Tách biệt hàm lấy Token của luồng phát hành hóa đơn và luồng tạo hóa đơn nháp.
  + Xác thực 2 lớp (2FA): Khi tài khoản bật 2FA, lấy `CustomData.Id` từ `/invoice/token` làm `UserID`, gọi `POST /invoice/2fa` với `DeviceID`, `Remember = true` và `Code` (OTP).
  + Làm mới Token: Gọi `POST /invoice/token/refresh` truyền chuỗi `tokenExpriedDate` khi token hết hạn.
- **Nhánh 2 - Xác thực INBOT 2 bước (`https://developer.misa.vn/apis`)**:
  + Bước 1 (`ValidateUser`): Gọi `POST /meinvoicebot/v1/validateuser` (Headers: `ClientID`, `CompanyTaxCode`, `UserName`; Body: `{"PassWord": "..."}`). Phản hồi trong `Data` có dạng `{CompanyID};{securetoken}`. Tách lấy `securetoken`.
  + Bước 2 (`GetToken`): Gọi `POST /meinvoicebot/v1/auth/jwttoken` (Headers: `ClientID`, `companytaxcode`, `username`, `securetoken`) để nhận `AccessToken` (JWT).
  + Mọi request INBOT sau đó đính kèm Header `Authorization: Bearer {jwt_token}` và `ClientID`. Khi gặp mã lỗi `TokenExpiredCode`, `InvalidTokenCode`, hoặc `INVALIDTOKEN`, tự động thực hiện lại luồng xác thực từ Bước 1.

### 2.2. Đồng bộ Cơ cấu Tổ chức (`misa.organization`) & Giám sát Tài nguyên
- **Lấy mã thuê bao (`SubscribersId`)**: Gọi `GET /meinvoicebot/v1/subscribers/code/{taxcode}` (hỗ trợ cả MST chi nhánh) để lấy trường `Id` lưu làm `SubscribersId` (CompanyID).
- **Lấy danh sách tổ chức/phòng ban (`OrganizationID`)**: Gọi `GET /meinvoicebot/v1/{SubscribersId}/organizations` lưu vào model `misa.organization` để phân quyền truy xuất hóa đơn.
- **Theo dõi tài nguyên (`Other`)**: Trích xuất đối tượng `Other` từ API danh sách hóa đơn INBOT để lưu cảnh báo hạn mức: `ProductPackCode`, `StartDate`, `ExpiredDate`, `NumberOfInvoice`, `NumberInvUsed`, `NumberInvStill`, `Status` (`0,1`: chính thức, `2`: dùng thử).

### 2.3. Điều phối Hàng đợi Tuần tự (`misa.queue.job`), Rate Limit & Xử lý Response
- **Xử lý tuần tự theo ký hiệu hóa đơn (`InvSeries`)**: Bắt buộc khóa và xử lý tuần tự cho mỗi ký hiệu hóa đơn theo vòng lặp: `[Gửi request -> Nhận response -> Xử lý response -> Lưu lại thông tin vào misa.einvoice.document]`.
- **Giới hạn lô (Batch Limit) & Rate Limit**:
  + Phát hành tối đa 30 bản ghi `misa.einvoice.document`/request, tối đa 400 dòng `misa.einvoice.document.line`/hóa đơn.
  + Giới hạn 10 requests/60 giây cho các API xác thực và lấy mẫu. Bắt HTTP Status `429` (`ErrorCode = "TooManyRequests"`) để tạm dừng và xếp lịch gọi lại.
- **Thứ tự kiểm tra Response & Auto-Retry**:
  + Kiểm tra tuần tự: `Success` -> `ErrorCode` cấp request -> `publishInvoiceResult[i].ErrorCode` (hoặc `CreateInvoiceResult` khi `SignType = 1`).
  + Hóa đơn chỉ phát hành thành công khi `Success = true` và `publishInvoiceResult[i].ErrorCode` rỗng; cập nhật `TransactionID`, `InvNo`, `InvDate` vào `misa.einvoice.document`.
  + Khi chạy luồng tự động (auto), nếu gặp mã lỗi `InvoiceDuplicated` hoặc `InvoiceNumberNotCotinuous` thì tự động retry phát hành lại.
- **Quy tắc số thập phân (`OptionUserDefined`)**: Định nghĩa số chữ số thập phân trong tag `OptionUserDefined` khớp với cấu hình làm tròn; bắt buộc làm tròn từng thành phần trên `misa.einvoice.document.line` trước rồi mới cộng tổng lên `misa.einvoice.document`.

---

# 3. PHÂN TÍCH QUY TRÌNH MODULE CON 1 (`dn_misa_connector_meinvoice`)

### 3.1. Đồng bộ Danh mục Mẫu Hóa đơn (`misa.invoice.template`) & Chứng thư số (`misa.certificate`)
- **Danh sách mẫu (`GET /invoice/templates`)**: Truyền `invoiceWithCode`, `ticket`, `year`, `haveTempOld` để lưu `IPTemplateID`, `TemplateName`, `InvSeries`, `InvTemplateNo`, `Inactive`, `IsSendSummary`, `IsPetrol`, `IsMoreVATRate`.
- **Quy tắc bóc tách ký hiệu `InvSeries` (VD: `1C25MYY`)**:
  + Ký tự thứ 1 (Loại hóa đơn): `1` = GTGT, `2` = Bán hàng, `5` = Vé điện tử, `6` = Phiếu xuất kho.
  + Ký tự thứ 2 (Mã CQT): `C` = Có mã, `K` = Không mã.
  + Ký tự thứ 5 (Hình thức): `T` = Hóa đơn thường, `M` = Hóa đơn từ máy tính tiền (MTT).
- **Kiểm tra Chứng thư số (`GET /invoice/get-certificates`)**: Kiểm tra danh sách chứng thư số HSM/eSign nâng cao; nếu trả về rỗng thì chặn phát hành với `SignType = 2`.

### 3.2. Thiết kế Bảng Độc lập `misa.einvoice.document` & Cơ chế Liên kết Chứng từ Gốc
- **Liên kết với chứng từ Odoo**:
  + Bảng `misa.einvoice.document` chứa các trường khóa ngoại: `move_id` (`Many2one('account.move')`), `pos_order_id` (`Many2one('pos.order')`), `picking_id` (`Many2one('stock.picking')`), và `origin_einvoice_id` (`Many2one('misa.einvoice.document')` - dùng khi thay thế/điều chỉnh).
  + Trên `account.move`, `pos.order`, `stock.picking`: Chỉ thêm trường liên kết `misa_einvoice_id` (bản ghi MISA hiệu lực hiện tại), `misa_einvoice_ids` (lịch sử các lần phát hành/thay thế) và nút bấm "Tạo/Phát hành HĐĐT MISA" để sinh bản ghi sang `misa.einvoice.document`.
- **Ánh xạ dữ liệu từ chứng từ gốc sang `misa.einvoice.document` (`InvoiceData`)**:
  + Thông tin chung: `RefID` (GUID duy nhất chống trùng), `InvSeries`, `InvTemplateNo`, `InvDate` (`yyyy-MM-dd`), `CurrencyCode` (mặc định `VND`), `ExchangeRate` (mặc định `1`), `PaymentMethodName` (mặc định `TM/CK`), `IsInvoiceSummary`, `IsSendEmail`, `ReceiverName`, `ReceiverEmail` (phân tách `;`, tối đa 255 ký tự).
  + Thông tin người mua: `BuyerCode`, `BuyerLegalName`, `BuyerTaxCode`, `BuyerAddress`, `BuyerFullName`, `BuyerPhoneNumber`, `BuyerEmail` (chỉ 1 email), `BuyerBankAccount`, `BuyerBankName`, `BuyerIDNumber` (12 chữ số), `BuyerPassport` (20 ký tự), `BuyerBudgetCode` (7 ký tự). Ràng buộc: nếu có `BuyerTaxCode` hoặc `BuyerBudgetCode` thì bắt buộc có `BuyerLegalName` và `BuyerAddress`.
- **Chi tiết dòng hàng trên `misa.einvoice.document.line` (`OriginalInvoiceDetail`)**:
  + `ItemType` (int, bắt buộc): `1` = Hàng hóa thường, `2` = Khuyến mại, `3` = Chiết khấu thương mại, `4` = Ghi chú/diễn giải, `5` = Hàng hóa đặc thù vận tải.
  + `LineNumber` (bắt đầu từ 1); `SortOrder` (bắt đầu từ 1, nhưng truyền `null` với `ItemType = 3` hoặc `ItemType = 4`).
  + Tiền hàng: `Quantity`, `UnitPrice`, `AmountOC`, `Amount`, `DiscountRate`, `DiscountAmountOC`, `DiscountAmount`, `AmountWithoutVATOC`, `VATRateName`, `VATAmountOC`.
- **Tổng tiền trên `misa.einvoice.document` & Tổng hợp thuế `misa.einvoice.tax.line` (`TaxRateInfo`)**:
  + `TotalSaleAmountOC = Sum(AmountOC, ItemType=1) - Sum(AmountOC, ItemType=3)`
  + `TotalDiscountAmountOC = Sum(DiscountAmountOC, ItemType=1) + Sum(AmountOC, ItemType=3)`
  + `TotalAmountWithoutVATOC = Sum(AmountWithoutVATOC, ItemType=1) - Sum(AmountWithoutVATOC, ItemType=3)`
  + `TotalVATAmountOC = Sum(VATAmountOC, ItemType=1) - Sum(VATAmountOC, ItemType=3)`
  + `TotalAmountOC = TotalAmountWithoutVATOC + TotalVATAmountOC`
  + Các trường quy đổi = trường `OC` * `ExchangeRate`. `TaxRateInfo` bắt buộc đối với hóa đơn GTGT.

### 3.3. Quy trình Hóa đơn Thay thế & Điều chỉnh trên `misa.einvoice.document` (Phụ lục XVII từ 15/12/2026)
- Khi tạo bản ghi `misa.einvoice.document` mới để thay thế (`ReferenceType = 1`) hoặc điều chỉnh (`ReferenceType = 2`) cho một `origin_einvoice_id` (hoặc từ Credit Note / Hóa đơn mới trên `account.move`):
  + Tự động lấy thông tin từ `origin_einvoice_id` để điền: `OrgInvoiceType = 1`, `OrgInvNo`, `OrgInvDate`, `InvoiceNote`.
  + Tự động tách ký hiệu gốc (VD: `1C24MAA`) thành `OrgInvTemplateNo = "1"` (ký tự đầu) và `OrgInvSeries = "C24MAA"` (phần còn lại).
  + **`AdjustReplaceReasonCode` (int, bắt buộc khi `ReferenceType` là 1 hoặc 2)**: Chọn mã lý do từ `1` đến `14` theo danh mục Phụ lục XVII Thông tư 91 (ghi vào thẻ XML `<LDDCTThe>` thuộc `<TTHDLQuan>`). Mã `13` dùng cho hóa đơn lập sai thường, mã `14` dùng cho thay thế hóa đơn điện tử từ máy tính tiền lập sai.

### 3.4. Điều phối 3 Luồng Ký số & Các Trường Đặc thù trên `misa.einvoice.document`
- **Luồng 1 - Ký số HSM (`SignType = 2`) & Máy tính tiền (`SignType = 5`)**: Gọi `POST /invoice/publishing` trực tiếp từ `misa.einvoice.document`.
- **Luồng 2 - Ký số USB Token/File mềm (`SignType = 1`)**: Thực hiện 3 bước trên `misa.einvoice.document`:
  1. Gọi API Cloud MISA tạo XML thô và lưu vào trường `raw_xml` (`CreateInvoiceResult`).
  2. Giao diện gọi API Local (`MISA SignedService` dưới máy trạm) để ký số vào `raw_xml` và lưu vào `signed_xml`.
  3. Gọi API Cloud MISA phát hành `signed_xml` lên MISA và Cơ quan Thuế.
- **Luồng 3 - Xem trước & Hóa đơn nháp**: Gọi `POST /invoice/unpublishview` lưu link xem trước (hiệu lực 5 phút) hoặc đẩy hóa đơn nháp lên `app3.meinvoice.vn`.
- **Các nhóm trường mở rộng lưu trực tiếp trên `misa.einvoice.document` & `misa.einvoice.document.line`**:
  + Nhóm Phiếu xuất kho (khi sinh từ `stock.picking`): `StockOutLegalName`, `StockOutTaxCode`, `StockOutAddress`, `StockOutFullName`, `InternalCommand`, `InternalCommandNo`, `InternalCommandOwner`, `InternalCommandDate`, `TransporterName`, `Transport`, `TransportContractCode`, `StockInLegalName`, `StockInTaxCode`, `StockInFullName`, `StockInAddress`, `ContractCode`, `ContractDate`, `JournalMemo`, `StockTotalAmountOC`, `StockTotalAmount`.
  + Nhóm Kinh doanh xe & Lô/Hạn dùng (trên `misa.einvoice.document.line`): `ChassisNumber`, `EngineNumber`, `LicensePlate` (khi `ItemType = 5`), `LotNo`, `ExpiryDate`.
  + Nhóm Khách sạn / Điện nước: `CheckIn`, `CheckOut`, `RoomNo`, `ServiceFeeRate`, `ExciseTaxRate`, `PeriodName`, `OldIndex`, `NewIndex`, `ClockInfos`.

---

# 4. PHÂN TÍCH QUY TRÌNH MODULE CON 2 (`dn_misa_connector_meinvoicebot`)

### 4.1. Thiết kế Bảng Độc lập `misa.inbot.document` & Đồng bộ Phân trang
- **Cấu trúc bảng độc lập**:
  + Toàn bộ hóa đơn đầu vào (`is_inbot = True`) và hóa đơn đầu ra (`is_inbot = False`) kéo từ INBOT về được lưu hoàn toàn tại bảng `misa.inbot.document` và các bảng chi tiết con (`misa.inbot.document.line`, `misa.inbot.related.line`, `misa.inbot.fee.line`).
  + Liên kết với `account.move`: Bảng `misa.inbot.document` có trường `move_id = fields.Many2one('account.move')`, và bảng `account.move` có trường `misa_inbot_id = fields.Many2one('misa.inbot.document')`.
- **API Đồng bộ danh sách & chi tiết**:
  + Đầu vào: `GET /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/v2/modified` và chi tiết `GET .../invoices/{InvoiceId}`.
  + Đầu ra: `GET /meinvoicebot/v1/{subscriberId}/{organizationId}/OutInvoices/modified` và chi tiết `GET .../OutInvoices/{invoiceID}`.
  + Tham số phân trang: `take` (tối đa 100, mặc định 20), `skip`, `from` (`yyyy-MM-dd`), `to` (`yyyy-MM-dd`), `IsFilterInvDate` (`true`: theo ngày hóa đơn, `false`: theo `ModifiedDate`).
- **Quy tắc xử lý trùng nguồn hóa đơn trên `misa.inbot.document`**: Nếu bản ghi có nguồn do user tự upload XML (`TypeInvoiceReceive = 1`), khi đồng bộ dữ liệu từ CQT về phát hiện trùng thì KHÔNG ghi đè XML của user đã upload, chỉ cập nhật các trạng thái kiểm tra chưa xử lý.

### 4.2. Phân tích Kết quả Kiểm tra (`CheckingResult`) & Cảnh báo Rủi ro trên `misa.inbot.document`
- **Đánh giá rủi ro người bán (`SellerRiskStatus` / `RiskStatus`)**:
  + `1`: Không có rủi ro.
  + `2`: Rủi ro theo công văn thuế thông báo danh sách đen -> Chặn sinh `account.move` tự động.
  + `3`: Chưa đủ thông tin kết luận.
  + `4`: Rủi ro theo trạng thái hoạt động 06 (không hoạt động tại địa chỉ đăng ký) -> Chặn sinh `account.move` tự động.
- **Lưu trữ & hiển thị đối tượng `CheckingResult`**: Tách các trường trạng thái kiểm tra gồm `SellerStatus`, `BuyerStatus`, `PublishedInvoiceStatus`, `SellerSignatureStatus`, `TaxaxionSignature` ngay trên `misa.inbot.document`.
- **Trạng thái & Tính chất Hóa đơn**:
  + Lưu đầy đủ bộ Enum: `InvoiceInfoStatusFlags`, `InvoiceCreatorFlags`, `CheckingStatusFlags`, `InvoiceCodeStatus`, `TypeInvoiceReceive`, `TThaiXuLyEnum`, `TinhChatEnum` (`1` Gốc, `2` Thay thế, `3` Điều chỉnh), `TThaiHDonEnum` (`1`..`7`).
  + Lưu danh sách hóa đơn liên quan vào bảng `misa.inbot.related.line` (`InvoiceRelateds` & `InfoND123`) để tự động tra cứu bản ghi `misa.inbot.document` gốc và `account.move` gốc tương ứng.

### 4.3. Lưu trữ Trường Nghị định 70 trên `misa.inbot.document` & Khởi tạo `account.move`
- **Toàn bộ trường đặc thù lưu tại `misa.inbot.document` và `misa.inbot.document.line`**:
  + Header (`InvoiceInbot` + NĐ70): `TransId`, `InvoiceId`, `SubscriberId`, `OrgId`, `SellerTaxCode`, `SellerName`, `SellerAddress`, `BuyerTaxCode`, `BuyerName`, `BuyerAddress`, `TemplateNo`, `Series`, `InvoiceNo`, `InvoiceDate`, `IssueDate`, `MCCQT`, `PaymentMethod`, `CcyCode`, `ExchangeRate`, bộ trường tổng tiền quy đổi và nguyên tệ (`...CC`), tiền giảm thuế NQ43 (`TotalTaxReductionAmount43`), `BuyerMSDVCQHVNS`, `SellerMSDVCQHVNS`, `BuyerNoCitizenIdentityCard`, `BuyerPassportNumber`, `NumberAgreement`, `AgreementDate`, `LicensePlate`, `From`, `Destination`, `IsReceiptDecree70`, `IsDiscountDecree70`.
  + Dòng hàng (`misa.inbot.document.line` - `Items` + NĐ70): `ItemId`, `LineNumber`, `ItemName`, `UnitName`, `Quantity`, `UnitPrice`, `AmountWithoutVat`, `VatRate` (`0`, `5`, `8`, `10`, `-1`, `-2`, `-3`), `VatAmount`, `DiscountAmount`, `Amount`, `Kind` (`0`..`5`), `SpecificProductType` (`0`..`3`), `VehicleFrameNumber`, `VehicleEngineNumber`, `TransportLicensePlate`, `ShipperName`, `ShipperAddress`, `ShipperTaxCode`, `ShipperIdentifier`.
- **Hàm sinh chứng từ kế toán (`action_create_account_move` từ `misa.inbot.document`)**:
  + Chỉ truyền các trường kế toán chuẩn sang `account.move` và `account.move.line` (Partner tìm/tạo theo `SellerTaxCode`, `ref = InvoiceNo`, `invoice_date`, tiền tệ, dòng sản phẩm/ghi chú, thuế, chiết khấu) rồi gán `move.misa_inbot_id = self.id` và `self.move_id = move.id`.

### 4.4. Đồng bộ Ngược 2 Chiều (Từ Sự kiện `account.move` qua `misa.inbot.document`) & Tải Tệp Nén
- **Trigger cập nhật thông tin hạch toán**:
  + Khi `account.move` (có gắn `misa_inbot_id`) được vào sổ (`action_post`), kích hoạt hàm trên `misa.inbot.document` gọi `POST /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoiceaccountingdateV2` truyền `Accountant` (tên kế toán), `AccountingDate` (`yyyy-MM-dd`), `InvoiceId`, `RefNo` (số chứng từ `account.move.name`).
  + Hỗ trợ chọn nhiều bản ghi `misa.inbot.document` hoặc `account.move` để gọi API cập nhật hàng loạt `POST .../invoices/invoiceaccountingdatemultiV2` (`InvoiceId` là mảng `string[]`).
- **Trigger cập nhật thông tin thanh toán**:
  + Khi `account.move` thay đổi trạng thái thanh toán (`payment_state` / `amount_residual`), kích hoạt hàm trên `misa.inbot.document` gọi `POST /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoicepayment` truyền `InvoiceId`, `PaymentDate` (định dạng `yyyy/MM/dd`), `PaymentPair`, `TotalAmountPayment`, `TotalAmountNotPayment`, `NumberPaymentNext`, và `AmountPayment` (`0`: Không thiết lập, `1`: Chưa thanh toán, `2`: Thanh toán toàn phần, `3`: Quá hạn, `4`: Đến hạn, `5`: Thanh toán một phần).
- **Hàng đợi tải tệp ZIP (`xml`/`pdf`) gắn vào `misa.inbot.document`**:
  + Bước 1 - Tạo Key tải: Gọi `POST /meinvoicebot/v1/{SubscribersId}/{organizationId}/download/zip` với `FileType` (`1`: xml+pdf, `2`: pdf, `3`: xml), `LstInvID`, `IsInbot` để lưu `Key` download (hiệu lực đến 24h cuối ngày).
  + Bước 2 - Tải tệp theo cơ chế trễ: Đặt lịch gọi `GET /meinvoicebot/v1/{SubscribersId}/{organizationId}/download/{Key}/download` sau tối thiểu `(10 x số hóa đơn tải)` giây (hoặc gom tải cuối ngày trước 24h), giải nén chuỗi Base64 và lưu file XML/PDF vào `misa.inbot.document` (đồng thời có thể chia sẻ `ir.attachment` sang `move_id` nếu đã tạo hóa đơn kế toán).
