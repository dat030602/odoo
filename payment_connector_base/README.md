Mình đồng ý. Với vai trò BA/SA, mình sẽ viết theo chuẩn tài liệu mà một team 5–20 dev có thể sử dụng để phát triển trực tiếp.

**Mục tiêu không phải là "ghi ý tưởng", mà là tạo ra Software Design Specification (SDS)**.

---

# Software Design Specification

## Project

**Generic Integration Framework for Odoo**

Version: 1.0

---

# 1. Vision

## 1.1 Mục tiêu

Xây dựng một framework tích hợp API theo hướng **Configuration Driven** (Low-code).

Framework phải cho phép tích hợp bất kỳ hệ thống bên ngoài nào mà **không cần sửa Core**.

Ví dụ:

* Payment Gateway
* Shipping
* ERP
* CRM
* E-Invoice
* SMS
* Email
* Banking
* AI Service
* OAuth Provider

Framework phải hỗ trợ cấu hình toàn bộ:

* API
* Authentication
* Payload
* Header
* Query Parameter
* Hash
* Signature
* Request
* Response
* Mapping
* Webhook
* Cron
* Logging

thông qua giao diện Odoo.

---

# 1.2 Mục tiêu thiết kế

Framework phải đáp ứng:

✓ Dynamic

✓ Extendable

✓ Low-code

✓ Reusable

✓ Configurable

✓ Secure

✓ Audit-able

✓ Versionable

✓ Multi Provider

✓ Multi Environment

---

# 1.3 Triết lý thiết kế

Framework không biết:

* MoMo
* VNPay
* Stripe
* DHL
* GHN

Framework chỉ biết:

```
Provider
    ↓
API
    ↓
Request
    ↓
Authentication
    ↓
HTTP
    ↓
Response
    ↓
Business Action
```

Mọi đặc thù của từng nhà cung cấp phải nằm trong **Configuration** hoặc **Plugin**, không nằm trong Core.

---

# 1.4 Design Principle

## Open Close Principle

Core không được sửa khi thêm Provider.

Ví dụ

```
Base

↓

Install

payment_momo

↓

Install

payment_vnpay

↓

Install

shipping_ghn

↓

Core không thay đổi.
```

---

## Single Responsibility

Mỗi Engine chỉ làm một việc.

Ví dụ

Hash Engine

chỉ hash.

Không build payload.

---

Payload Engine

chỉ build payload.

Không gọi API.

---

HTTP Engine

chỉ gửi request.

Không parse response.

---

Response Engine

chỉ parse response.

Không update Invoice.

---

Business Engine

chỉ thực hiện nghiệp vụ.

---

# 1.5 Kiến trúc tổng thể

```
                  +---------------------+
                  |     Odoo Record     |
                  +----------+----------+
                             |
                             |
                      Load Engine
                             |
                             |
                     Mapping Engine
                             |
                +------------+-----------+
                |                        |
        Compute Pipeline          Condition Engine
                |                        |
                +------------+-----------+
                             |
                       Payload Builder
                             |
                             |
                      Header Builder
                             |
                             |
                      Authentication
                             |
                             |
                       Signature Engine
                             |
                             |
                        HTTP Engine
                             |
                             |
                       Response Parser
                             |
                             |
                      Response Mapping
                             |
                             |
                    Business Action Engine
                             |
                             |
                           Logging
```

---

# 1.6 Các thành phần

## Core Engine

Framework gồm các Engine sau

| Engine                | Trách nhiệm             |
| --------------------- | ----------------------- |
| Load Engine           | Lấy dữ liệu nguồn       |
| Mapping Engine        | Mapping Source → Target |
| Compute Engine        | Transform dữ liệu       |
| Payload Builder       | Sinh Payload            |
| Header Builder        | Sinh Header             |
| Query Builder         | Sinh Query String       |
| Path Builder          | Sinh URL Parameter      |
| Authentication Engine | Xác thực                |
| Hash Engine           | Hash dữ liệu            |
| HTTP Engine           | Gửi HTTP Request        |
| Response Engine       | Parse Response          |
| Status Engine         | Mapping trạng thái      |
| Business Engine       | Xử lý nghiệp vụ         |
| Webhook Engine        | Nhận callback           |
| Scheduler Engine      | Đồng bộ định kỳ         |
| Logging Engine        | Audit Log               |
| Cache Engine          | Cache Token             |
| Plugin Engine         | Extension               |

---

# 1.7 Module Structure

```
connector_base/

    models/

    views/

    security/

    wizard/

    data/

    services/

        load_engine.py

        payload_engine.py

        mapping_engine.py

        compute_engine.py

        auth_engine.py

        hash_engine.py

        http_engine.py

        response_engine.py

        webhook_engine.py

        scheduler_engine.py

        cache_engine.py

        business_engine.py

        plugin_engine.py

```

Module Provider

```
payment_momo/

payment_vnpay/

shipping_ghn/

shipping_ghtk/

einvoice_meinvoice/

einvoice_vnpt/
```

Provider chỉ khai báo:

* API
* Setting
* Mapping
* Plugin (nếu cần)

Không sửa Engine.

---

# 1.8 Khả năng mở rộng

Framework phải hỗ trợ:

### Authentication

```
API Key

Basic

Bearer

JWT

OAuth2

HMAC

Custom
```

---

### Hash

```
MD5

SHA1

SHA256

SHA512

HMAC SHA256

HMAC SHA512

Custom
```

---

### Payload

```
JSON

XML

Multipart

Form Data

Raw

Binary
```

---

### Response

```
JSON

XML

HTML

CSV

TEXT
```

---

### HTTP Method

```
GET

POST

PUT

PATCH

DELETE
```

---

### Compute

Built-in

Custom Plugin

Python Expression

---

### Business Action

```
Create Record

Update Record

Call Method

Workflow

Server Action

Queue Job
```

---

# 1.9 Non Functional Requirement

## Performance

* Build Payload < 50 ms
* Compute < 20 ms
* HTTP Timeout configurable
* Retry configurable
* Support async (queue_job) cho các request không cần phản hồi ngay.

## Security

* Secret được mã hóa khi lưu.
* Không ghi Secret vào log.
* Verify Signature trước khi xử lý Webhook.
* Có whitelist IP cho Webhook (nếu nhà cung cấp hỗ trợ).
* Có cơ chế chống xử lý trùng (idempotency) bằng transaction/reference.

## Audit

Lưu đầy đủ:

* Request
* Response
* Payload
* Header (ẩn thông tin nhạy cảm)
* Duration
* Retry
* Exception
* User
* Company
* Timestamp

## Multi-company

* Mỗi Company có thể cấu hình Provider khác nhau.
* Cho phép cùng một Provider nhưng nhiều cấu hình (ví dụ nhiều Merchant).

## Version

Mỗi API có Version riêng.

Ví dụ:

```
MoMo

V2

V3
```

Không ảnh hưởng API cũ.

---

# 1.10 Định hướng phát triển

Framework được thiết kế để **không chỉ phục vụ Payment**, mà trở thành nền tảng tích hợp chung cho Odoo. Mọi module tích hợp sau này (ngân hàng, vận chuyển, hóa đơn điện tử, CRM, AI...) đều sử dụng cùng một Engine, chỉ bổ sung cấu hình và plugin khi cần.

---

## Kết quả của Chương 1

Sau chương này, team dev sẽ hiểu rõ:

* Phạm vi của framework.
* Triết lý thiết kế.
* Kiến trúc tổng thể.
* Các engine cần xây dựng.
* Các yêu cầu phi chức năng.
* Nguyên tắc mở rộng.

### Chương tiếp theo (Chương 2)

Mình sẽ đi vào **Domain Model & ERD**, bao gồm:

* Danh sách toàn bộ model của framework.
* Quan hệ giữa các model.
* Giải thích trách nhiệm của từng model.
* Xác định model nào là Core, model nào là Configuration, model nào là Runtime (Transaction/Log).

Đây sẽ là nền tảng để bắt đầu thiết kế database và triển khai code.

Tuyệt. Từ chương này mình sẽ viết như một **Solution Architect**. Mục tiêu là sau khi đọc xong, dev backend có thể bắt đầu tạo model mà gần như không cần hỏi lại BA.

---

# Chương 2 - Domain Model & ERD

---

# 2.1 Mục tiêu

Thiết kế Database theo hướng:

* Generic
* Reusable
* Configuration Driven
* Không phụ thuộc Provider
* Không phụ thuộc Payment

Framework chia thành 4 nhóm Model:

```text
Configuration
        │
        ▼
Execution
        │
        ▼
Transaction
        │
        ▼
Logging
```

---

# 2.2 Phân loại Model

## I. Configuration

Đây là phần admin cấu hình.

```text
connector.provider

connector.environment

connector.setting

connector.api

connector.api.version

connector.api.endpoint

connector.auth.method

connector.hash.method

connector.compute.function

connector.business.action

connector.mapping

connector.mapping.line

connector.status.mapping

connector.plugin
```

---

## II. Runtime

Lúc Engine chạy.

```text
connector.execution

connector.execution.step

connector.context

connector.cache

connector.webhook
```

---

## III. Transaction

Lưu giao dịch.

```text
connector.transaction

connector.transaction.retry

connector.scheduler.job
```

---

## IV. Logging

```text
connector.log

connector.request.log

connector.response.log

connector.error.log
```

---

# 2.3 Tổng quan ERD

```text
Provider
   │
   ├──────── Environment
   │
   ├──────── Setting
   │
   ├──────── API
   │             │
   │             ├──────── Header Mapping
   │             │
   │             ├──────── Query Mapping
   │             │
   │             ├──────── Payload Mapping
   │             │
   │             ├──────── Response Mapping
   │             │
   │             ├──────── Status Mapping
   │             │
   │             ├──────── Authentication
   │             │
   │             ├──────── Hash
   │             │
   │             └──────── Business Action
   │
   └──────── Plugin
```

Đây là ERD logic. ERD vật lý sẽ được mô tả sau.

---

# 2.4 connector.provider

Đây là model cao nhất.

Một Provider đại diện cho

* MoMo
* VNPay
* Stripe
* GHN
* VNPT Invoice

Không chứa logic.

Chỉ chứa metadata.

## Quan hệ

```text
Provider

↓

API

↓

Environment

↓

Setting

↓

Plugin
```

---

Field

| Field             | Type    | Required | Note            |
| ----------------- | ------- | -------- | --------------- |
| name              | Char    | ✓        | Display Name    |
| code              | Char    | ✓        | Unique          |
| active            | Boolean | ✓        |                 |
| description       | Text    |          |                 |
| module_name       | Char    |          | module cung cấp |
| company_dependent | Boolean |          |                 |

---

Constraint

```text
code unique
```

Ví dụ

```text
momo

vnpay

stripe

ghn
```

---

# 2.5 connector.environment

Một Provider có nhiều Environment.

Ví dụ

```text
MoMo

Sandbox

Production

UAT
```

---

Field

| Field       | Type     |
| ----------- | -------- |
| provider_id | Many2one |
| name        | Char     |
| code        | Char     |
| active      | Boolean  |
| priority    | Integer  |

---

Một Company có thể chọn Environment.

Không phải Provider.

---

# 2.6 connector.setting

Đây là phần rất quan trọng.

Không hardcode:

```python
partnerCode

accessKey

merchantId

secret
```

Mọi thứ đều là Record.

---

Field

| Field          | Type    |
| -------------- | ------- |
| provider_id    | M2O     |
| environment_id | M2O     |
| name           | Char    |
| code           | Char    |
| value          | Text    |
| encrypt        | Boolean |
| required       | Boolean |
| readonly       | Boolean |
| description    | Text    |

---

Ví dụ

```text
Partner Code

partner_code

MOMO
```

```text
Access Key

access_key

xxxxxxxx
```

---

Engine lấy

```python
provider.get_setting("partner_code")
```

---

# 2.7 connector.api

Provider

↓

API

Ví dụ

MoMo

↓

```text
Create Payment

Refund

Query Payment

Webhook

Token
```

---

Field

| Field       | Type      |
| ----------- | --------- |
| provider_id | M2O       |
| name        | Char      |
| code        | Char      |
| method      | Selection |
| endpoint    | Char      |
| body_type   | Selection |
| parser      | Selection |
| timeout     | Integer   |
| retry       | Integer   |
| active      | Boolean   |

---

Một API có

```text
Header

Payload

Response

Hash

Business Action
```

---

# 2.8 connector.mapping

Đây là trái tim Framework.

Không còn gọi Payload.

Vì dùng chung.

Ví dụ

Request

```text
Invoice.amount_total

↓

amount
```

Response

```text
resultCode

↓

payment_state
```

Là cùng một Engine.

---

Field

| Field  | Type      |
| ------ | --------- |
| api_id | M2O       |
| type   | Selection |
| name   | Char      |
| code   | Char      |
| active | Boolean   |

---

type

```text
Header

Payload

Query

Path

Response

```

---

# 2.9 connector.mapping.line

Đây là model lớn nhất.

Một dòng Mapping.

---

Field

| Field            | Type      |
| ---------------- | --------- |
| mapping_id       | M2O       |
| parent_id        | Self      |
| sequence         | Integer   |
| key              | Char      |
| source_type      | Selection |
| source_path      | Char      |
| fixed_value      | Text      |
| default_value    | Text      |
| compute_pipeline | O2M       |
| condition        | Char      |
| required         | Boolean   |
| is_array         | Boolean   |
| loop_path        | Char      |
| datatype         | Selection |

---

source_type

```text
Field

Fixed

Setting

Variable

Context

Expression

Plugin
```

---

datatype

```text
String

Integer

Float

Boolean

Date

Datetime

Object

Array

```

---

Nhờ parent_id

Engine build được

```json
{
   "partnerInfo":{
      "id":""
   }
}
```

Không cần code.

---

# 2.10 connector.compute.pipeline

Đây là ý mình muốn cải tiến thêm so với hội thoại trước.

Không lưu

```text
Compute = round
```

Mà lưu

Pipeline.

Ví dụ

```text
amount

↓

round

↓

multiply

↓

string

↓

amount
```

---

Model

```text
connector.compute.pipeline
```

---

Field

| Field           | Type    |
| --------------- | ------- |
| mapping_line_id | M2O     |
| sequence        | Integer |
| function_id     | M2O     |
| parameter       | Text    |

---

Engine

```python
value

↓

function1

↓

function2

↓

function3

↓

Done
```

---

# 2.11 connector.compute.function

Builtin

*

Plugin

---

Field

| Field       | Type      |
| ----------- | --------- |
| name        | Char      |
| code        | Char      |
| type        | Selection |
| python_code | Text      |
| active      | Boolean   |

---

type

```text
Builtin

Custom
```

---

Ví dụ

```text
uuid

format_date

round

multiply

base64

```

---

# 2.12 connector.hash.method

Không hardcode.

---

Field

| Field       | Type      |
| ----------- | --------- |
| name        | Char      |
| code        | Char      |
| algorithm   | Selection |
| python_path | Char      |

---

Ví dụ

```text
SHA256

HMAC SHA256

SHA512

```

---

# 2.13 connector.auth.method

Authentication.

---

Field

```text
API Key

Bearer

Basic

JWT

OAuth2

Custom
```

---

Không để API tự xử lý.

---

# 2.14 connector.business.action

Sau Response.

Engine phải làm gì?

---

Ví dụ

```text
Create Payment

Reconcile

Update Invoice

Call Method

Server Action

Queue Job

```

Không hardcode.

---

# 2.15 connector.status.mapping

Ví dụ

MoMo

```text
0

↓

Paid
```

```text
1006

↓

Pending
```

---

Không code.

---

# 2.16 Runtime Models

Runtime không phải cấu hình.

Ví dụ

```text
connector.execution
```

Lưu

```text
Execution ID

Start

End

Duration

Provider

API

Status

```

---

Execution Step

```text
Load

↓

Payload

↓

Hash

↓

HTTP

↓

Parser

↓

Business

```

Nếu lỗi

Biết lỗi tại đâu.

---

# 2.17 Transaction

Không nên log chung.

Transaction đại diện

Một lần giao tiếp.

Có

```text
Request

↓

Response

↓

Retry

↓

Done
```

---

# 2.18 Logging

Log chia thành

```text
Execution Log

HTTP Log

Exception Log

Webhook Log

```

Không nên dồn vào một bảng vì sẽ rất lớn và khó truy vấn.

---

# Kết quả Chương 2

Sau chương này, team dev đã có:

* Danh sách model.
* Phân lớp rõ giữa Configuration, Runtime, Transaction và Logging.
* Quan hệ giữa các model.
* Nền tảng để thiết kế database vật lý và sinh các model Odoo.

---

## Một đề xuất kiến trúc quan trọng

Sau khi hoàn thiện ERD, mình thấy framework sẽ **sạch hơn nếu chia thành 3 module core** thay vì một module lớn:

```text
connector_core
```

Chứa:

* Provider
* Environment
* Setting
* Authentication
* Hash
* HTTP Engine
* Logging

```text
connector_mapping
```

Chứa:

* Mapping
* Mapping Line
* Compute Pipeline
* Compute Function
* Condition
* Variable
* Context

```text
connector_runtime
```

Chứa:

* Execution
* Transaction
* Webhook
* Cron
* Business Action
* Cache

Các module như `payment_provider_momo`, `payment_provider_vnpay`, `shipping_ghn`... chỉ phụ thuộc vào các module core này. Cách tách này giúp giảm phụ thuộc, dễ test từng phần và thuận tiện phát hành theo từng giai đoạn. Ở **Chương 3**, mình sẽ đặc tả chi tiết từng model (field, constraint, index, quyền truy cập và lifecycle) theo đúng mức độ mà lập trình viên có thể bắt đầu code ngay.

Rất tốt. Từ chương này mình sẽ chuyển hẳn sang mức **Technical Specification** (mức dev có thể code trực tiếp).

> Theo kinh nghiệm của mình, **Chương 3 là chương quan trọng nhất**. Nếu thiết kế tốt thì toàn bộ framework sẽ rất sạch. Nếu thiết kế không tốt thì sau này sẽ phải sửa DB rất nhiều.

---

# Chương 3 - Physical Database Design

## 3.1 Quy ước

Tất cả model sử dụng prefix

```python
connector.*
```

Ví dụ

```text
connector.provider

connector.api

connector.mapping

connector.execution
```

Không nên dùng

```text
payment.*

integration.*
```

vì framework không chỉ dành cho Payment.

---

# 3.2 Model Layer

Framework chia thành 3 layer

```text
Presentation

↓

Configuration

↓

Engine

↓

Runtime

↓

Business
```

Database chỉ quản lý

```text
Configuration

Runtime

Log
```

Engine hoàn toàn Stateless.

---

# 3.3 connector.provider

Đây là Root Entity.

## Table

```text
connector_provider
```

---

## Field

| Field             | Type    | Index  | Required | Remark |   |
| ----------------- | ------- | ------ | -------- | ------ | - |
| id                | PK      |        | ✓        |        |   |
| name              | Char    | ✓      | ✓        |        |   |
| code              | Char    | Unique | ✓        |        |   |
| description       | Text    |        |          |        |   |
| active            | Boolean |        | ✓        |        |   |
| module_name       | Char    |        |          |        |   |
| company_dependent | Boolean |        |          |        |   |
| icon              | Binary  |        |          |        |   |
| sequence          | Integer |        |          |        |   |
| version           | Char    |        |          |        |   |
| author            | Char    |        |          |        |   |

---

## Constraint

```python
code unique
```

---

## Relation

```text
Provider

↓

Environment

↓

Setting

↓

API
```

---

## Không lưu

Không được lưu

```text
Merchant

API Key

Secret

Endpoint
```

vì chúng thuộc Environment.

---

# 3.4 connector.environment

Một Provider có nhiều môi trường.

Ví dụ

```text
MoMo

Sandbox

Production

UAT

Demo
```

---

## Table

```text
connector_environment
```

---

## Field

| Field       | Type     |
| ----------- | -------- |
| provider_id | Many2one |
| company_id  | Many2one |
| name        | Char     |
| code        | Char     |
| base_url    | Char     |
| active      | Boolean  |
| priority    | Integer  |

---

## Constraint

Unique

```text
provider

company

code
```

---

Ví dụ

```text
MoMo

Sandbox
```

và

```text
MoMo

Production
```

---

# 3.5 connector.setting

Theo mình model này nên cực Generic.

Không nên làm

```text
Partner Code

Access Key

Secret Key
```

thành field.

Sai.

Nó phải là Record.

---

## Table

```text
connector_setting
```

---

## Field

| Field          | Type      |
| -------------- | --------- |
| environment_id | Many2one  |
| name           | Char      |
| code           | Char      |
| value          | Text      |
| value_type     | Selection |
| encrypt        | Boolean   |
| required       | Boolean   |
| readonly       | Boolean   |
| description    | Text      |

---

value_type

```text
String

Integer

Float

Boolean

Password

JSON
```

---

Encrypt

Nếu True

Runtime decrypt.

Không hiển thị.

---

Không log.

---

# 3.6 connector.api

Đây là entity lớn thứ hai.

Một Provider có nhiều API.

---

Table

```text
connector_api
```

---

Field

| Field          | Type      |
| -------------- | --------- |
| provider_id    | M2O       |
| environment_id | M2O       |
| name           | Char      |
| code           | Char      |
| method         | Selection |
| endpoint       | Char      |
| body_type      | Selection |
| parser         | Selection |
| timeout        | Integer   |
| retry          | Integer   |
| active         | Boolean   |
| description    | Text      |

---

method

```text
GET

POST

PUT

PATCH

DELETE
```

---

body

```text
JSON

XML

FORM

MULTIPART

RAW

NONE
```

---

parser

```text
JSON

XML

CSV

TEXT
```

---

# 3.7 Quan hệ API

Một API

↓

Header

↓

Payload

↓

Query

↓

Path

↓

Response

↓

Status

↓

Business

↓

Authentication

↓

Hash

Không nên để chung.

---

# 3.8 connector.mapping

Đây là trái tim Framework.

Một API

↓

N Mapping.

---

Table

```text
connector_mapping
```

---

Field

| Field    | Type      |
| -------- | --------- |
| api_id   | M2O       |
| type     | Selection |
| name     | Char      |
| code     | Char      |
| sequence | Integer   |
| active   | Boolean   |

