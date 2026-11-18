Kiến trúc tích hợp toàn diện hệ sinh thái MISA trên Odoo 19 được thiết kế theo mô hình 1 Module Base và 2 Module Con nhằm dùng chung hạ tầng kết nối, đồng thời tách biệt rõ luồng phát hành hóa đơn điện tử đầu ra (meInvoice) với luồng xử lý hóa đơn đầu vào và đối soát (meInvoice Bot - INBOT).

## 1. Cấu trúc Phân tầng 3 Module trên Odoo 19

Mô hình phân tách giúp cô lập tầng giao thức mạng khỏi tầng nghiệp vụ kế toán, cho phép doanh nghiệp cài đặt độc lập hoặc kết hợp cả hai chiều hóa đơn:

* **Module Base (dn_misa_connector_base)**: Quản lý cấu hình đa công ty, bộ xác thực kép, hàng đợi tuần tự, kiểm soát Rate Limit, đồng bộ cơ cấu tổ chức và chuẩn hóa xử lý lỗi chung.
* **Module Con 1 (dn_misa_connector_meinvoice)**: Kế thừa phân hệ Kế toán, POS và Kho để phát hành hóa đơn điện tử, biên lai, phiếu xuất kho và điều phối các phương thức ký số.
* **Module Con 2 (dn_misa_connector_meinvoicebot)**: Tích hợp MISA INBOT để tự động đồng bộ hóa đơn đầu vào, kiểm tra rủi ro thuế, hạch toán hai chiều, đối soát đầu ra và tải tệp XML/PDF.



## 2. Module Base (dn_misa_connector_base): Hạ tầng & Giao thức Chung

### 2.1. Quản lý Cấu hình Đa công ty & Cơ chế Xác thực Kép (Dual Authentication)

Module Base mở rộng bảng công ty và thiết lập hệ thống để quản lý đồng thời hai cơ chế xác thực khác nhau của MISA trên cùng một nền tảng:

1. **Cấu hình kết nối tập trung**: Lưu trữ ClientID, ClientSecret, mã số thuế, tài khoản, mật khẩu, DeviceID và hai nhánh Base URL riêng biệt cho meInvoice và INBOT.
2. **Xác thực meInvoice (Luồng phát hành)**: Gọi API lấy Access Token (thời hạn 14 ngày, tách riêng token phát hành và tạo nháp), hỗ trợ xác thực hai lớp 2FA và tự động làm mới khi hết hạn.
3. **Xác thực INBOT 2 bước (Luồng Bot)**: Gọi API ValidateUser để lấy chuỗi CompanyID kèm securetoken, sau đó truyền securetoken vào API GetToken để nhận Bearer JWT Token.
4. **Đồng bộ Tổ chức & Giám sát Gói cước**: Tự động lấy mã thuê bao SubscribersId theo mã số thuế, đồng bộ danh sách phòng ban OrganizationID và cảnh báo số lượng hóa đơn còn lại từ đối tượng Other.



### 2.2. Điều phối Hàng đợi Tuần tự, Rate Limit & Chuẩn hóa Dữ liệu

Toàn bộ các ràng buộc kỹ thuật của máy chủ MISA được kiểm soát tập trung tại tầng ORM của Module Base trước khi trả kết quả về các module con:

* **Xử lý tuần tự theo ký hiệu**: Khóa bản ghi để thực thi vòng lặp gửi request, nhận và lưu phản hồi tuần tự theo từng ký hiệu hóa đơn, giới hạn tối đa 30 hóa đơn/request và 400 dòng/hóa đơn.
* **Kiểm soát Rate Limit**: Giới hạn tối đa 10 lượt gọi mỗi 60 giây đối với các API xác thực và lấy mẫu, tự động tạm dừng và xếp lịch lại khi nhận mã HTTP 429 (TooManyRequests).
* **Phân tích lỗi đa tầng & Auto-Retry**: Kiểm tra tuần tự từ cờ trạng thái chung đến mã lỗi từng hóa đơn; tự động kích hoạt phát hành lại khi gặp lỗi trùng hóa đơn hoặc số hóa đơn không liên tục.
* **Đồng bộ làm tròn thập phân**: Ánh xạ cấu hình độ chính xác thập phân của Odoo vào thẻ OptionUserDefined, đảm bảo nguyên tắc làm tròn từng phần trước khi cộng tổng.



## 3. Module Con 1 (dn_misa_connector_meinvoice): Phát hành Hóa đơn & Biên lai Đầu ra

### 3.1. Đồng bộ Danh mục & Ánh xạ Dữ liệu Nghiệp vụ

Module Con 1 kế thừa trực tiếp chứng từ kế toán, đơn hàng POS và phiếu kho để chuyển đổi dữ liệu ERP sang cấu trúc InvoiceData của MISA:

