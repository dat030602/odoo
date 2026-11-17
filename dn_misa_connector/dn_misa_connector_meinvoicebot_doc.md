# Tài liệu MISA meInvoice Bot (Xử lý hóa đơn đầu vào & đầu ra) - OpenAPI Specification

> Tài liệu tổng hợp toàn diện chi tiết từ MISA Open API Developer Portal (`developer.misa.vn`).

## MỤC LỤC & TỔNG QUAN HỆ THỐNG

### Overview

## Tài liệu tích hợp hóa đơn đầu vào MISA INBOT




Tài liệu này được soạn thảo nhằm cung cấp hướng dẫn chi tiết cho các nhà phát triển ứng dụng về cách tích hợp hệ thống hóa đơn đầu vào (INBOT) của MISA vào các ứng dụng hiện có. Thông qua việc thực hiện tích hợp này, doanh nghiệp có thể tự động hóa quá trình truy xuất và quản lý dữ liệu hóa đơn đầu vào, đảm bảo tuân thủ các quy định của pháp luật Việt Nam.

Tài liệu bao gồm các nội dung từ cấu trúc API, phương thức xác thực, cách gửi và nhận dữ liệu, đến việc xử lý các tình huống phổ biến trong quá trình triển khai tích hợp.




**Base URL: **<strong style="color: rgb(41, 82, 186);">https//developer.misa.vn/apis**

### What's New?

## What's New




- Phát hành lần đầu phiên bản V1.0.0

- Hỗ trợ luồng xác thực 2 bước: ValidateUser → GetToken

- API lấy danh sách hóa đơn đầu ra đã sửa đổi có phân trang

### Changelog

## Change Log


<table>
<thead><tr><th>Version</th><th>Ngày</th><th>Thay đổi</th></tr></thead>
<tbody>
<tr><td>V1.0.0</td><td>2026-07-03</td><td>Phát hành lần đầu</td></tr>
</tbody>
</table>

### Authentication

## Xác thực

Hệ thống INBOT (hóa đơn đầu vào) sử dụng cơ chế xác thực 2 bước:


- **ValidateUser** — Gửi ClientID, CompanyTaxCode, UserName (headers) + PassWord (body JSON) để nhận `securetoken`.
- **GetToken** — Gửi ClientID, companytaxcode, username, securetoken (headers) để nhận JWT token trong response.

Sau khi có JWT token, tất cả các request tiếp theo phải gửi kèm header:

<pre data-language="plain">
Authorization: Bearer {jwt_token}
ClientID: {your_client_id}
</pre>**Lưu ý:** Token có thời hạn sử dụng. Khi token hết hạn, cần thực hiện lại luồng xác thực từ bước 1.

## HƯỚNG DẪN NGHIỆP VỤ & LUỒNG XỬ LÝ (USE CASES)

### Use Case: Lấy danh sách hóa đơn đầu vào

- **ID**: `019f7d3d-f991-794e-9199-b9a846cdf946`



## CHI TIẾT DANH SÁCH API ENDPOINTS

### Nhóm: Authen

- **Group ID**: `f67d6cb3-768d-11f1-9f48-005056b30128`


#### [POST] /meinvoicebot/v1/validateuser - Xác thực người dùng

- **Endpoint ID**: `f6b9963e-768d-11f1-9f48-005056b30128`
- **Phương thức**: `POST`
- **Đường dẫn**: `/meinvoicebot/v1/validateuser`
- **Tóm tắt**: Xác thực người dùng

**Mô tả:**
API xác thực thông tin người dùng thông qua mã số thuế, tài khoản và mật khẩu. Trả về **securetoken** dùng để gọi API GetToken ở bước tiếp theo.

**Headers bắt buộc:**


- `ClientID` — ID được cấp bởi MISA khi đăng ký tích hợp
- `CompanyTaxCode` — Mã số thuế của đơn vị
- `UserName` — Tên tài khoản đăng nhập (email/SĐT)

**Body:** JSON chứa `PassWord` — mật khẩu tài khoản.

**Response:** Trả về securetoken trong field `Data` dạng `{CompanyID};{securetoken}`. Securetoken này dùng truyền trong header `securetoken` cho API `/auth/jwttoken`.

**Luồng nghiệp vụ:** Đây là bước 1 trong luồng xác thực: **ValidateUser → GetToken** → các API nghiệp vụ.

##### 1. Headers
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `ClientID` | `string` | Có | ID được cấp bởi MISA khi đăng ký tích hợp |
| `CompanyTaxCode` | `string` | Có | Mã số thuế của đơn vị |
| `UserName` | `string` | Có | Tên tài khoản đăng nhập (email hoặc SĐT) |

##### 3. Request Body Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `PassWord` | `string` | Có | Mật khẩu tài khoản |

##### Request Body Example
```json
{
    "PassWord": "12345678@Abc"
}
```

##### 4. Response Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Success` | `bool` | Không | Trạng thái request: true = thành công, false = thất bại |
| `ErrorCode` | `string` | Không | Mã lỗi nếu có. Rỗng = thành công |
| `Errors` | `string[]` | Không | Danh sách lỗi trả về |
| `Data` | `string` | Không | Chuỗi token dạng {CompanyID};{securetoken}. Securetoken dùng truyền trong header securetoken cho API /auth/jwttoken |
| `CustomData` | `string` | Không | Thông tin CustomData |

##### Mã lỗi thường gặp
## Mã lỗi thường gặp


Dưới đây là danh sách các mã lỗi thường gặp khi gọi API `/inbot/v1/validateuser`:


<table>
<thead><tr><th>Mã lỗi</th><th>Mô tả</th></tr></thead>
<tbody>
<tr><td>**TAXCODENOTEXIST**</td><td>Mã số thuế chưa tồn tại</td></tr>
<tr><td>**INVALIDTOKEN**</td><td>Mã bảo mật không hợp lệ</td></tr>
<tr><td>**USER_NOT_EXIST**</td><td>Người dùng không tồn tại</td></tr>
<tr><td>**MisaIdError**</td><td>Mã lỗi trả về từ MisaID</td></tr>
<tr><td>**INACTIVE_USER**</td><td>Người dùng bị ngừng theo dõi</td></tr>
<tr><td>**INACTIVE_USER_WRONG_PASSWORD**</td><td>Người dùng bị ngừng theo dõi và sai password</td></tr>
<tr><td>**WrongPassWord**</td><td>Sai password</td></tr>
<tr><td>**TwoFactorAuthen**</td><td>Tài khoản misaid bật xác thực hai lớp</td></tr>
<tr><td>**InvalidUserId**</td><td>Sai param userid</td></tr>
<tr><td>**INVALIDPARAMETER**</td><td>Tham số không hợp lệ</td></tr>
<tr><td>**InvalidServiceToken**</td><td>Sai service token</td></tr>
<tr><td>**INVALIDAPPID**</td><td>Mã ứng dụng không hợp lệ</td></tr>
</tbody>
</table>

---

#### [POST] /meinvoicebot/v1/auth/jwttoken - Lấy JWT Token

- **Endpoint ID**: `f6bce1ac-768d-11f1-9f48-005056b30128`
- **Phương thức**: `POST`
- **Đường dẫn**: `/meinvoicebot/v1/auth/jwttoken`
- **Tóm tắt**: Lấy JWT Token

**Mô tả:**
API lấy JWT token để truy cập các API nghiệp vụ. Sử dụng **securetoken** nhận được từ API ValidateUser.

**Headers bắt buộc:**


- `ClientID` — ID được cấp bởi MISA khi đăng ký tích hợp
- `companytaxcode` — Mã số thuế của đơn vị
- `username` — Tên tài khoản đăng nhập
- `securetoken` — Chuỗi token nhận được từ response của API ValidateUser

**Response:** Trả về Data/AccessToken: AccessToken này dùng làm Bearer token trong header Authorization cho các API tiếp theo..

**Luồng nghiệp vụ:** Đây là bước 2: ValidateUser → **GetToken** → các API nghiệp vụ.

##### 1. Headers
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `ClientID` | `string` | Có | ID được cấp bởi MISA khi đăng ký tích hợp |
| `companytaxcode` | `string` | Có | Mã số thuế của đơn vị |
| `username` | `string` | Có | Tên tài khoản đăng nhập |
| `securetoken` | `string` | Có | Chuỗi token nhận được từ response của API ValidateUser |

##### 4. Response Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Success` | `bool` | Không | Trạng thái request: true = thành công, false = thất bại |
| `ErrorCode` | `string` | Không | Mã lỗi nếu có. Rỗng = thành công |
| `Message` | `string[]` | Không | Danh sách danh mục trả về |
| `Data` | `string` | Không | Đối tượng chứa JWTToken |

