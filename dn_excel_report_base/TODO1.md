Sau khi xem hai file mẫu, mình thấy kiến trúc hiện tại vẫn là **hard-code report**:

* `COLUMNS` được khai báo trong Python. 
* `create_formats()` hard-code format. 
* `add_title()`, `add_header()`, `add_body()`, `add_signatures()` đều ghi dữ liệu cố định. 
* File thứ hai đã tách các bước rõ hơn (`prepare_formats`, `write_header`, `write_body`, `write_table`, `write_footer`, `write_signature`) nhưng vẫn hard-code từng phần. 

Nếu mục tiêu là **một engine Excel Report có thể cấu hình trên giao diện Odoo**, thì mình sẽ không cho người dùng cấu hình từng dòng excel mà chỉ cho cấu hình các thành phần cần thiết và để code chỉ còn là engine.

---

# Đề xuất thiết kế

## Kiến trúc

```
Excel Report

├── Report
│      ├── Worksheet
│      ├── Formats
│      ├── Header
│      ├── Title
│      ├── Body
│      ├── Footer
│      └── Signature
│
├── Columns
│      ├── Field
│      ├── Width
│      ├── Format
│      ├── Function
│      └── Visible
│
└── Functions
       ├── Value Function
       ├── Format Function
       └── Aggregate Function
```

---

# Luồng generate report

```
generate_excel()

↓

prepare worksheet()

↓

prepare format()

↓

header()

↓

title()

↓

body()

↓

footer()

↓

signature()
```

Đây chính là flow chuẩn nên sử dụng.

---

# 1. prepare worksheet()

Mục đích:

Đọc cấu hình trên View.

Ví dụ model

```
excel.report.column

- sequence
- field_id
- width
- visible
- group
- merge
- function_id
- format_id
```

Engine chỉ cần

```
for column in report.column_ids:
    worksheet.set_column(...)
```

---

# 2. prepare format()

Đây là phần rất nên tách.

Hiện nay

```
create_formats()
```

hard-code khoảng 20 format.

Nên chuyển thành

```
excel.report.format
```

Ví dụ

| Name    | Font  | Size | Bold  | Align  | Num Format |
| ------- | ----- | ---- | ----- | ------ | ---------- |
| Text    | Times | 11   | False | Left   |            |
| Integer | Times | 11   | False | Right  | #,##0      |
| Float   | Times | 11   | False | Right  | #,##0.00   |
| Header  | Times | 11   | True  | Center |            |
| Total   | Times | 11   | True  | Right  | #,##0      |

prepare_format()

```
for format in report.format_ids:
    workbook.add_format(...)
```

Sau đó cache

```
formats = {
    text: xxx,
    integer: xxx,
    total: xxx
}
```

---

# 3. Header

Header nên giữ mặc định.

Ví dụ

```
Company

Logo

Address

...
```

Chỉ cần setup

```
Show Logo

Show Address

Show Tax Code

```

không cần cho user kéo thả.

---

# 4. Title

Tương tự.

Mặc định

```
Title

Sub Title

Period
```

View chỉ nhập

```
Title

Subtitle

Expression
```

Ví dụ

```
Tháng %(month)s/%(year)s
```

---

# 5. Body

Đây là phần quan trọng nhất.

Hiện tại

```
for column in COLUMNS:
```

nên thành

```
for column in report.column_ids:
```

---

Mỗi column gồm

```
Field

Width

Format

Function

Visible

Group

Merge

Sum
```

Ví dụ

| Field   | Function    | Format |
| ------- | ----------- | ------ |
| partner | Upper Case  | Text   |
| amount  | Currency    | Money  |
| date    | Format Date | Date   |

Engine

```
value

↓

Function

↓

Format

↓

Write Cell
```

---

# Function nên thiết kế như thế nào

Đây là điểm mình nghĩ nên làm mạnh nhất.

Tạo model

```
excel.report.function
```

Ví dụ

| Code           | Name              |
| -------------- | ----------------- |
| none           | None              |
| uppercase      | Upper Case        |
| lowercase      | Lower Case        |
| date           | Date              |
| datetime       | Date Time         |
| currency       | Currency          |
| percent        | Percent           |
| remove_prefix  | Remove Prefix     |
| partner_name   | Partner Name      |
| employee_title | Employee Title    |
| concat         | Concat            |
| eval           | Python Expression |