* **Đồng bộ mẫu & Chứng thư số**: Tải danh sách mẫu hóa đơn để lưu ký hiệu, mẫu số (tự động nhận diện loại hóa đơn qua ký tự thứ 1, 2 và 5) và kiểm tra chứng thư số từ xa HSM/eSign.
* **Ánh xạ thông tin chung & Người mua**: Gắn mã tham chiếu GUID duy nhất theo từng đơn hàng để chống trùng, kiểm tra bắt buộc tên đơn vị và địa chỉ khi người mua có mã số thuế hoặc mã ngân sách.
* **Chi tiết hàng hóa & Tổng hợp thuế**: Phân loại dòng hàng theo 5 tính chất (hàng hóa thường, khuyến mại, chiết khấu, ghi chú không đánh số thứ tự, vận tải) và gom nhóm bảng tổng hợp thuế suất.
* **Mở rộng Phiếu xuất kho & Đặc thù**: Hỗ trợ xuất Phiếu xuất kho điện tử (lệnh điều động, người vận chuyển, kho xuất/nhập) và hóa đơn kinh doanh xe (số khung, số máy, biển số), khách sạn, điện nước.



### 3.2. Điều phối Luồng Ký số & Nghiệp vụ Thay thế / Điều chỉnh

Tùy thuộc vào cấu hình chữ ký số của doanh nghiệp trên Sổ nhật ký, Module Con 1 điều hướng phát hành qua các quy trình xử lý tương ứng:

* **Ký số HSM (SignType = 2) & Máy tính tiền (SignType = 5)**: Gọi trực tiếp API phát hành trong một bước duy nhất lên Cloud MISA và lưu lại mã giao dịch TransactionID để tra cứu.
* **Ký số USB Token (SignType = 1)**: Thực hiện qua 3 bước gồm gọi Cloud MISA tạo XML thô, dùng OWL Component gọi dịch vụ MISA SignedService tại máy trạm để ký số, rồi gửi XML đã ký lên Cloud phát hành.
* **Hóa đơn nháp & Xem trước**: Hỗ trợ đẩy dữ liệu hóa đơn nháp lên cổng web MISA hoặc tạo đường dẫn xem trước bản thể hiện hóa đơn có hiệu lực trong 5 phút.
* **Hóa đơn Thay thế & Điều chỉnh**: Tự động tách ký hiệu hóa đơn gốc thành mẫu số (ký tự đầu) và ký hiệu (phần còn lại), đồng thời bắt buộc truyền mã lý do từ 1 đến 14 theo Phụ lục XVII áp dụng từ 15/12/2026.



## 4. Module Con 2 (dn_misa_connector_meinvoicebot): Xử lý Hóa đơn Đầu vào & Đối soát INBOT

### 4.1. Đồng bộ Hóa đơn Đầu vào, Kiểm tra Rủi ro & Tạo Hóa đơn Mua hàng

Module Con 2 tự động kéo dữ liệu từ dịch vụ INBOT về vùng đệm trên Odoo, thực hiện sàng lọc rủi ro trước khi sinh chứng từ kế toán:

* **Đồng bộ phân trang theo thời gian**: Quét định kỳ danh sách hóa đơn đầu vào có thay đổi (tối đa 100 bản ghi/lần) và lấy chi tiết từng hóa đơn theo mã thuê bao và phòng ban.
* **Kiểm soát nguồn nhận hóa đơn**: Thiết lập quy tắc đồng bộ nhất quán do INBOT giữ nguyên file XML người dùng tự tải lên mà không ghi đè bằng XML kéo từ Cơ quan Thuế khi phát hiện trùng.
* **Kiểm tra hợp lệ & Cảnh báo rủi ro thuế**: Phân tích chi tiết kết quả kiểm tra chữ ký số, thông báo phát hành và chặn tạo chứng từ nếu nhà cung cấp nằm trong danh sách đen rủi ro thuế hoặc ngừng hoạt động.
* **Khởi tạo Hóa đơn Mua hàng**: Tự động tạo nhà cung cấp theo mã số thuế, ánh xạ dòng hàng, thuế suất, tiền giảm thuế Nghị quyết 43, hóa đơn liên quan và bộ trường Nghị định 70 (xe, vận tải, người gửi hàng).



### 4.2. Đồng bộ Ngược Hai chiều, Đối soát Đầu ra & Tải Tệp Nén

Sau khi kế toán xử lý hóa đơn trên Odoo 19, Module Con 2 thực hiện cập nhật ngược trạng thái lên INBOT và lưu trữ hồ sơ gốc:

* **Đồng bộ trạng thái hạch toán**: Khi xác nhận vào sổ hóa đơn mua hàng, Odoo tự động gọi API cập nhật đơn lẻ hoặc hàng loạt để ghi nhận tên kế toán, ngày hạch toán và số chứng từ lên MISA.
* **Đồng bộ trạng thái thanh toán**: Khi thực hiện đối soát thanh toán trên Odoo, hệ thống gọi API cập nhật ngày trả tiền, người thanh toán, số tiền đã trả, số còn nợ và trạng thái thanh toán.
* **Đối soát Hóa đơn Đầu ra**: Kéo danh sách và chi tiết hóa đơn đầu ra từ INBOT về Odoo để đối chiếu chéo doanh thu, phát hiện chênh lệch giữa phần mềm phát hành và sổ cái kế toán.
* **Hàng đợi tải tệp ZIP (XML/PDF)**: Gửi danh sách ID hóa đơn để tạo Key tải (hiệu lực đến 24h cuối ngày), sau đó đặt lịch chờ tối thiểu (10 x số lượng hóa đơn) giây để máy chủ MISA nén xong trước khi tải Base64 về lưu đính kèm.