##### Mã lỗi thường gặp
## Mã lỗi thường gặp


Dưới đây là danh sách các mã lỗi thường gặp khi gọi API `/inbot/v1/jwttoken`:


<table>
<thead><tr><th>Mã lỗi</th><th>Mô tả</th></tr></thead>
<tbody>
<tr><td>**INVALIDTOKEN**</td><td>Mã số thuế chưa tồn tại</td></tr>
<tr><td>**TokenExpiredCode**</td><td>Token hết hạn - Cần gọi hàm RefreshToken</td></tr>
<tr><td>**InvalidTokenCode**</td><td>Token lỗi cần đăng nhập lại</td></tr>
</tbody>
</table>

---

### Nhóm: Lấy cơ cấu tổ chức

- **Group ID**: `f67df01e-768d-11f1-9f48-005056b30128`


#### [GET] /meinvoicebot/v1/subscribers/code/{taxcode} - Lấy thông tin subscriber theo mã số thuế

- **Endpoint ID**: `f6bf5359-768d-11f1-9f48-005056b30128`
- **Phương thức**: `GET`
- **Đường dẫn**: `/meinvoicebot/v1/subscribers/code/{taxcode}`
- **Tóm tắt**: Lấy thông tin subscriber theo mã số thuế

**Mô tả:**
API lấy thông tin subscriber (doanh nghiệp đăng ký sử dụng dịch vụ) theo mã số thuế. Trả về thông tin cơ bản của doanh nghiệp bao gồm CompanyID — mã định danh duy nhất dùng cho các API tiếp theo.


**Headers bắt buộc:**




- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp



**Path parameter:**




- `taxcode` — Mã số thuế của doanh nghiệp cần tra cứu (VD: `0101243143-008`)



**Luồng nghiệp vụ:** Token → **Subscribers** → Organizations → Invoices.

##### 1. Headers
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `ClientId` | `string` | Có | ID được cấp bởi MISA khi đăng ký tích hợp |

##### 4. Response Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Success` | `bool` | Không | Trạng thái request: true = thành công, false = thất bại |
| `Data` | `json` | Không | Thông tin Subscribers  |
| `Id` | `string` | Không | SubscribersId sử dụng cho các api tiếp |

---

#### [GET] /meinvoicebot/v1/{SubscribersId}/organizations - Lấy danh sách tổ chức của công ty

- **Endpoint ID**: `f6c1af75-768d-11f1-9f48-005056b30128`
- **Phương thức**: `GET`
- **Đường dẫn**: `/meinvoicebot/v1/{SubscribersId}/organizations`
- **Tóm tắt**: Lấy danh sách tổ chức của công ty

**Mô tả:**
API lấy danh sách tổ chức/phòng ban của công ty dựa trên CompanyID. Mỗi tổ chức có một OrganizationID dùng để truy xuất hóa đơn thuộc tổ chức đó.

**Headers bắt buộc:**


- ClientID — ID được cấp bởi MISA khi đăng ký tích hợp
- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`

**Path parameter:**


- SubscribersId— CompanyID lấy từ response của API GetSubscribers

**Luồng nghiệp vụ:** Token → Subscribers → **Organizations** → Invoices.

##### 1. Headers
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `ClientID` | `string` | Có | ID được cấp bởi MISA khi đăng ký tích hợp |
| `Authorization` | `string` | Có | Bearer token (JWT) nhận từ API GetToken. Format: Bearer {token} |

---

### Nhóm: Lấy danh sách hóa đơn đầu vào

- **Group ID**: `f67e4406-768d-11f1-9f48-005056b30128`


#### [GET] /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/v2/modified - Lấy dữ liệu hóa đơn 

- **Endpoint ID**: `f6c4135d-768d-11f1-9f48-005056b30128`
- **Phương thức**: `GET`
- **Đường dẫn**: `/meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/v2/modified`
- **Tóm tắt**: Lấy dữ liệu hóa đơn 

**Mô tả:**
API lấy danh sách hóa đơn đầu ra đã được sửa đổi trong khoảng thời gian, có phân trang. Hỗ trợ lọc theo ngày hóa đơn hoặc ngày thay đổi.

**Headers bắt buộc:**


- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp
- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`

**Path parameters:**


- `SubscribersId` — SubscribersID lấy từ API GetSubscribers (Thẻ **Id **trong Respone trả về )
- `organizationId` — OrganizationID lấy từ API GetOrganizations (Thẻ **Id **trong Respone trả về )

**Query parameters:**


- `take` — Số lượng bản ghi lấy về (tối đa 100, mặc định 20)
- `skip` — Số lượng bản ghi bỏ qua (mặc định 0)
- `from` — Ngày bắt đầu (format: yyyy-MM-dd)
- `to` — Ngày kết thúc (format: yyyy-MM-dd)
- `IsFilterInvDate` — `true`: lọc theo ngày hóa đơn; `false`: lọc theo ngày thay đổi

**Luồng nghiệp vụ:** Token → Subscribers → Organizations → **Invoices (modified)**.




<strong style="color: rgb(255, 0, 0);">Quy tắc xử lý hóa đơn: User tự upload XML lên hệ thống -> Hệ thống lấy dữ liệu từ CQT -> check thấy trùng, không thực hiện replace XML của User đã upload (kể cả XML từ CQT khác với XML của User upload), chỉ thực hiện update các trạng thái chưa được xử lý theo dữ liệu XML, nên khi vận hành hệ thống, nên chốt nghiệp vụ là chỉ lấy tự dữ liệu từ CQT hoặc lấy dữ dữ liệu từ nhiều nguồn**

##### 1. Headers
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `ClientId` | `string` | Có | ID được cấp bởi MISA khi đăng ký tích hợp |
| `Authorization` | `string` | Có | Bearer token (JWT) nhận từ API GetToken. Format: Bearer {token} |

##### 2. Query / Path Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `take` | `integer` | Không | Số lượng bản ghi lấy về (tối đa 100, mặc định 20) |
| `skip` | `integer` | Không | Số lượng bản ghi bỏ qua (mặc định 0) |
| `from` | `string` | Có | Ngày bắt đầu (format: yyyy-MM-dd) |
| `to` | `string` | Có | Ngày kết thúc (format: yyyy-MM-dd) |
| `IsFilterInvDate` | `boolean` | Không | true: lọc theo ngày hóa đơn; false: lọc theo ngày thay đổi |

##### 4. Response Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Success` | `bool` | Không | Trạng thái trả về khi gọi api- true/false |
| `Message` | `string` | Không | Tin nhắn trả về nếu có lỗi |
| `Data` | `InvData` | Không | Thông tin danh sách hóa đơn trả về - Xem mô tả InvData |
| `Other` | `Other` | Không | Thông tin khác về tài nguyên - Xem mô tả Other |

##### Mô tả đối tượng InvData
<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Thông tin**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Kiểu DL**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Mô tả**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Total</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Long</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số bản ghi trả về</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Data</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">List<InvoiceInbot></span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Danh sách hóa đơn đầu vào - Xem mô tả </span><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">InvoiceInbot**</p></td></tr></tbody></table>

