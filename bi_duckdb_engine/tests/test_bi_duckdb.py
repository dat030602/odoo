from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from ..models import validate_extract_sql, extract_sql_params


@tagged('post_install', '-at_install')
class TestBiDuckDBEngine(TransactionCase):

    def test_sql_param_extraction(self):
        sql = """
            SELECT id, name
            FROM stock_move
            WHERE company_id IN :company_ids
              AND date >= :date_from
              AND state = :state
        """
        params = extract_sql_params(sql)
        self.assertEqual(params, ['date_from', 'state'])

    def test_sql_validation_success(self):
        sql = "SELECT id, name FROM sale_order WHERE company_id IN :company_ids"
        validated = validate_extract_sql(sql)
        self.assertEqual(validated, sql.strip())

    def test_sql_validation_missing_company_ids(self):
        sql = "SELECT id, name FROM sale_order"
        with self.assertRaises(ValueError):
            validate_extract_sql(sql)

    def test_sql_validation_forbidden_keywords(self):
        forbidden_queries = [
            "DELETE FROM sale_order WHERE company_id IN :company_ids",
            "UPDATE res_partner SET name = 'test' WHERE company_id IN :company_ids",
            "DROP TABLE sale_order; SELECT :company_ids",
            "SELECT pg_sleep(5), :company_ids",
            "SELECT * FROM res_users WHERE company_id IN :company_ids",
            "SELECT * FROM ir_config_parameter WHERE company_id IN :company_ids",
        ]
        for query in forbidden_queries:
            with self.subTest(query=query):
                with self.assertRaises(ValueError):
                    validate_extract_sql(query)

    def test_sql_validation_multiple_statements(self):
        sql = "SELECT 1 WHERE 1 IN :company_ids; SELECT 2"
        with self.assertRaises(ValueError):
            validate_extract_sql(sql)

    def test_report_and_views_creation(self):
        report = self.env['bi.duckdb.report'].create({
            'name': 'Test Sales Report',
            'code': 'test_sales_01',
            'company_id': self.env.company.id,
            'cache_ttl': 600,
            'pg_extract_sql': 'SELECT id, amount_total FROM sale_order WHERE company_id IN :company_ids AND date_order >= :date_from',
        })
        self.assertTrue(report.id)
        self.assertEqual(report.company_id, self.env.company)

        view = self.env['bi.duckdb.report.view'].create({
            'report_id': report.id,
            'name': 'Overview Tab',
            'duckdb_sql': 'SELECT * FROM raw_dataset LIMIT 10',
        })
        self.assertEqual(view.report_id, report)
        self.assertEqual(view.company_id, self.env.company)
        self.assertIn('Test Sales Report', view.display_name)

        action = report.action_open_report()
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('tag'), 'bi_duckdb_engine.report_action')
        self.assertEqual(action['context']['active_id'], report.id)
        self.assertEqual(action['params']['report_id'], report.id)
        self.assertIn('date_from', action['params']['param_names'])
        self.assertEqual(len(action['params']['views']), 1)

    def test_report_constraint_invalid_sql(self):
        with self.assertRaises(ValidationError):
            self.env['bi.duckdb.report'].create({
                'name': 'Bad SQL Report',
                'code': 'bad_sql_01',
                'pg_extract_sql': 'SELECT * FROM sale_order',  # missing :company_ids
            })