---

type

```text
HEADER

QUERY

PATH

PAYLOAD

RESPONSE
```

---

Ví dụ

Payload

↓

100 dòng.

Header

↓

5 dòng.

---

# 3.9 connector.mapping.line

Đây là model lớn nhất.

Theo mình khoảng

25~30 field.

---

Table

```text
connector_mapping_line
```

---

Field

| Field           | Type      |
| --------------- | --------- |
| mapping_id      | M2O       |
| parent_id       | Self      |
| sequence        | Integer   |
| key             | Char      |
| display_name    | Char      |
| source_type     | Selection |
| source_path     | Char      |
| fixed_value     | Text      |
| default_value   | Text      |
| required        | Boolean   |
| ignore_if_empty | Boolean   |
| condition       | Char      |
| datatype        | Selection |
| is_array        | Boolean   |
| loop_source     | Char      |
| loop_alias      | Char      |
| description     | Text      |

---

## source_type

```text
FIELD

SETTING

FIXED

VARIABLE

CONTEXT

PLUGIN

EXPRESSION

NONE
```

---

FIELD

Ví dụ

```text
partner_id.name
```

---

SETTING

```text
partner_code
```

---

CONTEXT

```text
today
```

---

VARIABLE

```text
amount100
```

---

PLUGIN

Plugin trả object.

---

# 3.10 Parent

Payload

```json
{
  "customer":{
      "id":"",
      "name":""
  }
}
```

Không cần code.

Chỉ cần

```text
parent_id
```

---

# 3.11 Array

Ví dụ

```json
items:[
]
```

Field

```text
is_array=True
```

Loop

```text
invoice_line_ids
```

Alias

```text
line
```

Trong child

```text
line.price_unit
```

---

# 3.12 datatype

Không phải Python.

Mà Business.

```text
STRING

INTEGER

FLOAT

BOOLEAN

DATE

DATETIME

OBJECT

ARRAY

NULL
```

Engine convert.

---

# 3.13 connector.compute.pipeline

Đây là điểm mình muốn nâng cấp nhiều nhất.

Không phải

```text
Compute

↓

Round
```

Mà là

Pipeline.

---

Ví dụ

```text
amount

↓

round(2)

↓

multiply(100)

↓

abs()

↓

string()

↓

Done
```

---

Table

```text
connector_compute_pipeline
```

---

Field

| Field           | Type    |
| --------------- | ------- |
| mapping_line_id | M2O     |
| sequence        | Integer |
| function_id     | M2O     |
| parameter_json  | Text    |
| stop_if_none    | Boolean |
| description     | Text    |

---

Parameter

JSON.

Ví dụ

```json
{
  "digit":2
}
```

---

# 3.14 Function

Table

```text
connector_compute_function
```

---

Field

| Field       | Type      |
| ----------- | --------- |
| name        | Char      |
| code        | Char      |
| type        | Selection |
| python_code | Text      |
| safe        | Boolean   |
| active      | Boolean   |

---

Builtin

```text
round

uuid

format_date

base64

```

---

Custom

Admin thêm.

---

# 3.15 Hash

Table

```text
connector_hash_method
```

---

Field

| Field       | Type      |
| ----------- | --------- |
| name        | Char      |
| code        | Char      |
| algorithm   | Selection |
| python_path | Char      |

---

Ví dụ

```text
SHA256

SHA512

MD5

HMAC SHA256
```

---

# 3.16 Auth

Không chỉ Payment.

---

Table

```text
connector_auth_method
```

---

Ví dụ

```text
OAuth2

JWT

Bearer

Basic

APIKey

Custom
```

---

# 3.17 Business Action

Theo mình nên dùng Strategy Pattern.

Business Action

không biết Payment.

---

Ví dụ

```text
Create Record

Update Record

Call Method

Queue Job

Server Action

Webhook

```

---

# 3.18 Execution

Execution

=

1 lần chạy.

---

Table

```text
connector_execution
```

---

Field

| Field       | Type      |
| ----------- | --------- |
| provider_id | M2O       |
| api_id      | M2O       |
| state       | Selection |
| start_time  | Datetime  |
| end_time    | Datetime  |
| duration    | Float     |
| retry       | Integer   |
| error       | Text      |

---

# 3.19 Execution Step

Đây là điểm mình khá thích.

Một Execution

↓

N Step

---

Ví dụ

```text
Load

OK

↓

Payload

OK

↓

Hash

OK

↓

HTTP

Fail
```

Không cần debug log.

Nhìn UI biết.

---

# 3.20 Log

Không nên lưu một bảng.

Theo mình nên chia

```text
connector_request_log

connector_response_log

connector_exception_log

connector_webhook_log

connector_scheduler_log
```

Lý do

Một số bảng sẽ cực lớn.

Query nhanh hơn.

---

# 3.21 Index

Các field bắt buộc index

```text
provider_id

environment_id

api_id

execution_id

company_id

code

state

create_date
```

---

# 3.22 Những điểm mình đề xuất thay đổi so với ý tưởng ban đầu

Đây là phần mình nghĩ sẽ giúp framework mạnh hơn khi triển khai thực tế:

### 1. Tách `connector.api` thành 2 model

Hiện tại `connector.api` đang chứa cả thông tin endpoint và cấu hình thực thi. Mình đề xuất:

```text
connector.api
```

* Name
* Code
* Provider
* Version
* Mục đích nghiệp vụ

```text
connector.api.endpoint
```

* Environment
* URL
* HTTP Method
* Timeout
* Retry
* Authentication
* Hash
* Body Type
* Parser

**Lợi ích:** cùng một API (`Create Payment`) có thể có endpoint khác nhau giữa Sandbox và Production, hoặc giữa phiên bản v2/v3 mà không cần nhân bản toàn bộ API.

---

### 2. Thêm `connector.variable`

Hiện bạn mới nhắc đến Variable trong Mapping, nhưng nên quản lý như một Runtime Context riêng:

```text
connector.variable
```

Ví dụ trong một Execution:

```text
uuid = xxxxx

token = yyyyy

amount100 = 150000

signature_string = abc...
```

Pipeline và các Mapping Line đều có thể đọc lại các biến này.

---

### 3. Thêm `connector.template`

Nhiều API yêu cầu chuỗi ký hoặc payload theo mẫu cố định.

Ví dụ:

```text
partnerCode={partnerCode}&orderId={orderId}&amount={amount}
```

Nếu có Template Engine, admin chỉ cần cấu hình template thay vì viết Expression hoặc Plugin.

---

Theo mình, **3 model này sẽ giảm đáng kể số lượng code đặc thù của từng Provider**, đặc biệt là với MoMo, VNPay, ZaloPay và các API ngân hàng. Chúng cũng là nền tảng tốt cho các chương tiếp theo, nơi mình sẽ đặc tả **Engine** (Load Engine, Mapping Engine, Compute Engine, HTTP Engine...) và luồng thực thi chi tiết. Đây sẽ là phần trực tiếp quyết định cách triển khai code của framework.

Rất hay. Từ đây trở đi chúng ta sẽ đi vào **Engine Design**. Đây mới là phần quyết định framework có thực sự "low-code" hay không.

Theo kinh nghiệm mình làm Integration Platform, **đừng code theo Model**, mà hãy code theo **Pipeline**.

Nghĩa là toàn bộ Framework chỉ có một Engine.

Mọi Provider chỉ cấu hình.

---

# Chương 4 - Engine Architecture

---

# 4.1 Design Principle

Framework không chạy theo Provider.

Framework chạy theo Pipeline.

Ví dụ

```text
Invoice

↓

Execution

↓

Load Engine

↓

Mapping Engine

↓

Compute Engine

↓

Authentication Engine

↓

HTTP Engine

↓

Response Engine

↓

Business Engine

↓

Finish
```

MoMo hay VNPay đều đi chung pipeline.

---

# 4.2 Execution Pipeline

Mình đề xuất Runtime chỉ có một hàm duy nhất.

```python
execute(api_code, source_record)
```

Ví dụ

```python
execute(
    api_code="create_payment",
    source_record=invoice
)
```

Engine tự làm tất cả.

Không gọi

```python
create_momo_payment()

create_vnpay()

call_xxx()
```

Sai design.

---

# 4.3 Engine Layer

```text
Execution Engine
        │
        ▼
Load Engine
        │
        ▼
Mapping Engine
        │
        ▼
Compute Engine
        │
        ▼
Template Engine
        │
        ▼
Authentication Engine
        │
        ▼
Hash Engine
        │
        ▼
HTTP Engine
        │
        ▼
Response Engine
        │
        ▼
Business Engine
        │
        ▼
Logging Engine
```

---

# 4.4 Execution Engine

Đây là Entry Point.

Trách nhiệm

* tạo execution
* tạo context
* load provider
* load api
* chạy pipeline
* rollback nếu lỗi
* log

Pseudo

```python
execution = create_execution()

context = build_context()

load()

map()

compute()

auth()

request()

parse()

business()

finish()
```

Execution Engine không biết HTTP.

Không biết Hash.

---

# 4.5 Context

Mình muốn bổ sung một object rất quan trọng.

```
ConnectorContext
```

Ví dụ

```python
context.provider

context.environment

context.api

context.execution

context.record

context.company

context.user

context.variables

context.cache
```

Tất cả Engine chỉ nhận

```python
context
```

Không truyền

20 parameter.

---

# 4.6 Load Engine

Đây là bước đầu tiên.

Input

```python
record
```

Ví dụ

Invoice.

Output

Dictionary.

```python
{
    "invoice":record,
    "company":company,
    "partner":partner
}
```

Sau này Mapping đọc.

---

## Hook

Đây là nơi Provider có thể override.

Ví dụ

MoMo

cần thêm

```python
token
```

Override

```python
load_extra()
```

Không sửa Core.

---

# 4.7 Mapping Engine

Đây là Engine lớn nhất.

Input

```python
Mapping
```

↓

build object.

Ví dụ

```python
partner.name

↓

customerName
```

Hay

```python
partner.country.code

↓

country
```

Không code.

---

## Mapping Flow

```text
Load Source

↓

Default

↓

Condition

↓

Compute

↓

Datatype

↓

Parent

↓

Object

↓

Done
```

---

# 4.8 Source Resolver

Đây là class riêng.

Không để Mapping Engine đọc Field.

Ví dụ

```python
partner_id.name
```

↓

Resolver.

Sau này

Setting

Variable

Plugin

đều dùng Resolver.

---

Mình đề xuất

```python
resolve(
    type,
    path
)
```

Ví dụ

```python
resolve(
 FIELD,
 "partner_id.name"
)
```

---

# 4.9 Variable Engine

Đây là phần hôm trước mình đề xuất.

Runtime

```python
variables={}
```

Ví dụ

```python
uuid

↓

save
```

Sau này

Signature

↓

lấy luôn.

Không tính lại.

---

# 4.10 Compute Engine

Không phải

```python
round(value)
```

Mà là

Pipeline.

Ví dụ

```text
amount

↓

round

↓

multiply

↓

string

↓

trim

↓

Done
```

Engine

```python
for step:

 execute(step)
```

---

# 4.11 Compute Function

Mình đề xuất chia

## Builtin

Code Python.

Ví dụ

```python
uuid()

today()

base64()

round()

format_date()

```

---

## Plugin

Module khác đăng ký.

Ví dụ

```python
my_function()
```

Không sửa Framework.

---

## Expression

Ví dụ

```
amount*100
```

Admin nhập.

safe_eval.

---

# 4.12 Template Engine

Đây là điểm mình muốn thêm.

Ví dụ

MoMo.

Chuỗi ký

```
partnerCode={partnerCode}&amount={amount}
```

Admin nhập.

Không code.

Engine

↓

Render.

Không cần

Plugin.

---

Mình còn muốn dùng cho

URL

```
/payment/{id}
```

Email

Webhook

Body

đều dùng.

---

# 4.13 Authentication Engine

Authentication

không nên nằm HTTP.

Sai Responsibility.

Authentication chỉ trả

```
Header

Query

Token

```

Ví dụ

Bearer.

↓

Header.

OAuth

↓

refresh token.

APIKey

↓

query.

---

# 4.14 Hash Engine

Hash

không biết HTTP.

Input

```
String
```

Output

```
Signature
```

Ví dụ

VNPay

↓

sort

↓

join

↓

hash

↓

signature

---

Mình đề xuất

Hash Builder

và

Hash Method

tách riêng.

Hash Builder

quyết định

```
field nào

separator

sort

```

Hash Method

chỉ hash.

---

# 4.15 HTTP Engine

HTTP

rất đơn giản.

Input

```
Method

URL

Header

Payload

```

Output

```
Raw Response
```

Không parse.

---

Retry.

Timeout.

SSL.

Proxy.

đều ở đây.

---

# 4.16 Response Engine

Input

Raw.

↓

Parser.

↓

Mapping.

↓

Status.

↓

Object.

Không update Invoice.

---

Parser

```
JSON

XML

CSV

HTML

TEXT
```

---

# 4.17 Business Engine

Sau khi parse.

Business

quyết định

làm gì.

Ví dụ

```
Create Payment

↓

Reconcile

↓

Invoice Paid
```

Hay

```
Update Delivery

```

Không liên quan Payment.

---

# 4.18 Plugin Engine

Mình muốn thêm một Registry.

Ví dụ

```python
register_plugin(
 code,
 class
)
```

Framework

không import.

Module khác

đăng ký.

Giống Odoo Report.

---

# 4.19 Logging Engine

Mỗi Step

↓

Log.

Ví dụ

```text
Load

12ms

OK
```

```text
Compute

4ms

OK
```

```text
HTTP

650ms

OK
```

Debug cực dễ.

---

# 4.20 Error Strategy

Mình đề xuất **không raise Exception ngay**.

Thay vào đó dùng Error Object xuyên suốt pipeline.

Ví dụ:

```python
ExecutionResult
```

```python
success

message

error

step

response
```

Nếu cần dừng:

```python
return result.fail(
    step="Hash",
    message="Missing secret_key"
)
```

Execution Engine quyết định:

* rollback
* retry
* log
* notify

Thay vì mỗi Engine tự xử lý exception.

---

# 4.21 Sequence Diagram

Luồng đầy đủ:

```text
User
 │
 ▼
Execution Engine
 │
 ▼
Load Engine
 │
 ▼
Mapping Engine
 │
 ▼
Compute Pipeline
 │
 ▼
Template Engine
 │
 ▼
Authentication Engine
 │
 ▼
Hash Engine
 │
 ▼
HTTP Engine
 │
 ▼
Response Parser
 │
 ▼
Response Mapping
 │
 ▼
Business Action
 │
 ▼
Logging
 │
 ▼
Done
```

---

# Những cải tiến mình đề xuất thêm sau khi hoàn thiện Chương 4

Đây là những điểm mình nghĩ sẽ làm framework "enterprise" hơn:

### 1. Event Bus nội bộ

Thay vì chỉ có Hook, mỗi bước phát sự kiện:

```text
before_execution
after_load
before_mapping
after_mapping
before_http
after_http
before_business
after_business
```

Module khác chỉ cần subscribe mà không override Engine.

---

### 2. Queue Mode

Execution nên hỗ trợ 3 chế độ:

* **Sync**: chạy ngay, trả kết quả.
* **Async**: đẩy vào `queue_job` hoặc hàng đợi.
* **Schedule**: chạy theo Cron.

Cùng một Engine, chỉ khác cách khởi tạo Execution.

---

### 3. Transaction Boundary

Mình đề xuất mỗi Execution có cấu hình:

* Commit sau mỗi Step.
* Commit sau Business Action.
* Rollback toàn bộ nếu lỗi.

Điều này rất quan trọng khi tích hợp với Odoo Accounting để tránh dữ liệu nửa chừng.

---

Theo lộ trình mình đang xây, **Chương 5 sẽ là Mapping Engine Specification**. Đây sẽ là chương dài nhất của tài liệu (ước khoảng 40–60 trang nếu viết đầy đủ), vì nó sẽ đặc tả toàn bộ DSL (Domain Specific Language) cho Mapping, Compute Pipeline, Variable, Condition, Loop, Array, Template và cách admin cấu hình để gần như không cần viết code khi tích hợp một Provider mới. Đây cũng là phần tạo nên giá trị lớn nhất của framework.

Đây là chương mình nghĩ là **quan trọng nhất của toàn bộ framework**.

> Theo mình, nếu **Mapping Engine** thiết kế tốt thì khoảng **80-90% Provider sẽ không cần viết code**.

Ở đây mình sẽ thay đổi một chút so với ý tưởng ban đầu.

**Không còn gọi là Payload Mapping nữa.**

Mình gọi là

> **Data Transformation Engine**

Tức là framework chỉ làm một việc:

> **Biến đổi dữ liệu từ A → B**

A có thể là

* Odoo Record
* JSON
* XML
* Dict
* Context
* Variable

B có thể là

* JSON
* Dict
* XML
* Header
* Query
* Business Object

Đây là điểm khác biệt so với rất nhiều framework Integration.

---

# Chương 5 - Data Transformation Engine

---

# 5.1 Triết lý

Framework KHÔNG build Payload.

Framework KHÔNG parse Response.

Framework chỉ làm

```text
Source

↓

Resolve

↓

Transform

↓

Build

↓

Target
```

Payload chỉ là một Target.

Response cũng là một Target.

---

# 5.2 Mapping Lifecycle

Một Mapping Line sẽ trải qua đúng 12 bước.

```text
1 Resolve Source

↓

2 Default

↓

3 Required Validation

↓

4 Condition

↓

5 Compute Pipeline

↓

6 Datatype Convert

↓

7 Variable Save

↓

8 Template Render

↓

9 Object Builder

↓

10 Parent Merge

↓

11 Array Merge

↓

12 Final Output
```

Đây là lifecycle cố định.

Provider không được thay đổi.

---

# 5.3 Mapping Object

Mình muốn thay model `connector.mapping.line` thành DSL.

Ví dụ

```yaml
key: amount

source:
    type: field
    path: amount_total

default: 0

condition:
    amount_total > 0

compute:

- round(2)

- multiply(100)

datatype: integer
```

Database chỉ là nơi lưu DSL.

Engine đọc DSL.

Không đọc Field trực tiếp.

---

## Vì sao?

Sau này export/import rất dễ.

Ví dụ

```yaml
Payload:

partnerCode:

setting:
    partner_code

amount:

field:
    amount_total

compute:

- multiply(100)
```

Import.

Done.

---

# 5.4 Source Resolver

Mình đề xuất tách riêng.

```python
Resolver
```

Có interface

```python
resolve(
    context,
    source
)
```

---

Các Resolver

```text
Field Resolver

Setting Resolver

Variable Resolver

Context Resolver

Plugin Resolver

Expression Resolver

Template Resolver
```

Core chỉ gọi

```python
resolver.resolve()
```

---

## Field Resolver

Ví dụ

```text
partner_id.country_id.code
```

↓

Resolve.

---

Có cache.

Không browse nhiều lần.

---

## Setting Resolver

Ví dụ

```text
merchant_id
```

↓

Setting.

↓

Value.

---

## Context Resolver

Ví dụ

```text
today

now

user

company

lang

tz
```

---

## Variable Resolver

Ví dụ

```text
signature_string
```

↓

Runtime Variable.

---

## Plugin Resolver

Provider.

↓

Return object.

---

## Expression Resolver

Ví dụ

```python
amount*100
```

↓

safe_eval.

---

# 5.5 Compute Pipeline

Đây là phần mình muốn đầu tư nhất.

Một value.

↓

Pipeline.

Ví dụ

```text
amount_total

↓

round

↓

multiply

↓

string

↓

trim

↓

Done
```

Không có giới hạn số bước.

---

Pipeline

```text
step1

↓

step2

↓

step3

↓

step4

```

---

Mỗi Step

Input

↓

Output.

---

# 5.6 Function Registry

Không nên

```python
if code=="round"
```

Sai.

Nên

```python
registry.execute(
 code
)
```

Module khác

đăng ký.

---

Ví dụ

```python
register(
 "round",
 RoundFunction
)
```

---

# 5.7 Function Category

Mình chia Function thành nhóm.

## String

```text
upper

lower

trim

replace

split

join

substring

pad_left

pad_right

length

regex_replace

regex_match

slug

camel

snake

title
```

---

## Number

```text
round

ceil

floor

abs

multiply

divide

plus

minus

mod

format_number

currency

```

---

## Date

```text
today

now

format

parse

timestamp

epoch

timezone

add_day

add_month

start_month

end_month

weekday
```

---

## JSON

```text
json_encode

json_decode

merge

flatten

pick

omit

sort_key

```

---

## Collection

```text
sum

max

min

unique

sort

reverse

first

last

count

```

---

## Encoding

```text
base64

hex

url_encode

url_decode

md5

sha256

gzip

```

---

## Utility

```text
uuid

random

coalesce

default

if

case

bool

```

---

## Payment

Đây là nhóm mới.

Ví dụ

```text
format_money

bank_amount

remove_dot

remove_comma

```

---

# 5.8 Variable

Mình muốn Variable mạnh hơn.

Không chỉ

```text
amount100
```

Mà có Scope.

Ví dụ

```text
Execution

Global

Loop

```

---

Execution

↓

chỉ trong execution.

---

Loop

↓

chỉ trong foreach.

---

Global

↓

nhiều API dùng.

---

# 5.9 Loop

Đây là điểm rất ít framework làm đẹp.

Ví dụ

Invoice Line.

↓

```text
invoice_line_ids
```

↓

Loop.

---

Context.

```text
line
```

---

Child.

```text
line.product_id.name
```

---

Ngoài ra

nên có

```text
index

first

last

odd

even

```

---

# 5.10 Condition

Hiện bạn chỉ nói

Condition.

Theo mình

Condition cũng nên là Pipeline.

Ví dụ

```text
amount

↓

>

↓

1000
```

Không phải

```python
amount>1000
```

---

Sau này

Visual Builder.

---

Nhưng vẫn cho phép

Expression.

---

# 5.11 Datatype

Không convert cuối.

Nên convert

sau Compute.

Ví dụ

```text
Float

↓

round

↓

Integer

↓

Done
```

---

# 5.12 Default

