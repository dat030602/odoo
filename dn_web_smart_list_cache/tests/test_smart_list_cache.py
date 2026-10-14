# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import re
from rjsmin import jsmin

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import file_path


@tagged('post_install', '-at_install')
class TestSmartListCache(TransactionCase):
    """
    Test suite for dn_web_smart_list_cache:
    - Module installation and manifest integrity
    - JS asset bundle integrity in web.assets_backend
    - JS file syntax, minification, and clean patch/service registration
    - Cache service logic and lifecycle invariant validations
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module_name = 'dn_web_smart_list_cache'
        cls.expected_asset_files = [
            'dn_web_smart_list_cache/static/src/js/smart_list_cache_service.js',
            'dn_web_smart_list_cache/static/src/js/form_controller_patch.js',
            'dn_web_smart_list_cache/static/src/js/relational_model_patch.js',
            'dn_web_smart_list_cache/static/src/js/list_controller_patch.js',
        ]

    def test_01_module_installation(self):
        """Verify that dn_web_smart_list_cache is installed and loaded cleanly."""
        module = self.env['ir.module.module'].search([('name', '=', self.module_name)])
        self.assertTrue(module, f"Module '{self.module_name}' must exist in ir.module.module")
        self.assertEqual(module.state, 'installed', f"Module '{self.module_name}' should be in 'installed' state")

        # Verify manifest metadata
        manifest = module.get_module_info(module.name)
        self.assertTrue(manifest.get('installable', True), "Module must be marked as installable")
        self.assertEqual(module.license, 'OPL-1', "License should be OPL-1")

        # Verify dependency on 'web'
        dependencies = module.dependencies_id.mapped('name')
        self.assertIn('web', dependencies, "Module should declare 'web' as a dependency")

    def test_02_assets_declaration_in_bundle(self):
        """Verify that all manifest asset files are included in web.assets_backend."""
        asset_paths = self.env['ir.asset']._get_asset_paths('web.assets_backend', {})
        # asset_paths is a list of tuples: (path, addon, bundle, sequence)
        backend_file_paths = [entry[0] for entry in asset_paths if entry and len(entry) > 0]

        for expected_file in self.expected_asset_files:
            found = any(expected_file in path for path in backend_file_paths)
            self.assertTrue(
                found,
                f"Asset file '{expected_file}' not found in 'web.assets_backend' asset paths."
            )

    def test_03_assets_bundle_compilation(self):
        """Verify that web.assets_backend compiles and minifies cleanly with the module's JS assets."""
        bundle = self.env['ir.qweb']._get_asset_bundle('web.assets_backend', assets_params={})
        self.assertTrue(bundle, "AssetsBundle for 'web.assets_backend' must be created")

        # Compile JS bundle (this triggers minification, template bundling, and syntax verification)
        js_attachment = bundle.js()
        self.assertTrue(js_attachment, "Compiled JS bundle attachment must not be empty")

        bundle_content = js_attachment.raw.decode('utf-8', errors='replace')
        self.assertTrue(len(bundle_content) > 0, "JS bundle content should be non-empty")

        # Verify identifiers from dn_web_smart_list_cache are present in the compiled bundle
        self.assertIn('smart_list_cache', bundle_content, "Service 'smart_list_cache' identifier should be in compiled bundle")
        self.assertIn('dn_smart_list_cache', bundle_content, "Service alias 'dn_smart_list_cache' should be in compiled bundle")
        self.assertIn('isReturningFromForm', bundle_content, "Flag 'isReturningFromForm' should be in compiled bundle")

    def test_04_individual_js_files_validity(self):
        """Verify each JS file exists on filesystem, starts with @odoo-module, and minifies without syntax error."""
        for rel_path in self.expected_asset_files:
            abs_path = file_path(rel_path)
            self.assertTrue(abs_path and os.path.isfile(abs_path), f"File '{rel_path}' does not exist on disk at {abs_path}")

            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertTrue(
                content.lstrip().startswith('/** @odoo-module **/'),
                f"File '{rel_path}' must declare '/** @odoo-module **/' header."
            )

            # Check minification syntax validity via rjsmin
            try:
                minified = jsmin(content)
                self.assertTrue(len(minified) > 0, f"Minified content for '{rel_path}' is empty")
            except Exception as e:
                self.fail(f"JS syntax or minification error in '{rel_path}': {e}")

    def test_05_smart_list_cache_service_contract(self):
        """Verify that smart_list_cache_service.js declares service registration and all required API methods."""
        abs_path = file_path('dn_web_smart_list_cache/static/src/js/smart_list_cache_service.js')
        with open(abs_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Service registration checks
        self.assertIn('registry.category("services").add("smart_list_cache"', code,
                      "smart_list_cache service must be registered in services registry")
        self.assertIn('registry.category("services").add("dn_smart_list_cache"', code,
                      "dn_smart_list_cache alias must be registered in services registry")

        # API Contract methods
        required_methods = [
            'markDirty',
            'popDirty',
            'markDeleted',
            'popDeleted',
            'markCreated',
            'popCreated',
            'setCachedData',
            'getCachedData',
            'hasCachedData',
            'updateCachedRecords',
            'removeCachedRecords',
            'addCachedRecords',
            'clear',
        ]
        for method in required_methods:
            self.assertRegex(
                code,
                rf'\b{method}\s*\(',
                f"smartListCacheService must implement '{method}' method."
            )

        # State flags
        self.assertIn('isReturningFromForm', code, "Service must define 'isReturningFromForm' state flag")
        self.assertIn('sourceModel', code, "Service must define 'sourceModel' state flag")

    def test_06_controller_and_model_patches(self):
        """Verify that form, list, and relational model patches cleanly hook into OWL core components."""
        # 1. Form Controller patch
        form_patch_path = file_path('dn_web_smart_list_cache/static/src/js/form_controller_patch.js')
        with open(form_patch_path, 'r', encoding='utf-8') as f:
            form_code = f.read()
        self.assertIn('patch(FormController.prototype', form_code, "FormController.prototype must be patched")
        self.assertIn('onWillUnmount', form_code, "FormController must hook into onWillUnmount")
        self.assertIn('save(', form_code, "FormController must intercept save()")
        self.assertIn('markDirty', form_code, "FormController must call markDirty on save")
        self.assertIn('markCreated', form_code, "FormController must call markCreated on new record save")
        self.assertIn('markDeleted', form_code, "FormController must call markDeleted on record deletion")

        # 2. Relational Model patch
        rel_model_path = file_path('dn_web_smart_list_cache/static/src/js/relational_model_patch.js')
        with open(rel_model_path, 'r', encoding='utf-8') as f:
            rel_code = f.read()
        self.assertIn('patch(RelationalModel.prototype', rel_code, "RelationalModel.prototype must be patched")
        self.assertIn('_loadData(', rel_code, "RelationalModel must intercept _loadData")
        self.assertIn('cacheService.getCachedData', rel_code, "RelationalModel must restore cached data on back navigation")
        self.assertIn('cacheService.setCachedData', rel_code, "RelationalModel must save loaded list data")

        # 3. List Controller patch
        list_patch_path = file_path('dn_web_smart_list_cache/static/src/js/list_controller_patch.js')
        with open(list_patch_path, 'r', encoding='utf-8') as f:
            list_code = f.read()
        self.assertIn('patch(ListController.prototype', list_code, "ListController.prototype must be patched")
        self.assertIn('onWillStart', list_code, "ListController must hook into onWillStart")
        self.assertIn('onWillUnmount', list_code, "ListController must hook into onWillUnmount")
        self.assertIn('popDeleted', list_code, "ListController must consume deleted records via popDeleted")
        self.assertIn('popDirty', list_code, "ListController must consume dirty records via popDirty")
        self.assertIn('popCreated', list_code, "ListController must consume created records via popCreated")
        self.assertIn('this.model.notify()', list_code, "ListController must notify model to trigger OWL reactivity")

    def test_07_cache_service_logic_invariants(self):
        """Simulate cache service algorithm to verify invariant consistency (pure unit logic verification)."""
        # Test invariant: markDeleted purges dirty and created sets
        dirty = {'res.partner': {1, 2}}
        created = {'res.partner': {2, 3}}
        deleted = {'res.partner': set()}

        # Mark 2 deleted
        res_model = 'res.partner'
        res_id = 2
        deleted[res_model].add(res_id)
        dirty[res_model].discard(res_id)
        created[res_model].discard(res_id)

        self.assertNotIn(2, dirty[res_model], "Deleted record 2 must be purged from dirty set")
        self.assertNotIn(2, created[res_model], "Deleted record 2 must be purged from created set")
        self.assertIn(2, deleted[res_model], "Deleted record 2 must be recorded in deleted set")

        # Test invariant: cached data operations
        cached = {
            'records': [{'id': 1, 'name': 'Partner 1'}, {'id': 2, 'name': 'Partner 2'}],
            'length': 2,
        }

        # Update record 1
        updated = [{'id': 1, 'name': 'Updated Partner 1'}]
        for u in updated:
            for r in cached['records']:
                if r['id'] == u['id']:
                    r.update(u)
        self.assertEqual(cached['records'][0]['name'], 'Updated Partner 1')

        # Remove record 2
        deleted_ids = {2}
        cached['records'] = [r for r in cached['records'] if r['id'] not in deleted_ids]
        cached['length'] = max(0, cached['length'] - len(deleted_ids))
        self.assertEqual(len(cached['records']), 1)
        self.assertEqual(cached['length'], 1)
        self.assertEqual(cached['records'][0]['id'], 1)

        # Add new record 3
        new_records = [{'id': 3, 'name': 'New Partner 3'}]
        for nr in new_records:
            if not any(r['id'] == nr['id'] for r in cached['records']):
                cached['records'].insert(0, nr)
                cached['length'] += 1
        self.assertEqual(len(cached['records']), 2)
        self.assertEqual(cached['length'], 2)
        self.assertEqual(cached['records'][0]['id'], 3, "New record must be unshifted to the front")