Engine

```
value

↓

function.execute(value)

↓

result
```

Ví dụ

```
Amount

↓

Currency()

↓

1,200,000
```

Hoặc

```
Partner

↓

Upper()

↓

ABC COMPANY
```

---

# Function có tham số

Ví dụ

```
Date

format="%d/%m/%Y"
```

hoặc

```
Round

digits=2
```

Nên có thêm

```
parameter
```

dạng JSON.

---

# Footer

Để mặc định

```
Note

Page

Printed Date
```

View

```
Footer Note

Show Print Date

Show User
```

---

# Signature

Đây là phần nên cấu hình hoàn toàn.

Model

```
excel.report.signature
```

One2many

---

Mỗi dòng

```
Sequence

Type

Partner

Title

Value

```

Type

```
Selection

Partner

Text
```

---

Nếu

```
Partner
```

thì

```
res.partner

↓

partner.user_ids

↓

hr.employee

↓

job_id.name
```

để lấy

```
Title
```

và

```
partner.name
```

---

Nếu

```
Text
```

thì

```
Title = nhập

Value = nhập
```

Ví dụ

| Title       | Value        |
| ----------- | ------------ |
| Prepared By | Nguyễn Văn A |
| Approved By | Lê Văn B     |

---

Engine

```
for signature in signature_ids:

if type == partner

    title = employee.job_id.name

    value = partner.name

else

    title = signature.title

    value = signature.value
```

---

# Đề xuất Data Model

```
excel.report
│
├── worksheet setup
├── format_ids
├── column_ids
├── signature_ids
├── header setup
├── title setup
├── footer setup
```

### excel.report.column

```
sequence
field_id
width
visible
group
merge
sum
function_id
format_id
```

### excel.report.function

```
name
code
python_method
parameter
```

### excel.report.format

```
name
font
size
bold
italic
align
valign
border
number_format
background
font_color
...
```

### excel.report.signature

```
sequence

type
    partner
    text

partner_id

title

value
```

---

## Lợi ích của thiết kế này

* **Tái sử dụng**: Một engine có thể phục vụ nhiều báo cáo Excel khác nhau.
* **Không cần sửa Python khi thay đổi hiển thị**: Thêm/xóa cột, đổi format, đổi hàm xử lý đều thực hiện trên giao diện cấu hình.
* **Mở rộng dễ dàng**: Chỉ cần bổ sung một hàm mới vào thư viện (`excel.report.function`) là tất cả báo cáo đều có thể sử dụng.
* **Phân tách rõ trách nhiệm**:

  * `prepare_worksheet()`: đọc cấu hình cột.
  * `prepare_format()`: khởi tạo và cache format.
  * `header()/title()/body()/footer()/signature()`: render từng phần.
  * `Function Library`: xử lý và biến đổi dữ liệu trước khi ghi ra Excel.
  * `Format Library`: quản lý định dạng hiển thị thống nhất trên toàn hệ thống.

Đây là kiến trúc phù hợp để chuyển từ các báo cáo Excel đang hard-code trong hai file mẫu sang một **Excel Report Engine** có khả năng cấu hình trên giao diện và tái sử dụng cho nhiều module trong Odoo.
Đúng, mình cũng nghĩ nên thiết kế theo hướng đó. Thực tế trong Odoo đây là pattern khá phổ biến: **Base module + Business module**.

Với yêu cầu của bạn, mình sẽ chia thành 2 tầng.

---

# Layer 1: excel_report_base

Module này chỉ đóng vai trò **Framework/Engine**, hoàn toàn không biết báo cáo gì.

Ví dụ:

```
excel_report_base
│
├── models
│      excel_report.py
│      excel_report_column.py
│      excel_report_format.py
│      excel_report_signature.py
│      excel_report_function.py
│
├── services
│      report_engine.py
│
└── abstract
       excel_report_abstract.py
```

Engine chỉ làm đúng các bước

```
generate()

↓

prepare worksheet()

↓

prepare formats()

↓

render header()

↓

render title()

↓

render body()

↓

render footer()

↓

render signature()
```