Hiện bạn có

Default Value.

Theo mình

nên có thêm

```text
Default If None

Default If Empty

Default If False

Default If Exception

```

Ví dụ

```text
False

↓

Unknown
```

---

# 5.13 Required

Nếu

Required=True.

↓

None.

↓

Error.

---

Không cần HTTP.

---

# 5.14 Ignore Empty

Field

```text
ignore_if_empty
```

Ví dụ

```json
{
"name":""
}
```

↓

Không build.

---

Rất nhiều API yêu cầu vậy.

---

# 5.15 Template Engine

Mình muốn nâng cấp.

Không chỉ

```text
{partner}
```

Mà

Jinja2.

Ví dụ

```jinja2
{{ partner.name }}
```

Hoặc

```jinja2
{{ amount*100 }}
```

Hoặc

```jinja2
{% if partner %}
...
{% endif %}
```

Template mạnh hơn Expression rất nhiều.

---

# 5.16 Object Builder

Đây là phần Build JSON.

Ví dụ

```json
{
"a":{

}
}
```

Parent.

↓

Child.

↓

Recursive.

---

Không cần Provider.

---

# 5.17 Merge Strategy

Đây là ý mình bổ sung.

Nếu

2 Mapping.

Cùng key.

Làm sao?

Có Strategy.

```text
Replace

Merge

Append

Ignore

Exception
```

---

# 5.18 Output

Output luôn là

Python Dict.

Không phải JSON.

HTTP Engine

serialize.

---

# 5.19 Validation

Sau Mapping.

Có Validation.

```text
Datatype

Required

Regex

Max

Min

Length

```

Fail.

↓

Execution Fail.

---

# 5.20 Mapping Debug

Theo mình nên có một màn hình cực kỳ quan trọng.

## Test Mapping

Admin chọn:

* Provider
* API
* Record

↓

Nhấn **Preview**

Framework hiển thị:

```text
Invoice.amount_total

↓

1500000

↓

round

↓

1500000

↓

multiply

↓

150000000

↓

int

↓

payload.amount
```

Đồng thời hiển thị payload cuối cùng:

```json
{
  "partnerCode": "MOMO",
  "amount": 150000000,
  "orderId": "..."
}
```

Điều này giúp debug mà **không cần gửi request thật**.

---

# 5.21 Những thay đổi mình đề xuất so với thiết kế ban đầu

Đây là những điểm mình nghĩ sẽ làm framework vượt xa các module tích hợp thông thường:

## 1. Mapping nên hỗ trợ nhiều Source cùng lúc

Ví dụ:

```text
first_name
last_name
```

↓

```text
full_name
```

Thông qua:

```text
concat(
 first_name,
 last_name
)
```

Hiện tại thiết kế chỉ cho một `source_path`, mình đề xuất hỗ trợ **multi-source**.

---

## 2. Compute Function nên nhận Context

Thay vì:

```python
execute(value)
```

Nên là:

```python
execute(
    value,
    context,
    parameters
)
```

Khi đó Function có thể truy cập:

* Company
* Currency
* Variables
* Current Record
* Environment
* Settings

Ví dụ `format_currency()` sẽ không cần truyền currency mỗi lần.

---

## 3. Mapping nên có Dependency Graph

Hiện Pipeline chạy theo `sequence`.

Mình đề xuất cho phép:

```text
signature

depends_on:

- amount
- partnerCode
- orderId
```

Framework tự tính đúng thứ tự, thay vì người cấu hình phải tự quản lý sequence rất dài.

Đây là cách mà các workflow engine hiện đại hoạt động và sẽ giúp framework dễ mở rộng hơn rất nhiều.

---

Theo mình, sau **Chương 5**, phần khó nhất của framework đã hoàn thành. Các chương tiếp theo sẽ là **Authentication Engine**, **HTTP Engine**, **Webhook/Cron Engine** và **Business Action Engine**, chủ yếu là hiện thực hóa pipeline đã thiết kế ở trên. Điều này cũng có nghĩa là khi bắt đầu code, đội phát triển sẽ ưu tiên hoàn thành **Mapping Engine** trước, vì đây là nền tảng mà các Engine còn lại đều sử dụng.

Rất tốt. Đến đây mình sẽ bắt đầu chỉnh lại kiến trúc theo hướng **Enterprise Integration Platform**.

Sau khi đọc lại toàn bộ các chương trước, mình thấy có một điểm cần thay đổi khá lớn.

> **Authentication + Hash + Header + Query + Payload thực chất đều là Data Mapping.**

Tức là chúng ta đang bị lặp lại rất nhiều model.

Ví dụ

```
Header Mapping

Payload Mapping

Query Mapping

Response Mapping
```

Thực ra đều dùng chung một Engine.

Chỉ khác Target.

Nên mình đề xuất sửa kiến trúc trước khi viết tiếp.

---

# Chương 6 - Request Builder Engine

(**Đây là chương mình đề xuất thay thế cho Authentication Engine**)

---

# 6.1 Tư tưởng mới

Framework sẽ chỉ có

```
Input Data

↓

Transformation Engine

↓

Request Builder

↓

HTTP
```

Request Builder sẽ sinh ra

```
Request

├── URL
├── Path Variable
├── Query
├── Header
├── Cookie
├── Body
├── Signature
```

Thay vì

```
Header Engine

Payload Engine

Query Engine
```

---

# 6.2 Request Object

Trong Runtime sẽ có object

```python
ConnectorRequest
```

Không phải dict.

Ví dụ

```python
request.method

request.url

request.path

request.query

request.header

request.cookie

request.body

request.timeout

request.verify_ssl
```

Cuối cùng HTTP Engine chỉ nhận object này.

---

# 6.3 Builder Pattern

Mình muốn dùng Builder Pattern.

```
RequestBuilder

↓

build_url()

↓

build_path()

↓

build_query()

↓

build_header()

↓

build_body()

↓

build_signature()

↓

Done
```

Không phải

HTTP Engine tự build.

---

# 6.4 URL Builder

Ví dụ

```
https://abc.com

+

/payment/{id}
```

↓

```
https://abc.com/payment/100
```

Path Variable

đã Mapping từ trước.

Builder chỉ replace.

---

# 6.5 Query Builder

Ví dụ

```
?id=100

&page=1

&limit=20
```

↓

Query Mapping.

Không có code riêng.

---

# 6.6 Header Builder

Header cũng chỉ là Mapping.

Ví dụ

```
Authorization

↓

Bearer xxx
```

Hay

```
partnerCode

↓

Setting
```

Không cần Header Engine.

---

# 6.7 Cookie Builder

Mình bổ sung.

Có khá nhiều API dùng Cookie.

Ví dụ

```
JSESSIONID

PHPSESSID

AWS Cookie
```

Không nên hardcode.

Cookie cũng là Mapping.

---

# 6.8 Body Builder

Body

↓

JSON

↓

Serialize.

Hoặc

↓

XML

↓

Serialize.

Builder quyết định.

Không phải HTTP.

---

# 6.9 Serializer

Body

không nên serialize trong HTTP.

Tách riêng.

Ví dụ

```
Dict

↓

JSON

```

Hay

```
Dict

↓

XML
```

Sau này

YAML

CSV

đều thêm được.

---

# 6.10 Signature Builder

Đây là phần mình muốn thay đổi khá nhiều.

Hôm trước

chúng ta có

```
Hash Method
```

Theo mình chưa đủ.

Có 3 khái niệm.

```
Signature Source

↓

Signature Builder

↓

Hash Method
```

Ví dụ

MoMo

```
partnerCode

amount

requestId

```

↓

Builder

↓

```
partnerCode=...

&amount=...

```

↓

SHA256

↓

Signature

---

VNPay

```
Sort

↓

Join

↓

URL Encode

↓

SHA512
```

Builder khác.

Hash giống.

---

# 6.11 Signature Source

Theo mình nên có model riêng.

Ví dụ

```
connector.signature.field
```

Admin chọn

```
partnerCode

accessKey

amount

```

Sequence.

Builder đọc.

---

# 6.12 Signature Builder

Builder chỉ làm

```
Sort

↓

Filter Empty

↓

Join

↓

Encode

↓

Template

↓

Done
```

Không Hash.

---

# 6.13 Hash Method

Hash

chỉ nhận

```
String

↓

Secret

↓

Hash
```

Không biết

Builder.

---

# 6.14 Authentication

Sau khi nghĩ lại,

Authentication cũng nên dùng Strategy.

```
Authentication

↓

Generate Header

↓

Done
```

Ví dụ

Bearer.

↓

```
Authorization

Bearer xxx
```

---

OAuth

↓

Nếu Token hết hạn.

↓

Refresh.

↓

Header.

---

Không nên

Authentication

đụng

Payload.

---

# 6.15 Token Cache

Đây là điểm mình muốn bổ sung.

Ví dụ

OAuth.

```
Access Token

↓

Cache

↓

Expire

↓

Refresh
```

Không call Login mỗi lần.

---

Model

```
connector.cache
```

---

# 6.16 HTTP Client

HTTP Client

nên là Interface.

Ví dụ

```
Requests

HTTPX

AIOHTTP
```

Sau này

Async.

---

# 6.17 Middleware

Đây là điểm mình rất muốn thêm.

Trước HTTP.

Có Middleware.

Ví dụ

```
Before Request

↓

Mask Secret

↓

Log

↓

HTTP

↓

Retry

↓

Response

↓

After Response
```

Sau này

Rate Limit.

Circuit Breaker.

Cache.

đều Middleware.

---

# 6.18 Retry Strategy

Không Retry trong HTTP.

Sai.

Có Strategy.

Ví dụ

```
Linear

Exponential

Fixed

Random
```

---

# 6.19 Circuit Breaker

Enterprise.

Nếu

```
10 lần

Fail
```

↓

Open.

↓

Không Call.

↓

5 phút.

↓

Half Open.

↓

OK.

↓

Close.

Không DDOS API.

---

# 6.20 Rate Limit

Có API

```
100 request/minute
```

Framework

tự chặn.

Không Provider.

---

# 6.21 Timeout Policy

Không chỉ Timeout.

Có

```
Connect Timeout

Read Timeout

Write Timeout
```

Riêng.

---

# 6.22 Proxy

Enterprise.

Một số khách

qua Proxy.

Builder.

---

# 6.23 SSL

```
Verify SSL

Certificate

Client Certificate
```

Không hardcode.

---

# 6.24 Request Debugger

Theo mình nên có màn hình cực mạnh.

```
Request

↓

Header

↓

Query

↓

Body

↓

Signature String

↓

Signature

↓

Raw HTTP

```

Admin copy.

↓

Import Postman.

---

# 6.25 Response

HTTP

chỉ trả

```
Status

Header

Body

Time

Cookie

```

Không parse.

---

# Những thay đổi mình đề xuất sau khi hoàn thành Chương 6

Sau khi viết đến đây, mình thấy có **một thay đổi rất lớn** mà mình khuyến nghị thực hiện trước khi code.

## Bỏ hoàn toàn khái niệm "API"

Thay vào đó dùng:

```
Connector Flow
```

Ví dụ

MoMo

```
Create Payment
```

Thực tế không phải một API.

Nó là

```
Load Token

↓

Build Request

↓

Call API

↓

Receive Response

↓

Create Payment

↓

Wait Webhook

↓

Confirm
```

Tức là một **Workflow**.

Nếu chỉ có `connector.api`

thì sau này

OAuth

S3 Upload

Multipart

Upload File

Webhook Verify

sẽ rất khó.

---

## Mình đề xuất thay bằng

```
connector.flow
```

Flow gồm nhiều Step.

Ví dụ

```
Step 1

Login

↓

Step 2

Get Token

↓

Step 3

Create Payment

↓

Step 4

Save Transaction

↓

Step 5

Wait Webhook
```

Mỗi Step

có

```
Request Mapping

↓

Response Mapping

↓

Business Action

```

---

## Đây là thay đổi lớn nhất của toàn bộ thiết kế

Nếu chấp nhận thay đổi này, framework sẽ **không còn là Payment Framework nữa**.

Nó sẽ trở thành một **Enterprise Integration Platform** tương tự:

* Apache Camel
* MuleSoft
* WSO2 Micro Integrator
* n8n (ở mức low-code)
* Node-RED (ở mức cấu hình)

nhưng được tích hợp trực tiếp trong Odoo.

### Mình khuyên nên đổi ngay từ bây giờ

Thay vì:

```
Provider
    └── API
```

nên chuyển sang:

```
Provider
    └── Flow
            ├── Step
            ├── Request Mapping
            ├── Response Mapping
            ├── Business Action
            └── Transition
```

Điều này sẽ giúp framework xử lý được cả các quy trình nhiều bước (OAuth, upload file, polling, xác nhận thanh toán...) mà không cần viết thêm logic đặc thù trong code. Theo mình, đây là hướng kiến trúc có giá trị lâu dài nhất nếu mục tiêu là xây dựng một framework có thể thương mại hóa.

Mình sẽ dừng một chút ở vai trò SA để **refactor kiến trúc** trước khi viết tiếp.

Sau Chương 6, mình nhận ra framework đã thay đổi bản chất.

Nó **không còn là API Connector** nữa.

Nó đã trở thành một **Workflow Engine**.

Nếu vẫn giữ mô hình

```text
Provider
    └── API
```

thì sau này sẽ gặp rất nhiều giới hạn.

Ví dụ OAuth2.

```
Login
 ↓
Receive Token
 ↓
Save Token
 ↓
Call Payment
 ↓
Receive Redirect
 ↓
Wait Webhook
 ↓
Verify
 ↓
Done
```

Đây không phải một API.

Đây là một Workflow.

---

# Vì vậy mình đề xuất đổi toàn bộ Domain

Không còn

```
Provider
    └── API
```

Mà là

```
Provider

    ↓

Flow

    ↓

Step

    ↓

Action

    ↓

Transition
```

Đây là kiến trúc mình khuyên nên theo.

---

# Chương 7 - Flow Engine

---

# 7.1 Mục tiêu

Flow Engine là Runtime Orchestrator.

Nó không biết

* HTTP

* Payment

* Mapping

* Business

Nó chỉ biết

```
Step

↓

Execute

↓

Next Step
```

---

# 7.2 Domain

Mình đề xuất thay toàn bộ

```
connector.api
```

bằng

```
connector.flow
```

---

Flow

Ví dụ

MoMo

```
Create Payment
```

Bên trong

```
Build Request

↓

Create Payment

↓

Save Transaction

↓

Wait Callback

↓

Finish
```

---

VNPay

```
Build URL

↓

Redirect

↓

Wait Return

↓

Verify Signature

↓

Finish
```

---

Đây mới đúng bản chất.

---

# 7.3 Flow

Model

```
connector.flow
```

Field

| Field       | Ý nghĩa |
| ----------- | ------- |
| Provider    |         |
| Name        |         |
| Code        |         |
| Version     |         |
| Description |         |
| Start Step  |         |
| Active      |         |

---

Một Provider

↓

N Flow

Ví dụ

```
MoMo

↓

Create Payment

↓

Refund

↓

Query Payment

↓

Webhook
```

---

# 7.4 Flow Step

Model

```
connector.flow.step
```

Field

| Field         | Meaning |
| ------------- | ------- |
| Flow          |         |
| Sequence      |         |
| Name          |         |
| Code          |         |
| Type          |         |
| Configuration |         |

---

Type

Mình đề xuất

```
LOAD

MAP

REQUEST

RESPONSE

BUSINESS

WAIT

WEBHOOK

CONDITION

LOOP

SCRIPT

END
```

---

Không có Payment.

---

# 7.5 Vì sao dùng Step Type?

Ví dụ

```
Load

↓

Request

↓

Response

↓

Business
```

Framework biết

phải gọi Engine nào.

Không cần

```
if provider=="momo"
```

---

# 7.6 Step Executor

Đây là Interface.

```
execute(
 context,
 step
)
```

Không biết

Step nào.

---

Executor Registry

```
LOAD

↓

LoadExecutor

REQUEST

↓

RequestExecutor

MAP

↓

MapExecutor

```

---

Module khác

đăng ký.

---

# 7.7 Step Output

Mỗi Step

không trả dict.

Mà trả

```
StepResult
```

Ví dụ

```
status

output

variables

duration

message

exception
```

Flow chỉ đọc.

---

# 7.8 Context

Mình muốn Context mạnh hơn.

```
Execution

↓

Context

    record

    variables

    request

    response

    cache

    flow

    current_step

```

Không truyền lung tung.

---

# 7.9 Transition

Đây là điểm cực kỳ quan trọng.

Hiện tại

Sequence

↓

Sequence.

Sai.

Phải là

Transition.

Ví dụ

```
HTTP

↓

200

↓

Business

```

Nhưng

```
500

↓

Retry
```

Hoặc

```
401

↓

Refresh Token
```

---

Model

```
connector.transition
```

Field

| Field     | Meaning |
| --------- | ------- |
| From Step |         |
| Condition |         |
| To Step   |         |
| Priority  |         |

---

Ví dụ

```
HTTP

↓

status==200

↓

Done
```

---

```
HTTP

↓

status==401

↓

Refresh Token
```

Không code.

---

# 7.10 Condition Engine

Transition

không dùng

Python.

Sai.

Nên

DSL.

Ví dụ

```
status

==

200
```

---

Hoặc

```
amount

>

100
```

Sau này

Visual Builder.

---

# 7.11 Loop

Step

cũng có thể là

Loop.

Ví dụ

```
Invoice

↓

Invoice Line

↓

Loop

↓

Call API

```

Không cần

Cron.

---

# 7.12 Wait Step

Payment

rất cần.

Ví dụ

```
Create QR

↓

Wait Payment

↓

Webhook

↓

Done
```

Wait

↓

Sleep.

↓

Resume.

---

Model

```
connector.wait
```

---

# 7.13 Resume Engine

Webhook

↓

Không tạo Execution mới.

↓

Resume Execution.

---

Ví dụ

```
Execution

Paused
```

↓

Webhook

↓

Continue.

---

Đây là Workflow thật.

---

# 7.14 Webhook Step

Webhook

cũng là

Step.

Ví dụ

```
Receive

↓

Verify

↓

Parse

↓

Business

```

Không có

Webhook Engine.

---

# 7.15 Retry

Retry

không ở HTTP.

Retry

là Transition.

Ví dụ

```
HTTP Fail

↓

Retry

↓

HTTP
```

Không code.

---

# 7.16 Decision

Step

```
Condition
```

↓

```
True

↓

Business A
```

```
False

↓

Business B
```

Không cần Python.

---

# 7.17 Parallel

Đây là tính năng mình rất muốn có.

Ví dụ

```
Sync Stock

↓

─────────────

Shopee

Lazada

TikTok

─────────────

↓

Merge

```

Framework

đợi.

↓

Merge.

---

Step Type

```
PARALLEL
```

---

# 7.18 Merge

Parallel

↓

Merge.

↓

Continue.

---

# 7.19 Sub Flow

Flow

gọi

Flow.

Ví dụ

```
Login
```

Flow.

↓

Payment.

↓

Reuse.

---

# 7.20 Error Flow

Nếu

Fail.

↓

Không Raise.

↓

Đi

```
On Error
```

Flow.

Ví dụ

```
Send Email

Notify

Rollback

```

---

# 7.21 Visual Flow

Theo mình

đây sẽ là USP của Framework.

Ví dụ

```
+--------+
| Start  |
+--------+
     |
     ▼
+-------------+
| Build Body  |
+-------------+
     |
     ▼
+-------------+
| HTTP POST   |
+-------------+
     |
   ┌─┴─────────────┐
   ▼               ▼
200 OK         401 Unauthorized
   │               │
   ▼               ▼
+---------+   +---------------+
| Success |   | Refresh Token |
+---------+   +---------------+
                    │
                    └───────► HTTP POST
```

Admin nhìn là hiểu.

Không cần đọc Code.

---

# Sau khi hoàn thành Chương 7, mình muốn thay đổi kiến trúc một lần cuối

Đây là thay đổi mà mình nghĩ sẽ quyết định framework có "đẳng cấp enterprise" hay không.

## Thay `Flow` bằng `State Machine`

Hiện tại chúng ta vẫn đang nghĩ theo Workflow.

Nhưng Payment thực chất là một **State Machine**.

Ví dụ:

```
Draft

↓

Request Created

↓

Waiting Payment

↓

Paid

↓

Refunded

↓

Cancelled
```

Webhook, Cron, Retry... đều chỉ là **Event** làm thay đổi State.

Nếu thiết kế theo State Machine:

* Retry trở thành Event.
* Webhook trở thành Event.
* Cron trở thành Event.
* Timeout trở thành Event.

Flow chỉ còn là một cách biểu diễn của State Machine.

### Kiến trúc cuối cùng mình đề xuất

```
Provider
        │
        ▼
Integration Definition
        │
        ▼
State Machine
        │
        ▼
Transition
        │
        ▼
Action
        │
        ▼
Engine
```

Đây là kiến trúc mà các workflow engine hiện đại như Camunda, Temporal hay nhiều BPM engine áp dụng.

---

## Tuy nhiên, với Odoo mình **không khuyến nghị triển khai State Machine ngay phiên bản đầu tiên**.

Lý do:

* Độ phức tạp tăng gấp 2–3 lần.
* Khó debug hơn.
* Thời gian phát triển kéo dài.

**Khuyến nghị của mình:**

* **V1:** Giữ kiến trúc **Flow + Step + Transition** như đã thiết kế. Đây là mức cân bằng giữa khả năng mở rộng và độ phức tạp.
* **V2:** Khi framework ổn định, refactor Flow Engine thành State Machine Engine mà vẫn giữ tương thích với các Flow đã cấu hình.

Đây là hướng mà mình sẽ theo nếu mục tiêu là xây dựng một framework có thể bán và duy trì lâu dài.
Mình sẽ tiếp tục, nhưng trước tiên mình muốn **chỉnh một điểm kiến trúc**.

---

# Sau 7 chương, mình thấy có 3 thứ đang bị lẫn

Hiện tại chúng ta có

```text
Flow

↓

Mapping

↓

Business Action
```

Nhưng Business Action thực ra không phải Engine.

Ví dụ

```text
Create Payment

Update Invoice

Reconcile

Create Picking
```

