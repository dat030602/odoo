from odoo import http
from odoo.http import request


class MetaMigratorGuideController(http.Controller):

    @http.route('/meta_migrator/guide', type='http', auth='public', website=False)
    def user_guide(self, **kwargs):
        """Render the standalone user guide documentation page."""
        return request.render('meta_migrator.user_guide_page', {})