##### Mô tả đối tượng InvoiceInbot
<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Thông tin**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Kiểu DL**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mô tả**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsHasXml</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có chứa dữ liệu XML không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsHasPdf</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có chứa dữ liệu PDF không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsMSTTCGPMISA</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải hóa đơn phát hành từ MISA không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsInvoiceSale</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải hóa đơn bán hàng không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsInvoice123</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải hóa đơn theo ND123 không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsMoreVat</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có nhiều loại thuế suất không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">HasSignature</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có chữ ký không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsVND</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải là VND không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsReceipt</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải là biên lai không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsDisplayTaxReductionNQ406</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có hiển thị giảm thuế NQ406 không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsDisplayTaxReductionNQ43</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có hiển thị giảm thuế NQ43 không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsInvoiceAdjust</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải là hóa đơn điều chỉnh không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsTaxOther</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có dùng loại thuế khác không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsMultiVat</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có nhiều loại thuế trên dòng hàng không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsRegisterCash</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải phát hành qua MTT không.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsTicketNoCode</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải mã vé không mã không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsHasInfoBuyer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có chứa thông tin người mua không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsRelativeInvoice</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có hóa đơn liên quan không?. (nếu có kiểm tra ở </span><u style="background-color: transparent; color: rgb(17, 85, 204); font-family: Inter; font-size: 14px;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.o54vsjqqbckv" rel="noopener noreferrer">RelativeInvoice</a></u><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">)</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsTaxReducedInvoice</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải hóa đơn giảm thuế không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsTaxReduction</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có giảm thuế không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsTaxReduction43</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có giảm thuế NQ43 không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsTaxReductionOther</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có giảm thuế khác không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsCheckND123</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có kiểm tra ND123 không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsInvoiceSendBySumary</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải hóa đơn gửi theo bảng tổng hợp không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsDiscountInvoice</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải là hóa đơn chiết khấu không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsValidBusinessAddress</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Địa chỉ doanh nghiệp có hợp lệ không?.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsDeleted</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Đánh dấu trạng thái xóa hóa đơn.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ActiveStatus</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái hoạt động của hóa đơn (</span><u style="background-color: transparent; color: rgb(17, 85, 204); font-family: Inter; font-size: 14px;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.cl58vxogoi84" rel="noopener noreferrer">ActiveStatus</a></u><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">)</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TypeInvoiceReceive</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Nguồn của hóa đơn (</span><u style="background-color: transparent; color: rgb(17, 85, 204); font-family: Inter; font-size: 14px;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.f1w302swxae8" rel="noopener noreferrer">TypeInvoiceReceive</a></u><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">)</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CheckDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày kiểm tra hóa đơn.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">AccountingDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày hạch toán</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Accountant</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Người hạch toán</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">InvoiceCodeStatus</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái mã hóa đơn.</span></p><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">2: Có mã</span></p><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">3: Không mã</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalFeesAmount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng tiềnphí.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">RefNo</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số chứng từ hạch toán</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">MCCQTText</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Diễn giải Mã CQT cấp.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">MCCQT</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã CQT cấp.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalHasDiscount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền có giảm giá.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">StatusInvoice</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái hóa đơn.</span></p><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><u style="background-color: transparent; color: rgb(17, 85, 204); font-family: Inter; font-size: 14px;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.w73d9uo0sn9r" rel="noopener noreferrer">InvoiceStatus</a></u></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">InfoChangeInvoice</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Diễn giải sự thay đổi hóa đơn</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SignatureStatus</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái chữ ký.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: bottom; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="bottom" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Fees</span></p></td><td style="height: 0pt; vertical-align: bottom; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="bottom" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">List<FeesInfo></span></p></td><td style="height: 0pt; vertical-align: bottom; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="bottom" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DSLPhi trong hóa đơn Nghị định 123</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TransId</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ID giao dịch.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">InvoiceId</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ID hóa đơn.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SubscriberId</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ID người đăng ký.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">OrgId</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ID tổ chức.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CompanyId</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ID công ty.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CompanyName</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tên công ty.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">InvSvcProvider</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Nguồn thông tư/nghị định của hóa đơn</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SellerTaxCode</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã số thuế người bán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SellerName</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tên người bán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SellerAddress</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Địa chỉ người bán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SellerPhoneNumber</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số điện thoại người bán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SellerRiskStatus</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái rủi ro của người bán (</span><u style="background-color: transparent; color: rgb(17, 85, 204); font-family: Inter; font-size: 14px;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.kv44l69kr23z" rel="noopener noreferrer">RickStatus</a></u><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">)</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerTaxCode</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã số thuế người mua.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerName</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tên người mua.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerAddress</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Địa chỉ người mua.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TemplateNo</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số mẫu hóa đơn.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Series</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Chuỗi phân loại hóa đơn.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">InvoiceNo</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số hóa đơn.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">InvoiceDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày phát hành hóa đơn.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: bottom; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="bottom" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IssueDate</span></p></td><td style="height: 0pt; vertical-align: bottom; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="bottom" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime?</span></p></td><td style="height: 0pt; vertical-align: bottom; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="bottom" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày cấp mã</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">PaymentMethod</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Phương thức thanh toán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CcyCode</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã tiền tệ.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ExchangeRate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tỷ giá hối đoái.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmountWithoutVat</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền không bao gồm VAT.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmountWithoutVatCC</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền không bao gồm VAT (nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">VatRate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tỷ lệ VAT.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalVATAmount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền VAT.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalVATAmountCC</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền VAT (đơn vị nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalDiscountAmount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền giảm giá.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalDiscountAmountCC</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền giảm giá (đơn vị nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền hóa đơn.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmountCC</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền hóa đơn (đơn vị nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmountText</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền bằng chữ.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Status</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái chung của hóa đơn.</span></p><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><u style="background-color: transparent; color: rgb(17, 85, 204); font-family: Inter; font-size: 14px;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.mamcr0bnvken" rel="noopener noreferrer">(InvoiceInfoFlags)</a></u></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">InvoiceCreator</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Nguồn gốc hóa đơn (</span><u style="background-color: transparent; color: rgb(17, 85, 204); font-family: Inter; font-size: 14px;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.nlaljldjxqo" rel="noopener noreferrer">CreatorEnum</a></u><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">)</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">StatusInvoices</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">List<String></span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Kiểm tra hợp lệ của hóa đơn</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SumTPhi</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng phí.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SumTPhiCC</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng phí (đơn vị nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalTaxReductionAmount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền giảm thuế.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalTaxReductionAmountCC</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền giảm thuế (đơn vị nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalTaxReductionAmount43</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền giảm thuế NQ43.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalTaxReductionAmount43CC</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền giảm thuế NQ43 (đơn vị nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmountNotPayment</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền chưa thanh toán.</span></p></td></tr><tr><td style="height: 20.3496pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="20.3496pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmountNotPaymentCC</span></p></td><td style="height: 20.3496pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="20.3496pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 20.3496pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="20.3496pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền chưa thanh toán (đơn vị nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmountPayment</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền đã thanh toán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TotalAmountPaymentCC</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền đã thanh toán (đơn vị nguyên tệ).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">AmountPayment</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số lần thanh toán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">PaymentDueDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày hết hạn thanh toán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">PaymentOutOfDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày quá hạn thanh toán.</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CostType</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Loại chi phí.</span></p></td></tr><tr><td style="height: 19.502pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="19.502pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Id</span></p></td><td style="height: 19.502pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="19.502pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 19.502pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="19.502pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ID duy nhất của hóa đơn (maxleng 36).</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CreatedDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày tạo hóa đơn.</span></p></td></tr><tr><td style="height: 19.5996pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="19.5996pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ModifiedDate</span></p></td><td style="height: 19.5996pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="19.5996pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 19.5996pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="19.5996pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày sửa đổi bản ghi lần cuối.</span></p></td></tr><tr><td>**Thông tin khác - Theo nghị định 70**

</td><td>


</td><td>Xem mô tả **Thông tin khác InvoiceInbot** -** theo nghị định 70**

</td></tr></tbody></table>

##### Mô tả thông tin khác InvoiceInbot - Theo nghị định 70
<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Thông tin**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Kiểu DL**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mô tả**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerMSDVCQHVNS</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã số đơn vị có quan hệ với ngân sách(Người mua) Đáp ứng Hóa đơn bán hàng, Hóa đơn GTGT, Hóa đơn bán tài sản công</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerNoCitizenIdentityCard</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Căn cước công dân(Người mua) - Áp dụng: Hóa đơn bán hàng, hóa đơn GTGT, hóa đơn bán tài sản công</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerPassportNumber</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số hộ chiếu(Người mua) - Đáp ứng Hóa đơn bán hàng, Hóa đơn GTGT, Hóa đơn bán tài sản công</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">NumberAgreement</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Hợp đồng bán/chuyển nhượng số (Thông tin chung) Áp dụng: Hóa đơn bán tài sản công</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">AgreementDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime?</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Hợp đồng ngày (Hợp đồng vận chuyển) (Thông tin chung) Áp dụng: Hóa đơn bán tài sản công</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">LicensePlate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Biển số xe</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">From</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Điểm đi</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Destination</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">điểm đến</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsReceiptDecree70</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">bool</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Biên lai theo ND70</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsDiscountDecree70</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">bool</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Đây là cờ đánh dấu hóa đơn là hóa đơn chiết khấu theo Nghị định 70</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerMSDVCQHVNS</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã số đơn vị có quan hệ với ngân sách của người mua</span></p></td></tr><tr><td style="height: 18.5039pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="18.5039pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerPassportNumber</span></p></td><td style="height: 18.5039pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="18.5039pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 18.5039pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="18.5039pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số hộ chiếu của người mua</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">BuyerNoCitizenIdentityCard</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số Căn cước công dân của người mua</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">NumberAgreement</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số hợp đồng vận chuyển</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">AgreementDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime?</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày ký hợp đồng vận chuyển</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SellerMSDVCQHVNS</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã số đơn vị có quan hệ với ngân sách của người bán</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">LicensePlate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Biển số xe vận chuyển hàng hóa</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Destination</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Điểm đến của hành trình</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">From</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Điểm đi của hành trình</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Destination</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Điểm đến</span></p></td></tr></tbody></table>

##### Mô tả thông tin Items
<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Thông tin**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Kiểu DL**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mô tả**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ItemId</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã định danh của mục hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">LineNumber</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số thứ tự dòng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ItemName</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tên của mục hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">UnitName</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tên đơn vị</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Quantity</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số lượng của mục hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">UnitPrice</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Giá đơn vị của mục hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">AmountWithoutVat</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền chưa bao gồm VAT</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsVatOther</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải là VAT khác không</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">VatRate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Thuế suất</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsTaxReduction</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải là giảm thuế không</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">VatAmount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số tiền thuế VAT</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DiscountAmount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số tiền giảm giá</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Amount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền bao gồm VAT</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsPromotion</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải là khuyến mãi không</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Others</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">List<</span><u style="background-color: transparent; color: rgb(17, 85, 204); font-family: Inter; font-size: 14px;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.q7d0i78juiw5" rel="noopener noreferrer">OtherInfo</a></u><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">></span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Các thông tin khác</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TaxReductionAmount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số tiền giảm thuế</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TaxReductionAmount43</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số tiền giảm thuế theo quy định 43</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Nature</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tính chất của hàng hóa</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">NatureText</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mô tả tính chất</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">AmountAfterDiscount</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Decimal</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tổng số tiền sau khi giảm giá</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><a href="https://docs.google.com/document/d/1K8c06WypdI70cKQ1qjgzKzNNxkjMTPKX-NbGGV2aJ7I/edit?tab=t.0#heading=h.mamcr0bnvken" rel="noopener noreferrer" style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Kind</a></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tính chất của hóa đơn ND123 - Xem mô tả </span><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Kind**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">KindXml</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Loại mã XML của mục hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">IsItemFee</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Boolean</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Có phải là phí hàng hóa không</span></p></td></tr><tr><td>**Thông tin khác Items** **- Theo nghị định 70**

</td><td>


</td><td>Xem mô tả **Thông tin khác Items** **- Theo nghị định 70**

</td></tr></tbody></table>

##### Mô tả thông tin khác Items - Theo nghị định 70
<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Thông tin**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Kiểu DL**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mô tả**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SpecificProductType</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Int</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Loại hàng hóa đặc trưng theo Nghị định 70</span></p><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">0: Chưa xác định</span></p><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">1: Kinh doanh xe máy, ô tô</span></p><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">2: Dịch vụ vận chuyển</span></p><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">3: Dịch vụ vận chuyển trên nền tảng số, TMĐT</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">VehicleFrameNumber</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số khung xe</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">VehicleEngineNumber</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số máy xe</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TransportLicensePlate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Biển kiểm soát phương tiện vận chuyển</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ShipperName</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tên người gửi hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ShipperAddress</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Địa chỉ người gửi hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ShipperTaxCode</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã số thuế người gửi hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ShipperIdentifier</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">string</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số định danh người gửi hàng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4pt;"><p data-cellpadding="4pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CheckedStatus</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4pt;"><p data-cellpadding="4pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">List<CheckedStatusObject></span></p></td><td style="height: 0pt; vertical-align: top; padding: 4pt;"><p data-cellpadding="4pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái kiểm tra của hóa đơn - Xem mô tả </span><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CheckedStatusObject**</p></td></tr></tbody></table>

##### Mô tả thông tin CheckedStatusObject
<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Thông tin**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Kiểu DL**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mô tả**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Status</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4pt;"><p data-cellpadding="4pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mô tả trạng thái kiểm tra</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CheckingStatus</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái kiểm tra của hóa đơn - Xem mô tả </span><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Enum**<span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;"> mục </span><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CheckingResultInvoiceStatusInvoice**</p></td></tr></tbody></table>

##### InvoiceInfoStatusFlags
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**1**

</td><td>Hóa đơn đang chờ kiểm tra

</td></tr><tr><td>**2**

</td><td>Hóa đơn hợp lệ

</td></tr><tr><td>**16**

</td><td>Hóa đơn không hợp lệ

</td></tr><tr><td>**24**

</td><td>Hóa đơn chưa thực hiện kiểm tra xong hết các chỉ tiêu

</td></tr><tr><td>**8**

</td><td>Hóa đơn nháp

</td></tr><tr><td>**999**

</td><td>Cờ chỉ dùng để lọc hóa đơn không có bản thể hiện pdf

</td></tr><tr><td>**998**

</td><td>Cờ dùng lọc hóa đơn không có file xml

</td></tr><tr><td>**997**

</td><td>Cờ dùng lọc hóa đơn có file xml

</td></tr><tr><td>**30**

</td><td>Hóa đơn rủi ro

</td></tr><tr><td>**29**

</td><td>Không rủi ro

</td></tr><tr><td>**31**

</td><td>Không kiểm tra

</td></tr></tbody></table>

##### KindND123 
<table><tbody><tr><td>**Giá trị **

</td><td>**Mô tả **

</td></tr><tr><td>**0**

</td><td>Không có tính chất

</td></tr><tr><td>**1**

</td><td>Tính chất 1 là HDDV

</td></tr><tr><td>**2**

</td><td>Tính chất 2 là khuyến mãi

</td></tr><tr><td>**3**

</td><td>Tính chất 3: Chiết khấu thương mại (thể hiện theo dòng)

</td></tr><tr><td>**4**

</td><td>Tính chất 4: Ghi chú diễn giải

</td></tr><tr><td>**5**

</td><td>Tính chất 5: Hàng hóa đặc trưng theo NĐ70 (Xe máy, ô tô, dịch vụ vận chuyển…)

</td></tr></tbody></table>

##### InvoiceCreatorFlags
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**0**

</td><td>Không phải hóa đơn

</td></tr><tr><td>**1**

</td><td>Hóa đơn được đọc tự động bởi hệ thống

</td></tr><tr><td>**2**

</td><td>Hóa đơn nhập tay

</td></tr><tr><td>**3**

</td><td>Hóa đơn lưu nháp

</td></tr><tr><td>**4**

</td><td>Hóa đơn không đủ thông tin để kiểm tra nhưng vẫn hợp lệ

</td></tr><tr><td>**5**

</td><td>Hóa đơn được đọc từ tool

</td></tr></tbody></table>

##### CheckingStatusFlags 
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**-1**

</td><td>Gặp lỗi trong quá trình check

</td></tr><tr><td>**0**

</td><td>Chưa kiểm tra

</td></tr><tr><td>**1**

</td><td>Hợp lệ

</td></tr><tr><td>**8**

</td><td>Không rõ trạng thái

</td></tr><tr><td>**16**

</td><td>Không hợp lệ

</td></tr><tr><td>**999**

</td><td>Đang kiểm tra

</td></tr></tbody></table>

##### GdtInvoiceIndexingStatusFlags
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**-1**

</td><td>Gặp lỗi trong quá trình check

</td></tr><tr><td>**0**

</td><td>Chưa kiểm tra

</td></tr><tr><td>**1**

</td><td>Hợp lệ

</td></tr><tr><td>**8**

</td><td>Không rõ trạng thái

</td></tr><tr><td>**16**

</td><td>Không hợp lệ

</td></tr><tr><td>**999**

</td><td>Đang kiểm tra

</td></tr></tbody></table>

##### InvoiceCodeStatus
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**1**

</td><td>Không có (None)

</td></tr><tr><td>**2**

</td><td>Hóa đơn có mã

</td></tr><tr><td>**3**

</td><td>Hóa đơn không mã

</td></tr></tbody></table>

##### TypeInvoiceReceive 
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**0**

</td><td>Tất cả

</td></tr><tr><td>**1**

</td><td>Hóa đơn upload

</td></tr><tr><td>**2**

</td><td>Hóa đơn email

</td></tr><tr><td>**3**

</td><td>Tự động

</td></tr><tr><td>**4**

</td><td>Hóa đơn nhập tay

</td></tr><tr><td>**5**

</td><td>Tự động từ tool

</td></tr></tbody></table>

##### TThaiXuLyEnum
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**0**

</td><td>Thuế Nhận (Tổng cục Thuế đã nhận)

</td></tr><tr><td>**1**

</td><td>Đang kiểm tra (Đang tiến hành kiểm tra điều kiện cấp mã)

</td></tr><tr><td>**2**

</td><td>Thuế Từ Chối (CQT từ chối hóa đơn theo từng lần phát sinh)

</td></tr><tr><td>**3**

</td><td>Đủ Điều Kiện (Hóa đơn đủ điều kiện cấp mã)

</td></tr><tr><td>**4**

</td><td>Không Đủ Điều Kiện (Hóa đơn không đủ điều kiện cấp mã)

</td></tr><tr><td>**5**

</td><td>Đã Cấp Mã (Đã cấp mã hóa đơn)

</td></tr><tr><td>**6**

</td><td>Nhận Không Cấp Mã (Tổng cục thuế đã nhận không mã)

</td></tr><tr><td>**7**

</td><td>Đã Kiểm Tra Không Có Mã (Đã kiểm tra định kỳ HĐĐT không có mã)

</td></tr><tr><td>**8**

</td><td>Nhận HD Máy Tính Tiền (Đã tiếp nhận hóa đơn máy tính tiền)

</td></tr></tbody></table>

##### TinhChatEnum
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**1**

</td><td>Hóa đơn gốc

</td></tr><tr><td>**2**

</td><td>Hóa đơn thay thế

</td></tr><tr><td>**3**

</td><td>Hóa đơn điều chỉnh

</td></tr></tbody></table>

##### TThaiHDonEnum
<table><thead><tr><th>Giá trị

</th><th>Mô tả

</th></tr></thead><tbody><tr><td>**0**

</td><td>Tất cả

</td></tr><tr><td>**1**

</td><td>Hóa đơn gốc

</td></tr><tr><td>**2**

</td><td>Hóa đơn thay thế

</td></tr><tr><td>**3**

</td><td>Hóa đơn điều chỉnh

</td></tr><tr><td>**4**

</td><td>Hóa đơn đã bị thay thế

</td></tr><tr><td>**5**

</td><td>Hóa đơn đã bị điều chỉnh

</td></tr><tr><td>**6**

</td><td>Hóa đơn đã bị xóa bỏ/hủy bỏ

</td></tr><tr><td>**7**

</td><td>Hóa đơn chưa xác định

</td></tr></tbody></table>

##### TypeAmountPayment
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**0**

</td><td>Không thiết lập

</td></tr><tr><td>**1**

</td><td>Chưa thanh toán

</td></tr><tr><td>**2**

</td><td>Thanh toán toàn phần

</td></tr><tr><td>**3**

</td><td>Quá hạn thanh toán

</td></tr><tr><td>**4**

</td><td>Đến hạn thanh toán

</td></tr><tr><td>**5**

</td><td>Thanh toán một phần

</td></tr></tbody></table>

##### KindLogicCheckingEnum
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**0**

</td><td>Không kiểm tra

</td></tr><tr><td>**1**

</td><td>Kiểm tra về tính đúng đắn của dữ liệu

</td></tr><tr><td>**2**

</td><td>Kiểm tra về vi phạm của hóa đơn

</td></tr></tbody></table>

##### CheckingResultStatusInvoice
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**0**

</td><td>Đang kiểm tra

</td></tr><tr><td>**1**

</td><td>Trạng thái hợp lệ

</td></tr><tr><td>**2**

</td><td>Trạng thái không hợp lệ

</td></tr><tr><td>**3**

</td><td>Bản nháp

</td></tr><tr><td>**4**

</td><td>Tính toán số liệu

</td></tr></tbody></table>

##### VatRate
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**0**

</td><td>Thuế suất 0%

</td></tr><tr><td>**5**

</td><td>Thuế suất 5%

</td></tr><tr><td>**8**

</td><td>Thuế suất 8%

</td></tr><tr><td>**10**

</td><td>Thuế suất 10%

</td></tr><tr><td>**-1**

</td><td>Không chịu thuế

</td></tr><tr><td>**-2**

</td><td>Không kê khai nộp thuế

</td></tr><tr><td>**-3**

</td><td>Khác (Hóa đơn 51)

</td></tr></tbody></table>

##### RiskStatus 
<table><tbody><tr><td>**Giá trị**

</td><td>**Mô tả**

</td></tr><tr><td>**0**

</td><td>Tất cả

</td></tr><tr><td>**1**

</td><td>Không có rủi ro

</td></tr><tr><td>**2**

</td><td>Rủi ro theo công văn thuế thông báo danh sách đen

</td></tr><tr><td>**3**

</td><td>Chưa đủ thông tin kết luận

</td></tr><tr><td>**4**

</td><td>Rủi ro theo trạng thái hoạt động 06 (không hoạt động tại địa chỉ đăng ký)

</td></tr></tbody></table>

##### Mô tả đối tượng CheckingResult
<table><tbody><tr><td><p style="text-align: center;">**Thông tin**</p></td><td><p style="text-align: center;">**Kiểu DL**</p></td><td><p style="text-align: center;">**Mô tả**</p></td></tr><tr><td>**CheckedAts**

</td><td>Object

</td><td>Thời gian các lần thực hiện kiểm tra các chỉ tiêu hóa đơn

</td></tr><tr><td>**Status**

</td><td>Integer

</td><td>Trạng thái chung của **CheckingResult**

</td></tr><tr><td>**SellerStatus**

</td><td>Object

</td><td>Trạng thái người bán

</td></tr><tr><td>  - ActiveStatus

</td><td>Object

</td><td>Trạng thái hoạt động của doanh nghiệp (ActiveStatus)

</td></tr><tr><td>  - TaxRiskStatus

</td><td>Object

</td><td>Trạng thái rủi ro của DN

</td></tr><tr><td>  - Name

</td><td>Object

</td><td>Kết quả kiểm tra thông tin tên doanh nghiệp

</td></tr><tr><td>  - Address

</td><td>Object

</td><td>Kết quả kiểm tra địa chỉ doanh nghiệp

</td></tr><tr><td>  - ModifiedDate

</td><td>Datetime

</td><td>Ngày cập nhật

</td></tr><tr><td>  - Status

</td><td>Integer

</td><td>Trạng thái của người bán

</td></tr><tr><td>**BuyerStatus**

</td><td>Object

</td><td>Thông tin người mua

</td></tr><tr><td>  - TaxCode

</td><td>Object

</td><td>Mst người mua

</td></tr><tr><td>  - Name

</td><td>Object

</td><td>Tên người mua

</td></tr><tr><td>  - Address

</td><td>Object

</td><td>Địa chỉ người mua

</td></tr><tr><td>  - Status

</td><td>Integer

</td><td>Trạng thái của người mua

</td></tr><tr><td>**PublishedInvoiceStatus**

</td><td>Object

</td><td>Kết quả kiểm tra thông tin liên quan đến thông báo phát hành hóa đơn

</td></tr><tr><td>  - HasInvoicePublished

</td><td>Object

</td><td>Có thông báo phát hành HĐ

</td></tr><tr><td>  - InvoiceNo

</td><td>Object

</td><td>Số hóa đơn hợp lệ: nằm trong khoảng của thông báo phát hành HĐ

</td></tr><tr><td>  - InvoiceDate

</td><td>Object

</td><td>Ngày hóa đơn hợp lệ: >= ngày sử dụng trên thông báo phát hành HĐ

</td></tr><tr><td>  - GdtIndexing

</td><td>Object

</td><td>Kết quả tra cứu hóa đơn trên cổng thuế (chụp ảnh màn hình tra cứu)

</td></tr><tr><td>  - Status

</td><td>Integer

</td><td>Trạng thái của hóa đơn

</td></tr><tr><td>  - InvoicePublishedId

</td><td>String

</td><td>Id của thông báo phát hành hóa đơn (để tham chiếu khi cần thiết)

</td></tr><tr><td>**SellerSignatureStatus**

</td><td>Object

</td><td>Thông tin ký số người bán

</td></tr><tr><td>  - HasSigned

</td><td>Object

</td><td>Đã có chữ ký số người bán

</td></tr><tr><td>  - Certificate

</td><td>Object

</td><td>Chứng thư số hợp lệ: chứng thư số do các nhà cung cấp hợp pháp cấp

</td></tr><tr><td>  - CertificateOwner

</td><td>Object

</td><td>Chứng thư số đúng chủ sở hữu: dựa vào mã số thuế trên Subject của chứng thư số

</td></tr><tr><td>  - SignedDate

</td><td>Object

</td><td>Ngày ký thuộc khoảng hiệu lực của chứng thư số

</td></tr><tr><td>  - SignedDateEqInvoiceDate

</td><td>Object

</td><td>Ngày ký trùng ngày hóa đơn

</td></tr><tr><td>  - Status

</td><td>Integer

</td><td>Trạng thái ký số người bán

</td></tr><tr><td>  - CertificateId

</td><td>String

</td><td>Id của chứng thư số (để tham chiếu khi cần)

</td></tr><tr><td>**TaxaxionSignature**

</td><td>


</td><td>Kết quả chữ ký số của CQT

</td></tr><tr><td>  - Issuer

</td><td>String

</td><td>Nhà cung cấp chứng thư số

</td></tr><tr><td>  - IssueTo

</td><td>String

</td><td>Chứng thư số được cấp cho

</td></tr><tr><td>  - ValidFrom

</td><td>Datetime

</td><td>Có hiệu lực từ ngày

</td></tr><tr><td>  - ValidTo

</td><td>Datetime

</td><td>Hiệu lực đến ngày

</td></tr><tr><td>  - DataWasModified

</td><td>Object

</td><td>Dữ liệu đã bị sửa đổi sau khi ký

</td></tr><tr><td>      - Status

</td><td>Integer

</td><td>Ngày ký thuộc khoảng hiệu lực của chứng thư số (CheckingStatus)

</td></tr><tr><td>  - AcceptOther

</td><td>Object

</td><td>Thể hiện xem người dùng đã chấp nhận thông tin trên hóa đơn CKS

</td></tr><tr><td>  - Status

</td><td>Integer

</td><td>Trạng thái

</td></tr></tbody></table>

##### Mô tả đối tượng InfoND123
<table><tbody><tr><td>**Thông tin**

</td><td>**Kiểu DL**

</td><td>**Mô tả**

</td></tr><tr><td>StatusExistTCT

</td><td>Integer

</td><td>Trạng thái tồn tại TCT (StatusExistTCT)

</td></tr><tr><td>ProcessingStatus

</td><td>Integer

</td><td>Trạng thái xử lý (ProcessingStatus)

</td></tr><tr><td>ResonRejectText

</td><td>String

</td><td>Lý do bị từ chối

</td></tr><tr><td>Nature

</td><td>Integer

</td><td>Tính chất của hóa đơn (InvoiceType)

</td></tr><tr><td>Status

</td><td>Integer

</td><td>Trạng thái hiện tại (InvoiceStatus)

</td></tr><tr><td>ListVat

</td><td>List<Object>

</td><td>Danh sách thông tin về thuế suất

</td></tr><tr><td>  - VatRate

</td><td>


</td><td>Loại thuế suất

</td></tr><tr><td>  - TotalVATAmount

</td><td>


</td><td>Tổng tiền thuế

</td></tr><tr><td>  - TotalAmountWithoutVat

</td><td>


</td><td>Tổng tiền trước thuế

</td></tr><tr><td>IsAdjusted

</td><td>Boolean

</td><td>Có phải hóa đơn điều chỉnh không?

</td></tr><tr><td>InvConnect

</td><td>Object

</td><td>Thông tin hóa đơn liên quan

</td></tr><tr><td>IsCheckedInvoiceReplace

</td><td>Boolean

</td><td>Kiểm tra hóa đơn đã thay thế hay chưa

</td></tr><tr><td>InvoiceRelateds

</td><td>List<InvoiceRelateds>

</td><td>Danh sách hóa đơn liên quan

</td></tr></tbody></table>

##### Mô tả đối tượng InvoiceRelateds
<table><tbody><tr><td>**Thông tin**

</td><td>**Kiểu DL**

</td><td>**Mô tả**

</td></tr><tr><td>InvoiceId

</td><td>String

</td><td>ID hóa đơn, định danh duy nhất cho hóa đơn.

</td></tr><tr><td>SubscriberId

</td><td>String

</td><td>ID của người đăng ký, định danh duy nhất cho người dùng.

</td></tr><tr><td>OrgId

</td><td>String

</td><td>ID của tổ chức, định danh duy nhất cho tổ chức.

</td></tr><tr><td>TemplateNo

</td><td>String

</td><td>Mẫu hóa đơn.

</td></tr><tr><td>Series

</td><td>String

</td><td>Ký hiệu hóa đơn.

</td></tr><tr><td>InvoiceNo

</td><td>String

</td><td>Số hóa đơn dạng số.

</td></tr><tr><td>InvoiceNoNumberGet

</td><td>Integer

</td><td>Số hóa đơn dưới dạng số nguyên.

</td></tr><tr><td>Noted

</td><td>String

</td><td>Ghi chú liên quan đến hóa đơn.

</td></tr><tr><td>Status

</td><td>Integer

</td><td>Trạng thái của hóa đơn (InvoiceInfoFlags).

</td></tr><tr><td>CheckedStatus

</td><td>Integer

</td><td>Trạng thái kiểm tra của hóa đơn (CheckedStatus).

</td></tr><tr><td>InvoiceDate

</td><td>DateTime

</td><td>Ngày phát hành hóa đơn.

</td></tr><tr><td>LinkSearch

</td><td>String

</td><td>Đường link để tìm kiếm hóa đơn trên hệ thống.

</td></tr><tr><td>TotalAmountWithoutVat

</td><td>Decimal

</td><td>Tổng số tiền chưa bao gồm thuế VAT.

</td></tr><tr><td>TotalAmountWithoutVatCC

</td><td>Decimal

</td><td>Tổng số tiền chưa bao gồm thuế VAT

</td></tr><tr><td>TotalVATAmount

</td><td>Decimal

</td><td>Tổng số tiền thuế VAT.

</td></tr><tr><td>TotalVATAmountCC

</td><td>Decimal

</td><td>Tổng số tiền thuế VAT (nguyên tệ).

</td></tr><tr><td>TotalDiscountAmount

</td><td>Decimal

</td><td>Tổng số tiền giảm giá.

</td></tr><tr><td>TotalDiscountAmountCC

</td><td>Decimal

</td><td>Tổng số tiền giảm giá (nguyên tệ).

</td></tr><tr><td>TotalAmount

</td><td>Decimal

</td><td>Tổng số tiền bao gồm thuế VAT và các khoản giảm giá.

</td></tr><tr><td>TotalAmountCC

</td><td>Decimal

</td><td>Tổng số tiền (nguyên tệ).

</td></tr><tr><td>SumTphi

</td><td>Decimal

</td><td>Tổng phí khác (nếu có).

</td></tr><tr><td>SumTphiCC

</td><td>Decimal

</td><td>Tổng phí khác (nguyên tệ).

</td></tr><tr><td>TotalTaxReductionAmount

</td><td>Decimal

</td><td>Tổng số tiền giảm thuế.

</td></tr><tr><td>TotalTaxReductionAmountCC

</td><td>Decimal

</td><td>Tổng số tiền giảm thuế (nguyên tệ).

</td></tr><tr><td>TotalTaxReductionAmount43

</td><td>Decimal

</td><td>Tổng số tiền giảm thuế theo mục 43 (nếu có).

</td></tr><tr><td>TotalTaxReductionAmount43CC

</td><td>Decimal

</td><td>Tổng số tiền giảm thuế theo mục 43 (nguyên tệ).

</td></tr></tbody></table>

##### Mô tả đối tượng OtherInfo
<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">Thông tin**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">Kiểu DL**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">Mô tả**</p></td></tr><tr><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">TTruong</span></p></td><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">String</span></p></td><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">Tên trường dữ liệu</span></p></td></tr><tr><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">KDLieu</span></p></td><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">String</span></p></td><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">Kiểu DL</span></p></td></tr><tr><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">DLieu</span></p></td><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">String</span></p></td><td style="height: 22.4344pt; vertical-align: top; padding: 4.25197pt;"><p data-cellpadding="4.25197pt" data-cellverticalalign="top" data-cellheight="22.4344pt" style="text-align: left;"><span style="font-size: 14px; font-family: Inter; color: rgb(0, 0, 0); background-color: transparent;">Giá trị dữ liệu</span></p></td></tr></tbody></table>

##### Mô tả đối tượng Other
<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Thông tin**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Kiểu DL**</p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Mô tả**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">TaxCode</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mã số thuế</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ProductPackCode</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Tên gói đang dùng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">StartDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày bắt đầu sử dụng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ExpiredDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày hết hạn</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">NumberOfInvoice</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số lượng hóa đơn</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">NumberInvUsed</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số lượng hóa đơn đã sử dụng</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Status</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái tài nguyên</span></p><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">0,1: chính thức</span></p><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">2: dùng thử</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">SubscriberStatus</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Trạng thái gói</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">NumberInvStill</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Integer</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Số lượng hóa đơn còn lại</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Description</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Mô tả gói</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ServerDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày server</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Id</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">String</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ID của gói</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">CreatedDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày khởi tạo</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">ModifiedDate</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">DateTime</span></p></td><td style="height: 0pt; vertical-align: top; padding: 5pt;"><p data-cellpadding="5pt" data-cellverticalalign="top" data-cellheight="0pt" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter; font-size: 14px;">Ngày cập nhật</span></p></td></tr></tbody></table>

---

#### [GET] /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/{InvoiceId} - Lấy chi tiết hóa đơn theo ID

- **Endpoint ID**: `019ef754-0001-7000-8000-000000000001`
- **Phương thức**: `GET`
- **Đường dẫn**: `/meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/{InvoiceId}`
- **Tóm tắt**: Lấy chi tiết hóa đơn theo ID

**Mô tả:**
API lấy thông tin chi tiết của một hóa đơn đầu vào theo ID hóa đơn. Trả về toàn bộ thông tin hóa đơn bao gồm thông tin người bán, người mua, dòng hàng, thuế, chiết khấu, thanh toán.


**Headers bắt buộc:**




- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp

- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`



**Path parameters:**




- `SubscribersId` — ID subscriber (CompanyID) lấy từ API GetSubscribers

- `organizationId` — ID tổ chức lấy từ API GetOrganizations

- `InvoiceId` — ID của hóa đơn cần lấy chi tiết



**Luồng nghiệp vụ:** Token → Subscribers → Organizations → Invoices (danh sách) → **Invoice detail**.


**Response:** Trả về thông tin chi tiết hóa đơn bao gồm: thông tin người bán (mã số thuế, tên, địa chỉ), thông tin người mua, thông tin chung (số hóa đơn, ngày phát hành, mẫu số, ký hiệu), chi tiết dòng hàng, tổng tiền, thuế, chiết khấu, và trạng thái thanh toán.

##### Respone trả về giống của đầu API lấy danh sách 


---

### Nhóm: Lấy danh sách hóa đơn đầu ra

- **Group ID**: `01a0b3c6-27b7-765e-97ec-361be7428892`


#### [GET] /meinvoicebot/v1/{subscriberId}/{organizationId}/OutInvoices/modified - Lấy theo modified time

- **Endpoint ID**: `01a0b3c6-645a-7f32-9923-3581d15131a9`
- **Phương thức**: `GET`
- **Đường dẫn**: `/meinvoicebot/v1/{subscriberId}/{organizationId}/OutInvoices/modified`
- **Tóm tắt**: Lấy theo modified time

**Mô tả:**
API lấy danh sách hóa đơn đầu ra đã được sửa đổi trong khoảng thời gian, có phân trang. Hỗ trợ lọc theo ngày hóa đơn hoặc ngày thay đổi.

**Headers bắt buộc:**


- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp
- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`

**Path parameters:**


- `SubscribersId` — SubscribersID lấy từ API GetSubscribers (Thẻ **Id **trong Respone trả về )
- `organizationId` — OrganizationID lấy từ API GetOrganizations (Thẻ **Id **trong Respone trả về )

**Query parameters:**


- `take` — Số lượng bản ghi lấy về (tối đa 100, mặc định 20)
- `skip` — Số lượng bản ghi bỏ qua (mặc định 0)
- `from` — Ngày bắt đầu (format: yyyy-MM-dd)
- `to` — Ngày kết thúc (format: yyyy-MM-dd)
- `IsFilterInvDate` — `true`: lọc theo ngày hóa đơn; `false`: lọc theo ngày thay đổi

**Luồng nghiệp vụ:** Token → Subscribers → Organizations → **Invoices (modified)**.

##### 1. Headers
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `ClientId` | `string` | Có | ID được cấp bởi MISA khi đăng ký tích hợp |
| `Authorization` | `string` | Có | Bearer token (JWT) nhận từ API GetToken. Format: Bearer {token} |

##### 2. Query / Path Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `take` | `integer` | Không | Số lượng bản ghi lấy về (tối đa 100, mặc định 20) |
| `skip` | `integer` | Không | Số lượng bản ghi bỏ qua (mặc định 0) |
| `from` | `string` | Không | Ngày bắt đầu (format: yyyy-MM-dd) |
| `to` | `string` | Không | Ngày kết thúc (format: yyyy-MM-dd) |
| `IsFilterInvDate` | `boolean` | Không | true: lọc theo ngày hóa đơn; false: lọc theo ngày thay đổi |

##### Xem mô tả của phần hóa đơn đầu vào


---

#### [GET] /meinvoicebot/v1/{subscribersID/{organizationsID}/OutInvoices/{invoiceID} - Lấy chi tiết 1 hóa đơn

- **Endpoint ID**: `01a0b3ce-4322-7afd-9afc-305b863dd578`
- **Phương thức**: `GET`
- **Đường dẫn**: `/meinvoicebot/v1/{subscribersID/{organizationsID}/OutInvoices/{invoiceID}`
- **Tóm tắt**: Lấy chi tiết 1 hóa đơn

**Mô tả:**
API lấy thông tin chi tiết của một hóa đơn đầu vào theo ID hóa đơn. Trả về toàn bộ thông tin hóa đơn bao gồm thông tin người bán, người mua, dòng hàng, thuế, chiết khấu, thanh toán.

**Headers bắt buộc:**


- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp
- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`

**Path parameters:**


- `SubscribersId` — ID subscriber (CompanyID) lấy từ API GetSubscribers
- `organizationId` — ID tổ chức lấy từ API GetOrganizations
- `InvoiceId` — ID của hóa đơn cần lấy chi tiết

**Luồng nghiệp vụ:** Token → Subscribers → Organizations → Invoices (danh sách) → **Invoice detail**.

**Response:** Trả về thông tin chi tiết hóa đơn bao gồm: thông tin người bán (mã số thuế, tên, địa chỉ), thông tin người mua, thông tin chung (số hóa đơn, ngày phát hành, mẫu số, ký hiệu), chi tiết dòng hàng, tổng tiền, thuế, chiết khấu, và trạng thái thanh toán.

##### Xem mô tả của phần hóa đơn đầu vào


---

### Nhóm: Nghiệp vụ khác

- **Group ID**: `af30733d-7f67-11f1-9e9d-005056b2d809`


#### [POST] /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoiceaccountingdateV2 - Thiết lập hạch toán cho hóa đơn

- **Endpoint ID**: `af313dca-7f67-11f1-9e9d-005056b2d809`
- **Phương thức**: `POST`
- **Đường dẫn**: `/meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoiceaccountingdateV2`
- **Tóm tắt**: Thiết lập hạch toán cho hóa đơn

**Mô tả:**
API thiết lập thông tin hạch toán cho một hóa đơn đầu vào: tên kế toán, ngày hạch toán, số chứng từ.


**Headers bắt buộc:**




- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp

- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`



**Path parameters:**




- `SubscribersId` — ID subscriber (CompanyID) lấy từ API GetSubscribers

- `organizationId` — ID tổ chức lấy từ API GetOrganizations

##### 3. Request Body Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Accountant` | `string` | Có | Tên kế toán viên |
| `AccountingDate` | `string` | Có | Ngày hạch toán (format: yyyy-MM-dd) |
| `InvoiceId` | `string` | Có | ID của hóa đơn cần thiết lập hạch toán |
| `RefNo` | `string` | Không | Số chứng từ hạch toán |

##### Request Body Example
```json
{
    "Accountant": "Nguyễn Văn A",
    "AccountingDate": "2024-07-16",
    "InvoiceId": "6695f62aa9637d2e11998037",
    "RefNo": ""
}
```

##### 4. Response Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Success` | `bool` | Có | Trạng thái request: true = thành công, false = thất bại |
| `Message` | `string` | Không | Tin nhắn trả về nếu có lỗi |
| `Data` | `string` | Không | Kết quả thiết lập hạch toán: "true" = thành công, "false" = thất bại |

---

#### [POST] /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoiceaccountingdatemultiV2 - Thiết lập hạch toán cho nhiều hóa đơn

- **Endpoint ID**: `af31e1c1-7f67-11f1-9e9d-005056b2d809`
- **Phương thức**: `POST`
- **Đường dẫn**: `/meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoiceaccountingdatemultiV2`
- **Tóm tắt**: Thiết lập hạch toán cho nhiều hóa đơn

**Mô tả:**
API thiết lập thông tin hạch toán cho nhiều hóa đơn đầu vào cùng lúc. Tương tự API markForAccounting nhưng `InvoiceId` là mảng các ID hóa đơn.


**Headers bắt buộc:**




- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp

- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`



**Path parameters:**




- `SubscribersId` — ID subscriber (CompanyID) lấy từ API GetSubscribers

- `organizationId` — ID tổ chức lấy từ API GetOrganizations

##### 3. Request Body Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Accountant` | `string` | Có | Tên kế toán viên |
| `AccountingDate` | `string` | Có | Ngày hạch toán (format: yyyy-MM-dd) |
| `InvoiceId` | `string[]` | Có | Danh sách ID hóa đơn cần thiết lập hạch toán |
| `RefNo` | `string` | Không | Số chứng từ hạch toán |

##### Request Body Example
```json
{
    "Accountant": "Nguyễn Văn A",
    "AccountingDate": "2024-07-16",
    "InvoiceId": ["6695f62aa9637d2e11998037", "6695f62aa9637d2e11998038"],
    "RefNo": ""
}
```

##### 4. Response Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Success` | `bool` | Có | Trạng thái request: true = thành công, false = thất bại |
| `Message` | `string` | Không | Tin nhắn trả về nếu có lỗi |
| `Data` | `string` | Không | Kết quả thiết lập hạch toán: "true" = thành công, "false" = thất bại |

---

#### [POST] /meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoicepayment - Cập nhật thông tin thanh toán hóa đơn

- **Endpoint ID**: `af32748d-7f67-11f1-9e9d-005056b2d809`
- **Phương thức**: `POST`
- **Đường dẫn**: `/meinvoicebot/v1/{SubscribersId}/{organizationId}/invoices/invoicepayment`
- **Tóm tắt**: Cập nhật thông tin thanh toán hóa đơn

**Mô tả:**
API cập nhật thông tin thanh toán cho một hóa đơn đầu vào: ngày thanh toán, người thanh toán, số tiền thanh toán, trạng thái thanh toán.


**Headers bắt buộc:**




- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp

- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`



**Path parameters:**




- `SubscribersId` — ID subscriber (CompanyID) lấy từ API GetSubscribers

- `organizationId` — ID tổ chức lấy từ API GetOrganizations



**Trạng thái thanh toán (AmountPayment):**




- `0` — Không thiết lập

- `1` — Chưa thanh toán

- `2` — Thanh toán toàn phần

- `3` — Quá hạn thanh toán

- `4` — Đến hạn thanh toán

- `5` — Thanh toán một phần

##### 3. Request Body Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `InvoiceId` | `string` | Có | ID của hóa đơn cần cập nhật thanh toán |
| `PaymentDate` | `string` | Có | Ngày thanh toán (format: yyyy/MM/dd) |
| `PaymentPair` | `string` | Không | Người thanh toán |
| `TotalAmountPayment` | `number` | Có | Số tiền đã thanh toán |
| `TotalAmountNotPayment` | `number` | Có | Số tiền chưa thanh toán |
| `NumberPaymentNext` | `string` | Không | Số ngày thanh toán tiếp theo |
| `AmountPayment` | `int` | Có | Trạng thái thanh toán: 0=Không thiết lập, 1=Chưa thanh toán, 2=Thanh toán toàn phần, 3=Quá hạn, 4=Đến hạn, 5=Thanh toán một phần |

##### Request Body Example
```json
{
    "InvoiceId": "6cb129c5-dc24-43b2-8a5e-2130c0d3d231",
    "PaymentDate": "2024/07/18",
    "PaymentPair": "nxson",
    "TotalAmountPayment": 100000,
    "TotalAmountNotPayment": 100001,
    "NumberPaymentNext": "",
    "AmountPayment": 1
}
```

##### 4. Response Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Success` | `bool` | Có | Trạng thái request: true = thành công, false = thất bại |
| `Message` | `string` | Không | Tin nhắn trả về nếu có lỗi |
| `Data` | `string` | Không | Kết quả cập nhật thanh toán: "true" = thành công, "false" = thất bại |

---

### Nhóm: Tải hóa đơn

- **Group ID**: `019fad0e-89b0-7aee-810b-d825ddc60635`


#### [POST] /meinvoicebot/v1/{SubscribersId}/{organizationId}/download/zip - Tạo key tải hóa đơn

- **Endpoint ID**: `019fad0f-f31d-7200-9259-9a92944fba1b`
- **Phương thức**: `POST`
- **Đường dẫn**: `/meinvoicebot/v1/{SubscribersId}/{organizationId}/download/zip`
- **Tóm tắt**: Tạo key tải hóa đơn

**Mô tả:**
API này trả về key download để sử dụng cho đầu API tải hóa đơn tiếp theo.

**Headers bắt buộc:**


- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp
- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`

**Path parameters:**


- `SubscribersId` — SubscribersID lấy từ API GetSubscribers
- `organizationId` — OrganizationID lấy từ API GetOrganizations

##### 3. Request Body Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `FileType` | `string` | Có | type dữ liệu : 1: xml+pdf,2:pdf,3:xml |
| `LstInvID` | `string` | Có | Danh sách id của hóa đơn |
| `IsInbot` | `boolean` | Không | Cờ đánh dấu là hóa đơn đầu vào hay đầu ra :  true => hóa đơn đầu vào, false => Hóa đơn đầu ra ,  không truyền thì mặc định = true |

##### Request Body Example
```json
{
    "FileType": 1,  
    "LstInvID": ["019db325f9467197aa27242558589e20","019c360c3a3076748f3c23b97a73dbbf"],
    "IsInbot": false
}
```

##### 4. Response Parameters
| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| `Success` | `string` | Không | kết quả request |
| `Data` | `string` | Không | chứa key download |
| `IsErrorBusiness` | `string` | Không | Mã lỗi trả về |

---

#### [GET] /meinvoicebot/v1/{SubscribersId}/{organizationId}/download/{Key}/download - Tải hóa đơn theo key

- **Endpoint ID**: `019fad19-237e-76d2-b555-09d97e03caca`
- **Phương thức**: `GET`
- **Đường dẫn**: `/meinvoicebot/v1/{SubscribersId}/{organizationId}/download/{Key}/download`
- **Tóm tắt**: Tải hóa đơn theo key

**Mô tả:**
API này trả về hóa đơn dạng byte64

**Headers bắt buộc:**


- `ClientId` — ID được cấp bởi MISA khi đăng ký tích hợp
- `Authorization` — Bearer token (JWT) nhận từ API GetToken. Format: `Bearer {jwt_token}`

**Path parameters:**


- `SubscribersId` — SubscribersID lấy từ API GetSubscribers
- `organizationId` — OrganizationID lấy từ API GetOrganizations
- Key - Lấy từ đầu API lấy key tải

**Chú ý : **

Phương thức này sẽ trả về tệp nén dạng byte (gọi api này sau (10 x số hóa đơn tải) giây – để server của Inbot kịp nén dữ liệu)

Hoặc có thể thực hiện cơ chế: tạo key hóa đơn lúc yêu cầu, rồi cuối ngày thực hiện tải hóa đơn

Key tải hóa đơn tồn tại đến 24h cuối ngày

---

## BẢNG TỔNG HỢP MÃ LỖI TOÀN HỆ THỐNG (ERROR CODES)

<table style="border: none;"><tbody><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 12pt;">Mã lỗi**</p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: center;"><strong style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 12pt;">Mô tả**</p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">TAXCODENOTEXIST</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Mã số thuế chưa tồn tại</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">INVALIDTOKEN</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Mã bảo mật không hợp lệ</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">USER_NOT_EXIST</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Người dùng không tồn tại</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">MisaIdError</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Mã lỗi trả về từ MisaiD</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">INACTIVE_USER</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Người dùng bị ngừng theo dõi</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">INACTIVE_USER_WRONGPASSWORD</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Người dùng bị ngừng theo dõi và sai password</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">WrongPassWord</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Sai password</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">TwoFactorAuthen</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Tài khoản misaid bật xác thực hai lớp</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">InvalidUserId</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">sai param userid</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">INVALIDPARAMETER</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Tham số không hợp lệ</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">InvalidServiceToken</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Sai service token</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">INVALIDAPPID</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Mã ứng dụng không hợp lệ</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">INVALIDTOKEN</span></p></td><td style="height: 0pt; vertical-align: top; padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Mã số thuế chưa tồn tại</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; background-color: rgb(255, 255, 255); padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellbackgroundcolor="rgb(255, 255, 255)" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">TokenExpiredCode</span></p></td><td style="height: 0pt; vertical-align: top; background-color: rgb(255, 255, 255); padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellbackgroundcolor="rgb(255, 255, 255)" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Token hết hạn - Cần gọi hàm RefreshToken</span></p></td></tr><tr><td style="height: 0pt; vertical-align: top; background-color: rgb(255, 255, 255); padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellbackgroundcolor="rgb(255, 255, 255)" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">InvalidTokenCode</span></p></td><td style="height: 0pt; vertical-align: top; background-color: rgb(255, 255, 255); padding: 4.25197pt;"><p data-cellheight="0pt" data-cellpadding="4.25197pt" data-cellbackgroundcolor="rgb(255, 255, 255)" data-cellverticalalign="top" style="text-align: left;"><span style="background-color: transparent; color: rgb(0, 0, 0); font-family: Inter, sans-serif; font-size: 11pt;">Token lỗi cần đăng nhập lại</span></p></td></tr></tbody></table>