Đây đều là Action.

Trong khi

```text
Request

Response

Mapping

Compute
```

là Engine.

Theo nguyên tắc SOLID thì chúng ta đang lẫn giữa

**Process Engine**

và

**Business Logic**

---

## Mình đề xuất chia thành 4 tầng

```text
Presentation Layer

↓

Configuration Layer

↓

Execution Layer

↓

Business Layer
```

Execution Layer KHÔNG BAO GIỜ biết

```text
Invoice

Sale Order

Payment

Picking

Stock
```

Execution chỉ biết

```text
Context

Action

Flow

Transition
```

Business Layer mới biết

```text
account.move

sale.order

stock.picking

...
```

Đây là thay đổi rất quan trọng.

---

# Chương 8 - Action Framework

Theo mình, Action mới là linh hồn của Framework.

Flow chỉ quyết định

Đi đâu.

Action mới quyết định

Làm gì.

---

# 8.1 Kiến trúc

```text
Flow

↓

Step

↓

Action

↓

Executor
```

Ví dụ

```text
HTTP Step

↓

Action

↓

Call HTTP
```

Hay

```text
Business Step

↓

Action

↓

Update Record
```

Flow không biết Action.

---

# 8.2 Action Registry

Không nên

```python
if action=="create_record"
```

Sai.

Nên

```python
registry.execute(
 action_code
)
```

---

Ví dụ

```python
register(
 "create_record",
 CreateRecordExecutor
)
```

---

Module khác

đăng ký.

---

# 8.3 Action Interface

Tất cả Action

đều có

```python
execute(
 context,
 configuration
)
```

Không có Exception.

Không trả Dict.

Chỉ trả

```python
ActionResult
```

---

# 8.4 ActionResult

```python
success

output

variables

message

next_step

error
```

Flow chỉ đọc.

---

# 8.5 Action Category

Theo mình nên chia

---

## Data

```text
Create Record

Update Record

Delete Record

Search

Browse
```

---

## HTTP

```text
Request

Download

Upload
```

---

## Variable

```text
Set Variable

Get Variable

Remove Variable

Copy Variable
```

---

## Compute

```text
Template

Expression

Compute

```

---

## Flow

```text
Goto

Wait

Loop

Break

Continue

End
```

---

## Notification

```text
Email

SMS

Webhook

Bus

```

---

## File

```text
Read

Write

CSV

Excel

PDF

ZIP
```

---

## AI

Sau này

```text
ChatGPT

OCR

Embedding

Vector

```

---

## Payment

```text
Generate QR

Verify Signature

Reconcile

```

Không nằm Base.

Module Payment.

---

# 8.6 Odoo Action

Theo mình đây là điểm cực mạnh.

Ví dụ

Action

↓

```text
Call Method
```

Admin nhập

```text
Model

Method
```

Ví dụ

```python
account.move

action_post()
```

Không code.

---

Hay

```python
sale.order

action_confirm()
```

---

# 8.7 Server Action

Tương tự

```text
Execute Server Action
```

Không code.

---

# 8.8 Queue Job

Action

↓

Queue.

↓

Background.

---

# 8.9 Delay

Action

↓

Sleep

↓

10 phút

↓

Resume

Không Cron.

---

# 8.10 Variable Action

Ví dụ

```text
Amount

↓

Save

↓

amount100
```

---

Hay

```text
token

↓

Cache
```

---

# 8.11 File Action

Ví dụ

Download.

↓

CSV.

↓

Import.

↓

Business.

Không cần Plugin.

---

# 8.12 Plugin Action

Provider.

↓

Đăng ký.

↓

Action.

Không sửa Base.

---

# 8.13 Composite Action

Đây là ý mình muốn thêm.

Một Action

=

N Action.

Ví dụ

```text
Update Invoice

↓

Create Payment

↓

Send Email

↓

Done
```

Admin chỉ kéo.

---

# 8.14 Compensation Action

Enterprise.

Ví dụ

```text
Payment

↓

Create Invoice

↓

Send API

↓

Fail
```

Rollback.

↓

Cancel Invoice.

---

Đây là Saga Pattern.

---

# 8.15 Transaction

Action

nên có

```text
Transaction

Yes

No
```

Ví dụ

HTTP

↓

No.

Update Invoice

↓

Yes.

---

# 8.16 Idempotency

Mình cực kỳ khuyến nghị.

Action

↓

Idempotent.

Ví dụ

Webhook.

↓

Call 5 lần.

↓

Invoice

Paid

1 lần.

---

# 8.17 Action Permission

Không phải ai cũng chạy được.

Ví dụ

```text
Call Python

```

↓

Admin.

---

# 8.18 Visual Action

Flow.

↓

Business.

↓

Action.

↓

Configuration.

Admin.

Không Code.

---

# 8.19 Action Marketplace

Theo mình đây là tính năng thương mại.

Ví dụ

Module

```text
connector_action_ai

connector_action_excel

connector_action_ftp

connector_action_sftp

connector_action_pdf

```

Cài.

↓

Có Action mới.

---

# 8.20 Điều mình muốn thay đổi rất lớn

Sau khi viết đến đây, mình thấy có một vấn đề trong toàn bộ thiết kế trước.

## Chúng ta đang cấu hình bằng rất nhiều model

Ví dụ

```text
Flow

↓

Step

↓

Transition

↓

Mapping

↓

Pipeline

↓

Function

↓

Condition
```

Số lượng model sẽ vượt 30.

Admin sẽ rất khó cấu hình.

---

# Mình đề xuất thay đổi hoàn toàn UI

Không cấu hình theo tree.

Mà theo

## Node Graph

Ví dụ

```text
+-----------+
| Load      |
+-----------+
      │
      ▼
+-----------+
| Mapping   |
+-----------+
      │
      ▼
+-----------+
| HTTP      |
+-----------+
      │
      ▼
+-----------+
| Condition |
+-----------+
   │      │
   ▼      ▼
+------+ +------+
|Paid | |Retry |
+------+ +------+
```

Mỗi Node

↓

Double Click.

↓

Config.

Giống

* n8n
* Node-RED
* Camunda Modeler

---

# Mình còn muốn thay đổi thêm một thứ

Đây là thay đổi cuối cùng mình nghĩ framework nên có.

## Thay "Mapping Line" bằng "Expression"

Hiện tại

```text
key

↓

source

↓

compute

↓

datatype

↓

default
```

Thực chất

đó là

Expression.

Ví dụ

```text
amount =
round(
 invoice.amount_total
 *100
)
```

Hay

```text
signature =
sha256(
 template(...)
)
```

Nếu chúng ta có

Expression Engine

thì

Mapping

Compute

Condition

Template

Default

đều dùng chung.

Tức là Framework chỉ còn

* Flow
* Action
* Expression

Theo mình đây là kiến trúc đẹp nhất.

---

# Kiến trúc V2 mình khuyến nghị

```text
Connector Framework

├── Flow Engine
├── Action Engine
├── Expression Engine
├── HTTP Engine
├── Runtime Engine
├── Plugin Engine
```

Chỉ còn **6 Engine**.

Tất cả những thứ khác (Mapping, Compute, Condition, Template, Hash Builder...) đều trở thành **Expression** hoặc **Action**.

---

## Đây là đề xuất quan trọng nhất mình đưa ra từ đầu cuộc thảo luận

Nếu chấp nhận refactor này **trước khi code**, mình tin:

* Số model giảm khoảng **35–40%**.
* Số service class giảm khoảng **50%**.
* Tính mở rộng tăng rất nhiều.
* Việc xây UI dạng Node Editor sẽ tự nhiên hơn rất nhiều.

**Mình sẽ chọn kiến trúc này nếu mục tiêu là xây một framework có thể bán thương mại trong nhiều năm, chứ không chỉ phục vụ tích hợp MoMo/VNPay.**
Đến đây mình sẽ chuyển sang góc nhìn của một **Chief Architect** thay vì BA.

Và mình sẽ nói một điều có thể hơi trái với những chương trước.

> **Đừng cố xây một n8n bên trong Odoo.**

Đây là sai lầm mà rất nhiều framework mắc phải.

---

# Sau khi phân tích lại toàn bộ

Hiện tại chúng ta có

```text
Flow

Action

Expression

HTTP

Runtime

Plugin
```

Nếu tiếp tục mở rộng

sẽ có

* Queue
* AI
* OCR
* FTP
* MQTT
* Kafka
* Email
* SOAP
* GraphQL

...

Lúc này framework sẽ rất lớn.

Trong khi mục tiêu ban đầu là

> Framework tích hợp Payment/API.

---

# Vì vậy mình đề xuất chia thành 3 Layer

Đây là kiến trúc mà mình sẽ chọn nếu build sản phẩm thương mại.

```text
connector_core
        │
        ├────────────┐
        │            │
        ▼            ▼
 connector_http   connector_runtime
        │            │
        └──────┬─────┘
               ▼
       connector_flow
               │
      ┌────────┴─────────┐
      ▼                  ▼
connector_payment   connector_storage
      ▼                  ▼
 momo               s3
 vnpay              ftp
 napas              minio
 zalopay
```

Điểm quan trọng là **Core không biết Payment**.

---

# Chương 9 - Module Architecture

Đây là chương cực kỳ quan trọng.

Theo mình framework nên chia thành nhiều addon Odoo thay vì một module lớn.

---

# 9.1 connector_core

Đây là module duy nhất không phụ thuộc gì ngoài `base`.

Chỉ chứa:

* Registry
* Base model
* Exception
* Context
* Result object
* Plugin loader
* Constant

Không có HTTP.

Không có Payment.

Không có JSON.

---

## Chứa các abstract class

Ví dụ:

```python
AbstractAction

AbstractExpression

AbstractPlugin

AbstractResolver

AbstractExecutor
```

Tất cả module khác kế thừa.

---

# 9.2 connector_runtime

Đây là trái tim Runtime.

Chứa:

* Execution
* Context
* Variable
* Cache
* Log
* Step Result
* Runtime Service

Không biết HTTP.

Không biết Payment.

---

# 9.3 connector_expression

Module này chỉ có một nhiệm vụ:

Đánh giá biểu thức.

Ví dụ

```text
invoice.amount_total * 100
```

Hoặc

```text
upper(partner.name)
```

Hoặc

```text
uuid()
```

Toàn bộ Compute Function chuyển về đây.

---

## Function Registry

```python
register_function()
```

Module khác đăng ký.

Ví dụ

connector_payment

đăng ký

```text
format_money()
```

---

# 9.4 connector_mapping

Module này chỉ build dữ liệu.

Input

↓

Expression

↓

Output

Không biết HTTP.

---

# 9.5 connector_http

Chỉ làm:

```text
ConnectorRequest

↓

HTTP Client

↓

ConnectorResponse
```

Không Mapping.

Không Hash.

Không Authentication.

---

# 9.6 connector_security

Theo mình nên tách riêng.

Chứa:

* Hash
* Signature
* OAuth
* JWT
* API Key
* Encrypt
* Secret

Sau này Payment chỉ dùng.

---

# 9.7 connector_flow

Flow Engine.

Step.

Transition.

Resume.

Không HTTP.

---

# 9.8 connector_business

Action.

Business.

Call Model.

Server Action.

Queue Job.

Không biết HTTP.

---

# 9.9 connector_webhook

Đây là module riêng.

Chứa:

* Route
* Verify
* Resume
* Replay
* Log

---

# 9.10 connector_scheduler

Cron.

Retry.

Polling.

Timeout.

Resume.

---

# 9.11 connector_ui

Toàn bộ:

* Preview
* Debug
* Flow Designer
* Mapping Preview
* Execution Viewer

Không có Logic.

---

# 9.12 connector_payment

Đây mới là nơi có

```text
PaymentTransaction

PaymentProvider

PaymentMethod
```

Không nằm Core.

---

# 9.13 connector_provider_momo

Module này cực nhỏ.

Chỉ chứa:

```text
Setting

Flow

Mapping

Action

Expression

```

Gần như không có Python.

---

# 9.14 connector_provider_vnpay

Tương tự.

Khác:

* Hash Builder
* Mapping
* Endpoint

---

# 9.15 connector_provider_xxx

Mỗi Provider chỉ nên khoảng:

```text
300-1000 dòng Python
```

Nếu vượt

5000 dòng

thì Framework đang sai.

---

# 9.16 Module Dependency

```text
base
 │
 ▼
connector_core
 │
 ├──────────────┐
 ▼              ▼
runtime     expression
 │              │
 ├──────┐       │
 ▼      ▼       ▼
mapping security http
     │      │     │
     └──┬───┴─────┘
        ▼
      flow
        │
        ▼
    business
        │
 ┌──────┴─────────┐
 ▼                ▼
payment        storage
 │                │
 ▼                ▼
 momo            s3
 vnpay           ftp
```

---

# 9.17 Plugin Discovery

Mình không thích

```python
import connector_payment
```

Mà dùng Registry.

Ví dụ

```python
register_action()

register_function()

register_provider()

register_hash()
```

Module cài vào.

↓

Auto có.

---

# 9.18 Version

Provider nên có Version.

Ví dụ

```text
MoMo

v2

v3
```

Hai Flow khác nhau.

Không ghi đè.

---

# 9.19 Package

Đề xuất cấu trúc source:

```text
connector_core/
    models/
    services/
    registry/
    exceptions/
    utils/

connector_flow/
    models/
    services/
    executors/

connector_expression/
    models/
    evaluators/
    functions/

connector_http/
    clients/
    middleware/
    serializers/

connector_payment/
    models/
    actions/

connector_provider_momo/
    data/
        flow.xml
        mapping.xml
        setting.xml
```

Điều này rất phù hợp với cách tổ chức của Odoo.

---

# 9.20 Điều mình muốn thay đổi cuối cùng

Sau gần 10 chương, mình nhận ra một vấn đề.

Chúng ta đang lưu **quá nhiều cấu hình trong database**.

Ví dụ:

* Mapping Line
* Transition
* Function
* Expression
* Pipeline
* Step

Nếu một Provider có 40 API thì số record có thể lên đến hàng chục nghìn.

## Mình đề xuất mô hình Hybrid

Thay vì lưu mọi thứ bằng record Odoo:

* **Metadata** lưu trong database (Provider, Setting, Version, Environment...).
* **Definition** lưu bằng YAML hoặc JSON trong module.

Ví dụ:

```yaml
flow:
  code: create_payment

steps:
  - type: mapping
  - type: request
  - type: response
```

Khi cài module:

* Import YAML vào cache.
* Database chỉ lưu phần người dùng được phép tùy chỉnh.

### Lợi ích

* Dễ quản lý bằng Git.
* Dễ review khi code.
* Dễ diff giữa các phiên bản.
* Không cần export/import hàng nghìn record XML.
* Có thể khóa các Flow chuẩn của Provider, nhưng vẫn cho phép người dùng tạo bản sao để tùy chỉnh.

---

# Đây là kiến trúc cuối cùng mình sẽ chọn

Nếu giao mình xây framework từ đầu, mình sẽ đi theo mô hình:

```text
Connector Platform
│
├── Core Engine
├── Runtime Engine
├── Expression Engine
├── Mapping Engine
├── HTTP Engine
├── Flow Engine
├── Business Engine
├── Security Engine
│
└── Provider Packages
        ├── MoMo
        ├── VNPay
        ├── Napas
        ├── ZaloPay
        ├── S3
        ├── FTP
        └── ...
```

## Tuy nhiên, có một điểm mình sẽ **không** làm theo các chương trước

Mình **không để admin cấu hình mọi thứ trên giao diện**.

Thay vào đó chia làm 3 mức:

1. **Framework Developer**: phát triển Engine, Action, Function, Resolver.
2. **Provider Developer**: xây dựng Flow, Mapping, Expression chuẩn cho MoMo, VNPay...
3. **Business User/Admin**: chỉ cấu hình Environment, Secret, Endpoint, Company Mapping và một số Rule.

Đây là ranh giới rất quan trọng.

Nếu cho Business User sửa toàn bộ Flow, Mapping, Expression thì hệ thống sẽ rất khó kiểm soát, khó hỗ trợ khách hàng và khó nâng cấp.

Theo mình, đây là kiến trúc cân bằng nhất giữa **tính linh hoạt**, **khả năng bảo trì**, **khả năng thương mại hóa** và **chi phí triển khai**. Đây cũng là hướng mình sẽ khuyến nghị nếu mục tiêu là phát triển một framework Odoo có thể bán cho nhiều khách hàng và duy trì trong nhiều năm.
Mình sẽ tiếp tục, nhưng từ đây mình sẽ chuyển hẳn sang góc nhìn **Technical Lead của Odoo**.

Sau gần 10 chương, mình thấy có **một điểm mà toàn bộ framework hiện tại còn thiếu**.

Đó là:

> **Lifecycle Management**

Đa số framework chỉ quan tâm **làm sao gọi API**.

Nhưng Enterprise lại quan tâm:

> **API này đang ở trạng thái gì? Có ai sửa không? Có rollback được không? Có audit được không?**

Đây là thứ khiến framework trở thành sản phẩm thương mại.

---

# Chương 10 - Lifecycle & Governance

Đây là chương mà mình nghĩ gần như **100% các module Odoo ngoài thị trường đều thiếu**.

---

# 10.1 Environment

Hiện tại chúng ta có

```text
Sandbox

Production
```

Theo mình chưa đủ.

Nên có

```text
Development

Testing

UAT

Sandbox

Production

Archive
```

Mỗi Environment có

```text
Endpoint

Secret

Certificate

Timeout

Rate Limit

Webhook URL

```

Hoàn toàn độc lập.

---

# 10.2 Provider Version

Ví dụ

MoMo

```text
v2

v2.5

v3
```

Không overwrite.

Mỗi Version có

```text
Flow

Expression

Request

Response

```

Riêng.

---

# 10.3 Publish Workflow

Flow không được sửa trực tiếp.

Nên có

```text
Draft

↓

Testing

↓

Approved

↓

Published

↓

Deprecated

↓

Archived
```

Giống Odoo Studio.

---

# 10.4 Clone

Admin

không sửa

Official Flow.

Mà

```text
Clone

↓

Customize
```

Giống Report.

---

# 10.5 Override

Ví dụ

Base

```text
Create Payment
```

Customer

Override

```text
Only Mapping
```

Không copy cả Flow.

---

Mình muốn

Inheritance.

Giống View.

---

# 10.6 Audit

Mỗi lần

sửa Mapping

↓

Log.

```text
Before

↓

After

↓

Who

↓

When
```

---

# 10.7 Compare

Đây là tính năng cực mạnh.

Ví dụ

MoMo v2

↓

Compare

↓

MoMo v3

Hiện

```text
Added

Removed

Modified
```

---

# 10.8 Import

Framework

nên import

```text
YAML

JSON

XML
```

---

# 10.9 Export

Không export

Record.

Export

Definition.

Ví dụ

```yaml
flow:

steps:

expression:

action:
```

Git quản lý.

---

# 10.10 Lock

Official Provider

↓

Readonly.

---

Customer

↓

Clone.

---

Không sửa.

---

# 10.11 Upgrade

Ví dụ

Update Module.

↓

Provider

v2

↓

v3

Customer

không mất Customize.

---

Giống

View Inheritance.

---

# 10.12 Dependency

Ví dụ

Flow

↓

dùng

```text
Action

Function

Expression
```

Nếu

xóa

Function.

↓

Framework biết.

---

Không Error Runtime.

---

# 10.13 Validation

Publish.

↓

Validate.

Ví dụ

```text
Missing Step

↓

Missing Action

↓

Loop Error

↓

Cycle

↓

Unused Variable

↓

Unknown Function
```

Không Publish.

---

# 10.14 Test Case

Đây là tính năng mình rất muốn.

Ví dụ

```text
Flow

↓

Test

↓

Input JSON

↓

Expected JSON

↓

Run

↓

PASS
```

Giống Unit Test.

---

Model

```text
connector.test.case
```

---

# 10.15 Mock

Không Call thật.

↓

Mock.

Ví dụ

```json
{
"resultCode":0
}
```

↓

Business.

---

Debug.

---

# 10.16 Replay

Execution.

↓

Replay.

↓

Run lại.

Không tạo.

Input mới.

---

# 10.17 Snapshot

Execution.

↓

Snapshot.

↓

Save

```text
Variable

Request

Response

Context
```

---

Debug.

---

# 10.18 Performance

Flow.

↓

Statistics.

Ví dụ

```text
Average

P95

P99

Error Rate

```

---

# 10.19 Dashboard

Provider.

↓

Dashboard.

```text
Today

Success

Error

Timeout

Retry

```

Không cần Kibana.

---

# 10.20 Health Check

Provider.

↓

Ping.

↓

Certificate.

↓

DNS.

↓

SSL.

↓

Webhook.

↓

OK.

---

# 10.21 Secret Rotation

Theo mình đây là tính năng rất quan trọng nhưng thường bị bỏ qua.

Ví dụ:

```text
Old Secret

↓

New Secret

↓

Grace Period (7 ngày)

↓

Old Secret hết hiệu lực
```

Điều này cho phép thay đổi Secret Key mà không làm gián đoạn giao dịch đang xử lý.

---

# 10.22 Idempotency Key

Mỗi Request nên có:

```text
Provider

+

Flow

+

Business Key

=

Idempotency Key
```

Ví dụ:

```text
momo:create_payment:INV000123
```

Nếu gọi lại:

* Không tạo giao dịch mới.
* Trả về Execution cũ hoặc tiếp tục Execution đang chờ.

Đây là tính năng rất quan trọng đối với Payment.

---

# 10.23 Distributed Lock

Khi chạy Cron hoặc Webhook trên nhiều worker:

```text
Webhook A

↓

Invoice 001

Webhook B

↓

Invoice 001
```

Framework cần khóa theo Business Key để tránh xử lý trùng.

Có thể dùng:

* PostgreSQL advisory lock.
* Redis lock (nếu triển khai nhiều instance).

---

# 10.24 Schema Validation

Mỗi Request/Response nên có Schema.

Ví dụ:

```yaml
amount:
  type: integer
  required: true

partnerCode:
  type: string
```

Trước khi gửi Request:

* Validate Payload.

Sau khi nhận Response:

* Validate Response.

