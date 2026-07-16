Đây là bản mình sẽ viết theo hướng **Product Proposal** thay vì Technical Design. Đối tượng đọc là Product Owner, BA, Functional Consultant hoặc khách hàng trên Odoo Store.

---

# Excel Report Builder

## Overview

Excel Report Builder là một framework giúp xây dựng và quản lý các báo cáo Excel trên Odoo theo hướng cấu hình (Configuration-first) thay vì lập trình (Code-first).

Thay vì phải viết hàng trăm dòng Python cho mỗi báo cáo, Functional Consultant chỉ cần cấu hình trên giao diện để:

* Thiết kế cấu trúc báo cáo.
* Chọn cột dữ liệu.
* Thiết lập định dạng.
* Áp dụng các hàm xử lý dữ liệu.
* Quản lý chữ ký.
* Quản lý nhiều template cho cùng một báo cáo.

Framework được chia thành **2 module**:

* **Excel Report Base (Free)**: Framework dành cho Developer.
* **Excel Report Builder (Professional)**: Công cụ dành cho Functional Consultant và Business User.

---

# Module 1: Excel Report Base (Free)

Đây là module nền tảng để các Developer xây dựng các báo cáo Excel có cấu trúc thống nhất.

Mục tiêu:

> Một engine duy nhất có thể tái sử dụng cho tất cả các báo cáo Excel.

## Core Engine

* Excel Report Engine
* Worksheet Engine
* Table Renderer
* Signature Renderer
* Cell Writer
* Image Writer
* Formula Writer

## Column Configuration

Cho phép cấu hình:

* Field
* Sequence
* Width
* Visibility
* Merge
* Alignment
* Format
* Function

## Format Library

Thư viện định dạng dùng chung.

Ví dụ:

* Text
* Integer
* Float
* Currency
* Date
* DateTime
* Percentage
* Header
* Total
* Footer

Developer có thể đăng ký thêm format mới.

---

## Function Registry

Framework cung cấp cơ chế đăng ký Function.

Ví dụ:

* Upper
* Lower
* Title
* Date Format
* Currency
* Percentage
* Concat
* Image
* QRCode
* Barcode

Các module khác có thể mở rộng mà không cần sửa Base.

---

## Signature Engine

Hỗ trợ:

* Partner
* Text

Tự động lấy:

* Employee
* Job Title
* Signature Name

---

## Multi-sheet Support

Một báo cáo có thể sinh nhiều Worksheet.

Ví dụ:

* Summary
* Detail
* Invoice
* Payment

---

## Hook API

Cho phép module khác override hoặc mở rộng:

* Prepare Data
* Header
* Title
* Footer
* Function Registry
* Format Library
* Worksheet

---

## Developer API

Ví dụ:

```python
_prepare_data()

_prepare_header()

_prepare_footer()

_prepare_signature()
```

Toàn bộ phần render Table được dùng lại.

---

# Module 2: Excel Report Builder (Professional)

Đây là module hướng tới Functional Consultant.

Không cần lập trình.

Không cần chỉnh sửa Python.

Tất cả thao tác được thực hiện trên giao diện.

---

# Report Designer

Thiết kế báo cáo bằng giao diện.

Quản lý:

* Worksheet
* Header
* Title
* Table
* Footer
* Signature

---

# Template Manager

Một báo cáo có thể có nhiều Template.

Ví dụ:

Sales Report

* Internal
* Customer
* Finance
* Warehouse

Người dùng chỉ chọn Template khi Export.

---

# Dynamic Column Builder

Quản lý:

* Field
* Width
* Position
* Merge
* Group
* Visible
* Format
* Function

---

# Function Marketplace

Thư viện Function có thể mở rộng.

Ví dụ:

Text

* Upper
* Lower
* Trim
* Replace

Number

* Round
* Currency
* Percentage

Date

* Date Format
* Fiscal Period

Image

* Image
* Barcode
* QRCode

Business

* Employee Title
* Partner Category
* Product Code

Module khác có thể bổ sung thêm Function.

---

# Expression Engine

Cho phép lấy dữ liệu bằng Expression.

Ví dụ:

```python
partner_id.name
```

```python
partner_id.parent_id.name
```

```python
amount_total - amount_tax
```

```python
len(line_ids)
```

Không cần tạo Compute Field.

---

# Formula Column

Cho phép tạo cột tính toán.

Ví dụ:

Revenue

Cost

Profit

Formula

```
Revenue - Cost
```

Không cần viết Python.

---

# Conditional Formatting

