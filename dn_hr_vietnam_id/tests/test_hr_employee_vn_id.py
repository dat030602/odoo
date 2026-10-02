# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestHrEmployeeVnId(TransactionCase):
    """Unit tests for Vietnam HR Employee Identification (CCCD/CMND) module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Employee = cls.env['hr.employee']
        cls.today = fields.Date.today()

    def test_valid_cccd(self):
        """Tạo nhân viên với CCCD 12 số hợp lệ, kiểm tra sync sang identification_id, kiểm tra strip khoảng trắng."""
        employee = self.Employee.create({
            'name': 'Nguyen Van A',
            'vn_id_type': 'cccd',
            'vn_id_number': '  001099012345  ',
        })
        self.assertEqual(employee.vn_id_number, '001099012345', "Whitespace should be stripped.")
        self.assertEqual(
            employee.identification_id,
            '001099012345',
            "identification_id should automatically sync from vn_id_number."
        )
        self.assertEqual(employee.vn_id_type, 'cccd')

    def test_invalid_cccd(self):
        """Kiểm tra raise ValidationError khi số CCCD không đủ/thừa số hoặc chứa ký tự chữ cái."""
        # 11 số (thiếu số)
        with self.assertRaises(ValidationError, msg="CCCD with 11 digits must raise ValidationError"):
            self.Employee.create({
                'name': 'Nguyen Van Invalid 1',
                'vn_id_type': 'cccd',
                'vn_id_number': '00109901234',
            })

        # 13 số (thừa số)
        with self.assertRaises(ValidationError, msg="CCCD with 13 digits must raise ValidationError"):
            self.Employee.create({
                'name': 'Nguyen Van Invalid 2',
                'vn_id_type': 'cccd',
                'vn_id_number': '0010990123456',
            })

        # 12 ký tự nhưng chứa chữ cái
        with self.assertRaises(ValidationError, msg="CCCD containing letters must raise ValidationError"):
            self.Employee.create({
                'name': 'Nguyen Van Invalid 3',
                'vn_id_type': 'cccd',
                'vn_id_number': '00109901234A',
            })

    def test_valid_cmnd(self):
        """Tạo nhân viên với CMND 9 số hợp lệ, kiểm tra strip khoảng trắng và sync identification_id."""
        employee = self.Employee.create({
            'name': 'Tran Van B',
            'vn_id_type': 'cmnd',
            'vn_id_number': '  123456789  ',
        })
        self.assertEqual(employee.vn_id_number, '123456789', "Whitespace should be stripped.")
        self.assertEqual(employee.identification_id, '123456789', "identification_id should match vn_id_number.")
        self.assertEqual(employee.vn_id_type, 'cmnd')

    def test_invalid_cmnd(self):
        """Kiểm tra raise ValidationError khi CMND không đúng 9 chữ số."""
        # 8 số (thiếu số)
        with self.assertRaises(ValidationError, msg="CMND with 8 digits must raise ValidationError"):
            self.Employee.create({
                'name': 'Tran Van Invalid 1',
                'vn_id_type': 'cmnd',
                'vn_id_number': '12345678',
            })

        # 10 số (thừa số)
        with self.assertRaises(ValidationError, msg="CMND with 10 digits must raise ValidationError"):
            self.Employee.create({
                'name': 'Tran Van Invalid 2',
                'vn_id_type': 'cmnd',
                'vn_id_number': '1234567890',
            })

        # 9 ký tự nhưng chứa chữ cái
        with self.assertRaises(ValidationError, msg="CMND containing letters must raise ValidationError"):
            self.Employee.create({
                'name': 'Tran Van Invalid 3',
                'vn_id_type': 'cmnd',
                'vn_id_number': '12345678X',
            })

    def test_unique_id_number(self):
        """Kiểm tra raise ValidationError khi tạo 2 nhân viên active có cùng số ID."""
        self.Employee.create({
            'name': 'Active Employee 1',
            'vn_id_type': 'cccd',
            'vn_id_number': '001099000001',
            'active': True,
        })

        # Trùng số trên nhân viên active khác -> ValidationError
        with self.assertRaises(ValidationError, msg="Duplicate active CCCD must raise ValidationError"):
            self.Employee.create({
                'name': 'Active Employee 2',
                'vn_id_type': 'cccd',
                'vn_id_number': '001099000001',
                'active': True,
            })

        # Nhân viên inactive (archived) trùng số -> Cho phép tạo nhân viên active
        archived_emp = self.Employee.create({
            'name': 'Archived Employee',
            'vn_id_type': 'cccd',
            'vn_id_number': '001099000002',
            'active': False,
        })
        active_emp = self.Employee.create({
            'name': 'Active Employee',
            'vn_id_type': 'cccd',
            'vn_id_number': '001099000002',
            'active': True,
        })
        self.assertTrue(archived_emp.id and active_emp.id)

    def test_batch_duplicate(self):
        """Kiểm tra raise ValidationError khi tạo batch nhân viên có trùng số CCCD."""
        vals_list = [
            {
                'name': 'Batch Emp 1',
                'vn_id_type': 'cccd',
                'vn_id_number': '001099000003',
            },
            {
                'name': 'Batch Emp 2',
                'vn_id_type': 'cccd',
                'vn_id_number': '001099000003',
            },
        ]
        with self.assertRaises(ValidationError, msg="Duplicate ID within same batch must raise ValidationError"):
            self.Employee.create(vals_list)

    def test_date_validations(self):
        """Kiểm tra ràng buộc logic ngày cấp, ngày hết hạn và ngày sinh."""
        # 1. Ngày cấp trong tương lai -> ValidationError
        future_date = self.today + timedelta(days=1)
        with self.assertRaises(ValidationError, msg="Issue date in future must raise ValidationError"):
            self.Employee.create({
                'name': 'Future Issue Date Emp',
                'vn_id_type': 'cccd',
                'vn_id_number': '001099000011',
                'vn_id_issue_date': future_date,
            })

        # 2. Ngày hết hạn bằng ngày cấp -> ValidationError
        issue_date = self.today - timedelta(days=365)
        with self.assertRaises(ValidationError, msg="Expiry date equal to issue date must raise ValidationError"):
            self.Employee.create({
                'name': 'Expiry Equal Issue Emp',
                'vn_id_type': 'cccd',
                'vn_id_number': '001099000012',
                'vn_id_issue_date': issue_date,
                'vn_id_expiry_date': issue_date,
            })

        # 3. Ngày hết hạn trước ngày cấp -> ValidationError
        with self.assertRaises(ValidationError, msg="Expiry date before issue date must raise ValidationError"):
            self.Employee.create({
                'name': 'Expiry Before Issue Emp',
                'vn_id_type': 'cccd',
                'vn_id_number': '001099000013',
                'vn_id_issue_date': issue_date,
                'vn_id_expiry_date': issue_date - timedelta(days=1),
            })

        # 4. Ngày cấp trước ngày sinh -> ValidationError
        birthday = self.today - timedelta(days=365 * 20)
        with self.assertRaises(ValidationError, msg="Issue date before birthday must raise ValidationError"):
            self.Employee.create({
                'name': 'Issue Before Birthday Emp',
                'vn_id_type': 'cccd',
                'vn_id_number': '001099000014',
                'birthday': birthday,
                'vn_id_issue_date': birthday - timedelta(days=1),
            })

        # 5. Dữ liệu ngày tháng hợp lệ
        emp = self.Employee.create({
            'name': 'Valid Dates Emp',
            'vn_id_type': 'cccd',
            'vn_id_number': '001099000015',
            'birthday': birthday,
            'vn_id_issue_date': birthday + timedelta(days=365 * 15),
            'vn_id_expiry_date': birthday + timedelta(days=365 * 25),
        })
        self.assertTrue(emp.id)

    def test_write_sync_identification_id(self):
        """Kiểm tra write cập nhật vn_id_number đồng bộ sang identification_id."""
        employee = self.Employee.create({
            'name': 'Sync Write Emp',
        })
        self.assertFalse(employee.identification_id)

        # Cập nhật số CCCD có khoảng trắng ở đầu và cuối
        employee.write({
            'vn_id_type': 'cccd',
            'vn_id_number': '  001099000020  ',
        })
        self.assertEqual(employee.vn_id_number, '001099000020', "Whitespace should be stripped on write.")
        self.assertEqual(
            employee.identification_id,
            '001099000020',
            "identification_id should be synced when it was previously empty."
        )

        # Nếu identification_id đã có giá trị từ trước, cập nhật vn_id_number không ghi đè
        employee.write({'identification_id': 'PASSPORT_ABC_123'})
        employee.write({'vn_id_number': '001099000021'})
        self.assertEqual(
            employee.identification_id,
            'PASSPORT_ABC_123',
            "Existing identification_id should not be overwritten."
        )

    def test_unarchive_duplicate(self):
        """Lưu trữ 1 nhân viên, tạo nhân viên mới cùng số, unarchive nhân viên cũ -> raise ValidationError."""
        emp1 = self.Employee.create({
            'name': 'Emp 1 to Archive',
            'vn_id_type': 'cccd',
            'vn_id_number': '001099000030',
            'active': True,
        })
        # Archive emp1
        emp1.write({'active': False})

        # Tạo emp2 cùng số CCCD thành công vì emp1 đã lưu trữ
        emp2 = self.Employee.create({
            'name': 'Emp 2 Active',
            'vn_id_type': 'cccd',
            'vn_id_number': '001099000030',
            'active': True,
        })
        self.assertTrue(emp2.id)

        # Unarchive emp1 -> ValidationError vì emp2 đang active cùng số
        with self.assertRaises(ValidationError, msg="Unarchiving duplicate ID must raise ValidationError"):
            emp1.write({'active': True})