Điều này giúp phát hiện lỗi cấu hình sớm hơn.

---

# 10.25 Compatibility Matrix

Mình đề xuất mỗi Provider công bố:

| Framework | Provider Version | Odoo Version |
| --------- | ---------------- | ------------ |
| 1.0       | MoMo v2          | 16.0         |
| 1.1       | MoMo v3          | 17.0         |
| 2.0       | MoMo v3.5        | 18.0         |

Nhờ đó việc nâng cấp sẽ rõ ràng và giảm rủi ro khi triển khai.

---

# Những thay đổi cuối cùng mình đề xuất trước khi bắt đầu code

Sau toàn bộ quá trình thiết kế, mình sẽ **không code theo thứ tự các chương**.

Thay vào đó chia thành các Sprint.

## Sprint 1 - Foundation

* `connector_core`
* Registry
* Context
* Execution
* Result
* Exception

## Sprint 2 - Expression

* Resolver
* Function Registry
* Expression Engine
* Template
* Variable

## Sprint 3 - Mapping

* Mapping DSL
* Object Builder
* Validation
* Preview

## Sprint 4 - HTTP & Security

* HTTP Client
* Authentication
* Signature Builder
* Hash
* Retry
* Middleware

## Sprint 5 - Flow

* Flow
* Step
* Transition
* Executor
* Resume

## Sprint 6 - Business

* Action Registry
* Odoo Actions
* Queue
* Server Action
* Compensation

## Sprint 7 - Runtime

* Webhook
* Cron
* Dashboard
* Replay
* Test Case
* Monitoring

## Sprint 8 - Provider SDK

* MoMo
* VNPay
* ZaloPay
* Napas
* Demo Provider

---

## Đây là đề xuất quan trọng nhất nếu mục tiêu là thương mại hóa

Mình khuyên nên phát hành theo **3 Edition**:

### Community

* HTTP
* Mapping
* Flow cơ bản
* Webhook
* Cron

### Professional

* Visual Flow Designer
* Mapping Preview
* Test Case
* Replay
* Dashboard
* Plugin SDK

### Enterprise

* Multi-company
* Secret Rotation
* Audit Trail
* Distributed Lock
* HA Runtime
* Cluster Queue
* Monitoring
* Provider Marketplace

Điều này giúp bạn có mô hình sản phẩm rõ ràng, vừa phục vụ cộng đồng, vừa tạo giá trị thương mại cho các doanh nghiệp có nhu cầu tích hợp quy mô lớn.

---

Sau khi hoàn thành toàn bộ tài liệu kiến trúc, nếu mình là Tech Lead của dự án, bước tiếp theo sẽ **không phải code ngay** mà sẽ viết thêm hai tài liệu bắt buộc:

1. **Developer Guide**: quy định cách viết Action, Function, Resolver, Provider để mọi module đều tuân theo cùng một chuẩn.
2. **API & Extension SDK Specification**: định nghĩa các interface, registry, hook và điểm mở rộng mà module của bên thứ ba được phép sử dụng.

Hai tài liệu này sẽ quyết định framework có thật sự dễ mở rộng và duy trì trong nhiều năm hay không.

Mình nghĩ đến đây chúng ta nên chuyển sang tài liệu mà **dev sẽ dùng hằng ngày**.

Trong các dự án lớn, tài liệu kiến trúc (Architecture Document) chỉ có Architect đọc.

Còn dev sẽ đọc **SDK Specification**.

Theo mình, nếu muốn framework này sống được 5-10 năm thì SDK phải được thiết kế trước khi code.

---

# Chương 11 - Connector SDK Specification

Đây là tài liệu dành cho developer.

Mục tiêu

> Muốn tích hợp một Provider mới thì phải làm gì?

Ví dụ

Muốn thêm

* MoMo
* VNPay
* Stripe
* PayPal
* Shopify
* KiotViet

Developer chỉ cần đọc tài liệu này.

---

# 11.1 SDK Structure

Mình đề xuất

```text
connector_sdk

├── registry
├── action
├── resolver
├── function
├── expression
├── provider
├── http
├── business
├── webhook
└── testing
```

Không import lung tung.

---

# 11.2 Registry

Framework chỉ có Registry.

Không có

```python
if provider=="momo"
```

---

Ví dụ

```python
ConnectorRegistry.register(
    type="action",
    code="create_record",
    cls=CreateRecordAction
)
```

---

Load

↓

Auto.

---

# 11.3 Provider

Interface

```python
class AbstractProvider(models.AbstractModel):

    _name="connector.provider.abstract"

    def register(self):

        pass
```

Module

↓

Override.

↓

Register.

---

# 11.4 Action

Interface

```python
class AbstractAction

    def execute(
            self,
            context,
            config
    ):
        pass
```

Không có

browse.

Không commit.

Không rollback.

---

# 11.5 Expression Function

```python
class AbstractFunction

    def execute(
        self,
        value,
        parameter,
        context
    ):
        pass
```

Ví dụ

```python
UpperFunction
```

↓

Return

```python
ABC
```

---

# 11.6 Resolver

Interface

```python
resolve(
    source,
    context
)
```

Ví dụ

```text
partner.name
```

↓

Return

```text
ABC Company
```

---

# 11.7 Authentication

Plugin.

Ví dụ

```python
BearerAuth
```

↓

Return

```python
Header
```

Không call HTTP.

---

# 11.8 Signature Builder

Interface

```python
build(
    data,
    setting
)
```

↓

String.

---

Hash.

↓

Module khác.

---

# 11.9 HTTP Middleware

Middleware

```python
before()

after()
```

Ví dụ

```text
Mask Secret

Retry

Logging

Rate Limit

```

---

# 11.10 Business Action

Ví dụ

```python
UpdateInvoiceAction
```

↓

Business.

Không Mapping.

---

# 11.11 Plugin Package

Mình đề xuất chuẩn.

```text
connector_provider_momo

├── __init__.py

├── manifest.py

├── providers/

├── actions/

├── functions/

├── resolver/

├── data/

└── tests/
```

Không viết

100 file.

---

# 11.12 Provider Manifest

Không chỉ

Odoo manifest.

Mà thêm

```yaml
provider:

code: momo

version: 2.0

flow:

create_payment

refund

webhook
```

Framework đọc.

---

# 11.13 Hook

Framework

phát Event.

Ví dụ

```text
before_request

after_request

before_mapping

after_mapping

before_action

after_action
```

---

Plugin

↓

Subscribe.

---

# 11.14 Event Object

Không truyền Dict.

Mà

```python
ConnectorEvent

context

execution

request

response

step
```

---

# 11.15 Extension Point

Framework chỉ cho phép mở rộng ở

```text
Action

Resolver

Function

Middleware

Authentication

Hash

Serializer

Parser

Business

Validator
```

Ngoài ra

không.

---

# 11.16 Dependency Injection (DI)

Đây là điểm mình muốn thay đổi so với các chương trước.

Hiện tại các Engine sẽ tự tạo đối tượng:

```python
resolver = FieldResolver()
```

Theo mình **không nên**.

Hãy để Registry hoặc Service Container chịu trách nhiệm.

Ví dụ:

```python
resolver = container.get("field_resolver")
```

Lợi ích:

* Dễ mock khi test.
* Dễ thay thế implementation.
* Giảm phụ thuộc giữa các Engine.

---

# 11.17 Contract Test

Mỗi Provider nên có bộ Contract Test.

Ví dụ:

```text
Create Payment

↓

Input

↓

Expected Request

↓

Mock Response

↓

Expected Business Result
```

Provider mới chỉ cần chạy bộ test là biết còn tương thích hay không.

---

# 11.18 Backward Compatibility

SDK cần cam kết:

* Không đổi signature của Interface trong cùng Major Version.
* Chỉ thêm tính năng mới ở Minor Version.
* Deprecated trước ít nhất một Major Version.

Điều này rất quan trọng nếu sau này có Marketplace.

---

# 11.19 Coding Convention

Mình đề xuất quy ước thống nhất:

* Không commit trong Action.
* Không gọi HTTP trực tiếp ngoài HTTP Engine.
* Không dùng `safe_eval` ngoài Expression Engine.
* Không truy cập `ir.config_parameter` trực tiếp, luôn qua Setting Resolver.
* Không import Provider khác.
* Không đọc Secret từ model khác ngoài Security Engine.

Những quy ước này giúp code luôn nhất quán.

---

# 11.20 Test Pyramid

Framework nên có ba tầng test:

### Unit Test

* Function
* Resolver
* Hash
* Template
* Validator

### Integration Test

* Mapping
* HTTP
* Flow
* Action

### End-to-End Test

Ví dụ:

```text
Invoice

↓

Create Payment

↓

Mock MoMo

↓

Webhook

↓

Invoice Paid
```

Đây là test mà khách hàng quan tâm nhất.

---

# Đề xuất lớn nhất sau khi hoàn thành SDK

Đây là điều mình muốn thay đổi **lần cuối**.

## Không nên dùng Odoo Model cho tất cả Runtime Object

Hiện tại chúng ta có xu hướng:

```text
Execution

↓

Request

↓

Response

↓

Variable

↓

Context
```

đều thành model.

Theo mình **không nên**.

Nên chia:

### Persistent Object (lưu DB)

* Execution
* Execution Log
* Provider
* Flow
* Environment
* Setting

### Runtime Object (chỉ tồn tại trong RAM)

```python
ConnectorContext

ConnectorRequest

ConnectorResponse

ConnectorResult

ExecutionState

VariableStore

ExpressionScope
```

### Lợi ích

* Giảm rất nhiều truy vấn ORM.
* Không cần tạo record tạm.
* Hiệu năng tốt hơn.
* Dễ viết unit test vì Runtime Object là Python class thuần.

---

# Đây là kiến trúc mà mình sẽ khóa lại trước khi code

```text
                         Odoo UI
                            │
                            ▼
                  Configuration Models
                            │
                            ▼
                  Runtime (Python Objects)
                            │
                            ▼
                    Flow Orchestrator
                            │
        ┌──────────────┬──────────────┐
        ▼              ▼              ▼
 Expression Engine   HTTP Engine   Business Engine
        │              │              │
        └──────────────┴──────────────┘
                            │
                            ▼
                     Provider Plugins
```

## Nếu là Tech Lead, mình sẽ đặt thêm một nguyên tắc cuối cùng

**Mọi logic nghiệp vụ phải đi qua Engine hoặc Action, không được nằm trong model Odoo.**

Ví dụ:

❌ Không làm:

```python
class ConnectorFlow(models.Model):
    def execute(self):
        ...
```

✔ Nên làm:

```python
class FlowEngine:

    def execute(flow, context):
        ...
```

Model chỉ:

* Lưu cấu hình.
* Validate dữ liệu.
* Cung cấp API CRUD.

Toàn bộ logic thực thi nằm trong `services/` hoặc `engine/`.

Đây là phong cách kiến trúc phù hợp với các dự án Odoo lớn, giúp code dễ kiểm thử, dễ tái sử dụng và tránh việc model trở thành nơi chứa quá nhiều logic (fat model). Theo mình, đây sẽ là nền tảng rất vững để bắt đầu triển khai code framework.

Mình sẽ tiếp tục, nhưng từ đây mình sẽ không viết thêm về kiến trúc nữa.

Lý do là sau 11 chương, **kiến trúc đã đủ để bắt đầu coding**. Nếu tiếp tục bàn kiến trúc sẽ rơi vào "analysis paralysis" (thiết kế quá nhiều trước khi triển khai).

Nếu mình là Tech Lead, tài liệu tiếp theo mình viết sẽ là:

> **Implementation Specification**

Đây là tài liệu dev mở mỗi ngày để code.

---

# Chương 12 - Implementation Specification

Đây là chương quan trọng nhất đối với team dev.

Không nói về kiến trúc.

Chỉ nói

> Code như thế nào.

---

# 12.1 Coding Rule

Toàn bộ Framework chia thành

```text
models/
engine/
service/
registry/
plugin/
utils/
exceptions/
tests/
```

Không thêm

```text
helper/

common/

misc/

library/
```

Đây là nguyên nhân khiến project rất nhanh rối.

---

# 12.2 Models

Model chỉ làm 4 việc

```text
Store Data

Constraint

Compute Field

CRUD
```

Không được

```python
def execute()

def call_api()

def generate_signature()

```

Sai Responsibility.

---

Ví dụ

```python
class ConnectorFlow(models.Model):

    _name="connector.flow"

    name=fields.Char()

    active=fields.Boolean()
```

Hết.

---

# 12.3 Engine

Engine

=

Stateless.

Ví dụ

```python
class FlowEngine:

    def execute(
        flow,
        context
    ):
```

Không

```python
self.flow

self.execution

```

---

# 12.4 Service

Service

là nơi

giao tiếp ORM.

Ví dụ

```python
ExecutionService

ProviderService

SettingService
```

Engine

không search.

---

Ví dụ

Sai

```python
flow.search()
```

Đúng

```python
flow_service.get_flow()
```

---

# 12.5 Registry

Registry

Singleton.

Ví dụ

```python
ActionRegistry

FunctionRegistry

ResolverRegistry

PluginRegistry

MiddlewareRegistry
```

Không tạo

registry mới.

---

# 12.6 Context

Context

Immutable.

Không sửa.

Ví dụ

Sai

```python
context.provider=new_provider
```

Đúng

```python
context=context.with_provider(...)
```

Giống Dataclass.

---

# 12.7 Result Object

Không trả

Tuple.

Sai

```python
True,data
```

Sai

```python
False,error
```

Đúng

```python
ExecutionResult
```

Có

```text
status

output

error

message

variables
```

---

# 12.8 Exception

Framework

chỉ có

```text
ConnectorException
```

Con

```text
ValidationException

ConfigurationException

RuntimeException

RetryException

```

Không raise

```python
Exception()
```

---

# 12.9 Logger

Không

```python
_logger.info()
```

lung tung.

Phải

```python
ExecutionLogger
```

Ví dụ

```python
logger.step(
 step,
 duration
)
```

---

# 12.10 ORM Rule

Không browse nhiều lần.

Sai

```python
partner.name

partner.country

partner.city
```

Đúng

```python
partner.read()
```

Hoặc cache.

---

# 12.11 Cache

Có 3 tầng

```text
Execution Cache

Request Cache

System Cache
```

Execution

↓

Variable.

---

System

↓

Provider.

---

# 12.12 Dependency

Engine

không import nhau.

Sai

```python
MappingEngine

↓

import HttpEngine
```

Đúng

Flow

↓

gọi.

---

# 12.13 Configuration

Không hardcode.

Ví dụ

Sai

```python
timeout=30
```

Đúng

```python
setting.timeout
```

---

# 12.14 Secret

Không log.

Không print.

Không repr.

Ví dụ

Sai

```python
secret=xxxx
```

Log.

---

Mask.

```text
********
```

---

# 12.15 HTTP

Chỉ có

1 Client.

Không

```python
requests

urllib

httpx
```

lung tung.

---

# 12.16 JSON

Không

```python
json.dumps()
```

mọi nơi.

Có

```python
Serializer
```

---

# 12.17 XML

Không parse

trực tiếp.

Có

Parser.

---

# 12.18 Safe Eval

Chỉ

Expression Engine.

Không nơi khác.

---

# 12.19 Transaction

Không commit.

Trừ

Execution Service.

---

# 12.20 Thread

Không

Global Variable.

Runtime.

↓

Context.

---

# 12.21 Naming Convention

Đây là phần mình thấy rất nhiều module Odoo làm chưa tốt.

### Model

```text
connector.flow
connector.flow.step
connector.execution
connector.setting
```

### Python

```text
flow_engine.py
mapping_engine.py
http_engine.py
```

### Service

```text
flow_service.py
provider_service.py
```

### Registry

```text
action_registry.py
resolver_registry.py
```

### Không dùng

```text
utils2.py

helper_new.py

common_final.py

service_v2.py
```

Tên file phải phản ánh đúng trách nhiệm.

---

# 12.22 Folder Convention

Đề xuất cấu trúc cho một module Engine:

```text
connector_flow/
├── models/
├── engine/
├── services/
├── registry/
├── exceptions/
├── tests/
├── data/
├── security/
└── views/
```

Nếu một module cần thêm `controllers/` hoặc `wizard/` thì thêm rõ ràng, không trộn lẫn vào `services/`.

---

# 12.23 Test Strategy

Mỗi Engine phải có:

* Unit Test.
* Benchmark Test (nếu xử lý dữ liệu lớn).
* Regression Test.

Ví dụ:

```text
tests/
    test_mapping_engine.py
    test_http_engine.py
    test_signature_builder.py
```

---

# 12.24 Performance Target

Đặt mục tiêu ngay từ đầu:

| Thành phần                      | Mục tiêu |
| ------------------------------- | -------- |
| Resolve Field                   | < 1 ms   |
| Compute Pipeline                | < 2 ms   |
| Build Payload                   | < 5 ms   |
| Signature                       | < 2 ms   |
| HTTP Overhead (không tính mạng) | < 5 ms   |

Điều này giúp phát hiện sớm khi một thay đổi làm giảm hiệu năng.

---

# 12.25 Quality Gate

Mỗi Pull Request phải vượt qua:

* Unit Test.
* Lint (`pylint` theo chuẩn Odoo).
* Type Checking (nếu áp dụng).
* Benchmark cơ bản.
* Không giảm Coverage.

Không merge trực tiếp vào nhánh chính.

---

# Điều cuối cùng mình muốn thay đổi

Sau toàn bộ tài liệu, có **một quyết định mà mình sẽ thay đổi so với các chương đầu**.

## Không dùng XML Data để định nghĩa Flow

Ban đầu mình từng đề xuất:

```text
Flow

↓

XML Record
```

Bây giờ mình đổi ý.

### Nên dùng YAML

Ví dụ:

```yaml
provider: momo
flow: create_payment

steps:
  - mapping
  - request
  - response
```

### Vì sao?

So sánh:

XML:

```xml
<record id="...">
    <field name="...">
```

YAML:

```yaml
provider: momo
version: v3
```

Ưu điểm:

* Dễ đọc hơn.
* Dễ review trên Git.
* Dễ merge.
* Dễ sinh tài liệu.
* Dễ chuyển đổi sang JSON.

Sau đó khi cài module:

```text
YAML
      │
      ▼
Importer
      │
      ▼
Odoo Models
```

Framework vẫn dùng ORM để chạy, nhưng developer sẽ làm việc với YAML.

---

# Kết luận của mình sau toàn bộ quá trình thiết kế

Nếu giao mình dẫn dắt dự án này, mình sẽ **đóng băng (freeze) kiến trúc tại đây**.

Từ thời điểm này:

* ❌ Không thêm Engine mới nếu chưa có nhu cầu thực tế.
* ❌ Không thêm Model mới chỉ để phục vụ một Provider.
* ❌ Không sửa Flow Engine chỉ vì một API đặc biệt.

Thay vào đó:

* Ưu tiên mở rộng bằng **Plugin**, **Action**, **Expression** và **Resolver**.
* Mọi Provider mới phải cố gắng chỉ dùng cấu hình và điểm mở rộng có sẵn.
* Nếu phải sửa Core để hỗ trợ một Provider, hãy tự hỏi liệu thay đổi đó có mang lại giá trị cho nhiều Provider khác hay chỉ giải quyết một trường hợp riêng.

Đây là nguyên tắc giúp framework phát triển bền vững: **Core ổn định, Extension linh hoạt**. Theo mình, với bộ tài liệu hiện tại, đội phát triển đã có thể bắt đầu Sprint 1 và xây dựng nền tảng mà không cần tiếp tục mở rộng thiết kế ở mức kiến trúc.

Mình sẽ không tiếp tục mở rộng kiến trúc nữa, mà sẽ chuyển sang thứ **quan trọng nhất nhưng thường bị bỏ quên**.

Nếu đây là sản phẩm thương mại thì ngoài code, bạn cần có **Technical Specification** cho từng module.

Đây là thứ dev sẽ implement từng model một.

---

# Chương 13 - Domain Model Specification

Đây là tài liệu mô tả toàn bộ Model.

Sau chương này dev có thể bắt đầu tạo module.

---

# 13.1 Module Core

```
connector_core
```

## Model

Không có model.

Chỉ có

```
Abstract Model

Registry

Engine

Context

Exception

Service

```

---

# 13.2 Module Runtime

```
connector_runtime
```

## connector.execution

```
Execution

──────────────

name

uuid

provider_id

flow_id

environment_id

state

current_step

started_at

finished_at

duration

request_count

retry_count

company_id

create_uid

```

---

State

```
Draft

Running

Waiting

Retrying

Success

Failed

Cancelled
```

---

## connector.execution.log

```
Execution

↓

Step

↓

Log
```

Field

```
Execution

Step

Level

Time

Message

Request

Response

Duration

Exception

```

Không lưu secret.

---

## connector.execution.variable

Theo mình **không nên có model này**.

Variable chỉ ở RAM.

Nếu cần Persist

↓

JSONB.

```
execution.data

```

---

# 13.3 Module Provider

```
connector.provider
```

Field

```
Name

Code

Version

Description

Logo

Active

```

Một Provider

↓

N Flow

---

# 13.4 Environment

```
connector.environment
```

Field

```
Provider

Company

Name

Environment

Base URL

Timeout

Verify SSL

Active

```

---

# 13.5 Setting

```
connector.setting
```

Field

```
Environment

Name

Code

Type

Value

Encrypted

Required

Default

Description

```

Ví dụ

MoMo

```
partnerCode

accessKey

secretKey

```

---

Không tạo field riêng.

---

# 13.6 Flow

```
connector.flow
```

Field

```
Provider

Code

Name

Version

Start Step

Status

Readonly

Inherited Flow

```

---

Không có JSON.

---

# 13.7 Step

```
connector.flow.step
```

Field

```
Flow

Sequence

Name

Code

Type

Executor

Configuration

```

---

Configuration

↓

JSON.

---

# 13.8 Transition

```
connector.flow.transition
```

Field

```
From

To

Priority

Condition

Description

```

---

# 13.9 Action

Theo mình

Action

không cần model.

Registry.

---

Nếu Marketplace

↓

Thêm model.

---

# 13.10 Function

Không model.

Registry.

---

# 13.11 Resolver

