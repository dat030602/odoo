# Cổng thanh toán trực tuyến VNPAY - Thanh toán PAY
#### _Đây là document hỗ trợ tìm hiểu và tích hợp Cổng thanh toán trực tuyến VNPAY vào Odoo trên môi trường phát triển_
> _Người sử dụng module có thể sử dụng vào hệ thống thật bằng cách yêu cầu đăng ký hợp tác với VNPay ở đường dẫn [https://vnpay.vn/lien-he](https://vnpay.vn/lien-he) và yêu cầu chúng tôi chỉnh sử lại các đường dẫn trong module để có thể sử dụng trên môi trường thanh toán thật trên thị trường. Nếu người dùng có thể chỉnh sửa mã nguồn thì chỉ cần đăng ký hợp tác với VNPay_

<div>
    <a href='https://www.odoo.com/'>
        <img src="/static/img/2560px-Odoo_logo.svg.png" alt="drawing" style="width:30%;margin-left:7.3333333%;margin-right:7.3333333%"/>
    </a>
    <a href='https://vnpay.vn/'>
        <img src="/static/img//06ncktiwd6dc1694418196384.png" alt="drawing" style="width:30%;margin-left:7.3333333%;margin-right:7.3333333%"/>
    </a>
<div>



## Giới thiệu
VNPay là cổng thanh toán trực tuyến được sử dụng nhiều nhiều hiện nay được tích hợp rất nhiều hình thức thanh toán với hầu hết các ngân hàng đang hoạt động tại Việt Nam như:
- Quét mã QR
- Thẻ ATM và tài khoản ngân hàng
- Thanh toán quốc tế
- Ví điện tử VNPAY

Với VNPay, người dùng luôn có thể thực hiện thanh toán ở bất cứ đâu hỗ trợ thanh toán trực tuyến, đồng thời còn giúp quá trình chuyển đổi số được diễn ra nhanh hơn.

Bằng việc mang internet được phủ sóng hầu như cả nước, thanh toán trực tuyến đang dần tiếp cận đến nhiều loại người dùng từ người trẻ, trung niên, đến người không còn khả năng lao động hay các bạn đang học THPT cũng được phổ cập dùng cổng thanh toán trực tuyến. Vì thế nhu cầu sử dụng thanh toán trực tuyến tăng cao, các trang web thương mại điện tử hay các giao dịch thực hiện trên trang web được yêu cầu tích hợp các cổng thanh toán trực tuyến.

Đó là lý do chúng tôi thực hiện việc tích hợp cổng thanh toán trực tuyến VNPay vào trang web thương mại điện tử của chúng tôi xây dựng trên Odoo.

### * Lợi ích khi sử dụng module tích hợp Cổng thanh toán trực tuyến VNPay vào Odoo
- Thanh toán nhanh chóng
- Giao dịch an toàn
- Đảm bảo quyền lợi người dùng

## Mốc thời gian

![Alt text](/image_document/image-3.png)


## Các bước merchant cần xử lý tích hợp code cài đặt

1. Cài đặt code build **URL thanh toán chuyển hướng**.
1. Cài đặt code **vnp_ReturnUrl URL** thông báo kết quả thanh toán.
1. Cài đặt code **IPN URL** cập nhật kết quả thanh toán. Gửi lại VNPAY URL này khi thiết lập xong.

#### Mô hình kết nối

![Alt text](/image_document/image-4.png)

- **Bước 1**: Khách hàng thực hiện mua hàng trên Website - ứng dụng TMĐT và tiến hành thanh toán trực tuyến cho đơn hàng.
- **Bước 2**: Website - ứng dụng TMĐT thành lập yêu cầu thanh toán dưới dạng URL mang thông tin thanh toán và chuyển hướng khách hàng sang Cổng thanh toán VNPAY bằng URL đó.
Cổng thanh toán VNPAY xử lý yêu cầu thanh toán mà Website - ứng dụng TMĐT gửi sang. Khách hàng tiến hành nhập hoặc xử lý xác thực các thông tin được yêu cầu Thanh toán.
- **Bước 3,4**: Khách hàng nhập thông tin để xác minh tài khoản Ngân hàng của khách hàng và xác thực giao dịch (Nhập thông tin tài khoản, thẻ hoặc quét mã VNPAY-QR).
- **Bước 5**: Giao dịch thành công tại Ngân hàng, VNPAY tiến hành:
Chuyển hướng khách hàng về Website - ứng dụng TMĐT **_(vnp_ReturnUrl)**
Thông báo cho Website - ứng dụng TMĐT kết quả thanh toán của khách hàng thông qua IPN URL. Merchant cập nhật kết quả thanh toán VNPAY gửi tại URL này.
- **Bước 6**: Merchant hiển thị kết quả giao dịch tới khách hàng **_(vnp_ReturnUrl)_**.

## Sơ đồ tuần tự

![Alt text](/image_document/image-5.png)

## Thông tin cấu hình

Các thông tin cần thiết kết nối vào môi trường Sandbox Cổng thanh toán VNPAY:

- Mã TmnCode **vnp_TmnCode** là mã định danh kết nối được khai báo tại hệ thống của VNPAY. Mã định danh tương ứng với tên miền website, ứng dụng, dịch vụ của merchant kết nối vào VNPAY. Mỗi đơn vị có thể có một hoặc nhiều mã TmnCode kết nối.

- URL thanh toán (Sandbox): **https://sandbox.vnpayment.vn/paymentv2/vpcpay.html**

- Secret Key **vnp_HashSecret** Chuỗi bí mật sử dụng để kiểm tra toàn vẹn dữ liệu khi hai hệ thống trao đổi thông tin (checksum).

- URL truy vấn kết quả giao dịch - hoàn tiền (Sandbox): **https://sandbox.vnpayment.vn/merchant_webapi/merchant.html**

Nếu chưa có thông tin cấu hình tích hợp, bạn có thể đăng ký ngay tại đây **http://sandbox.vnpayment.vn/devreg/** Hệ thống sẽ gửi thông tin kết nối về email bạn đăng ký

## Tạo URL Thanh toán

URL thanh toán (Sandbox): https://sandbox.vnpayment.vn/paymentv2/vpcpay.html

Phương thức: GET

URL Thanh toán là địa chỉ URL mang thông tin thanh toán.

Website TMĐT gửi sang Cổng thanh toán VNPAY các thông tin này khi xử lý giao dịch thanh toán trực tuyến cho Khách mua hàng.

URL có dạng:

```
https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_Amount=1806000&vnp_Command=pay&vnp_CreateDate=20210801153333&vnp_CurrCode=VND&vnp_IpAddr=127.0.0.1&vnp_Locale=vn&vnp_OrderInfo=Thanh+toan+don+hang+%3A5&vnp_OrderType=other&vnp_ReturnUrl=https%3A%2F%2Fdomainmerchant.vn%2FReturnUrl&vnp_TmnCode=DEMOV210&vnp_TxnRef=5&vnp_Version=2.1.0&vnp_SecureHash=3e0d61a0c0534b2e36680b3f7277743e8784cc4e1d68fa7d276e79c23be7d6318d338b477910a27992f5057bb1582bd44bd82ae8009ffaf6d141219218625c42
```

Hay dễ nhìn hơn là:

```
https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?
vnp_Amount=1806000
&vnp_Command=pay
&vnp_CreateDate=20210801153333
&vnp_CurrCode=VND
&vnp_IpAddr=127.0.0.1
&vnp_Locale=vn
&vnp_OrderInfo=Thanh+toan+don+hang+%3A5
&vnp_OrderType=other
&vnp_ReturnUrl=https%3A%2F%2Fdomainmerchant.vn%2FReturnUrl
&vnp_TmnCode=DEMOV210
&vnp_TxnRef=5
&vnp_Version=2.1.0
&vnp_SecureHash=3e0d61a0c0534b2e36680b3f7277743e8784cc4e1d68fa7d276e79c23be7d6318d338b477910a27992f5057bb1582bd44bd82ae8009ffaf6d141219218625c42
```

### Danh sách tham số - Thông tin gửi sang VNPAY (vnp_Command=pay)

| Tham số | Kiểu dữ liệu | Bắt buộc/Tùy chọn | Mô tả |
| ------ | ------ | ------ | ------ |
| vnp_Version | Alphanumeric[1,8] | Bắt buộc | Phiên bản api mà merchant kết nối. Phiên bản hiện tại là : 2.1.0 |
| vnp_Command | Alpha[1,16] | Bắt buộc | Mã API sử dụng, mã cho giao dịch thanh toán là: pay |
| vnp_TmnCode | Alphanumeric[8] | Bắt buộc | Mã website của merchant trên hệ thống của VNPAY. Ví dụ: 2QXUI4J4 |
| vnp_Amount	 | Numeric[1,12] | Bắt buộc | Số tiền thanh toán. Số tiền không mang các ký tự phân tách thập phân, phần nghìn, ký tự tiền tệ. Để gửi số tiền thanh toán là 10,000 VND (mười nghìn VNĐ) thì merchant cần nhân thêm 100 lần (khử phần thập phân), sau đó gửi sang VNPAY là: 1000000 |
| vnp_BankCode | Alphanumeric[3,20] | Tùy chọn | Mã phương thức thanh toán, mã loại ngân hàng hoặc ví điện tử thanh toán. <br /> Nếu không gửi sang tham số này, chuyển hướng người dùng sang VNPAY chọn phương thức thanh toán.<br />***Lưu ý:***<br />Các mã loại hình thức thanh toán lựa chọn tại website-ứng dụng của merchant<br />**vnp_BankCode=VNPAYQR** Thanh toán quét mã QR<br />**vnp_BankCode=VNBANK** Thẻ ATM - Tài khoản ngân hàng nội địa **vnp_BankCode=INTCARD** Thẻ thanh toán quốc tế |
| vnp_CreateDate | Numeric[14] | Bắt buộc | Là thời gian phát sinh giao dịch định dạng yyyyMMddHHmmss (Time zone GMT+7) Ví dụ: 20220101103111 |
| vnp_CurrCode | Alpha[3] | Bắt buộc | Đơn vị tiền tệ sử dụng thanh toán. Hiện tại chỉ hỗ trợ VND |
| vnp_IpAddr	 | Alphanumeric[7,45] | Bắt buộc | Địa chỉ IP của khách hàng thực hiện giao dịch. Ví dụ: 13.160.92.202 |
| vnp_Locale | Alpha[2,5] | Bắt buộc | Ngôn ngữ giao diện hiển thị. Hiện tại hỗ trợ Tiếng Việt (vn), Tiếng Anh (en) |
| vnp_OrderInfo | Alphanumeric[1,255] | Bắt buộc | Thông tin mô tả nội dung thanh toán **_quy định dữ liệu gửi sang VNPAY (Tiếng Việt không dấu và không bao gồm các ký tự đặc biệt)_**<br />Ví dụ: Nap tien cho thue bao 0123456789. So tien 100,000 VND |
| vnp_OrderType | Alpha[1,100] | Bắt buộc | Mã danh mục hàng hóa. Mỗi hàng hóa sẽ thuộc một nhóm danh mục do VNPAY quy định. Xem thêm bảng Danh mục hàng hóa |
| vnp_ReturnUrl | Alphanumeric[10,255] | Bắt buộc | URL thông báo kết quả giao dịch khi Khách hàng kết thúc thanh toán. Ví dụ: https://domain.vn/VnPayReturn |
| vnp_ExpireDate | Numeric[14] | Bắt buộc | Thời gian hết hạn thanh toán GMT+7, định dạng: yyyyMMddHHmmss |
| vnp_TxnRef	 | Alphanumeric[1,100] | Bắt buộc | Mã tham chiếu của giao dịch tại hệ thống của merchant. Mã này là duy nhất dùng để phân biệt các đơn hàng gửi sang VNPAY. Không được trùng lặp trong ngày. Ví dụ: 23554 |
| vnp_SecureHash | Alphanumeric[32,256] | Bắt buộc | Mã kiểm tra (checksum) để đảm bảo dữ liệu của giao dịch không bị thay đổi trong quá trình chuyển từ merchant sang VNPAY. Việc tạo ra mã này phụ thuộc vào cấu hình của merchant và phiên bản api sử dụng. Phiên bản hiện tại hỗ trợ SHA256, HMACSHA512. |

### Lưu ý

- Dữ liệu checksum được thành lập dựa trên việc sắp xếp tăng dần của tên tham số (QueryString)
- Số tiền cần thanh toán nhân với 100 để triệt tiêu phần thập phân trước khi gửi sang VNPAY
- vnp_BankCode: Giá trị này tùy chọn.
    - Nếu loại bỏ tham số không gửi sang, khách hàng sẽ chọn phương thức thanh toán, ngân hàng thanh toán tại VNPAY.
    - Nếu thiết lập giá trị (chọn Ngân hàng thanh toán tại Website-ứng dụng TMĐT), Tham khảo bảng mã trả về tại API:
    <br/> **Endpoint:** https://sandbox.vnpayment.vn/qrpayauth/api/merchant/get_bank_list
    <br/> **Http method:** POST
    <br/>**Content-Type:** application/x-www-form-urlencoded
    <br/>**key**:  tmn_code
    <br/>**value**: Theo mã định danh kết nối (vnp_TmnCode) VNPAY cung cấp
- Trong URL thanh toán có tham số vnp_ReturnUrl là URL thông báo kết quả giao dịch khi Khách hàng kết thúc thanh toán

## Return URL được VNPay trả về

Dữ liệu VNPAY trả về bằng cách chuyển hướng trình duyệt web của khách hàng theo địa chỉ web mà Merchant cung cấp khi gửi yêu cầu thanh toán. Trên URL này mang thông tin kết quả thanh toán của khách hàng.

VNPAY trả về kết quả thanh toán URL có dạng:

```
https://{domain}/ReturnUrl?vnp_Amount=1000000&vnp_BankCode=NCB&vnp_BankTranNo=20170829152730&vnp_CardType=ATM&vnp_OrderInfo=Thanh+toan+don+hang+thoi+gian%3A+2017-08-29+15%3A27%3A02&vnp_PayDate=20170829153052&vnp_ResponseCode=00&vnp_TmnCode=2QXUI4J4&vnp_TransactionNo=12996460&vnp_TxnRef=23597&vnp_SecureHashType=SHA256&vnp_SecureHash=20081f0ee1cc6b524e273b6d4050fefd
```

Hay dễ nhìn hơn là:

```
https://{domain}/ReturnUrl?
vnp_Amount=1000000
&vnp_BankCode=NCB
&vnp_BankTranNo=20170829152730
&vnp_CardType=ATM
&vnp_OrderInfo=Thanh+toan+don+hang+thoi+gian%3A+2017-08-29+15%3A27%3A02
&vnp_PayDate=20170829153052
&vnp_ResponseCode=00
&vnp_TmnCode=2QXUI4J4
&vnp_TransactionNo=12996460&vnp_TxnRef=23597
&vnp_SecureHashType=SHA256&vnp_SecureHash=20081f0ee1cc6b524e273b6d4050fefd
```

Trong đó **https://{domain}/ReturnUrl** là URL nhận kết quả hệ thống gửi sang VNPAY theo URL thanh toán qua tham số **vnp_ReturnUrl**

### Danh sách tham số - Thông tin nhận về từ VNPAY (vnp_Command=pay)

| Tham số | Kiểu dữ liệu | Bắt buộc/Tùy chọn | Mô tả |
| ------ | ------ | ------ | ------ |
| vnp_TmnCode | Alphanumeric[8] | Bắt buộc | Mã website của merchant trên hệ thống của VNPAY. Ví dụ: 2QXUI4J4 |
| vnp_Amount	 | Numeric[1,12] | Bắt buộc | Số tiền thanh toán. Số tiền không mang các ký tự phân tách thập phân, phần nghìn, ký tự tiền tệ. Để gửi số tiền thanh toán là 10,000 VND (mười nghìn VNĐ) thì merchant cần nhân thêm 100 lần (khử phần thập phân), sau đó gửi sang VNPAY là: 1000000 |
| vnp_BankCode | Alphanumeric[3,20] | Tùy chọn | Mã phương thức thanh toán, mã loại ngân hàng hoặc ví điện tử thanh toán. <br /> Nếu không gửi sang tham số này, chuyển hướng người dùng sang VNPAY chọn phương thức thanh toán.<br />***Lưu ý:***<br />Các mã loại hình thức thanh toán lựa chọn tại website-ứng dụng của merchant<br />**vnp_BankCode=VNPAYQR** Thanh toán quét mã QR<br />**vnp_BankCode=VNBANK** Thẻ ATM - Tài khoản ngân hàng nội địa **vnp_BankCode=INTCARD** Thẻ thanh toán quốc tế |
| vnp_BankTranNo | Alphanumeric[1,255] | Tùy chọn | Mã giao dịch tại Ngân hàng. Ví dụ: NCB20170829152730 |
| vnp_CardType | Alpha[2,20] | Tùy chọn	 | Loại tài khoản/thẻ khách hàng sử dụng:ATM,QRCODE |
| vnp_PayDate | Numeric[14] | Bắt buộc | Thời gian thanh toán. Định dạng: yyyyMMddHHmmss |
| vnp_OrderInfo | Alphanumeric[1,255] | Bắt buộc | Thông tin mô tả nội dung thanh toán **_quy định dữ liệu gửi sang VNPAY (Tiếng Việt không dấu và không bao gồm các ký tự đặc biệt)_**<br />Ví dụ: Nap tien cho thue bao 0123456789. So tien 100,000 VND |
| vnp_TransactionNo | Numeric[1,15] | Bắt buộc | Mã giao dịch ghi nhận tại hệ thống VNPAY. Ví dụ: 20170829153052 |
| vnp_ResponseCode		 | Numeric[2] | Bắt buộc | Địa chỉ IP của khách hàng thực hiện giao dịch. Ví dụ: 13.160.92.202 |
| vnp_Locale | Numeric[2] | Bắt buộc | Mã phản hồi kết quả thanh toán. Quy định mã trả lời 00 ứng với kết quả Thành công cho tất cả các API. **Tham khảo thêm tại bảng mã lỗi** |
| vnp_TransactionStatus	 | Alpha[1,100] | Bắt buộc | Mã phản hồi kết quả thanh toán. Tình trạng của giao dịch tại Cổng thanh toán VNPAY.<br />-**00**: Giao dịch thanh toán được thực hiện thành công tại VNPAY<br />-**Khác 00**: Giao dịch không thành công tại VNPAY Tham khảo thêm tại bảng mã lỗi |
| vnp_TxnRef	 | Alphanumeric[1,100] | Bắt buộc | Giống mã gửi sang VNPAY khi gửi yêu cầu thanh toán. Ví dụ: 23554 |
| vnp_SecureHashType | Alphanumeric[3,10] | Tùy chọn	 | Loại mã băm sử dụng: SHA256, HmacSHA512 |
| vnp_SecureHash | Alphanumeric[32,256] | Bắt buộc | Mã kiểm tra (checksum) để đảm bảo dữ liệu của giao dịch không bị thay đổi trong quá trình chuyển từ merchant sang VNPAY. Việc tạo ra mã này phụ thuộc vào cấu hình của merchant và phiên bản api sử dụng. Phiên bản hiện tại hỗ trợ SHA256, HMACSHA512. |

### Lưu ý

- URL này chỉ kiểm tra toàn vẹn dữ liệu (checksum) và hiển thị thông báo tới khách hàng
- Không cập nhật kết quả giao dịch tại địa chỉ này

## Bảng mã lỗi của hệ thống thanh toán PAY

### vnp_TransactionStatus

| Mã lỗi | Mô tả |
| ------ | ------ |
| 00 | Giao dịch thành công |
| 01 | Giao dịch chưa hoàn tất |
| 02 | Giao dịch bị lỗi |
| 04 | Giao dịch đảo (Khách hàng đã bị trừ tiền tại Ngân hàng nhưng GD chưa thành công ở VNPAY) |
| 05 | VNPAY đang xử lý giao dịch này (GD hoàn tiền)  |
| 06 | VNPAY đã gửi yêu cầu hoàn tiền sang Ngân hàng (GD hoàn tiền)  |
| 07 | Giao dịch bị nghi ngờ gian lận  |
| 09 | Giao dịch Hoàn trả bị từ chối |

### vnp_ResponseCode VNPAY phản hồi qua IPN và Return URL:

| Mã lỗi | Mô tả |
| ------ | ------ |
| 00 | Giao dịch thành công |
| 07 | Trừ tiền thành công. Giao dịch bị nghi ngờ (liên quan tới lừa đảo, giao dịch bất thường). |
| 09 | Giao dịch không thành công do: Thẻ/Tài khoản của khách hàng chưa đăng ký dịch vụ InternetBanking tại ngân hàng. |
| 10 | Giao dịch không thành công do: Khách hàng xác thực thông tin thẻ/tài khoản không đúng quá 3 lần |
| 11 | Giao dịch không thành công do: Đã hết hạn chờ thanh toán. Xin quý khách vui lòng thực hiện lại giao dịch.  |
| 12 | Giao dịch không thành công do: Thẻ/Tài khoản của khách hàng bị khóa.  |
| 13 | Giao dịch không thành công do Quý khách nhập sai mật khẩu xác thực giao dịch (OTP). Xin quý khách vui lòng thực hiện lại giao dịch.  |
| 24 | Giao dịch không thành công do: Khách hàng hủy giao dịch |
| 51 | Giao dịch không thành công do: Tài khoản của quý khách không đủ số dư để thực hiện giao dịch |
| 65 | Giao dịch không thành công do: Tài khoản của Quý khách đã vượt quá hạn mức giao dịch trong ngày |
| 75 | Ngân hàng thanh toán đang bảo trì |
| 79 | Giao dịch không thành công do: KH nhập sai mật khẩu thanh toán quá số lần quy định. Xin quý khách vui lòng thực hiện lại giao dịch |
| 99 | Các lỗi khác (lỗi còn lại, không có trong danh sách mã lỗi đã liệt kê) |

### Thông tin thẻ test

| # | Thông tin thẻ | Ghi chú |
| ------ | ------ | ------ |
| 1 | Ngân hàng: **NCB**<br/>Số thẻ: **9704198526191432198**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày phát hành: **07/15**<br/>Mật khẩu OTP: **123456** | Thành công |
| 2 | Ngân hàng: **NCB**<br/>Số thẻ: **9704195798459170488**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày phát hành: **07/15**<br/>Mật khẩu OTP: **123456** | Thẻ không đủ số dư |
| 3 | Ngân hàng: **NCB**<br/>Số thẻ: **9704192181368742**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày phát hành: **07/15**<br/>Mật khẩu OTP: **123456** | Thẻ chưa kích hoạt |
| 4 | Ngân hàng: **NCB**<br/>Số thẻ: **9704193370791314**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày phát hành: **07/15**<br/>Mật khẩu OTP: **123456** | Thẻ bị khóa |
| 5 | Ngân hàng: **NCB**<br/>Số thẻ: **9704194841945513**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày phát hành: **07/15**<br/>Mật khẩu OTP: **123456** | Thẻ bị hết hạn |
| 6 | Loại thẻ quốc tế: **VISA (No 3DS)**<br/>Số thẻ: **4456530000001005**<br/>CVC/CVV: **123**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày hết hạn: **12/23**<br/>Email: **test@gmail.com**<br/>Địa chỉ: **22 Lang Ha**<br/> Thành phố: **Ha Noi** | Thành công |
| 7 | Loại thẻ quốc tế: **VISA (3DS)**<br/>Số thẻ: **4456530000001096**<br/>CVC/CVV: **123**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày hết hạn: **12/23**<br/>Email: **test@gmail.com**<br/>Địa chỉ: **22 Lang Ha**<br/>Thành phố: **Ha Noi** | Thành công |
| 8 | Loại thẻ quốc tế: **MasterCard** (No 3DS)<br/>Số thẻ: **5200000000001005**<br/>CVC/CVV: **123**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày hết hạn: **12/23**<br/>Email: **test@gmail.com**<br/>Địa chỉ: **22 Lang Ha**<br/>Thành phố: **Ha Noi** | Thành công |
| 9 | Loại thẻ quốc tế: **MasterCard (3DS)**<br/>Số thẻ: **5200000000001096**<br/>CVC/CVV: **123**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày hết hạn: **12/23**<br/>Email: **test@gmail.com**<br/>Địa chỉ: **22 Lang Ha**<br/>Thành phố: **Ha Noi** | Thành công |
| 10 | Loại thẻ quốc tế: **JCB (No 3DS)**<br/>Số thẻ: **3337000000000008**<br/>CVC/CVV: **123**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày hết hạn: **12/23**<br/>Email: **test@gmail.com**<br/>Địa chỉ: **22 Lang Ha**<br/>Thành phố: **Ha Noi** | Thành công |
| 11 | Loại thẻ quốc tế: **JCB (3DS)**<br/>Số thẻ: **3337000000200004**<br/>CVC/CVV: **123**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày hết hạn: **12/23**<br/>Email: **test@gmail.com**<br/>Địa chỉ: **22 Lang Ha** <br/>Thành phố: **Ha Noi** | Thành công |
| 12 | Loại thẻ ATM nội địa: **Nhóm Bank qua NAPAS**<br/>Số thẻ: **9704000000000018**<br/>Số thẻ: **9704020000000016**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày phát hành: **03/07**<br/>OTP: **otp** | Thành công |
| 13 | Loại thẻ ATM nội địa: **EXIMBANK**<br/>Số thẻ: **9704310005819191**<br/>Tên chủ thẻ: **NGUYEN VAN A**<br/>Ngày hết hạn: **10/26** | Thành công |


## Cài đặt

### Yêu cầu

- Odoo: Version 16

- Postgre: Version 15

- Python3

### Cấu hình

- ***__manifest__.py***

File chứa các cấu hình của module

```sh
{
    'name': 'Payment Provider: VNPay',
    'category': 'Accounting/Payment Providers',
    'depends': ['payment'],
    'data': [
        # File cài đặt import ở đây
    ],
    'application': False,
    'assets': {
        'web.assets_frontend': [
            # File cài đặt import ở đây
        ],
    },
    # File cài đặt import ở đây
}
```

- ***const.py***

File chứa các hằng số mặc định khi thực hiện thanh toán

```sh
ORDER_TYPE
VNPAY_RETURN_URL
VNPAY_WEBHOOK_URL
VNPAY_PAYMENT_URL
VNPAY_API_URL
VNPAY_VERSION
VNPAY_CURRCODE
SUPPORTED_CURRENCIES
```

- ***models/payment_provider.py***


``` sh
# Setup dữ liệu ban đầu của cổng thanh toán như:
#       -support_express_checkout
#       -support_manual_capture
#       -support_tokenization
#       -support_refund
def _compute_feature_support_fields(self):
# Code here ...

# Lắng nghe sự thay đổi của 2 biến vnpay_tmn_code và vnpay_hash_secret_key
# Nếu người dùng không nhập vào mà chuyển trong chế độ Test Mode hay Enable thì sẽ báo lỗi
@api.constrains('state', 'vnpay_tmn_code', 'vnpay_hash_secret_key')
def _check_state_of_connected_account_is_never_test(self):
# Code here ...

# Lấy TMN Code
def _vnpay_get_tmn_code(self):
# Code here ...

# Lấy Hash Secret Key
def _vnpay_get_hash_secret_key(self):
# Code here ...
```

- ***models/payment_transaction.py***

File tạo ra các cột cần người dùng nhập và các hàm khởi tạo để hỗ trợ để cấu hình module thanh toán

```sh
VNPAY_TMN_CODE
VNPAY_HASH_SECRET_KEY

# Nhận yêu cầu thanh toán, sau đó xử lý dữ liệu gửi về thành một JSON gửi cho file /static/src/js/payment_form.js
def _get_specific_processing_values(self, processing_values):
# Code here ...

def _get_tx_from_notification_data(self, provider_code, notification_data):
# Code here ...

def _process_notification_data(self, notification_data):
# Code here ...

# Gửi yêu cầu thanh toán
def _send_payment_request(self):
# Code here ...
```

- ***static/src/js/payment_form.js***
Xử lý JSON từ hàm _get_specific_processing_values của file **models/payment_transaction.py** gửi qua rồi dùng method POST gửi JSON qua _/payment/vnpay/payment-generate-url/_ 

```sh

/** @odoo-module */
/* global VNPay */

import checkoutForm from "payment.checkout_form";
import manageForm from "payment.manage_form";

// import { VNPAY_CONFIG } from "@payment_vnpay/static/src/js/vnpay_config";

const vnpayMixin = {
	/**
	 * Redirect the customer to VNPay hosted payment page.
	 *
	 * @override method from payment.payment_form_mixin
	 * @private
	 * @param {string} code - The code of the payment option
	 * @param {number} paymentOptionId - The id of the payment option handling the transaction
	 * @param {object} processingValues - The processing values of the transaction
	 * @return {undefined}
	 */
	_processRedirectPayment: async function (code, paymentOptionId, processingValues) {
		if (code !== "vnpay") {
			return this._super(...arguments);
		}

		try {
			# Code here...
		} catch (error) {
			console.error("Error: ", error);
		}
		return;
	},
};

checkoutForm.include(vnpayMixin);
manageForm.include(vnpayMixin);

```

- ***static/py/vnpay.py***
Xử lý trung gian các dữ liệu trong file **_models/payment_transaction.py_** và **controllers/main.py** giúp mã nguồn dễ nhìn, dễ hiểu hơn

```sh

# Xử lý thông tin nhận về từ hàm _get_specific_processing_values ở file models/payment_transaction.py thành một JSON
def render_payload(self, base_url, lang):
# Code here ...

# Quá trình lấy URL thanh toán:
# 1. Chuyển JSON thành một chuỗi query string
def generate_query_string_payment(self, query):
# Code here ...

# 2. Hash chuỗi query string
def get_hashValue_payment(self, query, secret_key):
# Code here ...

# 3. Generate 2 dữ liệu trả về trên thành một URL
def generate_url_payment(self, params, secret_key):
# Code here ...

# Khi nhận Return URL từ VNPay sau khi thanh toán, ta tách dữ liệu ra và Hash một lần nữa
# và so sánh chuỗi vừa hash được với SecureValue của Return URL VNPay

def validate_response(self, secret_key, query):
# Code here ...

def __hmacsha512(key, data):
# Code here ...
```

- ***controllers/main.py***

Thực hiện các hành động xử lý, chuyển hướng các dữ liệu gửi đi và nhận về từ VNPay

```sh
payment_code = ''

_payment_status = '/payment/status'
    
_payment_generate_url = '/payment/vnpay/payment-generate-url/'

# Lấy URL đã generate ở file static/py/vnpay.py chuyển hướng sang trang thanh toán của VNPay
@http.route(_payment_generate_url, type='json', auth='public')
def vnpay_payment_generate_url(self, **data):
# Code here

_payment_progess = '/payment/vnpay/payment-return/'

# Xử lý return URL, xác nhận URL hợp lệ, xuất ra trạng thái thanh toán
# và chuyển hướng sang trang /payment/status của odoo
@http.route(_payment_progess)
def vnpay_payment_return(self):
# Code here

```

- ***data/payment_icon_data.xml***: Tạo các icon ngân hàng, ví điện tử mà cổng thanh toán VNPay có thể thực hiện giao dịch để người dùng có thể biết được mình có thể thanh toán không.

- ***data/payment_provider_data.xml***: Thêm các icon đã tạo ở trên vào **Payment Provider** của VNPay.

- ***payment_provider_views.xml***: Giao hiện cấu hình TMN code, Hash Secret Key và một số cấu hình khác

- ***payment_templates.xml***: Hiển thị VNPay được xuất hiện trong giao hiện _Checkout_

### Cài đặt (môi trường phát triển)

Nếu bạn chưa cài đặt Odoo và Docker thì vào [đây](https://github.com/T4Tekco/odoo-payment/tree/main#readme)

#### Odoo

Khi đã khởi động server Odoo thì server sẽ yêu cầu tạo database, cứ nhập đầy đủ thông tin và tạo thôi _(bạn nên tích vào Demo data để dễ dùng thử hơn)_

![Alt text](/image_document/image-1.png)

Sau đó bạn vào Apps trong Odoo, chọn Sales (bán hàng), Website (bạn cứ set up Website theo hướng dẫn của Odoo) để cài đặt module.

Tiếp theo, vào Setting (Thiết lập), lăn chuột đến cuối cùng chọn vào **Activate the developer mode** (hay Kích hoạt chế độ nhà phát triển)

![Alt text](/image_document/image-2.png)

Bạn quay lại Apps (Ứng dụng), tìm kiếm: VNPay (nhớ huỷ đi tìm kiếm App hiện có) và cài đặt module.

Sau khi cài đặt, bạn vào Setting --> Sales --> Online Payment, tích vào rồi Save, rồi quay lại chỗ đó chọn _Payment Provider_.

Vào trang Payment Provider, bạn chọn vào VNPay, nhập vào Hash Secret Key và TMN Code (Bạn tham khảo các tạo Hash Secret Key và TMN Code tại https://sandbox.vnpayment.vn/devreg, tên Website, website đăng ký nhập một website trên mạng là được). Tiếp theo, bạn bật chế độ **Test Mode**

Cuối cùng bạn chỉ cần vào trang web và thực hiện demo thanh toán.

## License

Công ty TNHH T4TEK

**Module Open Source**