Nhưng trong đó chỉ có **table** và **signature** là có implementation mặc định.

Ví dụ

```python
class ExcelReportEngine:

    def render_header(self):
        pass

    def render_title(self):
        pass

    def render_body(self):
        pass

    def render_footer(self):
        pass

    def render_signature(self):
        self._render_default_signature()

    def render_table(self):
        self._render_default_table()
```

---

# Layer 2: business module

Ví dụ

```
sale_excel_report
purchase_excel_report
stock_excel_report
hr_excel_report
```

Mỗi module chỉ override những phần cần.

Ví dụ

```
sale_excel_report

Header

Title

Body

Footer
```

Signature và Table dùng luôn Base.

---

## Ví dụ

```
Base

generate()

↓

Header()

↓

Title()

↓

Table()

↓

Footer()

↓

Signature()
```

Sale Report

```
Header()      override

Title()       override

Table()       dùng base

Footer()      override

Signature()   dùng base
```

---

Stock Report

```
Header()      override

Title()       override

Table()       dùng base

Footer()      override

Signature()   dùng base
```

---

# Vì sao Table nên nằm trong Base?

Qua hai file mẫu mình thấy khoảng **80% code đang nằm ở việc render table**:

* đọc column
* set width
* merge group
* format cell
* sum
* merge row
* write formula
* write image
* number format
* date format
* function
* total
* subtotal

Những phần này gần như report nào cũng giống nhau.

Khác nhau chủ yếu là:

```
Data

↓

Columns

↓

Function

↓

Format
```

Engine không cần biết dữ liệu gì.

---

# Signature cũng vậy

Signature gần như report nào cũng

```
Title

Người lập

Kế toán

Giám đốc

...
```

Khác nhau chỉ là số lượng.

Cho nên chỉ cần One2many

```
Sequence

Type

Partner/Text

Title

Value
```

là đủ.

Engine render.

---

# Header, Title, Footer thì không nên cố generic

Đây là chỗ mình sẽ **không cố cấu hình hết trên UI**.

Ví dụ

Report A

```
Logo

Company

Address

Tax code
```

Report B

```
Warehouse

Document No

Version

Revision

Issue Date
```

Report C

```
Department

Branch

Factory

```

Nếu cố đưa hết lên View thì sẽ sinh ra rất nhiều field:

```
show_logo

show_tax

show_company

show_branch

show_address

show_factory

show_document_no

...
```

Sau vài report sẽ rất khó bảo trì.

---

# Nên dùng Hook

Trong Base

```python
generate()

↓

_prepare_worksheet()

↓

_prepare_formats()

↓

_header()

↓

_title()

↓

_table()

↓

_footer()

↓

_signature()
```

Trong Base

```python
def _header(self):
    pass

def _title(self):
    pass

def _footer(self):
    pass
```

Business module override

```python
class SaleExcelReport(ExcelReportEngine):

    def _header(self):
        ...

    def _title(self):
        ...

    def _footer(self):
        ...
```

---

# Mình còn đề xuất thêm 1 hook nữa

```
generate()

↓

_prepare_data()

↓

_prepare_worksheet()

↓

_prepare_formats()

↓

_header()

↓

_title()

↓

_table()

↓

_footer()

↓

_signature()
```

Trong đó:

* `_prepare_data()`: business module xử lý dữ liệu, group, subtotal, tính toán KPI...
* `_table()`: engine chỉ render dữ liệu đã chuẩn hóa theo cấu hình cột.

Ví dụ `_prepare_data()` trả về:

```python
[
    {
        "type": "detail",
        "values": {...}
    },
    {
        "type": "subtotal",
        "values": {...}
    },
    {
        "type": "grand_total",
        "values": {...}
    }
]
```

Engine không cần biết đó là báo cáo Sales, Stock hay HR; chỉ cần đọc từng dòng và render theo `type`. Cách tách này giúp phần tính toán nghiệp vụ nằm ở module con, còn phần xuất Excel vẫn được tái sử dụng tối đa trong `excel_report_base`.