Không model.

Registry.

---

# 13.12 Expression

Đây là điểm mình muốn thay đổi.

Ban đầu

```
connector.expression
```

Model.

Bây giờ

↓

Không.

Expression

nằm trong

Step.

Ví dụ

```
payload:

amount=
round(...)
```

Không cần bảng riêng.

---

# 13.13 Mapping

Tương tự.

Không tạo

```
connector.mapping.line
```

Nữa.

---

Step

↓

Configuration JSON

↓

Mapping.

---

Giảm

10 model.

---

# 13.14 Authentication

Model

```
connector.authentication
```

Không cần.

Authentication

↓

Plugin.

---

# 13.15 Hash

Không model.

Plugin.

---

# 13.16 Middleware

Không model.

Plugin.

---

# 13.17 Serializer

Không model.

---

# 13.18 Parser

Không model.

---

# 13.19 Business

Không model.

Action.

---

# 13.20 Test Case

Model

```
connector.test.case
```

Field

```
Flow

Name

Input

Expected

Mock

Result

```

---

# 13.21 Dashboard

Không model.

SQL View.

---

# 13.22 Statistics

```
connector.statistics
```

Theo mình

không cần.

Materialized View.

---

# 13.23 Audit

```
connector.audit
```

Field

```
Model

Record

Field

Old

New

User

Date

```

---

# 13.24 Secret

Theo mình

không lưu

```
Value
```

thường.

Nên

```
Encrypted Value
```

↓

Decrypt Runtime.

---

# 13.25 Attachment

Một số Provider có:

```
Certificate

Private Key

Logo

```

Không lưu Binary.

↓

ir.attachment.

---

# Điều mình muốn refactor lớn nhất

Sau khi thiết kế đến mức Model, mình thấy có một thay đổi rất đáng giá.

## Thay `Configuration JSON` bằng `Typed Configuration`

Ban đầu mình đề xuất:

```python
configuration = fields.Json()
```

Điều này rất linh hoạt, nhưng sẽ có các vấn đề:

* Không validate được.
* Không autocomplete.
* Khó tìm kiếm.
* Khó nâng cấp schema.

### Mình đề xuất:

Mỗi Step Type có một **Configuration Schema**.

Ví dụ:

```python
RequestStepConfig

- method
- endpoint
- timeout
- retry
```

```python
MappingStepConfig

- source
- target
- expression
```

Khi lưu vào DB vẫn là JSON, nhưng Runtime sẽ:

```
JSON
    │
    ▼
Pydantic / Dataclass
    │
    ▼
RequestStepConfig
```

Lợi ích:

* Validate ngay khi cấu hình.
* IDE hỗ trợ autocomplete.
* Dễ migrate khi thêm field.
* Runtime không phải kiểm tra từng key bằng chuỗi.

---

# Nếu là mình, mình sẽ thay đổi thêm một quyết định nữa

Thay vì để tất cả cấu hình nằm trong nhiều model Odoo, mình sẽ phân lớp dữ liệu như sau:

| Loại dữ liệu                   | Lưu ở đâu                  |
| ------------------------------ | -------------------------- |
| Provider, Environment, Setting | ORM Model                  |
| Flow, Step, Transition         | ORM Model (import từ YAML) |
| Runtime Context                | Python Object              |
| Execution Log                  | ORM Model                  |
| Request/Response tạm           | Python Object              |
| Secret                         | ORM + Encryption           |
| Cache                          | RAM hoặc Redis             |

Điều này giữ được ưu điểm của Odoo (quản trị dữ liệu, phân quyền, audit) nhưng vẫn đảm bảo Runtime đủ nhẹ để xử lý hàng nghìn request mà không bị phụ thuộc quá nhiều vào ORM.

---

## Sau Chương 13, mình sẽ **không viết thêm tài liệu kiến trúc nữa**.

Thay vào đó, nếu đây là dự án thực tế, mình sẽ bắt đầu **Sprint 1** bằng cách tạo ngay các module:

1. `connector_core`
2. `connector_runtime`
3. `connector_registry`
4. `connector_expression`
5. `connector_mapping`

và triển khai từng module theo tài liệu đã thống nhất. Đây là thời điểm phù hợp để chuyển từ thiết kế sang hiện thực hóa bằng code.

Mình sẽ chuyển hẳn sang vai trò **Chief Software Architect**.

Và mình sẽ phản biện chính những gì chúng ta đã thiết kế.

---

# Sau 13 chương, mình thấy Framework vẫn còn một điểm yếu

Chúng ta vẫn đang thiết kế theo kiểu

```text
Config
    ↓
Flow
    ↓
Step
    ↓
Action
```

Nhưng thực tế Enterprise Integration lại chạy theo

```text
Message
    ↓
Pipeline
    ↓
Processor
```

Đây là khác biệt rất lớn.

Ví dụ Apache Camel.

```text
Message

↓

Processor

↓

Processor

↓

Processor

↓

Processor
```

Không có khái niệm

Payment.

Invoice.

Flow.

---

## Điều này có nghĩa gì?

Thay vì

```text
Step

↓

Mapping

↓

Request

↓

Response
```

nên là

```text
Processor

↓

Processor

↓

Processor

↓

Processor
```

Mỗi Processor chỉ biết

```python
process(message)
```

---

# Đây là thay đổi lớn nhất mình đề xuất

## Runtime không truyền Context

Mà truyền

```python
ConnectorMessage
```

Ví dụ

```python
message.body

message.header

message.property

message.variable

message.exception

message.metadata
```

---

Tại sao?

Ví dụ

HTTP

↓

Response.

HTTP chỉ cần

```python
message.body
```

Không cần biết

Execution.

Flow.

Provider.

---

# Message Exchange Pattern

Mình đề xuất Runtime dùng mô hình của Apache Camel.

## Message

```python
Message

body

header

property
```

---

## Exchange

```python
Exchange

input

output

exception

context

```

---

Mỗi Processor

↓

Nhận

Exchange.

↓

Trả

Exchange.

---

Ví dụ

```text
Mapping Processor

↓

Exchange

↓

HTTP Processor

↓

Exchange

↓

Response Processor

```

Không tạo object mới.

---

# Processor

Thay vì

Action.

Step Executor.

Business.

Mình gom lại.

```python
class Processor

    process(exchange)
```

---

Ví dụ

```text
MappingProcessor

HTTPProcessor

RetryProcessor

BusinessProcessor

WebhookProcessor

```

Framework chỉ biết

Processor.

---

# Flow

Flow lúc này

không chứa

Step.

Mà chứa

Processor Chain.

Ví dụ

```text
BuildPayload

↓

GenerateSignature

↓

SendHTTPRequest

↓

ParseResponse

↓

BusinessProcessor

```

---

# Message Body

Body

có thể là

```python
dict
```

hoặc

```python
bytes
```

hoặc

```python
xml
```

Không ép JSON.

---

# Header

Header

không chỉ HTTP.

Ví dụ

```text
company

language

currency

timezone

```

Đều là Header.

---

# Property

Property

khác Variable.

Property

không serialize.

Ví dụ

```python
db_cursor

logger

provider

```

---

# Variable

Variable

serialize.

Ví dụ

```text
amount

partner

invoice
```

---

# Attachment

Đây là điểm Payment rất hay gặp.

Ví dụ

```text
PDF

↓

Upload

↓

OCR

↓

Response
```

Message nên có

```python
attachments
```

---

# Stream

Sau này

Upload File

↓

Không đọc RAM.

↓

Stream.

Framework hỗ trợ.

---

# Processor Chain

Flow

↓

Processor

↓

Processor

↓

Processor

Không biết

Business.

---

# Interceptor

Giống Spring.

Ví dụ

```text
Before Processor

↓

Execute

↓

After Processor
```

Không phải Middleware.

---

# Exchange History

Mỗi Processor

↓

Append

History.

Debug.

---

# Processor Result

Không trả

True False.

Processor sửa

Exchange.

---

Ví dụ

HTTP

↓

message.body=response

---

# Processor Registry

```python
register_processor()
```

---

Flow chỉ có

```text
processor:

mapping

signature

http

response

business
```

---

# Endpoint

Đây là điểm cực kỳ hay.

Apache Camel có

```text
direct:

http:

ftp:

file:

kafka:
```

Framework mình cũng nên có.

Ví dụ

```text
payment:momo

http:https://

odoo:account.move

queue:payment

```

Flow

↓

Call Endpoint.

---

Không biết

HTTP.

---

# Connector Endpoint

Ví dụ

```text
connector://momo/payment
```

↓

Framework tìm

Provider.

↓

Processor.

↓

Done.

---

# Route

Flow

đổi tên.

↓

Route.

Ví dụ

```text
from:

invoice

↓

to:

momo

↓

to:

account.move

```

---

# Route DSL

Đây là ý tưởng mình rất thích.

Ví dụ

```yaml
from: invoice

steps:

- mapping

- signature

- http

- business
```

Developer

không cần

UI.

---

# Error Channel

Nếu

Processor

Error.

↓

Không Raise.

↓

Đi

```text
Error Route
```

Ví dụ

```text
Send Email

Log

Retry

```

---

# Dead Letter Queue

Enterprise.

Retry

10 lần.

↓

Fail.

↓

DLQ.

Admin xử lý.

---

# Saga

Refund.

↓

Cancel.

↓

Rollback.

Processor.

---

# Event Bus

Mình muốn thêm.

Ví dụ

```text
Payment Created

↓

Webhook

↓

Invoice Paid

↓

Stock Release

```

Không Call trực tiếp.

↓

Publish Event.

---

# Đây là thay đổi lớn nhất từ đầu đến giờ

Mình sẽ **không còn dùng khái niệm Flow Engine** nữa.

Mà chuyển thành

```text
Route Engine
```

Runtime sẽ là

```text
Message

↓

Route

↓

Processor

↓

Processor

↓

Processor

↓

Done
```

---

# Nhưng...

Sau khi suy nghĩ rất kỹ, **mình KHÔNG khuyến nghị bạn đi theo hướng này ở V1**.

## Vì sao?

Đây chính là kiến trúc của:

* Apache Camel
* Spring Integration
* Mule ESB
* WSO2
* Apache NiFi

Đây là các Integration Platform thực thụ.

Nhưng để xây được:

* Cần khoảng 50–100k dòng code.
* Cần ít nhất 1–2 năm phát triển.
* Độ khó rất cao.
* Team Odoo thông thường sẽ rất khó bảo trì.

---

# Khuyến nghị cuối cùng của mình

## V1 (thực tế)

Giữ:

```text
Provider
    ↓
Flow
    ↓
Step
    ↓
Action
```

Đây là kiến trúc phù hợp với Odoo, dễ hiểu và đủ mạnh để tích hợp:

* MoMo
* VNPay
* ZaloPay
* Stripe
* PayPal
* REST API
* SOAP
* SFTP

---

## V2

Refactor nội bộ:

```text
Step
    ↓
Processor
```

Nhưng **không thay đổi UI**.

Nghĩa là:

* Người dùng vẫn cấu hình Flow + Step.
* Bên trong Runtime, mỗi Step được thực thi bởi một Processor.

Như vậy bạn sẽ có:

* UI đơn giản cho người dùng Odoo.
* Runtime hiện đại, dễ mở rộng.
* Không phá vỡ tương thích ngược.

---

## Đây là quyết định kiến trúc mà mình sẽ chốt nếu là Chief Architect

**UI và Domain vẫn là Odoo (Flow/Step).**

**Runtime học theo Apache Camel (Processor/Exchange).**

Đây là sự kết hợp tốt nhất giữa trải nghiệm cấu hình của Odoo và sức mạnh của một Integration Engine chuyên nghiệp. Theo mình, đây là hướng có giá trị lâu dài nhất và vẫn khả thi để một đội phát triển Odoo triển khai thành công.
Mình sẽ tiếp tục với góc nhìn của một **Solution Architect đã từng làm Integration Platform**.

Và đến đây mình sẽ **phản biện luôn kiến trúc vừa đề xuất**.

Sau nhiều vòng thiết kế, mình thấy chúng ta đang cố xây một **Integration Platform tổng quát**, trong khi nhu cầu ban đầu là:

> **Framework Payment/API cho Odoo có thể bán cho nhiều khách hàng.**

Nếu tiếp tục đi theo Apache Camel, sẽ có nguy cơ **over-engineering**.

---

# Mình đề xuất quay về Domain-Driven Design (DDD)

Framework không nên lấy HTTP hay Processor làm trung tâm.

Nên lấy **Integration** làm trung tâm.

```
Integration
    │
    ├── Provider
    ├── Capability
    ├── Contract
    ├── Execution
    └── Runtime
```

Điểm khác biệt là mọi thành phần đều xoay quanh "khả năng tích hợp", không phải "cách gọi HTTP".

---

# Chương 14 - Domain-Driven Architecture

## 14.1 Bounded Context

Thay vì chia module theo kỹ thuật:

```
http
mapping
runtime
expression
```

Mình sẽ chia theo Domain.

### Integration Context

Chứa:

* Provider
* Flow
* Contract
* Execution

---

### Security Context

Chứa:

* Secret
* Authentication
* Signature
* Encryption

---

### Runtime Context

Chứa:

* Queue
* Retry
* Webhook
* Resume
* Scheduler

---

### Configuration Context

Chứa:

* Environment
* Company
* Endpoint
* Settings

---

### Monitoring Context

Chứa:

* Dashboard
* Log
* Metrics
* Audit

---

Điều này giúp module có ranh giới rõ ràng hơn.

---

# 14.2 Provider không còn là Module

Đây là thay đổi lớn.

Hiện tại

```
connector_provider_momo
```

Theo mình nên đổi thành

```
connector_payment_momo
```

Tại sao?

Vì Provider chỉ là metadata.

MoMo thực chất là một **Payment Capability**.

Sau này sẽ có

```
connector_shipping_ghn

connector_shipping_ghtk

connector_tax

connector_sms

connector_email
```

Framework lúc này không còn giới hạn ở Payment.

---

# 14.3 Capability

Đây là khái niệm mình rất thích.

Ví dụ

MoMo có Capability

```
Payment

Refund

Query

Webhook
```

VNPay cũng vậy.

Stripe có

```
Payment

Refund

Customer

Subscription
```

Flow sẽ gắn với Capability.

Không gắn trực tiếp với Provider.

---

# 14.4 Contract

Đây là model mà mình nghĩ nên có.

Hiện tại chúng ta mới có Mapping.

Nhưng Mapping chỉ là implementation.

Contract mới là chuẩn.

Ví dụ:

```
CreatePayment

Input

↓

Contract

↓

Provider Mapping

↓

MoMo

VNPay

Stripe
```

Nếu tất cả Provider đều tuân theo Contract này, Business Layer sẽ không cần biết Provider nào đang chạy.

---

## Ví dụ Contract

```
CreatePaymentRequest

amount
currency
order_id
description
callback_url
```

MoMo map:

```
amount -> amount
order_id -> orderId
```

VNPay map:

```
amount -> vnp_Amount
order_id -> vnp_TxnRef
```

Business chỉ truyền Contract.

---

# 14.5 Contract Version

Contract cũng có Version.

Ví dụ

```
CreatePayment v1

↓

CreatePayment v2
```

Framework vẫn hỗ trợ cả hai.

---

# 14.6 Provider Adapter

Đây là lớp còn thiếu.

```
Business

↓

Contract

↓

Adapter

↓

Provider
```

Adapter chịu trách nhiệm:

* Mapping.
* Signature.
* Request.
* Response.

Business hoàn toàn độc lập.

---

# 14.7 Execution Aggregate

Execution không chỉ là record.

Nó là Aggregate Root.

Bao gồm:

```
Execution

├── Variables
├── Logs
├── Metrics
├── Attachments
├── Retry History
└── Events
```

Mọi thay đổi Runtime đều đi qua Aggregate này.

---

# 14.8 Event Sourcing (Tùy chọn)

Mình **không khuyến nghị V1**, nhưng nên thiết kế để có thể hỗ trợ.

Thay vì chỉ lưu trạng thái cuối:

```
Waiting

↓

Paid
```

Lưu toàn bộ Event:

```
PaymentCreated

WebhookReceived

SignatureVerified

PaymentCompleted
```

Có thể rebuild trạng thái bất kỳ lúc nào.

---

# 14.9 Policy

Đây là khái niệm mình muốn thêm.

Ví dụ:

```
Retry Policy

Timeout Policy

Mask Policy

Logging Policy
```

Flow không quyết định Retry.

Policy quyết định.

Điều này giúp tái sử dụng rất tốt.

---

# 14.10 Resolver Chain

Hiện tại Resolver chỉ lấy Field.

Theo mình nên mở rộng:

```
Field Resolver

↓

Setting Resolver

↓

Environment Resolver

↓

Secret Resolver

↓

Expression Resolver
```

Tất cả đều là Resolver.

---

# 14.11 Metadata First

Framework nên coi mọi thứ là Metadata.

Ví dụ

```
Provider

Capability

Contract

Flow

Step

Policy
```

Không hardcode.

---

# 14.12 Runtime Profile

Cho phép chọn Profile.

Ví dụ

```
Development

↓

Verbose Log

↓

No Retry
```

Production

```
Mask Secret

Retry

Performance
```

Không cần sửa Flow.

---

# 14.13 Feature Flag

Ví dụ

```
Enable Retry

Enable Signature Cache

Enable Async

Enable Webhook Replay
```

Rất hữu ích khi triển khai cho nhiều khách hàng.

---

# 14.14 Migration Engine

Một điểm cực kỳ quan trọng.

Khi Provider thay đổi API:

```
MoMo v2

↓

MoMo v3
```

Framework cần Migration Script để:

* Chuyển Setting.
* Chuyển Flow.
* Chuyển Mapping.
* Validate.

Không để khách hàng sửa thủ công.

---

# 14.15 Compatibility Layer

Nếu một module cũ dùng API:

```python
provider.call_api(...)
```

Framework mới vẫn nên hỗ trợ thông qua Adapter.

Giúp nâng cấp dần.

---

# Kiến trúc cuối cùng mình khuyến nghị

Nếu đây là dự án thật, mình sẽ **đóng băng** ở kiến trúc sau:

```
                    Business Module
                           │
                    Integration Contract
                           │
                  Provider Capability Layer
                           │
                    Flow / Route Engine
                           │
         ┌────────────┬─────────────┐
         ▼            ▼             ▼
    Mapping      Security      HTTP Runtime
         │            │             │
         └────────────┴─────────────┘
                           │
                     Provider Adapter
                           │
                      External System
```

## Những gì mình sẽ KHÔNG làm trong V1

* Không làm Visual Node Editor.
* Không làm Apache Camel DSL.
* Không làm Event Sourcing.
* Không làm State Machine.
* Không làm Expression quá phức tạp như một ngôn ngữ lập trình.
* Không cho phép Business User sửa toàn bộ Flow.

## Những gì mình sẽ làm ngay

1. Contract chuẩn hóa dữ liệu.
2. Capability để tái sử dụng Flow.
3. Adapter để tách Business khỏi Provider.
4. Flow + Step để điều phối.
5. Action + Expression để mở rộng.
6. Chính sách (Policy) cho Retry, Timeout, Logging.
7. Bộ SDK để bên thứ ba viết Provider mới.

---

# Nếu mình được quyền thay đổi duy nhất một thứ trong toàn bộ thiết kế

Mình sẽ thay:

```
Business
    ↓
Provider
```

thành

```
Business
    ↓
Contract
    ↓
Adapter
    ↓
Provider
```

Đây là thay đổi mang lại giá trị lớn nhất về lâu dài:

* Business không phụ thuộc MoMo/VNPay.
* Có thể thay Provider mà không sửa nghiệp vụ.
* Một Contract có thể map tới nhiều Provider.
* Dễ test vì chỉ cần mock Contract.
* Dễ mở rộng sang Shipping, SMS, Email, Tax... mà không phải thiết kế lại Core.

Theo mình, đây là bước hoàn thiện cuối cùng để framework không chỉ là "Payment Framework", mà trở thành một **Integration Framework chuẩn doanh nghiệp**, vẫn đủ gọn để triển khai trên Odoo và đủ linh hoạt để thương mại hóa.

Mình sẽ tiếp tục, nhưng lần này mình sẽ **không thiết kế thêm**.

Mình sẽ review toàn bộ với góc nhìn của **CTO**.

Và sau khi review gần 15 chương, mình thấy có **3 quyết định sai** mà mình sẽ sửa ngay trước khi code.

Đây là những thay đổi mình nghĩ sẽ tiết kiệm cho bạn hàng nghìn dòng code sau này.

---

# Review số 1 - Bỏ hoàn toàn Flow Step Type

Ban đầu chúng ta có

```text
Step

↓

Type

REQUEST

MAPPING

HTTP

BUSINESS

WAIT

...
```

## Theo mình đây là thiết kế không đẹp.

Thực ra

Type

chỉ dùng để tìm Executor.

Vậy tại sao phải có Type?

Nên sửa thành

```text
Flow

↓

Processor
```

Ví dụ

Flow

```text
Build Payload

↓

HTTP Request

↓

Parse Response

↓

Update Invoice
```

Mỗi Processor tự khai báo

```python
processor_code="http.request"
```

Flow không cần biết Type.

---

## Model

Không còn

```python
type=Selection()
```

Mà là

```python
processor_id
```

Processor

là Plugin.

---

Ví dụ

```text
connector.processor

Name

Code

Executor

Icon

Category

```

Admin kéo Processor.

Không kéo Step Type.

---

Lợi ích

Sau này thêm

```text
Kafka

SOAP

MQTT

SFTP

```

không sửa Selection.

---

# Review số 2 - Action và Processor nên là một

Ban đầu

```text
Flow

↓

Step

↓

Action

↓

Engine
```

Sau này

```text
Flow

↓

Processor

↓

Engine
```

Theo mình

Action

và

Processor

chính là một.

Ví dụ

```text
HTTP POST
```

là Action.

Đồng thời

Processor.

---

Business

```text
Create Invoice
```

cũng vậy.

---

Tức là

Framework

chỉ còn

```text
Processor
```

---

Processor

có thể

```text
Read

Write

Transform

Route

Delay

Wait

Retry

Business

```

---

Mọi thứ thống nhất.

