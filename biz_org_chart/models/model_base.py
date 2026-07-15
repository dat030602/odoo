from lxml.builder import E

from odoo import models, api


class BaseModel(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _get_default_org_view(self):
        """ Generates a default org view, based on _rec_name.
        
        This method is automatically triggered each time the `_fields_view_get()` is called

        :returns: a org view as an lxml document
        :rtype: etree._Element
        """
        return E.org(string=self._description)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        """
        Override to return data for parent records too
        """
        if self._context.get('org_chart', False):
            records = self.search(domain or [], offset, limit, order)
            if records:
                domain = [('id', 'parent_of', records.ids)]
        return super(BaseModel, self).search_read(domain, fields, offset, limit, order, **read_kwargs)