Theo mình, đây là kiến trúc phù hợp nhất với Odoo: **Base chỉ là framework render Excel**, còn **mỗi module nghiệp vụ chỉ override phần chuẩn bị dữ liệu và các khu vực tự do (header/title/footer)**, trong khi **table và signature được chuẩn hóa và tái sử dụng**. Điều này giúp giảm đáng kể lượng code lặp giữa các báo cáo và dễ mở rộng khi phát sinh report mới.

Nếu đứng ở góc độ Product Owner và nhìn thị trường Odoo Apps thì mình sẽ đánh giá như sau:

## Nếu chỉ là Base Excel Export

Bao gồm:

* Dynamic column
* Dynamic format
* Function
* Signature
* Excel engine

=> **Mình sẽ không bán.**

Lý do:

Trên Odoo Store hiện có rất nhiều module tương tự:

* report_xlsx
* report_xlsx_helper
* excel_report
* dynamic_xlsx
* xlsx_helper

Khách hàng sẽ nhìn thấy:

> "À, chỉ là export excel."

Rất khó tạo khác biệt.

Giá trị cảm nhận khoảng **20~40 USD**.

---

# Nếu là Excel Report Builder

Đây là hướng mình nghĩ nên đi.

Đừng gọi là

> Excel Export Base

Mà gọi là

> Excel Report Builder

hoặc

> Dynamic Excel Report Designer

Khách hàng nhìn vào sẽ thấy khác.

Ví dụ

```
Excel Report Builder

✓ Configure columns

✓ Configure formats

✓ Built-in functions

✓ Group

✓ Merge

✓ Total

✓ Sub Total

✓ Signature

✓ Dynamic Header

✓ Dynamic Footer

✓ Preview

✓ Multi Template
```

Lúc này sản phẩm không còn là library nữa.

Nó là một tool.

---

# Nếu chỉ dành cho Developer

Ví dụ

```
class SaleReport(BaseExcel):
```

thì chỉ developer dùng.

Khách hàng cuối không quan tâm.

=> Không nên bán.

---

# Nếu dành cho Functional Consultant

Ví dụ

Có menu

```
Excel Reports

↓

Create

↓

Columns

↓

Functions

↓

Preview

↓

Download
```

Thì Consultant tạo được report.

Đây mới là thứ khách hàng trả tiền.

---

# Theo mình nên chia làm 2 module

## Module 1 (Free)

```
excel_report_base
```

Bao gồm

* Engine
* Function Registry
* Format Registry
* Signature
* API

Đối tượng:

Developer

Mục tiêu:

Thu hút download.

Ví dụ

10.000 download.

---

## Module 2 (Paid)

```
excel_report_builder
```

Bao gồm

* UI Builder
* Dynamic Columns
* Dynamic Format
* Preview
* Designer
* Expression
* Configuration

Đối tượng

Functional Consultant

Business User

Giá

79$

99$

149$

đều hợp lý.

---

# Vì sao nên Free Base?

Ví dụ

Developer cài

```
excel_report_base
```

Sau đó project mới

```
sale_report

purchase_report

stock_report
```

Đều dùng Base.

Sau này họ muốn

```
Không muốn code nữa.

↓

Mua Builder.
```

Đó là cách nhiều hãng Odoo đang làm.

---

# Nếu chỉ có Builder thì sao?

Có thể bán.

Nhưng phải thật sự mạnh.

Ví dụ

```
Excel Builder

Columns

Functions

Conditional Format

Formula

Merge

Freeze

Group

Subtotal

Image

QR Code

Barcode

Signature

Multi Sheet

Preview

Import Template

Export Template
```

Lúc đó đây là một sản phẩm hoàn chỉnh.

Không còn là library nữa.

---

# Đánh giá tiềm năng

Nếu hoàn thiện theo hướng **Excel Report Builder**, mình sẽ chấm:

| Tiêu chí                     | Đánh giá     |
| ---------------------------- | ------------ |
| Ý tưởng                      | ⭐⭐⭐⭐⭐        |
| Tính tái sử dụng             | ⭐⭐⭐⭐⭐        |
| Khả năng mở rộng             | ⭐⭐⭐⭐⭐        |
| Giá trị với Consultant       | ⭐⭐⭐⭐⭐        |
| Giá trị với End User         | ⭐⭐⭐⭐☆        |
| Khả năng bán trên Odoo Store | **8.5–9/10** |