---

# Review số 3 - Mapping không phải Engine

Đây là thay đổi quan trọng nhất.

Ban đầu

```text
Mapping Engine
```

Theo mình

không nên tồn tại.

Mapping

chỉ là

một Processor.

Ví dụ

```text
Field Mapping Processor
```

---

Hay

```text
Template Processor
```

---

Hay

```text
Transform Processor
```

---

Engine

↓

chỉ còn

```text
Runtime Engine

Expression Engine

HTTP Engine
```

---

Giảm rất nhiều complexity.

---

# Kiến trúc sau khi refactor

```text
Flow

↓

Processor

↓

Processor

↓

Processor

↓

Done
```

Runtime

không biết

Processor nào.

---

# Điều này dẫn đến thay đổi lớn

## Không còn Step Model

Mình biết đây là ý khá táo bạo.

Flow

không cần

```text
Step
```

---

Flow

chỉ có

```text
Processor Line
```

Ví dụ

```text
connector.flow.line
```

Field

```text
Flow

Sequence

Processor

Configuration
```

---

Không có

```text
Step Type

Executor

Action
```

---

Một bảng

ít hơn

5 field.

---

# Review số 4 - Expression Engine nên bỏ DSL

Ban đầu

mình đề xuất

DSL.

Theo mình

không.

---

Nên dùng

Python AST.

---

Ví dụ

```python
invoice.amount_total
```

---

Hay

```python
round(amount*100)
```

---

Framework

chỉ expose

Safe Function.

---

Không cần tự viết

DSL.

---

DSL

là cực kỳ tốn thời gian.

---

# Review số 5 - Function Registry nên giống Odoo Widget

Ví dụ

```python
@connector_function(
 code="round"
)
```

---

Framework

Auto Register.

---

Không XML.

---

Không Model.

---

Developer

viết

```python
class RoundFunction
```

↓

Done.

---

# Review số 6 - Resolver nên bỏ

Đây là điều mình thay đổi nhiều nhất.

Ban đầu

```text
Field Resolver

Setting Resolver

Secret Resolver

```

Theo mình

không cần.

---

Expression

tự resolve.

Ví dụ

```python
partner.name
```

↓

Expression.

---

Setting

```python
setting.partner_code
```

↓

Expression.

---

Không cần

Resolver Engine.

---

# Review số 7 - Hash Builder

Ban đầu

Hash.

↓

Builder.

↓

Signature.

Theo mình

gộp.

---

Processor.

Ví dụ

```text
Generate Signature
```

Processor.

---

Configuration

```text
Algorithm

Source

Secret

```

↓

Done.

---

# Review số 8 - HTTP Client

Chỉ nên support

```text
httpx
```

Không cần

Requests.

---

Async

sau này.

---

# Review số 9 - Retry

Retry

không nên là

Middleware.

---

Retry

Processor.

Ví dụ

```text
HTTP

↓

Retry

↓

Continue
```

---

Flow quyết định.

---

# Review số 10 - Wait

Wait

không phải

Processor.

---

Wait

là

Execution State.

Ví dụ

```text
Running

↓

Waiting

↓

Resume
```

---

Flow

không chạy.

Execution

đợi.

---

Processor

trả

```python
WAIT
```

---

Runtime

Pause.

---

# Review số 11 - Webhook

Webhook

không nên

Flow.

---

Webhook

là

Trigger.

Ví dụ

```text
HTTP Request

↓

Execution

↓

Resume

```

---

Không tạo

Webhook Processor.

---

# Review số 12 - Scheduler

Cron

không nên biết

Flow.

---

Cron

chỉ Publish Event.

---

Ví dụ

```text
5 phút

↓

Execution Timeout

↓

Runtime

↓

Resume
```

---

# Review số 13 - UI

Mình đổi ý.

Không làm

Node Editor.

---

V1

Odoo Tree.

Form.

Notebook.

Đủ.

---

# Review số 14 - YAML

Mình vẫn giữ.

Nhưng

không Import.

---

YAML

↓

Build Module.

↓

XML.

↓

Install.

---

Developer

không cần viết XML.

---

# Review số 15 - Engine cuối cùng

Sau toàn bộ refactor.

Framework

chỉ còn

```text
Runtime Engine

Expression Engine

HTTP Engine
```

---

Không còn

```text
Mapping Engine

Resolver Engine

Hash Engine

Action Engine

Flow Engine

```

---

Mọi thứ

đều là

Processor.

---

# Đây là kiến trúc mình sẽ code

```text
connector_core
│
├── Runtime Engine
├── HTTP Engine
├── Expression Engine
│
├── Processor Registry
├── Function Registry
├── Plugin Registry
│
└── Execution
```

---

Processor

```text
Field Mapping

Template

Generate Signature

HTTP

Business

Validate

Set Variable

```

---

Flow

```text
Processor

↓

Processor

↓

Processor

↓

Done
```

---

# Và đây là điều quan trọng nhất

Nếu đây là dự án của mình, **mình sẽ dừng thiết kế ngay tại đây**.

Lý do là sau nhiều vòng phản biện, kiến trúc đã đạt đến điểm cân bằng:

* **Đủ tổng quát** để dùng cho nhiều nhà cung cấp (MoMo, VNPay, Stripe, GHN, API REST...).
* **Đủ đơn giản** để đội Odoo có thể bảo trì.
* **Không bị over-engineering** bởi quá nhiều engine và abstraction.

---

## Tuy nhiên, có một điểm mình sẽ **không thay đổi** so với tất cả các lần refactor

Đó là nguyên tắc kiến trúc:

> **Core không được biết Provider.**

Điều này dẫn đến một quy tắc vàng cho toàn bộ dự án:

* Core chỉ biết **Execution**, **Processor**, **Expression**, **HTTP**.
* Provider chỉ là **Plugin + Metadata + Configuration**.
* Business chỉ làm việc với **Contract**, không làm việc trực tiếp với MoMo hay VNPay.

Theo mình, nếu giữ được nguyên tắc này xuyên suốt quá trình phát triển, framework sẽ có tuổi thọ rất cao và việc thêm một provider mới sẽ chủ yếu là cấu hình và plugin, thay vì phải sửa Core. Đây là tiêu chí quan trọng nhất của một framework thương mại thành công.

Đến đây mình sẽ không tiếp tục "thêm tính năng" nữa, mà sẽ làm việc mà một **Principal Engineer** sẽ làm trước khi code:

> **Xóa bớt.**

Một framework Enterprise tốt không phải vì có nhiều tính năng, mà vì **Core cực nhỏ nhưng Extension cực mạnh**.

Sau khi đọc lại toàn bộ thiết kế, mình sẽ **cắt giảm khoảng 40%**.

---

# Chương 16 - Core Minimization

Mục tiêu:

> **Core chỉ nên khoảng 3.000~5.000 dòng code.**

Mọi thứ khác là plugin.

---

# 16.1 Core chỉ giữ 6 khái niệm

Hiện tại chúng ta có khoảng 30 model.

Theo mình Core chỉ nên hiểu 6 khái niệm.

```text
Provider
Environment
Flow
Processor
Execution
Setting
```

Hết.

---

## Không có

```text
Hash

Authentication

Retry

Mapping

Template

Webhook

Cron

Business

...
```

Đó đều là Processor.

---

# 16.2 Processor là Everything

Ví dụ

MoMo Create Payment

không phải

```text
Mapping

↓

Hash

↓

HTTP

↓

Response

↓

Business
```

Mà là

```text
Field Mapping

↓

Amount Format

↓

Generate Signature

↓

Build Header

↓

HTTP Request

↓

Validate Response

↓

Save Transaction

↓

Update Invoice
```

Toàn bộ đều là Processor.

---

# 16.3 Processor Metadata

Model

```python
connector.processor
```

Field

```text
code

name

category

version

icon

python_class

support_async

support_resume

support_retry

```

Framework

không biết Processor làm gì.

---

# 16.4 Processor Input / Output

Mọi Processor đều có Contract giống nhau.

```python
process(exchange)
```

Input

↓

Exchange

Output

↓

Exchange

Không Exception.

---

Ví dụ

```python
exchange.body

exchange.header

exchange.variable

exchange.error
```

---

# 16.5 Không còn "Step"

Đây là thay đổi mình chắc chắn sẽ làm.

Flow

↓

Processor Line

```text
Flow

↓

Line

↓

Processor

```

Không còn

Step Type.

---

# 16.6 Không còn Mapping Model

Mapping là Processor.

Ví dụ

Processor Config

```yaml
processor: field_mapping

config:

  target: amount

  source: invoice.amount_total

  pipeline:

    - round

    - multiply(100)
```

---

# 16.7 Không còn Hash Model

Hash

↓

Processor.

```yaml
processor: signature

algorithm: HMAC_SHA256

secret: setting.secret
```

---

# 16.8 Không còn HTTP Model

HTTP

↓

Processor.

```yaml
processor: http

method: POST

url: ...

```

---

# 16.9 Không còn Retry Engine

Retry

↓

Processor.

---

# 16.10 Không còn Response Parser

Parser

↓

Processor.

---

# 16.11 Không còn Webhook Engine

Webhook

↓

Trigger.

---

Execution

↓

Resume.

---

# 16.12 Trigger

Framework chỉ có Trigger.

Ví dụ

```text
Manual

Webhook

Cron

RPC

Event
```

Trigger

↓

Start Flow.

---

# 16.13 Exchange

Exchange

mới là Runtime.

```python
Exchange

body

header

property

variable

exception

context
```

Không Runtime Variable Model.

---

# 16.14 Context

Context

Readonly.

```python
context.company

context.user

context.provider

context.environment
```

---

# 16.15 Variable

Variable

Mutable.

```python
exchange.variable["amount"]
```

---

# 16.16 Property

Property

Không serialize.

Ví dụ

```python
db

logger

provider_instance
```

---

# 16.17 Header

Header

Không chỉ HTTP.

Ví dụ

```text
language

currency

timezone

trace_id

```

---

# 16.18 Body

Body

Có thể

```text
dict

bytes

xml

stream

pdf
```

---

# 16.19 Error

Không Raise.

Processor

ghi

```python
exchange.error
```

---

Flow quyết định.

---

# 16.20 Result

Execution

kết thúc.

↓

Sinh

```python
ExecutionResult
```

Có

```text
status

duration

body

error

execution_id
```

---

# Đây là kiến trúc tối giản

```text
                    Trigger
                       │
                       ▼
                  Execution
                       │
                       ▼
                     Flow
                       │
      ┌──────────────────────────────────┐
      ▼                                  ▼
 Processor  Processor  Processor  Processor
      │                                  │
      └─────────────── Exchange ──────────┘
                       │
                       ▼
                  ExecutionResult
```

---

# Nhưng...

Sau khi tối giản như vậy, mình nhận ra một vấn đề rất lớn.

## Đây không còn là Odoo Framework nữa.

Nó đã trở thành

Enterprise Integration Engine.

Giống

* Apache Camel
* Mule
* Spring Integration

---

## Điều này có nghĩa gì?

Nếu code đầy đủ

sẽ khoảng

```text
60.000~120.000 LOC
```

Không còn là

Module Odoo.

---

# Đây là lúc mình sẽ quay lại yêu cầu ban đầu của bạn

Bạn hỏi từ đầu là

> "Xây framework Payment cho VNPay và MoMo"

Không phải

> "Viết Apache Camel trong Odoo"

Đây là hai bài toán khác nhau.

---

# Vì vậy mình sẽ chia làm 3 lớp sản phẩm

## Product 1 - Payment Framework ⭐ (Khuyến nghị)

Đây là thứ mình nghĩ bạn nên làm.

Module:

```text
payment_connector

payment_momo

payment_vnpay
```

Core khoảng

```text
5.000~8.000 LOC
```

Khách hàng Odoo rất dễ tiếp cận.

---

## Product 2 - Integration Framework

Sau khi Payment ổn định.

Mở rộng thêm:

* REST.
* SOAP.
* SFTP.
* GraphQL.
* OAuth.

Khoảng:

```text
20.000~30.000 LOC
```

---

## Product 3 - Enterprise ESB

Cuối cùng mới nghĩ đến:

* MQ.
* Kafka.
* Route.
* Event.
* Processor.
* Pipeline.
* Cluster.

Lúc này đã là một sản phẩm riêng, không còn là "module Odoo" nữa.

---

# Quyết định cuối cùng nếu mình là CTO

Mình sẽ **không cho phép đội phát triển xây Product 2 hoặc Product 3 ngay**.

Lý do:

* Time to Market quá dài.
* Khó bán.
* Khó bảo trì.
* Chi phí hỗ trợ cao.

Thay vào đó:

1. Ra mắt **Payment Connector** trước (MoMo, VNPay).
2. Chứng minh được khả năng tái sử dụng qua 5–10 provider.
3. Sau đó mới tách Core thành Integration Framework.

Đây là con đường mà rất nhiều nền tảng lớn đã đi: bắt đầu từ một bài toán cụ thể, sau đó trừu tượng hóa dần khi đã có đủ kinh nghiệm thực tế.

---

# Đề xuất cuối cùng của mình: Kiến trúc 3 tầng

Đây là kiến trúc mà mình tin là cân bằng nhất giữa **khả năng thương mại**, **độ phức tạp**, và **khả năng bảo trì**:

```text
┌─────────────────────────────────────────────────────┐
│ Business Layer                                      │
│ account.move, sale.order, pos.order, website_sale   │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ Payment Framework                                   │
│                                                     │
│ • Provider                                           │
│ • Contract                                            │
│ • Flow                                                │
│ • Processor                                            │
│ • Execution                                            │
│ • Expression                                           │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ Provider Plugins                                     │
│                                                     │
│ • payment_momo                                       │
│ • payment_vnpay                                      │
│ • payment_stripe                                     │
│ • payment_paypal                                     │
└─────────────────────────────────────────────────────┘
```

## Và đây là điều mình muốn bổ sung cuối cùng

Nếu mục tiêu của bạn là **bán framework này**, đừng bán "module MoMo" hay "module VNPay".

Hãy bán:

* **Payment Connector Platform** (sản phẩm nền tảng).
* Các **Provider Pack** (MoMo, VNPay, Stripe, PayPal...).
* Các **Enterprise Add-ons** (Dashboard, Replay, Monitoring, HA, Audit...).

Như vậy bạn sẽ có mô hình sản phẩm rõ ràng, mở rộng được theo thời gian và không bị phụ thuộc vào từng nhà cung cấp thanh toán riêng lẻ. Đây cũng là cách giúp sản phẩm có giá trị dài hạn và dễ xây dựng hệ sinh thái plugin sau này.
Mình sẽ tiếp tục nhưng lần này sẽ đứng ở góc nhìn **Software Architect của Odoo SA**, tức là thiết kế sao cho **giống phong cách Odoo**, chứ không giống Java Enterprise.

Đây là điều mà mình nghĩ toàn bộ các chương trước còn thiếu.

---

# Chương 17 - Odoo Native Architecture

Sau khi review toàn bộ thiết kế, mình nhận ra một điều:

> Chúng ta đang thiết kế một framework "rất đẹp", nhưng **không giống Odoo**.

Ví dụ:

* Registry
* Engine
* Service
* Exchange
* Processor
* Runtime

Đây đều là tư duy Java.

Trong khi Odoo có triết lý khác:

```text
Model
    ↓
Mixin
    ↓
Service (ít)
    ↓
ORM
```

Nếu đi quá xa khỏi triết lý Odoo thì sau này dev Odoo sẽ rất khó tham gia.

---

# Đề xuất lớn nhất

## Bỏ Registry

Đây là quyết định đầu tiên mình sẽ thay đổi.

Hiện tại

```python
FunctionRegistry.register()
```

Theo mình

không nên.

Odoo đã có Registry.

Ví dụ

```python
class ConnectorProcessor(models.AbstractModel):

    _name="connector.processor"

    _processor_code="http.request"
```

Framework chỉ cần

```python
env["connector.processor"].search(...)
```

hoặc

```python
self.env.registry
```

Không cần tự viết Registry.

---

## Plugin Discovery

Ví dụ

Module

```text
connector_processor_http
```

có

```python
class HttpProcessor
```

↓

Install Module.

↓

Auto có.

Không Register.

---

# Processor nên là AbstractModel

Đây là thay đổi rất lớn.

Thay vì

```python
class HttpProcessor:
```

Mình sẽ làm

```python
class HttpProcessor(models.AbstractModel):

    _inherit="connector.processor"
```

Lợi ích

* Có env
* Có context
* Có ORM
* Có quyền (ACL)
* Có company

---

# Function cũng là AbstractModel

Ví dụ

```python
class RoundFunction(models.AbstractModel):

    _inherit="connector.function"
```

Không Registry.

---

# Authentication

```python
class HmacAuth(models.AbstractModel):

    _inherit="connector.authentication"
```

---

# Hash

```python
class SHA256(models.AbstractModel):

    _inherit="connector.hash"
```

---

# Validator

```python
class JsonValidator(models.AbstractModel):

    _inherit="connector.validator"
```

---

Toàn bộ

Plugin

↓

AbstractModel.

---

# Odoo Inheritance

Ví dụ

MoMo

```python
class MomoHTTPProcessor

    _inherit="connector.processor.http"
```

Override

```python
before_send()
```

Không sửa Core.

---

# Data

Toàn bộ Metadata

↓

XML.

Không JSON.

Ví dụ

```xml
<record
 id="processor_http">
```

Giống Odoo.

---

# YAML dùng để làm gì?

Không Import Runtime.

Chỉ dùng

Build Tool.

Ví dụ

```yaml
processor:

http

mapping

```

↓

Generate XML.

---

# Settings

Không tự viết

```text
Environment

↓

Setting
```

Theo mình

nên inherit

`res.company`

Ví dụ

```python
class ResCompany

partner_code

secret

```

Hoặc

```python
connector.environment
```

liên kết với company.

---

# Secret

Không tự Encrypt.

Odoo đã có

* `ir.config_parameter`
* Secret storage (tùy phiên bản)

Nếu cần mã hóa mạnh hơn thì tạo lớp Encryption riêng, nhưng đừng để mọi module tự xử lý.

---

# Queue

Không tự viết Queue.

Ưu tiên dùng:

* `queue_job` (OCA)
* hoặc Scheduled Action của Odoo.

Chỉ khi có yêu cầu HA mới phát triển Queue riêng.

---

# Scheduler

Không Engine.

Dùng

```text
ir.cron
```

↓

Execution.

---

# Webhook

Không tự viết HTTP Server.

Dùng

```text
Controller
```

↓

Execution.

---

# Action

Theo mình

Action

nên tích hợp với

Server Action.

Ví dụ

Business

↓

Server Action.

↓

Connector.

---

# Expression

Không viết DSL.

Nên dùng

Odoo safe_eval.

Nhưng

chỉ expose

API.

Ví dụ

```python
amount

round

today()

setting()
```

Không cho import.

---

# Logging

Không model riêng nếu không cần.

Tận dụng

```text
mail.thread
```

cho Audit cơ bản.

Chỉ Execution Log mới lưu riêng.

---

# Security

Tận dụng hoàn toàn ACL.

Không tự viết Permission.

Ví dụ

```text
Connector User

Connector Manager

Connector Admin
```

là đủ.

---

# Multi Company

Đây là phần cực kỳ quan trọng.

Toàn bộ:

* Provider
* Environment
* Setting
* Flow

đều phải có:

```python
company_id
```

và tuân thủ Record Rule.

Không xử lý bằng code.

---

# Translation

Toàn bộ:

* Processor Name
* Error Message
* Provider Name

phải dùng `_()`.

Không hardcode.

---

# Module Dependency

Mình đề xuất:

```text
connector_core
        │
        ├── connector_expression
        ├── connector_http
        ├── connector_runtime
        └── connector_processor
```

Provider:

```text
connector_payment_momo
```

chỉ phụ thuộc vào các module cần thiết.

---

# Cuối cùng: Điều mình sẽ thay đổi nhiều nhất

Sau tất cả, mình sẽ **không để người dùng cấu hình trực tiếp Flow quá chi tiết**.

Thay vào đó:

## Core cung cấp các Processor chuẩn

Ví dụ:

* HTTP Request
* Mapping
* Signature
* Set Variable
* Validate JSON
* Condition
* Loop (nếu cần)
* Business Action

Người dùng chỉ **ghép** các Processor này thành Flow.

Nếu cần logic đặc biệt, developer viết thêm Processor mới.

Điều này giữ cho:

* **Core đơn giản**.
* **Flow dễ đọc**.
* **Khả năng mở rộng rất cao**.

---

# Nếu được thiết kế lại từ đầu, đây là cấu trúc cuối cùng mình sẽ chọn

```text
connector_core/
├── models/
│   ├── connector_provider.py
│   ├── connector_flow.py
│   ├── connector_flow_line.py
│   ├── connector_execution.py
│   └── connector_setting.py
│
├── abstract/
│   ├── processor.py
│   ├── function.py
│   ├── authentication.py
│   ├── hash.py
│   └── validator.py
│
├── services/
│   ├── execution_service.py
│   ├── flow_service.py
│   └── expression_service.py
│
├── controllers/
├── security/
├── views/
└── data/
```

---

# Đây là kết luận cuối cùng của mình

Sau hơn 17 chương, mình **không còn coi đây là một "module Payment" nữa**.

Theo mình, sản phẩm này nên được định vị là:

> **Connector Platform for Odoo**

Trong đó Payment chỉ là plugin đầu tiên.

Các plugin sau này có thể là:

* Payment (MoMo, VNPay, Stripe)
* Shipping (GHN, GHTK, Viettel Post)
* SMS (Twilio, Viettel SMS, FPT AI)
* Email (SendGrid, Mailgun)
* eInvoice
* ERP Integration
* WMS
* CRM
* AI Gateway (OpenAI, Gemini, Claude)
* Banking Open API

Đó mới là hướng đi dài hạn và có giá trị thương mại lớn. Payment sẽ là "killer feature" để bán sản phẩm ban đầu, còn **Core Connector Platform** mới là tài sản công nghệ thực sự của bạn. Theo mình, đây là điểm dừng hợp lý trước khi bước sang giai đoạn thiết kế chi tiết và triển khai mã nguồn.