Thiết lập định dạng theo điều kiện.

Ví dụ:

Amount > 1.000.000

↓

Background đỏ

Quantity = 0

↓

Gray

Expired

↓

Yellow

---

# Group Builder

Group dữ liệu theo:

* Company
* Branch
* Warehouse
* Customer
* Product
* Category

Hệ thống tự động Merge và Group.

---

# Aggregate Library

Hỗ trợ:

* Sum
* Count
* Average
* Min
* Max
* Distinct Count

Có thể mở rộng thêm Aggregate Function.

---

# Variable System

Sử dụng biến trong Header, Footer, Title.

Ví dụ:

```
${company}

${branch}

${warehouse}

${today}

${month}

${year}

${user}

${page}
```

Không cần viết Python.

---

# Preview

Preview báo cáo trước khi Export.

Cho phép kiểm tra:

* Format
* Width
* Merge
* Header
* Footer

---

# Import Excel Template *(Roadmap)*

Import file Excel có sẵn.

Framework sẽ đọc:

* Merge
* Width
* Height
* Font
* Border
* Background
* Color

Functional Consultant chỉ cần mapping dữ liệu.

---

# Version Management *(Roadmap)*

Quản lý nhiều phiên bản Template.

Ví dụ:

* Version 1
* Version 2
* Version 3

Cho phép Rollback.

---

# Scheduler *(Roadmap)*

Tự động:

* Generate Report
* Export Excel
* Send Email

Theo lịch.

---

# REST API *(Roadmap)*

Cho phép hệ thống khác gọi:

```
POST /api/report
```

để sinh báo cáo Excel.

---

# Đối tượng sử dụng

## Excel Report Base

Đối tượng:

* Odoo Developer

Mục tiêu:

* Xây dựng Framework chung
* Tái sử dụng Engine
* Chuẩn hóa Report

---

## Excel Report Builder

Đối tượng:

* Functional Consultant
* Business Analyst
* Key User
* End User

Mục tiêu:

* Tạo báo cáo mới mà không cần lập trình
* Quản lý Template
* Thay đổi cột hiển thị
* Thay đổi định dạng
* Thêm Function
* Quản lý nhiều mẫu báo cáo

---

# Feature Comparison

| Feature                | Base (Free) | Builder (Professional) |
| ---------------------- | :---------: | :--------------------: |
| Excel Report Engine    |      ✅      |            ✅           |
| Worksheet Engine       |      ✅      |            ✅           |
| Table Renderer         |      ✅      |            ✅           |
| Signature Engine       |      ✅      |            ✅           |
| Column Configuration   |      ✅      |         ✅ (UI)         |
| Format Library         |      ✅      |         ✅ (UI)         |
| Function Registry      |      ✅      |     ✅ (Marketplace)    |
| Hook API               |      ✅      |            ✅           |
| Multi-sheet            |      ✅      |            ✅           |
| Developer Extension    |      ✅      |            ✅           |
| Report Designer        |      ❌      |            ✅           |
| Template Manager       |      ❌      |            ✅           |
| Dynamic Column Builder |      ❌      |            ✅           |
| Function Marketplace   |      ❌      |            ✅           |
| Expression Engine      |      ❌      |            ✅           |
| Formula Column         |      ❌      |            ✅           |
| Conditional Formatting |      ❌      |            ✅           |
| Group Builder          |      ❌      |            ✅           |
| Aggregate Library      |      ❌      |            ✅           |
| Variable System        |      ❌      |            ✅           |
| Report Preview         |      ❌      |            ✅           |
| Import Excel Template  |      ❌      |       🚀 Roadmap       |
| Version Management     |      ❌      |       🚀 Roadmap       |
| Scheduler              |      ❌      |       🚀 Roadmap       |
| REST API               |      ❌      |       🚀 Roadmap       |

## Định hướng sản phẩm

* **Excel Report Base** là framework miễn phí giúp chuẩn hóa việc phát triển báo cáo Excel trong Odoo, hướng đến cộng đồng Developer.
* **Excel Report Builder** là sản phẩm thương mại tập trung vào trải nghiệm của Functional Consultant, giúp thiết kế và bảo trì báo cáo Excel bằng cấu hình thay vì lập trình.

Cách phân chia này tạo ra ranh giới rõ ràng giữa **Engine** (Free) và **Builder** (Paid): Developer vẫn có đầy đủ nền tảng để mở rộng, trong khi doanh nghiệp và Consultant trả phí cho các công cụ giúp giảm thời gian triển khai và bảo trì báo cáo.