## Điều mình sẽ bổ sung để tăng giá trị thương mại

Hiện ý tưởng của bạn mới dừng ở **render Excel**. Để đủ sức cạnh tranh trên Odoo Store, mình sẽ bổ sung thêm:

* **Template Manager**: nhiều template cho cùng một model.
* **Preview cấu hình** trước khi xuất file.
* **Function Registry**: thư viện hàm có thể mở rộng qua module khác.
* **Format Library**: tái sử dụng định dạng giữa các report.
* **Multi-sheet**: hỗ trợ nhiều worksheet trong một file.
* **Expression Engine**: cho phép lấy giá trị bằng biểu thức (`partner_id.name`, `amount_total * 1.1`,...).
* **Hook API**: module khác có thể đăng ký thêm Function và Format mà không sửa Base.

Theo mình, **Base Engine nên miễn phí** để tạo cộng đồng và khuyến khích developer sử dụng. Phần **Builder (UI cấu hình báo cáo)** mới là phần nên thương mại hóa vì đó là giá trị mà Functional Consultant và doanh nghiệp sẵn sàng trả tiền. Đây cũng là mô hình phổ biến của nhiều sản phẩm Odoo thành công: miễn phí phần framework, bán phần công cụ cấu hình và trải nghiệm người dùng.

Nếu mục tiêu là **đăng Odoo Store và có doanh thu**, thì đừng nghĩ theo hướng **Excel Export**, hãy nghĩ theo hướng **Excel Platform**.

Mình sẽ chia theo các gói tính năng để dễ xác định MVP và roadmap.

---

# 1. Report Designer ⭐⭐⭐⭐⭐ (Core)

Đây là tính năng bán được nhất.

Không chỉ cấu hình cột.

Cho phép kéo thả các section

```
Header

↓

Title

↓

Table

↓

Footer

↓

Signature
```

Ví dụ

```
+------------------------+
| Header                 |
+------------------------+

+------------------------+
| Title                  |
+------------------------+

+------------------------+
| Table                  |
+------------------------+

+------------------------+
| Footer                 |
+------------------------+
```

Consultant chỉ kéo thả.

Không cần code.

---

# 2. Function Marketplace ⭐⭐⭐⭐⭐

Giống Excel Formula.

Ví dụ có sẵn

```
Upper()

Lower()

Round()

Date()

Datetime()

Currency()

Percent()

Remove Prefix()

Image()

QR Code()

Barcode()

Employee Title()

Concat()

Substring()

If()

Case()

Lookup()

Domain()

```

Module khác có thể đăng ký thêm Function.

Ví dụ

```
Stock

↓

Lot()

```

```
HR

↓

Employee Age()

```

```
Sale

↓

Customer Rank()
```

Không cần sửa Base.

---

# 3. Conditional Formatting ⭐⭐⭐⭐⭐

Rất nhiều khách hàng thích.

Ví dụ

```
Amount > 1000000

↓

Background đỏ
```

```
Quantity = 0

↓

Grey
```

```
Expired

↓

Yellow
```

Giống Excel.

---

# 4. Formula Column ⭐⭐⭐⭐⭐

Không lấy dữ liệu từ Odoo.

Mà tạo cột tính toán.

Ví dụ

```
Sales

Cost

Profit
```

Profit

```
Sales - Cost
```

Không cần sửa Python.

---

# 5. Expression Engine ⭐⭐⭐⭐⭐

Đây là điểm cực mạnh.

Ví dụ

```
partner_id.name
```

```
partner_id.parent_id.name
```

```
amount_total * 1.1
```

```
len(line_ids)
```

```
date.strftime(...)
```

Thay vì phải tạo field compute.

---

# 6. Group Builder ⭐⭐⭐⭐⭐

Hiện đang hardcode.

Cho phép

```
Group By

↓

Partner

↓

Date

↓

Warehouse

↓

Category
```

Engine tự subtotal.

---

# 7. Multi Level Group ⭐⭐⭐⭐⭐

Ví dụ

```
Company

↓

Warehouse

↓

Category

↓

Product
```

Giống Pivot.

---

# 8. Aggregate Library ⭐⭐⭐⭐⭐

Không chỉ Sum.

Có