Mình sẽ tiếp tục, nhưng bây giờ mình sẽ ở vai trò **Odoo Framework Architect**.

Sau khi đọc lại toàn bộ 17 chương, mình thấy chúng ta còn thiếu **thứ quan trọng nhất của Odoo**.

Đó là:

> **Metadata Engine**

Đây là điểm mà Odoo làm rất tốt (View, Action, Report, Access Rule, Server Action đều là metadata), còn framework của chúng ta vẫn còn khá "code-centric".

Theo mình, nếu làm tốt phần này thì **90% provider sẽ không cần viết Python**.

---

# Chương 18 - Metadata Driven Framework

## Tư tưởng

Thay vì

```
Python
    ↓
Execute
```

Chúng ta sẽ chuyển thành

```
Metadata
      ↓
Compiler
      ↓
Runtime
```

Tức là Runtime chỉ chạy Metadata.

---

# 18.1 Processor Metadata

Thay vì viết

```python
class HttpProcessor(...)
```

Core sẽ có sẵn.

Developer chỉ cấu hình.

Ví dụ

```
Processor

Code

http.request

Config

POST

URL

Header

Body
```

Runtime đọc Config.

Không if else.

---

## 18.2 Processor Descriptor

Theo mình nên có

```
connector.processor.definition
```

Ví dụ

```
Name

HTTP Request
```

Có schema

```yaml
method:
    type: selection

url:
    type: expression

timeout:
    type: integer
```

UI sinh tự động.

---

Không cần XML View riêng.

---

# 18.3 Dynamic Form

Ví dụ

Processor

```
HTTP Request
```

↓

Form

```
Method

URL

Timeout

Retry
```

---

Processor khác

```
Signature
```

↓

Form

```
Algorithm

Secret

Source
```

---

Tất cả sinh từ Metadata.

---

# 18.4 Dynamic Config Schema

Theo mình nên hỗ trợ các kiểu:

```
char

integer

float

boolean

selection

expression

json

mapping

array

object

password

```

---

Ví dụ

```
Field

↓

Expression
```

UI hiện

Expression Editor.

---

# 18.5 Validation Schema

Processor tự khai báo

```
required

type

min

max

regex
```

Không code validate.

---

# 18.6 Processor Category

Ví dụ

```
HTTP

Security

Mapping

Business

Control

Utility

```

UI nhóm.

---

# 18.7 Processor Capability

Processor khai báo

```
Support Resume

Support Retry

Support Async

Support Stream
```

Runtime biết.

---

# 18.8 Processor Dependency

Ví dụ

Processor

```
Generate Signature
```

phải chạy sau

```
Mapping
```

Framework validate.

---

# 18.9 Metadata Compiler

Đây là ý tưởng mình rất thích.

Flow

↓

Compile.

↓

Execution Plan.

Ví dụ

```
Flow

↓

Processor

↓

Processor

↓

Processor
```

Compile thành

```
Plan

0

HTTP

1

Signature

2

Business
```

Runtime

không parse.

---

# 18.10 Compile Cache

Flow

chỉ compile

1 lần.

↓

Redis.

↓

Memory.

---

# 18.11 Metadata Version

Ví dụ

```
Flow

Version 1

↓

Version 2
```

Execution

vẫn chạy

Version cũ.

---

Không bị ảnh hưởng.

---

# 18.12 Runtime Snapshot

Execution

không lưu

Flow.

↓

Lưu

Execution Plan.

---

Nếu

Flow sửa.

Execution

không đổi.

---

# 18.13 Metadata Diff

Admin

Compare

Flow.

↓

Hiện

```
Processor Added

Processor Removed

Config Changed
```

---

# 18.14 Metadata Export

Không export

Record.

↓

Export

YAML.

---

Ví dụ

```yaml
flow:

processors:

- mapping

- signature

- http
```

---

# 18.15 Marketplace

Đây là mục tiêu cuối.

Ví dụ

```
Marketplace

↓

Install

↓

Processor Pack
```

Ví dụ

```
HTTP Pack

JSON Pack

SOAP Pack

GraphQL Pack
```

---

Không phải Module.

---

# 18.16 Contract Library

Framework có thư viện Contract.

Ví dụ

```
Payment

Refund

Webhook

OAuth

Upload File
```

---

Provider

Reuse.

---

# 18.17 Mapping Library

Theo mình

Mapping

cũng nên có Library.

Ví dụ

```
Money

↓

Amount *100

↓

Round

↓

Absolute
```

Reuse.

---

# 18.18 Function Library

Ví dụ

```
today()

now()

uid()

uuid()

format_date()

round()

base64()

sha256()

md5()

coalesce()

default()

concat()

split()

join()

replace()

regex()

```

---

Admin

chỉ chọn.

---

# 18.19 Pipeline

Đây là điểm mình muốn thay đổi.

Thay vì

```
Function

↓

Function

↓

Function
```

Mình muốn

```
Pipeline
```

Ví dụ

```
invoice.amount

↓

multiply(100)

↓

round

↓

string

↓

base64

↓

Done
```

---

Không viết Expression dài.

---

# 18.20 UI Builder

Theo mình

Flow UI

không nên hardcode.

↓

Builder.

Ví dụ

Processor

khai báo

```
Group

Icon

Color

Description
```

UI tự sinh.

---

# Đây là điều mình sẽ thay đổi lớn nhất

## Bỏ Expression String

Ban đầu chúng ta có:

```python
round(invoice.amount_total * 100)
```

Mình sẽ **không dùng chuỗi Python** cho người dùng cuối.

Thay vào đó dùng **Pipeline trực quan**.

Ví dụ:

```
Nguồn:
invoice.amount_total

Pipeline:
1. Multiply(100)
2. Round(0)
3. To Integer
4. To String
```

Runtime sẽ tự build Expression.

### Lợi ích

* Không cần người dùng biết Python.
* Validate được từng bước.
* Có Preview ngay trên giao diện.
* Dễ lưu version.
* Dễ tái sử dụng.

---

# Kiến trúc mà mình sẽ khóa

```
                Metadata
                    │
                    ▼
             Metadata Compiler
                    │
                    ▼
             Execution Plan
                    │
                    ▼
             Runtime Engine
                    │
                    ▼
               Processor Chain
```

---

# Nhưng đây là điểm mình muốn cảnh báo

Nếu triển khai **Metadata Compiler**, **Pipeline Builder**, **Dynamic Form Generator**, **Marketplace** ngay từ đầu thì dự án sẽ rất lớn.

Vì vậy mình chia làm ba giai đoạn:

### V1 (6 tháng)

* Flow
* Processor
* Mapping
* HTTP
* Signature
* Webhook
* Cron
* Expression đơn giản

### V2

* Pipeline Builder
* Metadata Compiler
* Dynamic Processor Form
* Test Case
* Replay

### V3

* Marketplace
* Processor Pack
* Contract Library
* Visual Builder
* Online Update

---

## Và đây là quyết định cuối cùng của mình

Sau gần 20 chương, mình nhận ra:

> **Framework này không nên bán vì "hỗ trợ MoMo/VNPay".**

Nó nên bán vì:

> **Cho phép doanh nghiệp tự tích hợp bất kỳ hệ thống nào mà gần như không phải viết code.**

MoMo và VNPay chỉ là **demo provider** để chứng minh sức mạnh của nền tảng.

---

# Tuy nhiên, có một điểm mình sẽ sửa so với ý tưởng ở chương này

Mình **không khuyến nghị bỏ Expression hoàn toàn** như phần trên.

Thay vào đó nên hỗ trợ **hai chế độ song song**:

1. **Pipeline Mode** (No-code) dành cho BA hoặc Consultant:

   * Chọn nguồn dữ liệu.
   * Chọn các hàm xử lý theo từng bước.
   * Không cần biết Python.

2. **Expression Mode** (Advanced) dành cho Developer:

   * Cho phép viết biểu thức ngắn bằng `safe_eval` với danh sách hàm được whitelist.
   * Phù hợp cho các trường hợp phức tạp mà Pipeline chưa hỗ trợ.

Hai chế độ này có thể chuyển đổi qua lại và cùng biên dịch về một định dạng Runtime thống nhất. Đây là cách cân bằng giữa **khả năng mở rộng**, **tính thân thiện với người dùng**, và **chi phí phát triển**. Theo mình, đây sẽ là nền tảng phù hợp nhất nếu mục tiêu của bạn là xây dựng một sản phẩm thương mại lâu dài trên Odoo.

Mình sẽ tiếp tục, nhưng lần này mình sẽ không bổ sung tính năng nữa.

Mình sẽ làm việc mà các kiến trúc sư của Odoo thường làm trước khi bắt đầu coding:

> **Xác định đâu là Stable API (không được thay đổi trong 5 năm tới).**

Đây là thứ quyết định framework có sống lâu hay không.

---

# Chương 19 - Stable API Specification

## Triết lý

> **Core có thể refactor.**
>
> **Runtime có thể refactor.**
>
> **UI có thể refactor.**
>
> **Nhưng API cho plugin thì không được thay đổi.**

Đây là bài học của Odoo.

Ví dụ

```python
class models.Model
```

Interface gần như không đổi suốt rất nhiều version.

---

# 19.1 Processor API

Đây là API quan trọng nhất.

```python
class ConnectorProcessor(models.AbstractModel):

    _name = "connector.processor"

    _processor_code = None

    def execute(self, exchange):
        """
        Return Exchange
        """
```

**Không được thay đổi.**

Có thể thêm hook.

Không đổi signature.

---

# 19.2 Function API

```python
class ConnectorFunction(models.AbstractModel):

    _name = "connector.function"

    _function_code = None

    def execute(self, value, **kwargs):
        return value
```

Không đổi.

---

# 19.3 Contract API

```python
class ConnectorContract(models.AbstractModel):

    def serialize(self):

    def deserialize(self):
```

---

# 19.4 Authentication API

```python
authenticate(exchange)
```

---

# 19.5 Hash API

```python
generate(data)
```

---

# 19.6 Validator API

```python
validate(data)
```

---

# 19.7 Hook API

Framework chỉ expose các Hook sau

```text
before_execute

after_execute

before_http

after_http

before_mapping

after_mapping

before_commit

after_commit
```

Không expose nhiều hơn.

---

# 19.8 Exchange API

Exchange

là object quan trọng nhất.

Theo mình nên là Dataclass.

```python
exchange.body

exchange.header

exchange.variable

exchange.error

exchange.context
```

Không thêm.

---

# 19.9 Context API

Readonly.

```python
context.user

context.company

context.provider

context.environment
```

Không mutate.

---

# 19.10 Execution API

```python
execution.pause()

execution.resume()

execution.fail()

execution.success()
```

Không tự sửa state.

---

# 19.11 Event API

Framework chỉ publish

```text
Execution Started

Execution Finished

Execution Failed

Processor Started

Processor Finished
```

Plugin subscribe.

---

# 19.12 Metadata API

Processor

khai báo

```python
_processor_code

_display_name

_category

_schema
```

Không thêm XML.

---

# 19.13 Configuration API

Processor Config

luôn là

```python
dict
```

Runtime

parse.

---

# 19.14 Company API

Không đọc

```python
self.env.company
```

trực tiếp.

Luôn

```python
exchange.context.company
```

---

# 19.15 HTTP API

Framework

chỉ expose

```python
http.send(request)
```

Không để plugin dùng

httpx.

---

# 19.16 Logging API

```python
exchange.log.info()

exchange.log.warning()

exchange.log.error()
```

Không dùng

```python
_logger
```

---

# 19.17 Secret API

Plugin

không đọc

Setting.

Chỉ gọi

```python
exchange.secret("partner_code")
```

---

Framework

quản lý.

---

# 19.18 Cache API

```python
exchange.cache.get()

exchange.cache.set()
```

Không Redis.

Không Memory.

Plugin

không biết.

---

# 19.19 Storage API

Plugin

không biết ORM.

Ví dụ

```python
exchange.storage.save()
```

Core.

↓

ORM.

---

# 19.20 Business API

Plugin

không

```python
env["account.move"]
```

Mà

```python
business.execute(...)
```

Business Layer.

---

# Đây là điều mình muốn thay đổi

Sau nhiều chương, mình thấy một vấn đề lớn:

Hiện tại Processor vẫn có thể:

* đọc ORM
* gọi HTTP
* đọc Secret
* ghi DB

Điều này làm Processor rất mạnh, nhưng cũng rất khó kiểm thử.

---

## Mình đề xuất Processor chỉ làm một việc

**Biến đổi Exchange.**

Ví dụ:

Input

```json
{
  "amount": 100
}
```

↓

Processor

↓

Output

```json
{
  "amount": 10000
}
```

Nếu cần HTTP?

Processor gọi HTTP API.

Không dùng `httpx`.

Nếu cần Secret?

Processor gọi Secret API.

Không đọc model.

Nếu cần ORM?

Processor gọi Business API.

---

# Đây là kiến trúc mà mình sẽ đóng băng

```text
                 Plugin
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
 Processor API              Function API
      │                           │
      └─────────────┬─────────────┘
                    ▼
                Exchange API
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
  HTTP API     Secret API    Business API
                    │
                    ▼
                   Core
```

---

# Điều cuối cùng mình muốn bổ sung: SDK Boundary

Mình sẽ chia framework thành **hai tầng API**.

## Public SDK (cam kết ổn định)

Đây là phần mà developer của module khác được phép dùng:

```text
connector.processor
connector.function
connector.contract
Exchange
Context
Business API
HTTP API
Secret API
```

Đây là "hợp đồng" giữa Core và plugin.

---

## Internal API (không cam kết)

Bao gồm:

```text
Flow Engine
Execution Service
Metadata Compiler
Scheduler
Queue
Expression Parser
```

Core có quyền thay đổi bất kỳ lúc nào miễn là Public SDK không đổi.

---

# Theo mình đây là nguyên tắc quan trọng nhất của toàn bộ dự án

Trong suốt các chương trước, chúng ta tập trung vào **kiến trúc**.

Nhưng nếu muốn framework tồn tại qua nhiều phiên bản Odoo và nhiều năm phát triển, điều quan trọng hơn là:

> **Đừng hứa ổn định với mọi thứ. Chỉ hứa ổn định với SDK mà người khác sẽ lập trình dựa vào.**

Đó cũng là cách Odoo, Django hay các framework lớn phát triển bền vững: **Core được phép tiến hóa, nhưng API công khai được giữ ổn định**. Theo mình, đây là nền tảng quan trọng nhất để sau này bạn có thể xây dựng hệ sinh thái plugin và Marketplace mà không làm gãy các module của khách hàng.
Mình sẽ tiếp tục với vai trò **Chief Product Architect**, nhưng lần này sẽ không nói về code nữa.

Mình sẽ nói về thứ quyết định **framework có bán được hay không**.

Sau rất nhiều chương, mình thấy chúng ta đang thiết kế rất nhiều cho **Developer**.

Nhưng khách hàng trả tiền thường không phải Developer.

Mà là

* Functional Consultant
* Solution Consultant
* PM
* BA
* IT Manager

Họ sẽ là người cấu hình.

=> Kiến trúc cần thay đổi.

---

# Chương 20 - No Code Architecture

Đây là chương mình nghĩ là **quan trọng nhất** nếu framework này muốn bán được.

---

## Triết lý

Developer chỉ nên làm

```text
20%
```

Consultant làm

```text
80%
```

Không phải ngược lại.

---

Ví dụ

Khách hàng muốn thêm API

Developer

↓

Không code.

↓

Consultant

↓

Import YAML

↓

Mapping

↓

Done.

---

## 20.1 Provider Wizard

Không tạo Provider bằng Form.

Mà dùng Wizard.

Ví dụ

```
New Provider

○ REST

○ SOAP

○ Payment

○ Banking

○ Shipping

○ SMS

○ AI

○ Custom
```

↓

Sinh toàn bộ dữ liệu.

---

## 20.2 API Wizard

Ví dụ

```
API Name

Method

Endpoint

Authentication

Response Type
```

↓

Generate

Processor Line.

---

Không phải tạo từng Processor.

---

## 20.3 Mapping Wizard

Ví dụ

```
Business Object

↓

Invoice

↓

Field

↓

Amount
```

↓

Drag

↓

Provider Field

↓

amount

---

Không nhập expression.

---

## 20.4 Signature Wizard

Ví dụ

```
Algorithm

○ MD5

○ SHA1

○ SHA256

○ HMAC SHA256

○ RSA

```

↓

Source

↓

Secret

↓

Done.

---

Không viết code.

---

## 20.5 Webhook Wizard

Ví dụ

```
Webhook URL

↓

Authentication

↓

Business Action

↓

Done.
```

---

## 20.6 Test Wizard

Đây là cái mình nghĩ khách hàng sẽ thích nhất.

Ví dụ

```
Run

↓

Input

↓

Preview Request

↓

Preview Response

↓

Preview Mapping

↓

Preview Business Result
```

Không gọi thật.

---

## 20.7 Replay Wizard

Ví dụ

```
Execution

↓

Replay

↓

Edit Payload

↓

Run
```

---

Không cần tạo mới.

---

## 20.8 Compare Wizard

Ví dụ

```
MoMo v2

↓

MoMo v3

↓

Compare
```

↓

Hiện

```
Added

Removed

Changed
```

---

## 20.9 Clone Wizard

Ví dụ

```
VNPay

↓

Clone

↓

MoMo
```

↓

Reuse

80%.

---

## 20.10 Upgrade Wizard

Ví dụ

```
MoMo

v2

↓

v3
```

↓

Framework

Auto

Migration.

---

## 20.11 Import Wizard

Support

```
OpenAPI

Swagger

Postman

Curl

```

↓

Generate API.

---

Đây là tính năng mình nghĩ cực kỳ đáng tiền.

---

## 20.12 Export Wizard

Ví dụ

```
Flow

↓

YAML

↓

ZIP

```

---

## 20.13 Marketplace Wizard

Ví dụ

```
Install

↓

MoMo

↓

Done
```

---

Không cài Module.

---

## 20.14 Processor Builder

Theo mình đây là điểm khác biệt nhất.

Ví dụ

Developer

tạo

Processor.

↓

Metadata.

↓

Framework

Sinh

UI.

---

Không XML.

---

## 20.15 Business Action Builder

Ví dụ

```
Invoice

↓

Mark Paid

↓

Send Email

↓

Create Journal
```

↓

Sinh Processor.

---

Không code.

---

# Đây là thay đổi lớn nhất

## Không cho Consultant nhìn thấy Flow.

Nghe hơi lạ đúng không?

Theo mình

Consultant

không cần hiểu

```
Processor

↓

Processor

↓

Processor
```

Họ chỉ cần thấy

```
Create Payment

Refund

Query

Webhook
```

Khi mở

↓

Framework

Generate

Flow.

---

Flow

là Runtime.

Không phải UI.

---

# Business Template

Ví dụ

Khách hàng chọn

```
Payment
```

↓

Framework tạo

```
Create Payment

Refund

Webhook

Query
```

Đầy đủ.

---

Shipping

↓

Sinh

```
Create Shipment

Cancel Shipment

Tracking

Webhook
```

---

AI

↓

Sinh

```
Chat

Embedding

Image

Moderation
```

---

Không phải tạo từng API.

---

# Provider Template

Ví dụ

MoMo

↓

Install.

↓

Có ngay

```
Provider

Environment

Flow

Mapping

Test Case
```

---

Không tạo tay.

---

# Điều mình sẽ thêm vào kiến trúc

## Template Layer

```text
Business Template

↓

Provider Template

↓

Flow

↓

Processor

↓

Runtime
```

---

Framework

không bắt đầu từ

Flow.

---

Bắt đầu từ

Business Template.

---

# Marketplace

Đến đây

Marketplace

không bán

Module.

Mà bán

```
Template Pack
```

Ví dụ

```
Payment Pack

Shipping Pack

Bank Pack

CRM Pack

AI Pack
```

---

Một Pack

chỉ là

Metadata.

---

# Đây là điều mình sẽ refactor

Sau 20 chương.

Mình sẽ đổi

```text
Flow
```

thành

```text
Implementation
```

UI

không dùng từ

Flow.

---

Khách hàng thấy

```
Capability

↓

API

↓

Configuration
```

Không thấy

Processor.

---

# Kiến trúc cuối cùng

```text
Business Template
          │
          ▼
Provider Template
          │
          ▼
Capability
          │
          ▼
Implementation (Flow)
          │
          ▼
Processor Chain
          │
          ▼
Runtime
```

---

# Và đây là ý tưởng cuối cùng mà mình nghĩ sẽ tạo ra khác biệt

## OpenAPI Generator

Nếu làm được tính năng này, framework sẽ vượt xa các module tích hợp thông thường.

Quy trình:

1. Người dùng nhập URL OpenAPI hoặc upload file Swagger.
2. Framework tự sinh:

   * Provider.
   * Environment.
   * API.
   * Contract.
   * Mapping skeleton.
3. Consultant chỉ cần:

   * Chọn Authentication.
   * Điều chỉnh Mapping.
   * Chạy Test.

Đối với nhiều hệ thống REST chuẩn, thời gian tích hợp có thể giảm từ vài ngày xuống còn vài chục phút.

---

# Sau 20 chương, nếu mình là người lập roadmap sản phẩm

Mình sẽ không tiếp tục mở rộng kiến trúc nữa mà chuyển sang **Product Roadmap**:

### Phase 1 - Payment Platform

* MoMo
* VNPay
* Stripe
* PayPal

### Phase 2 - Universal REST Connector

* OpenAPI Import
* OAuth2
* GraphQL
* Webhook Builder

### Phase 3 - Enterprise Integration

* Message Queue
* Event Bus
* Distributed Execution
* Monitoring
* Marketplace

Đến thời điểm này, mình cho rằng kiến trúc đã đủ trưởng thành để **ngừng thiết kế và bắt đầu xây dựng MVP**. Trong thực tế, giá trị lớn nhất sẽ đến từ việc triển khai 2–3 provider đầu tiên (MoMo, VNPay, Stripe), sau đó dùng kinh nghiệm thực tế để tinh chỉnh Core thay vì tiếp tục bổ sung thêm tầng trừu tượng trên giấy. Đây là cách có xác suất thành công cao nhất cho một sản phẩm thương mại.
