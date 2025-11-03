import logging
from .tiktok import Tiktok

_logger = logging.getLogger(__name__)


class Client:
    def __init__(self, connector):
        self.tiktok = Tiktok(connector)

    # Tiktok
    
    def get_authorized_category_assets(self, **kwargs):
        """Get authorized category assets from TikTok Shop"""
        return self.tiktok.get_authorized_category_assets(**kwargs)
    
    def get_authorized_shops(self, **kwargs):
        """Get authorized shops from TikTok Shop"""
        return self.tiktok.get_authorized_shops(**kwargs)
    
    # Order APIs
    def _order_get_order_list(self, **kwargs):
        """Get order list from TikTok Shop"""
        return self.tiktok._order_get_order_list(**kwargs)
    
    def _order_get_price_detail(self, **kwargs):
        """Get price detail from TikTok Shop"""
        return self.tiktok._order_get_price_detail(**kwargs)
    
    def _order_add_external_order_references(self, **kwargs):
        """Add external order references to TikTok Shop"""
        return self.tiktok._order_add_external_order_references(**kwargs)
    
    def _order_get_external_order_references(self, **kwargs):
        """Get external order references from TikTok Shop"""
        return self.tiktok._order_get_external_order_references(**kwargs)
    
    def _order_search_order_by_external_order_reference(self, **kwargs):
        """Search order by external order reference from TikTok Shop"""
        return self.tiktok._order_search_order_by_external_order_reference(**kwargs)
    
    def _order_get_order_detail(self, **kwargs):
        """Get order detail from TikTok Shop"""
        return self.tiktok._order_get_order_detail(**kwargs)