```
Sum

Avg

Count

Max

Min

Median

Distinct Count

```

---

# 9. Template Library ⭐⭐⭐⭐

Một Report

↓

Nhiều Template

Ví dụ

```
Invoice

↓

Internal

↓

Customer

↓

Accounting

↓

Warehouse
```

Chỉ khác Header.

---

# 10. Import Existing Excel ⭐⭐⭐⭐⭐

Cực đáng tiền.

Upload

```
template.xlsx
```

Engine đọc

```
Merge

Width

Height

Font

Border

Color

Image

```

Chỉ mapping field.

Đây là tính năng rất ít module có.

---

# 11. Variable System ⭐⭐⭐⭐⭐

Ví dụ

```
${company}

${user}

${today}

${month}

${year}

${warehouse}

${branch}
```

Trong Title.

Không cần code.

---

# 12. Preview ⭐⭐⭐⭐⭐

Trên View

```
Generate Preview

↓

HTML

↓

Excel
```

Không cần tải file.

---

# 13. Multi Sheet ⭐⭐⭐⭐⭐

Một Report

↓

Nhiều Worksheet

Ví dụ

```
Summary

Sales

Invoice

Payment

```

---

# 14. Widget Library ⭐⭐⭐⭐

Cho Header

```
Image

Text

Rich Text

Table

QRCode

Barcode

```

---

# 15. Permission ⭐⭐⭐⭐

Ví dụ

```
Admin

↓

Edit Template
```

```
User

↓

Generate Only
```

---

# 16. Version Control ⭐⭐⭐⭐⭐

Template

```
V1

V2

V3
```

Rollback.

Khách Enterprise thích.

---

# 17. Scheduler ⭐⭐⭐⭐⭐

Tự động

```
8AM

↓

Generate

↓

Email

↓

Attachment
```

Không cần Automation khác.

---

# 18. REST API ⭐⭐⭐⭐⭐

```
POST

/api/report/sales

↓

Excel
```

Cho Mobile.

---

# 19. Theme ⭐⭐⭐⭐

Một click

```
Corporate

Blue

Green

Dark

Accounting
```

Toàn bộ format đổi.

---

# 20. Plugin System ⭐⭐⭐⭐⭐

Ví dụ

```
excel_hr

↓

Register Function
```

```
Employee Age()

Employee Title()

```

```
excel_stock

↓

Lot()

Expiry()

```

Base không sửa.

---

# 21. Chart ⭐⭐⭐⭐

Excel Chart

```
Bar

Pie

Line

```

Từ dữ liệu.

---

# 22. AI Formula (Tương lai)

Ví dụ nhập

```
Tính doanh thu sau thuế
```

Sinh

```
amount_total*0.9
```

---

# Theo mình, sản phẩm nên chia thành 3 phiên bản

## Community (Free)

* Excel Engine
* Table
* Format
* Function
* Signature

---

## Professional (99–149 USD)

* Report Designer
* Conditional Format
* Formula
* Expression
* Multi Template
* Multi Sheet
* Scheduler
* Preview

---

## Enterprise (299 USD+)

* Import Excel Template
* Plugin System
* Version
* API
* Dashboard
* Charts
* AI Formula

---

## Tính năng mình đánh giá có giá trị thương mại cao nhất

Nếu chỉ được chọn 5 tính năng để đầu tư, mình sẽ ưu tiên:

1. **Import Excel Template** – cho phép doanh nghiệp dùng ngay mẫu Excel hiện có, chỉ cần map dữ liệu.
2. **Expression + Formula Engine** – tạo cột tính toán mà không cần viết Python.
3. **Conditional Formatting** – tô màu, cảnh báo, định dạng theo điều kiện như Excel.
4. **Multi-sheet + Template Manager** – hỗ trợ nhiều worksheet và nhiều mẫu cho cùng một báo cáo.
5. **Plugin/Extension System** – cho phép các module khác đăng ký thêm Function, Format hoặc Widget mà không sửa Base.

Đây là những tính năng tạo sự khác biệt rõ ràng so với các module export Excel phổ biến trên Odoo Store và khiến sản phẩm trở thành một **nền tảng thiết kế báo cáo Excel**, thay vì chỉ là một công cụ xuất file Excel.

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
