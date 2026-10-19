import unittest
from odoo.addons.meta_migrator.models import view_merge


class TestViewMerge(unittest.TestCase):

    def test_canonical_text(self):
        xml1 = '<field name="foo" required="1" invisible="0"/>'
        xml2 = '<field  invisible="0"   required="1"  name="foo" />'
        self.assertEqual(view_merge.canonical_text(xml1), view_merge.canonical_text(xml2))

    def test_append_to_existing_data(self):
        source = '<data><xpath expr="//sheet" position="inside"><field name="x_test"/></xpath></data>'
        target = '<data>\n    <xpath expr="//header" position="inside"><button name="btn"/></xpath>\n</data>'

        res = view_merge.plan_append(source, target, source_inherit=True, target_inherit=True)
        self.assertIsNone(res.error)
        self.assertEqual(len(res.added), 1)
        self.assertEqual(len(res.present), 0)
        self.assertFalse(res.wrapped)
        self.assertIn('<field name="x_test"/>', res.new_arch)
        self.assertIn('<button name="btn"/>', res.new_arch)

    def test_idempotent_append(self):
        source = '<data><xpath expr="//sheet" position="inside"><field name="x_test"/></xpath></data>'
        target = '<data>\n    <xpath expr="//header" position="inside"><button name="btn"/></xpath>\n</data>'

        res1 = view_merge.plan_append(source, target, source_inherit=True, target_inherit=True)
        self.assertEqual(len(res1.added), 1)

        # Run again using the output of the first run as the target
        res2 = view_merge.plan_append(source, res1.new_arch, source_inherit=True, target_inherit=True)
        self.assertEqual(len(res2.added), 0)
        self.assertEqual(len(res2.present), 1)
        self.assertEqual(res2.new_arch, res2.old_view_text)

    def test_target_wrapped_when_lacking_data(self):
        source = '<xpath expr="//sheet" position="inside"><field name="x_extra"/></xpath>'
        target = '<xpath expr="//sheet" position="inside"><field name="x_orig"/></xpath>'

        res = view_merge.plan_append(source, target, source_inherit=True, target_inherit=True)
        self.assertIsNone(res.error)
        self.assertTrue(res.wrapped)
        self.assertEqual(len(res.added), 1)
        self.assertTrue(res.new_arch.startswith('<data>'))
        self.assertTrue(res.new_arch.endswith('</data>'))
        self.assertIn('x_orig', res.new_arch)
        self.assertIn('x_extra', res.new_arch)

    def test_target_self_closing_data(self):
        source = '<data><xpath expr="//sheet" position="inside"><field name="x_extra"/></xpath></data>'
        target = '<data/>'

        res = view_merge.plan_append(source, target, source_inherit=True, target_inherit=True)
        self.assertIsNone(res.error)
        self.assertEqual(len(res.added), 1)
        self.assertIn('<field name="x_extra"/>', res.new_arch)

    def test_primary_view_rejected(self):
        source = '<data><xpath expr="//sheet" position="inside"><field name="x_extra"/></xpath></data>'
        target = '<form><sheet><field name="name"/></sheet></form>'

        res = view_merge.plan_append(source, target, source_inherit=True, target_inherit=False)
        self.assertIsNotNone(res.error)
        self.assertIn('primary', res.error.lower())

    def test_invalid_xml_handling(self):
        source = '<data><xpath expr="//sheet"></data>'
        target = '<data><xpath expr="//sheet"/></data>'

        res = view_merge.plan_append(source, target, source_inherit=True, target_inherit=True)
        self.assertIsNotNone(res.error)
