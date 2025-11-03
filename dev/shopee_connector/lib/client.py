import logging
from .shopee import Shopee

_logger = logging.getLogger(__name__)


class Client:
    def __init__(self, connector):
        self.shopee = Shopee(connector)

    # Shopee
    ## Product
    # https://open.shopee.com/documents/v2/v2.product.get_item_list?module=89&type=1
    def product_get_item_list(self, **kwargs):
        return self.shopee.product_get_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_item_base_info?module=89&type=1
    def product_get_item_base_info(self, **kwargs):
        return self.shopee.product_get_item_base_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_category?module=89&type=1
    def product_get_category(self, **kwargs):
        return self.shopee.product_get_category(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_attribute_tree?module=89&type=1
    def product_get_attribute_tree(self, **kwargs):
        return self.shopee.product_get_attribute_tree(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_brand_list?module=89&type=1
    def product_get_brand_list(self, **kwargs):
        return self.shopee.product_get_brand_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_item_limit?module=89&type=1
    def product_get_item_limit(self, **kwargs):
        return self.shopee.product_get_item_limit(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_item_extra_info?module=89&type=1
    def product_get_item_extra_info(self, **kwargs):
        return self.shopee.product_get_item_extra_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.add_item?module=89&type=1
    def product_add_item(self, **kwargs):
        return self.shopee.product_add_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.update_item?module=89&type=1
    def product_update_item(self, **kwargs):
        return self.shopee.product_update_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.delete_item?module=89&type=1
    def product_delete_item(self, **kwargs):
        return self.shopee.product_delete_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.init_tier_variation?module=89&type=1
    def product_init_tier_variation(self, **kwargs):
        return self.shopee.product_init_tier_variation(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.update_tier_variation?module=89&type=1
    def product_update_tier_variation(self, **kwargs):
        return self.shopee.product_update_tier_variation(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_model_list?module=89&type=1
    def product_get_model_list(self, **kwargs):
        return self.shopee.product_get_model_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.add_model?module=89&type=1
    def product_add_model(self, **kwargs):
        return self.shopee.product_add_model(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.update_model?module=89&type=1
    def product_update_model(self, **kwargs):
        return self.shopee.product_update_model(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.delete_model?module=89&type=1
    def product_delete_model(self, **kwargs):
        return self.shopee.product_delete_model(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.unlist_item?module=89&type=1
    def product_unlist_item(self, **kwargs):
        return self.shopee.product_unlist_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.update_price?module=89&type=1
    def product_update_price(self, **kwargs):
        return self.shopee.product_update_price(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.update_stock?module=89&type=1
    def product_update_stock(self, **kwargs):
        return self.shopee.product_update_stock(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.boost_item?module=89&type=1
    def product_boost_item(self, **kwargs):
        return self.shopee.product_boost_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_boosted_list?module=89&type=1
    def product_get_boosted_list(self, **kwargs):
        return self.shopee.product_get_boosted_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_item_promotion?module=89&type=1
    def product_get_item_promotion(self, **kwargs):
        return self.shopee.product_get_item_promotion(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.update_sip_item_price?module=89&type=1
    def product_update_sip_item_price(self, **kwargs):
        return self.shopee.product_update_sip_item_price(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.search_item?module=89&type=1
    def product_search_item(self, **kwargs):
        return self.shopee.product_search_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_comment?module=89&type=1
    def product_get_comment(self, **kwargs):
        return self.shopee.product_get_comment(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.reply_comment?module=89&type=1
    def product_reply_comment(self, **kwargs):
        return self.shopee.product_reply_comment(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.category_recommend?module=89&type=1
    def product_category_recommend(self, **kwargs):
        return self.shopee.product_category_recommend(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.register_brand?module=89&type=1
    def product_register_brand(self, **kwargs):
        return self.shopee.product_register_brand(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_recommend_attribute?module=89&type=1
    def product_get_recommend_attribute(self, **kwargs):
        return self.shopee.product_get_recommend_attribute(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_weight_recommendation?module=89&type=1
    def product_get_weight_recommendation(self, **kwargs):
        return self.shopee.product_get_weight_recommendation(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_size_chart_list?module=89&type=1
    def product_get_size_chart_list(self, **kwargs):
        return self.shopee.product_get_size_chart_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_size_chart_detail?module=89&type=1
    def product_get_size_chart_detail(self, **kwargs):
        return self.shopee.product_get_size_chart_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_item_violation_info?module=89&type=1
    def product_get_item_violation_info(self, **kwargs):
        return self.shopee.product_get_item_violation_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_variations?module=89&type=1
    def product_get_variations(self, **kwargs):
        return self.shopee.product_get_variations(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_all_vehicle_list?module=89&type=1
    def product_get_all_vehicle_list(self, **kwargs):
        return self.shopee.product_get_all_vehicle_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_vehicle_list_by_compatibility_detail?module=89&type=1
    def product_get_vehicle_list_by_compatibility_detail(self, **kwargs):
        return self.shopee.product_get_vehicle_list_by_compatibility_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_item_content_diagnosis_result?module=89&type=1
    def product_get_item_content_diagnosis_result(self, **kwargs):
        return self.shopee.product_get_item_content_diagnosis_result(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_item_list_by_content_diagnosis?module=89&type=1
    def product_get_item_list_by_content_diagnosis(self, **kwargs):
        return self.shopee.product_get_item_list_by_content_diagnosis(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_kit_item_limit?module=89&type=1
    def product_get_kit_item_limit(self, **kwargs):
        return self.shopee.product_get_kit_item_limit(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.add_kit_item?module=89&type=1
    def product_add_kit_item(self, **kwargs):
        return self.shopee.product_add_kit_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.update_kit_item?module=89&type=1
    def product_update_kit_item(self, **kwargs):
        return self.shopee.product_update_kit_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_kit_item_info?module=89&type=1
    def product_get_kit_item_info(self, **kwargs):
        return self.shopee.product_get_kit_item_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_ssp_list?module=89&type=1
    def product_get_ssp_list(self, **kwargs):
        return self.shopee.product_get_ssp_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_ssp_info?module=89&type=1
    def product_get_ssp_info(self, **kwargs):
        return self.shopee.product_get_ssp_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.add_ssp_item?module=89&type=1
    def product_add_ssp_item(self, **kwargs):
        return self.shopee.product_add_ssp_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.link_ssp?module=89&type=1
    def product_link_ssp(self, **kwargs):
        return self.shopee.product_link_ssp(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.unlink_ssp?module=89&type=1
    def product_unlink_ssp(self, **kwargs):
        return self.shopee.product_unlink_ssp(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_aitem_by_pitem_id?module=89&type=1
    def product_get_aitem_by_pitem_id(self, **kwargs):
        return self.shopee.product_get_aitem_by_pitem_id(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.search_attribute_value_list?module=89&type=1
    def product_search_attribute_value_list(self, **kwargs):
        return self.shopee.product_search_attribute_value_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_main_item_list?module=89&type=1
    def product_get_main_item_list(self, **kwargs):
        return self.shopee.product_get_main_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_direct_item_list?module=89&type=1
    def product_get_direct_item_list(self, **kwargs):
        return self.shopee.product_get_direct_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_direct_shop_recommended_price?module=89&type=1
    def product_get_direct_shop_recommended_price(self, **kwargs):
        return self.shopee.product_get_direct_shop_recommended_price(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.get_product_certification_rule?module=89&type=1
    def product_get_product_certification_rule(self, **kwargs):
        return self.shopee.product_get_product_certification_rule(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.product.search_unpackaged_model_list?module=89&type=1
    def product_search_unpackaged_model_list(self, **kwargs):
        return self.shopee.product_search_unpackaged_model_list(**kwargs)
    
    ## Global Product APIs
    # https://open.shopee.com/documents/v2/v2.global_product.get_category?module=90&type=1
    def global_product_get_category(self, **kwargs):
        return self.shopee.global_product_get_category(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_attribute_tree?module=90&type=1
    def global_product_get_attribute_tree(self, **kwargs):
        return self.shopee.global_product_get_attribute_tree(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_brand_list?module=90&type=1
    def global_product_get_brand_list(self, **kwargs):
        return self.shopee.global_product_get_brand_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_global_item_limit?module=90&type=1
    def global_product_get_global_item_limit(self, **kwargs):
        return self.shopee.global_product_get_global_item_limit(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_global_item_list?module=90&type=1
    def global_product_get_global_item_list(self, **kwargs):
        return self.shopee.global_product_get_global_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_global_item_info?module=90&type=1
    def global_product_get_global_item_info(self, **kwargs):
        return self.shopee.global_product_get_global_item_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.add_global_item?module=90&type=1
    def global_product_add_global_item(self, **kwargs):
        return self.shopee.global_product_add_global_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.update_global_item?module=90&type=1
    def global_product_update_global_item(self, **kwargs):
        return self.shopee.global_product_update_global_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.delete_global_item?module=90&type=1
    def global_product_delete_global_item(self, **kwargs):
        return self.shopee.global_product_delete_global_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.init_tier_variation?module=90&type=1
    def global_product_init_tier_variation(self, **kwargs):
        return self.shopee.global_product_init_tier_variation(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.update_tier_variation?module=90&type=1
    def global_product_update_tier_variation(self, **kwargs):
        return self.shopee.global_product_update_tier_variation(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.add_global_model?module=90&type=1
    def global_product_add_global_model(self, **kwargs):
        return self.shopee.global_product_add_global_model(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.update_global_model?module=90&type=1
    def global_product_update_global_model(self, **kwargs):
        return self.shopee.global_product_update_global_model(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.delete_global_model?module=90&type=1
    def global_product_delete_global_model(self, **kwargs):
        return self.shopee.global_product_delete_global_model(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_global_model_list?module=90&type=1
    def global_product_get_global_model_list(self, **kwargs):
        return self.shopee.global_product_get_global_model_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.support_size_chart?module=90&type=1
    def global_product_support_size_chart(self, **kwargs):
        return self.shopee.global_product_support_size_chart(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.update_size_chart?module=90&type=1
    def global_product_update_size_chart(self, **kwargs):
        return self.shopee.global_product_update_size_chart(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.create_publish_task?module=90&type=1
    def global_product_create_publish_task(self, **kwargs):
        return self.shopee.global_product_create_publish_task(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_publishable_shop?module=90&type=1
    def global_product_get_publishable_shop(self, **kwargs):
        return self.shopee.global_product_get_publishable_shop(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_publish_task_result?module=90&type=1
    def global_product_get_publish_task_result(self, **kwargs):
        return self.shopee.global_product_get_publish_task_result(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_published_list?module=90&type=1
    def global_product_get_published_list(self, **kwargs):
        return self.shopee.global_product_get_published_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.update_price?module=90&type=1
    def global_product_update_price(self, **kwargs):
        return self.shopee.global_product_update_price(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.update_stock?module=90&type=1
    def global_product_update_stock(self, **kwargs):
        return self.shopee.global_product_update_stock(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.set_sync_field?module=90&type=1
    def global_product_set_sync_field(self, **kwargs):
        return self.shopee.global_product_set_sync_field(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_global_item_id?module=90&type=1
    def global_product_get_global_item_id(self, **kwargs):
        return self.shopee.global_product_get_global_item_id(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.category_recommend?module=90&type=1
    def global_product_category_recommend(self, **kwargs):
        return self.shopee.global_product_category_recommend(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_recommend_attribute?module=90&type=1
    def global_product_get_recommend_attribute(self, **kwargs):
        return self.shopee.global_product_get_recommend_attribute(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_shop_publishable_status?module=90&type=1
    def global_product_get_shop_publishable_status(self, **kwargs):
        return self.shopee.global_product_get_shop_publishable_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_variations?module=90&type=1
    def global_product_get_variations(self, **kwargs):
        return self.shopee.global_product_get_variations(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_size_chart_detail?module=90&type=1
    def global_product_get_size_chart_detail(self, **kwargs):
        return self.shopee.global_product_get_size_chart_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_size_chart_list?module=90&type=1
    def global_product_get_size_chart_list(self, **kwargs):
        return self.shopee.global_product_get_size_chart_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.search_global_attribute_value_list?module=90&type=1
    def global_product_search_global_attribute_value_list(self, **kwargs):
        return self.shopee.global_product_search_global_attribute_value_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.get_local_adjustment_rate?module=90&type=1
    def global_product_get_local_adjustment_rate(self, **kwargs):
        return self.shopee.global_product_get_local_adjustment_rate(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.global_product.update_local_adjustment_rate?module=90&type=1
    def global_product_update_local_adjustment_rate(self, **kwargs):
        return self.shopee.global_product_update_local_adjustment_rate(**kwargs)
    
    ## Media Space APIs
    # https://open.shopee.com/documents/v2/v2.media_space.init_video_upload?module=91&type=1
    def media_space_init_video_upload(self, **kwargs):
        return self.shopee.media_space_init_video_upload(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.media_space.upload_video_part?module=91&type=1
    def media_space_upload_video_part(self, **kwargs):
        return self.shopee.media_space_upload_video_part(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.media_space.complete_video_upload?module=91&type=1
    def media_space_complete_video_upload(self, **kwargs):
        return self.shopee.media_space_complete_video_upload(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.media_space.get_video_upload_result?module=91&type=1
    def media_space_get_video_upload_result(self, **kwargs):
        return self.shopee.media_space_get_video_upload_result(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.media_space.cancel_video_upload?module=91&type=1
    def media_space_cancel_video_upload(self, **kwargs):
        return self.shopee.media_space_cancel_video_upload(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.media_space.upload_image?module=91&type=1
    def media_space_upload_image(self, **kwargs):
        return self.shopee.media_space_upload_image(**kwargs)
    
    ## Media APIs
    # https://open.shopee.com/documents/v2/v2.media.upload_image?module=130&type=1
    def media_upload_image(self, **kwargs):
        return self.shopee.media_upload_image(**kwargs)
    
    ## Shop APIs
    # https://open.shopee.com/documents/v2/v2.shop.get_shop_info?module=92&type=1
    def shop_get_shop_info(self, **kwargs):
        return self.shopee.shop_get_shop_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop.get_profile?module=92&type=1
    def shop_get_profile(self, **kwargs):
        return self.shopee.shop_get_profile(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop.update_profile?module=92&type=1
    def shop_update_profile(self, **kwargs):
        return self.shopee.shop_update_profile(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop.get_warehouse_detail?module=92&type=1
    def shop_get_warehouse_detail(self, **kwargs):
        return self.shopee.shop_get_warehouse_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop.get_shop_notification?module=92&type=1
    def shop_get_shop_notification(self, **kwargs):
        return self.shopee.shop_get_shop_notification(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop.get_authorised_reseller_brand?module=92&type=1
    def shop_get_authorised_reseller_brand(self, **kwargs):
        return self.shopee.shop_get_authorised_reseller_brand(**kwargs)
    
    ## Merchant APIs
    # https://open.shopee.com/documents/v2/v2.merchant.get_merchant_info?module=93&type=1
    def merchant_get_merchant_info(self, **kwargs):
        return self.shopee.merchant_get_merchant_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.merchant.get_shop_list_by_merchant?module=93&type=1
    def merchant_get_shop_list_by_merchant(self, **kwargs):
        return self.shopee.merchant_get_shop_list_by_merchant(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.merchant.get_merchant_warehouse_location_list?module=93&type=1
    def merchant_get_merchant_warehouse_location_list(self, **kwargs):
        return self.shopee.merchant_get_merchant_warehouse_location_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.merchant.get_merchant_warehouse_list?module=93&type=1
    def merchant_get_merchant_warehouse_list(self, **kwargs):
        return self.shopee.merchant_get_merchant_warehouse_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.merchant.get_warehouse_eligible_shop_list?module=93&type=1
    def merchant_get_warehouse_eligible_shop_list(self, **kwargs):
        return self.shopee.merchant_get_warehouse_eligible_shop_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.merchant.get_merchant_prepaid_account_list?module=93&type=1
    def merchant_get_merchant_prepaid_account_list(self, **kwargs):
        return self.shopee.merchant_get_merchant_prepaid_account_list(**kwargs)
    
    ## Order APIs
    # https://open.shopee.com/documents/v2/v2.order.get_order_list?module=94&type=1
    def order_get_order_list(self, **kwargs):
        return self.shopee.order_get_order_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_order_detail?module=94&type=1
    def order_get_order_detail(self, **kwargs):
        return self.shopee.order_get_order_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_shipment_list?module=94&type=1
    def order_get_shipment_list(self, **kwargs):
        return self.shopee.order_get_shipment_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.search_package_list?module=94&type=1
    def order_search_package_list(self, **kwargs):
        return self.shopee.order_search_package_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_package_detail?module=94&type=1
    def order_get_package_detail(self, **kwargs):
        return self.shopee.order_get_package_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.split_order?module=94&type=1
    def order_split_order(self, **kwargs):
        return self.shopee.order_split_order(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.unsplit_order?module=94&type=1
    def order_unsplit_order(self, **kwargs):
        return self.shopee.order_unsplit_order(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.cancel_order?module=94&type=1
    def order_cancel_order(self, **kwargs):
        return self.shopee.order_cancel_order(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.handle_buyer_cancellation?module=94&type=1
    def order_handle_buyer_cancellation(self, **kwargs):
        return self.shopee.order_handle_buyer_cancellation(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.set_note?module=94&type=1
    def order_set_note(self, **kwargs):
        return self.shopee.order_set_note(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_pending_buyer_invoice_order_list?module=94&type=1
    def order_get_pending_buyer_invoice_order_list(self, **kwargs):
        return self.shopee.order_get_pending_buyer_invoice_order_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_buyer_invoice_info?module=94&type=1
    def order_get_buyer_invoice_info(self, **kwargs):
        return self.shopee.order_get_buyer_invoice_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.upload_invoice_doc?module=94&type=1
    def order_upload_invoice_doc(self, **kwargs):
        return self.shopee.order_upload_invoice_doc(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.download_invoice_doc?module=94&type=1
    def order_download_invoice_doc(self, **kwargs):
        return self.shopee.order_download_invoice_doc(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.handle_prescription_check?module=94&type=1
    def order_handle_prescription_check(self, **kwargs):
        return self.shopee.order_handle_prescription_check(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_warehouse_filter_config?module=94&type=1
    def order_get_warehouse_filter_config(self, **kwargs):
        return self.shopee.order_get_warehouse_filter_config(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_booking_list?module=94&type=1
    def order_get_booking_list(self, **kwargs):
        return self.shopee.order_get_booking_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_booking_detail?module=94&type=1
    def order_get_booking_detail(self, **kwargs):
        return self.shopee.order_get_booking_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.generate_fbs_invoices?module=94&type=1
    def order_generate_fbs_invoices(self, **kwargs):
        return self.shopee.order_generate_fbs_invoices(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.get_fbs_invoices_result?module=94&type=1
    def order_get_fbs_invoices_result(self, **kwargs):
        return self.shopee.order_get_fbs_invoices_result(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.order.download_fbs_invoices?module=94&type=1
    def order_download_fbs_invoices(self, **kwargs):
        return self.shopee.order_download_fbs_invoices(**kwargs)
    
    ## Logistics APIs
    # https://open.shopee.com/documents/v2/v2.logistics.get_shipping_parameter?module=95&type=1
    def logistics_get_shipping_parameter(self, **kwargs):
        return self.shopee.logistics_get_shipping_parameter(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_mass_shipping_parameter?module=95&type=1
    def logistics_get_mass_shipping_parameter(self, **kwargs):
        return self.shopee.logistics_get_mass_shipping_parameter(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.ship_order?module=95&type=1
    def logistics_ship_order(self, **kwargs):
        return self.shopee.logistics_ship_order(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.mass_ship_order?module=95&type=1
    def logistics_mass_ship_order(self, **kwargs):
        return self.shopee.logistics_mass_ship_order(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.update_shipping_order?module=95&type=1
    def logistics_update_shipping_order(self, **kwargs):
        return self.shopee.logistics_update_shipping_order(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_tracking_number?module=95&type=1
    def logistics_get_tracking_number(self, **kwargs):
        return self.shopee.logistics_get_tracking_number(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_mass_tracking_number?module=95&type=1
    def logistics_get_mass_tracking_number(self, **kwargs):
        return self.shopee.logistics_get_mass_tracking_number(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_shipping_document_parameter?module=95&type=1
    def logistics_get_shipping_document_parameter(self, **kwargs):
        return self.shopee.logistics_get_shipping_document_parameter(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.create_shipping_document?module=95&type=1
    def logistics_create_shipping_document(self, **kwargs):
        return self.shopee.logistics_create_shipping_document(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_shipping_document_result?module=95&type=1
    def logistics_get_shipping_document_result(self, **kwargs):
        return self.shopee.logistics_get_shipping_document_result(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.download_shipping_document?module=95&type=1
    def logistics_download_shipping_document(self, **kwargs):
        return self.shopee.logistics_download_shipping_document(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_shipping_document_data_info?module=95&type=1
    def logistics_get_shipping_document_data_info(self, **kwargs):
        return self.shopee.logistics_get_shipping_document_data_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_tracking_info?module=95&type=1
    def logistics_get_tracking_info(self, **kwargs):
        return self.shopee.logistics_get_tracking_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_address_list?module=95&type=1
    def logistics_get_address_list(self, **kwargs):
        return self.shopee.logistics_get_address_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.set_address_config?module=95&type=1
    def logistics_set_address_config(self, **kwargs):
        return self.shopee.logistics_set_address_config(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.delete_address?module=95&type=1
    def logistics_delete_address(self, **kwargs):
        return self.shopee.logistics_delete_address(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_channel_list?module=95&type=1
    def logistics_get_channel_list(self, **kwargs):
        return self.shopee.logistics_get_channel_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.update_channel?module=95&type=1
    def logistics_update_channel(self, **kwargs):
        return self.shopee.logistics_update_channel(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_operating_hours?module=95&type=1
    def logistics_get_operating_hours(self, **kwargs):
        return self.shopee.logistics_get_operating_hours(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_operating_hour_restrictions?module=95&type=1
    def logistics_get_operating_hour_restrictions(self, **kwargs):
        return self.shopee.logistics_get_operating_hour_restrictions(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.update_operating_hours?module=95&type=1
    def logistics_update_operating_hours(self, **kwargs):
        return self.shopee.logistics_update_operating_hours(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.delete_special_operating_hour?module=95&type=1
    def logistics_delete_special_operating_hour(self, **kwargs):
        return self.shopee.logistics_delete_special_operating_hour(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.batch_update_tpf_warehouse_tracking_status?module=95&type=1
    def logistics_batch_update_tpf_warehouse_tracking_status(self, **kwargs):
        return self.shopee.logistics_batch_update_tpf_warehouse_tracking_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.batch_ship_order?module=95&type=1
    def logistics_batch_ship_order(self, **kwargs):
        return self.shopee.logistics_batch_ship_order(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.update_tracking_status?module=95&type=1
    def logistics_update_tracking_status(self, **kwargs):
        return self.shopee.logistics_update_tracking_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_booking_shipping_parameter?module=95&type=1
    def logistics_get_booking_shipping_parameter(self, **kwargs):
        return self.shopee.logistics_get_booking_shipping_parameter(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.ship_booking?module=95&type=1
    def logistics_ship_booking(self, **kwargs):
        return self.shopee.logistics_ship_booking(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_booking_tracking_number?module=95&type=1
    def logistics_get_booking_tracking_number(self, **kwargs):
        return self.shopee.logistics_get_booking_tracking_number(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_booking_shipping_document_parameter?module=95&type=1
    def logistics_get_booking_shipping_document_parameter(self, **kwargs):
        return self.shopee.logistics_get_booking_shipping_document_parameter(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.create_booking_shipping_document?module=95&type=1
    def logistics_create_booking_shipping_document(self, **kwargs):
        return self.shopee.logistics_create_booking_shipping_document(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_booking_shipping_document_result?module=95&type=1
    def logistics_get_booking_shipping_document_result(self, **kwargs):
        return self.shopee.logistics_get_booking_shipping_document_result(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.download_booking_shipping_document?module=95&type=1
    def logistics_download_booking_shipping_document(self, **kwargs):
        return self.shopee.logistics_download_booking_shipping_document(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_booking_shipping_document_data_info?module=95&type=1
    def logistics_get_booking_shipping_document_data_info(self, **kwargs):
        return self.shopee.logistics_get_booking_shipping_document_data_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_booking_tracking_info?module=95&type=1
    def logistics_get_booking_tracking_info(self, **kwargs):
        return self.shopee.logistics_get_booking_tracking_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.download_to_label?module=95&type=1
    def logistics_download_to_label(self, **kwargs):
        return self.shopee.logistics_download_to_label(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.create_shipping_document_job?module=95&type=1
    def logistics_create_shipping_document_job(self, **kwargs):
        return self.shopee.logistics_create_shipping_document_job(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.get_shipping_document_job_status?module=95&type=1
    def logistics_get_shipping_document_job_status(self, **kwargs):
        return self.shopee.logistics_get_shipping_document_job_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.download_shipping_document_job?module=95&type=1
    def logistics_download_shipping_document_job(self, **kwargs):
        return self.shopee.logistics_download_shipping_document_job(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.logistics.update_self_collection_order_logistics?module=95&type=1
    def logistics_update_self_collection_order_logistics(self, **kwargs):
        return self.shopee.logistics_update_self_collection_order_logistics(**kwargs)
    
    ## First Mile APIs
    # https://open.shopee.com/documents/v2/v2.first_mile.get_unbind_order_list?module=96&type=1
    def first_mile_get_unbind_order_list(self, **kwargs):
        return self.shopee.first_mile_get_unbind_order_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_detail?module=96&type=1
    def first_mile_get_detail(self, **kwargs):
        return self.shopee.first_mile_get_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.generate_first_mile_tracking_number?module=96&type=1
    def first_mile_generate_first_mile_tracking_number(self, **kwargs):
        return self.shopee.first_mile_generate_first_mile_tracking_number(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.bind_first_mile_tracking_number?module=96&type=1
    def first_mile_bind_first_mile_tracking_number(self, **kwargs):
        return self.shopee.first_mile_bind_first_mile_tracking_number(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.unbind_first_mile_tracking_number?module=96&type=1
    def first_mile_unbind_first_mile_tracking_number(self, **kwargs):
        return self.shopee.first_mile_unbind_first_mile_tracking_number(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_tracking_number_list?module=96&type=1
    def first_mile_get_tracking_number_list(self, **kwargs):
        return self.shopee.first_mile_get_tracking_number_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_waybill?module=96&type=1
    def first_mile_get_waybill(self, **kwargs):
        return self.shopee.first_mile_get_waybill(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_channel_list?module=96&type=1
    def first_mile_get_channel_list(self, **kwargs):
        return self.shopee.first_mile_get_channel_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_courier_delivery_channel_list?module=96&type=1
    def first_mile_get_courier_delivery_channel_list(self, **kwargs):
        return self.shopee.first_mile_get_courier_delivery_channel_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_transit_warehouse_list?module=96&type=1
    def first_mile_get_transit_warehouse_list(self, **kwargs):
        return self.shopee.first_mile_get_transit_warehouse_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.generate_and_bind_first_mile_tracking_number?module=96&type=1
    def first_mile_generate_and_bind_first_mile_tracking_number(self, **kwargs):
        return self.shopee.first_mile_generate_and_bind_first_mile_tracking_number(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.bind_courier_delivery_first_mile_tracking_number?module=96&type=1
    def first_mile_bind_courier_delivery_first_mile_tracking_number(self, **kwargs):
        return self.shopee.first_mile_bind_courier_delivery_first_mile_tracking_number(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.unbind_first_mile_tracking_number_all?module=96&type=1
    def first_mile_unbind_first_mile_tracking_number_all(self, **kwargs):
        return self.shopee.first_mile_unbind_first_mile_tracking_number_all(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_courier_delivery_detail?module=96&type=1
    def first_mile_get_courier_delivery_detail(self, **kwargs):
        return self.shopee.first_mile_get_courier_delivery_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_courier_delivery_waybill?module=96&type=1
    def first_mile_get_courier_delivery_waybill(self, **kwargs):
        return self.shopee.first_mile_get_courier_delivery_waybill(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.first_mile.get_courier_delivery_tracking_number_list?module=96&type=1
    def first_mile_get_courier_delivery_tracking_number_list(self, **kwargs):
        return self.shopee.first_mile_get_courier_delivery_tracking_number_list(**kwargs)
    
    ## Payment APIs
    # https://open.shopee.com/documents/v2/v2.payment.get_escrow_detail?module=97&type=1
    def payment_get_escrow_detail(self, **kwargs):
        return self.shopee.payment_get_escrow_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.set_shop_installment_status?module=97&type=1
    def payment_set_shop_installment_status(self, **kwargs):
        return self.shopee.payment_set_shop_installment_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_shop_installment_status?module=97&type=1
    def payment_get_shop_installment_status(self, **kwargs):
        return self.shopee.payment_get_shop_installment_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_payout_detail?module=97&type=1
    def payment_get_payout_detail(self, **kwargs):
        return self.shopee.payment_get_payout_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.set_item_installment_status?module=97&type=1
    def payment_set_item_installment_status(self, **kwargs):
        return self.shopee.payment_set_item_installment_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_item_installment_status?module=97&type=1
    def payment_get_item_installment_status(self, **kwargs):
        return self.shopee.payment_get_item_installment_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_payment_method_list?module=97&type=1
    def payment_get_payment_method_list(self, **kwargs):
        return self.shopee.payment_get_payment_method_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_wallet_transaction_list?module=97&type=1
    def payment_get_wallet_transaction_list(self, **kwargs):
        return self.shopee.payment_get_wallet_transaction_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_escrow_list?module=97&type=1
    def payment_get_escrow_list(self, **kwargs):
        return self.shopee.payment_get_escrow_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_payout_info?module=97&type=1
    def payment_get_payout_info(self, **kwargs):
        return self.shopee.payment_get_payout_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_billing_transaction_info?module=97&type=1
    def payment_get_billing_transaction_info(self, **kwargs):
        return self.shopee.payment_get_billing_transaction_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_escrow_detail_batch?module=97&type=1
    def payment_get_escrow_detail_batch(self, **kwargs):
        return self.shopee.payment_get_escrow_detail_batch(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.generate_income_statement?module=97&type=1
    def payment_generate_income_statement(self, **kwargs):
        return self.shopee.payment_generate_income_statement(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_income_statement?module=97&type=1
    def payment_get_income_statement(self, **kwargs):
        return self.shopee.payment_get_income_statement(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.generate_income_report?module=97&type=1
    def payment_generate_income_report(self, **kwargs):
        return self.shopee.payment_generate_income_report(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.payment.get_income_report?module=97&type=1
    def payment_get_income_report(self, **kwargs):
        return self.shopee.payment_get_income_report(**kwargs)
    
    ## Discount APIs
    # https://open.shopee.com/documents/v2/v2.discount.add_discount?module=99&type=1
    def discount_add_discount(self, **kwargs):
        return self.shopee.discount_add_discount(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.discount.add_discount_item?module=99&type=1
    def discount_add_discount_item(self, **kwargs):
        return self.shopee.discount_add_discount_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.discount.delete_discount?module=99&type=1
    def discount_delete_discount(self, **kwargs):
        return self.shopee.discount_delete_discount(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.discount.delete_discount_item?module=99&type=1
    def discount_delete_discount_item(self, **kwargs):
        return self.shopee.discount_delete_discount_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.discount.get_discount?module=99&type=1
    def discount_get_discount(self, **kwargs):
        return self.shopee.discount_get_discount(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.discount.get_discount_list?module=99&type=1
    def discount_get_discount_list(self, **kwargs):
        return self.shopee.discount_get_discount_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.discount.update_discount?module=99&type=1
    def discount_update_discount(self, **kwargs):
        return self.shopee.discount_update_discount(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.discount.update_discount_item?module=99&type=1
    def discount_update_discount_item(self, **kwargs):
        return self.shopee.discount_update_discount_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.discount.end_discount?module=99&type=1
    def discount_end_discount(self, **kwargs):
        return self.shopee.discount_end_discount(**kwargs)
    
    ## Bundle Deal APIs
    # https://open.shopee.com/documents/v2/v2.bundle_deal.add_bundle_deal?module=110&type=1
    def bundle_deal_add_bundle_deal(self, **kwargs):
        return self.shopee.bundle_deal_add_bundle_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.add_bundle_deal_item?module=110&type=1
    def bundle_deal_add_bundle_deal_item(self, **kwargs):
        return self.shopee.bundle_deal_add_bundle_deal_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.get_bundle_deal_list?module=110&type=1
    def bundle_deal_get_bundle_deal_list(self, **kwargs):
        return self.shopee.bundle_deal_get_bundle_deal_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.get_bundle_deal?module=110&type=1
    def bundle_deal_get_bundle_deal(self, **kwargs):
        return self.shopee.bundle_deal_get_bundle_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.get_bundle_deal_item?module=110&type=1
    def bundle_deal_get_bundle_deal_item(self, **kwargs):
        return self.shopee.bundle_deal_get_bundle_deal_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.update_bundle_deal?module=110&type=1
    def bundle_deal_update_bundle_deal(self, **kwargs):
        return self.shopee.bundle_deal_update_bundle_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.update_bundle_deal_item?module=110&type=1
    def bundle_deal_update_bundle_deal_item(self, **kwargs):
        return self.shopee.bundle_deal_update_bundle_deal_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.end_bundle_deal?module=110&type=1
    def bundle_deal_end_bundle_deal(self, **kwargs):
        return self.shopee.bundle_deal_end_bundle_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.delete_bundle_deal?module=110&type=1
    def bundle_deal_delete_bundle_deal(self, **kwargs):
        return self.shopee.bundle_deal_delete_bundle_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.bundle_deal.delete_bundle_deal_item?module=110&type=1
    def bundle_deal_delete_bundle_deal_item(self, **kwargs):
        return self.shopee.bundle_deal_delete_bundle_deal_item(**kwargs)
    
    ## Add On Deal APIs
    # https://open.shopee.com/documents/v2/v2.add_on_deal.add_add_on_deal?module=111&type=1
    def add_on_deal_add_add_on_deal(self, **kwargs):
        return self.shopee.add_on_deal_add_add_on_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.add_add_on_deal_main_item?module=111&type=1
    def add_on_deal_add_add_on_deal_main_item(self, **kwargs):
        return self.shopee.add_on_deal_add_add_on_deal_main_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.add_add_on_deal_sub_item?module=111&type=1
    def add_on_deal_add_add_on_deal_sub_item(self, **kwargs):
        return self.shopee.add_on_deal_add_add_on_deal_sub_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.delete_add_on_deal?module=111&type=1
    def add_on_deal_delete_add_on_deal(self, **kwargs):
        return self.shopee.add_on_deal_delete_add_on_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.delete_add_on_deal_main_item?module=111&type=1
    def add_on_deal_delete_add_on_deal_main_item(self, **kwargs):
        return self.shopee.add_on_deal_delete_add_on_deal_main_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.delete_add_on_deal_sub_item?module=111&type=1
    def add_on_deal_delete_add_on_deal_sub_item(self, **kwargs):
        return self.shopee.add_on_deal_delete_add_on_deal_sub_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.get_add_on_deal_list?module=111&type=1
    def add_on_deal_get_add_on_deal_list(self, **kwargs):
        return self.shopee.add_on_deal_get_add_on_deal_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.get_add_on_deal?module=111&type=1
    def add_on_deal_get_add_on_deal(self, **kwargs):
        return self.shopee.add_on_deal_get_add_on_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.get_add_on_deal_main_item?module=111&type=1
    def add_on_deal_get_add_on_deal_main_item(self, **kwargs):
        return self.shopee.add_on_deal_get_add_on_deal_main_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.get_add_on_deal_sub_item?module=111&type=1
    def add_on_deal_get_add_on_deal_sub_item(self, **kwargs):
        return self.shopee.add_on_deal_get_add_on_deal_sub_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.update_add_on_deal?module=111&type=1
    def add_on_deal_update_add_on_deal(self, **kwargs):
        return self.shopee.add_on_deal_update_add_on_deal(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.update_add_on_deal_main_item?module=111&type=1
    def add_on_deal_update_add_on_deal_main_item(self, **kwargs):
        return self.shopee.add_on_deal_update_add_on_deal_main_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.update_add_on_deal_sub_item?module=111&type=1
    def add_on_deal_update_add_on_deal_sub_item(self, **kwargs):
        return self.shopee.add_on_deal_update_add_on_deal_sub_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.add_on_deal.end_add_on_deal?module=111&type=1
    def add_on_deal_end_add_on_deal(self, **kwargs):
        return self.shopee.add_on_deal_end_add_on_deal(**kwargs)
    
    ## Voucher APIs
    # https://open.shopee.com/documents/v2/v2.voucher.add_voucher?module=112&type=1
    def voucher_add_voucher(self, **kwargs):
        return self.shopee.voucher_add_voucher(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.voucher.delete_voucher?module=112&type=1
    def voucher_delete_voucher(self, **kwargs):
        return self.shopee.voucher_delete_voucher(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.voucher.end_voucher?module=112&type=1
    def voucher_end_voucher(self, **kwargs):
        return self.shopee.voucher_end_voucher(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.voucher.update_voucher?module=112&type=1
    def voucher_update_voucher(self, **kwargs):
        return self.shopee.voucher_update_voucher(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.voucher.get_voucher?module=112&type=1
    def voucher_get_voucher(self, **kwargs):
        return self.shopee.voucher_get_voucher(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.voucher.get_voucher_list?module=112&type=1
    def voucher_get_voucher_list(self, **kwargs):
        return self.shopee.voucher_get_voucher_list(**kwargs)
    
    ## Shop Flash Sale APIs
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.get_time_slot_id?module=123&type=1
    def shop_flash_sale_get_time_slot_id(self, **kwargs):
        return self.shopee.shop_flash_sale_get_time_slot_id(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.create_shop_flash_sale?module=123&type=1
    def shop_flash_sale_create_shop_flash_sale(self, **kwargs):
        return self.shopee.shop_flash_sale_create_shop_flash_sale(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.get_item_criteria?module=123&type=1
    def shop_flash_sale_get_item_criteria(self, **kwargs):
        return self.shopee.shop_flash_sale_get_item_criteria(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.add_shop_flash_sale_items?module=123&type=1
    def shop_flash_sale_add_shop_flash_sale_items(self, **kwargs):
        return self.shopee.shop_flash_sale_add_shop_flash_sale_items(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.get_shop_flash_sale_list?module=123&type=1
    def shop_flash_sale_get_shop_flash_sale_list(self, **kwargs):
        return self.shopee.shop_flash_sale_get_shop_flash_sale_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.get_shop_flash_sale?module=123&type=1
    def shop_flash_sale_get_shop_flash_sale(self, **kwargs):
        return self.shopee.shop_flash_sale_get_shop_flash_sale(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.get_shop_flash_sale_items?module=123&type=1
    def shop_flash_sale_get_shop_flash_sale_items(self, **kwargs):
        return self.shopee.shop_flash_sale_get_shop_flash_sale_items(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.update_shop_flash_sale?module=123&type=1
    def shop_flash_sale_update_shop_flash_sale(self, **kwargs):
        return self.shopee.shop_flash_sale_update_shop_flash_sale(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.update_shop_flash_sale_items?module=123&type=1
    def shop_flash_sale_update_shop_flash_sale_items(self, **kwargs):
        return self.shopee.shop_flash_sale_update_shop_flash_sale_items(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.delete_shop_flash_sale?module=123&type=1
    def shop_flash_sale_delete_shop_flash_sale(self, **kwargs):
        return self.shopee.shop_flash_sale_delete_shop_flash_sale(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_flash_sale.delete_shop_flash_sale_items?module=123&type=1
    def shop_flash_sale_delete_shop_flash_sale_items(self, **kwargs):
        return self.shopee.shop_flash_sale_delete_shop_flash_sale_items(**kwargs)
    
    ## Follow Prize APIs
    # https://open.shopee.com/documents/v2/v2.follow_prize.add_follow_prize?module=113&type=1
    def follow_prize_add_follow_prize(self, **kwargs):
        return self.shopee.follow_prize_add_follow_prize(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.follow_prize.delete_follow_prize?module=113&type=1
    def follow_prize_delete_follow_prize(self, **kwargs):
        return self.shopee.follow_prize_delete_follow_prize(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.follow_prize.end_follow_prize?module=113&type=1
    def follow_prize_end_follow_prize(self, **kwargs):
        return self.shopee.follow_prize_end_follow_prize(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.follow_prize.update_follow_prize?module=113&type=1
    def follow_prize_update_follow_prize(self, **kwargs):
        return self.shopee.follow_prize_update_follow_prize(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.follow_prize.get_follow_prize_detail?module=113&type=1
    def follow_prize_get_follow_prize_detail(self, **kwargs):
        return self.shopee.follow_prize_get_follow_prize_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.follow_prize.get_follow_prize_list?module=113&type=1
    def follow_prize_get_follow_prize_list(self, **kwargs):
        return self.shopee.follow_prize_get_follow_prize_list(**kwargs)
    
    ## Top Picks APIs
    # https://open.shopee.com/documents/v2/v2.top_picks.get_top_picks_list?module=100&type=1
    def top_picks_get_top_picks_list(self, **kwargs):
        return self.shopee.top_picks_get_top_picks_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.top_picks.add_top_picks?module=100&type=1
    def top_picks_add_top_picks(self, **kwargs):
        return self.shopee.top_picks_add_top_picks(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.top_picks.update_top_picks?module=100&type=1
    def top_picks_update_top_picks(self, **kwargs):
        return self.shopee.top_picks_update_top_picks(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.top_picks.delete_top_picks?module=100&type=1
    def top_picks_delete_top_picks(self, **kwargs):
        return self.shopee.top_picks_delete_top_picks(**kwargs)
    
    ## Shop Category APIs
    # https://open.shopee.com/documents/v2/v2.shop_category.add_shop_category?module=101&type=1
    def shop_category_add_shop_category(self, **kwargs):
        return self.shopee.shop_category_add_shop_category(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_category.get_shop_category_list?module=101&type=1
    def shop_category_get_shop_category_list(self, **kwargs):
        return self.shopee.shop_category_get_shop_category_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_category.delete_shop_category?module=101&type=1
    def shop_category_delete_shop_category(self, **kwargs):
        return self.shopee.shop_category_delete_shop_category(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_category.update_shop_category?module=101&type=1
    def shop_category_update_shop_category(self, **kwargs):
        return self.shopee.shop_category_update_shop_category(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_category.add_item_list?module=101&type=1
    def shop_category_add_item_list(self, **kwargs):
        return self.shopee.shop_category_add_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_category.get_item_list?module=101&type=1
    def shop_category_get_item_list(self, **kwargs):
        return self.shopee.shop_category_get_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.shop_category.delete_item_list?module=101&type=1
    def shop_category_delete_item_list(self, **kwargs):
        return self.shopee.shop_category_delete_item_list(**kwargs)
    
    ## Returns APIs
    # https://open.shopee.com/documents/v2/v2.returns.get_return_detail?module=102&type=1
    def returns_get_return_detail(self, **kwargs):
        return self.shopee.returns_get_return_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.get_return_list?module=102&type=1
    def returns_get_return_list(self, **kwargs):
        return self.shopee.returns_get_return_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.confirm?module=102&type=1
    def returns_confirm(self, **kwargs):
        return self.shopee.returns_confirm(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.dispute?module=102&type=1
    def returns_dispute(self, **kwargs):
        return self.shopee.returns_dispute(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.get_available_solutions?module=102&type=1
    def returns_get_available_solutions(self, **kwargs):
        return self.shopee.returns_get_available_solutions(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.offer?module=102&type=1
    def returns_offer(self, **kwargs):
        return self.shopee.returns_offer(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.accept_offer?module=102&type=1
    def returns_accept_offer(self, **kwargs):
        return self.shopee.returns_accept_offer(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.convert_image?module=102&type=1
    def returns_convert_image(self, **kwargs):
        return self.shopee.returns_convert_image(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.upload_proof?module=102&type=1
    def returns_upload_proof(self, **kwargs):
        return self.shopee.returns_upload_proof(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.query_proof?module=102&type=1
    def returns_query_proof(self, **kwargs):
        return self.shopee.returns_query_proof(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.get_return_dispute_reason?module=102&type=1
    def returns_get_return_dispute_reason(self, **kwargs):
        return self.shopee.returns_get_return_dispute_reason(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.cancel_dispute?module=102&type=1
    def returns_cancel_dispute(self, **kwargs):
        return self.shopee.returns_cancel_dispute(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.get_shipping_carrier?module=102&type=1
    def returns_get_shipping_carrier(self, **kwargs):
        return self.shopee.returns_get_shipping_carrier(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.returns.upload_shipping_proof?module=102&type=1
    def returns_upload_shipping_proof(self, **kwargs):
        return self.shopee.returns_upload_shipping_proof(**kwargs)
    
    ## Account Health APIs
    # https://open.shopee.com/documents/v2/v2.account_health.get_shop_performance?module=103&type=1
    def account_health_get_shop_performance(self, **kwargs):
        return self.shopee.account_health_get_shop_performance(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.account_health.get_metric_source_detail?module=103&type=1
    def account_health_get_metric_source_detail(self, **kwargs):
        return self.shopee.account_health_get_metric_source_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.account_health.get_penalty_point_history?module=103&type=1
    def account_health_get_penalty_point_history(self, **kwargs):
        return self.shopee.account_health_get_penalty_point_history(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.account_health.get_punishment_history?module=103&type=1
    def account_health_get_punishment_history(self, **kwargs):
        return self.shopee.account_health_get_punishment_history(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.account_health.get_listings_with_issues?module=103&type=1
    def account_health_get_listings_with_issues(self, **kwargs):
        return self.shopee.account_health_get_listings_with_issues(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.account_health.get_late_orders?module=103&type=1
    def account_health_get_late_orders(self, **kwargs):
        return self.shopee.account_health_get_late_orders(**kwargs)
    
    ## Ads APIs
    # https://open.shopee.com/documents/v2/v2.ads.get_total_balance?module=117&type=1
    def ads_get_total_balance(self, **kwargs):
        return self.shopee.ads_get_total_balance(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_shop_toggle_info?module=117&type=1
    def ads_get_shop_toggle_info(self, **kwargs):
        return self.shopee.ads_get_shop_toggle_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_recommended_keyword_list?module=117&type=1
    def ads_get_recommended_keyword_list(self, **kwargs):
        return self.shopee.ads_get_recommended_keyword_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_recommended_item_list?module=117&type=1
    def ads_get_recommended_item_list(self, **kwargs):
        return self.shopee.ads_get_recommended_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_all_cpc_ads_hourly_performance?module=117&type=1
    def ads_get_all_cpc_ads_hourly_performance(self, **kwargs):
        return self.shopee.ads_get_all_cpc_ads_hourly_performance(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_all_cpc_ads_daily_performance?module=117&type=1
    def ads_get_all_cpc_ads_daily_performance(self, **kwargs):
        return self.shopee.ads_get_all_cpc_ads_daily_performance(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.create_auto_product_ads?module=117&type=1
    def ads_create_auto_product_ads(self, **kwargs):
        return self.shopee.ads_create_auto_product_ads(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.edit_auto_product_ads?module=117&type=1
    def ads_edit_auto_product_ads(self, **kwargs):
        return self.shopee.ads_edit_auto_product_ads(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_product_campaign_daily_performance?module=117&type=1
    def ads_get_product_campaign_daily_performance(self, **kwargs):
        return self.shopee.ads_get_product_campaign_daily_performance(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_product_campaign_hourly_performance?module=117&type=1
    def ads_get_product_campaign_hourly_performance(self, **kwargs):
        return self.shopee.ads_get_product_campaign_hourly_performance(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_product_level_campaign_id_list?module=117&type=1
    def ads_get_product_level_campaign_id_list(self, **kwargs):
        return self.shopee.ads_get_product_level_campaign_id_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_product_level_campaign_setting_info?module=117&type=1
    def ads_get_product_level_campaign_setting_info(self, **kwargs):
        return self.shopee.ads_get_product_level_campaign_setting_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.create_manual_product_ads?module=117&type=1
    def ads_create_manual_product_ads(self, **kwargs):
        return self.shopee.ads_create_manual_product_ads(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.edit_manual_product_ad_keywords?module=117&type=1
    def ads_edit_manual_product_ad_keywords(self, **kwargs):
        return self.shopee.ads_edit_manual_product_ad_keywords(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.edit_manual_product_ads?module=117&type=1
    def ads_edit_manual_product_ads(self, **kwargs):
        return self.shopee.ads_edit_manual_product_ads(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_create_product_ad_budget_suggestion?module=117&type=1
    def ads_get_create_product_ad_budget_suggestion(self, **kwargs):
        return self.shopee.ads_get_create_product_ad_budget_suggestion(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_product_recommended_roi_target?module=117&type=1
    def ads_get_product_recommended_roi_target(self, **kwargs):
        return self.shopee.ads_get_product_recommended_roi_target(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_ads_fácil_shop_rate?module=117&type=1
    def ads_get_ads_facil_shop_rate(self, **kwargs):
        return self.shopee.ads_get_ads_facil_shop_rate(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.check_create_gms_product_campaign_eligibility?module=117&type=1
    def ads_check_create_gms_product_campaign_eligibility(self, **kwargs):
        return self.shopee.ads_check_create_gms_product_campaign_eligibility(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.create_gms_product_campaign?module=117&type=1
    def ads_create_gms_product_campaign(self, **kwargs):
        return self.shopee.ads_create_gms_product_campaign(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.edit_gms_product_campaign?module=117&type=1
    def ads_edit_gms_product_campaign(self, **kwargs):
        return self.shopee.ads_edit_gms_product_campaign(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.list_gms_user_deleted_item?module=117&type=1
    def ads_list_gms_user_deleted_item(self, **kwargs):
        return self.shopee.ads_list_gms_user_deleted_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.edit_gms_item_product_campaign?module=117&type=1
    def ads_edit_gms_item_product_campaign(self, **kwargs):
        return self.shopee.ads_edit_gms_item_product_campaign(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_gms_campaign_performance?module=117&type=1
    def ads_get_gms_campaign_performance(self, **kwargs):
        return self.shopee.ads_get_gms_campaign_performance(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.ads.get_gms_item_performance?module=117&type=1
    def ads_get_gms_item_performance(self, **kwargs):
        return self.shopee.ads_get_gms_item_performance(**kwargs)
    
    ## Public APIs
    # https://open.shopee.com/documents/v2/v2.public.get_shops_by_partner?module=104&type=1
    def public_get_shops_by_partner(self, **kwargs):
        return self.shopee.public_get_shops_by_partner(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.public.get_merchants_by_partner?module=104&type=1
    def public_get_merchants_by_partner(self, **kwargs):
        return self.shopee.public_get_merchants_by_partner(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.public.get_access_token?module=104&type=1
    def public_get_access_token(self, **kwargs):
        return self.shopee.public_get_access_token(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.public.refresh_access_token?module=104&type=1
    def public_refresh_access_token(self, **kwargs):
        return self.shopee.public_refresh_access_token(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.public.get_token_by_resend_code?module=104&type=1
    def public_get_token_by_resend_code(self, **kwargs):
        return self.shopee.public_get_token_by_resend_code(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.public.get_ip_ranges?module=104&type=1
    def public_get_ip_ranges(self, **kwargs):
        return self.shopee.public_get_ip_ranges(**kwargs)
    
    ## SBS APIs
    # https://open.shopee.com/documents/v2/v2.sbs.get_bound_whs_info?module=124&type=1
    def sbs_get_bound_whs_info(self, **kwargs):
        return self.shopee.sbs_get_bound_whs_info(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.sbs.get_current_inventory?module=124&type=1
    def sbs_get_current_inventory(self, **kwargs):
        return self.shopee.sbs_get_current_inventory(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.sbs.get_expiry_report?module=124&type=1
    def sbs_get_expiry_report(self, **kwargs):
        return self.shopee.sbs_get_expiry_report(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.sbs.get_stock_aging?module=124&type=1
    def sbs_get_stock_aging(self, **kwargs):
        return self.shopee.sbs_get_stock_aging(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.sbs.get_stock_movement?module=124&type=1
    def sbs_get_stock_movement(self, **kwargs):
        return self.shopee.sbs_get_stock_movement(**kwargs)
    
    ## FBS Shop APIs
    # https://open.shopee.com/documents/v2/v2.fbs.query_br_shop_enrollment_status?module=126&type=1
    def fbs_query_br_shop_enrollment_status(self, **kwargs):
        return self.shopee.fbs_query_br_shop_enrollment_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.fbs.query_br_shop_invoice_error?module=126&type=1
    def fbs_query_br_shop_invoice_error(self, **kwargs):
        return self.shopee.fbs_query_br_shop_invoice_error(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.fbs.query_br_shop_block_status?module=126&type=1
    def fbs_query_br_shop_block_status(self, **kwargs):
        return self.shopee.fbs_query_br_shop_block_status(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.fbs.query_br_sku_block_status?module=126&type=1
    def fbs_query_br_sku_block_status(self, **kwargs):
        return self.shopee.fbs_query_br_sku_block_status(**kwargs)
    
    ## Livestream APIs
    # https://open.shopee.com/documents/v2/v2.livestream.upload_image?module=125&type=1
    def livestream_upload_image(self, **kwargs):
        return self.shopee.livestream_upload_image(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.create_session?module=125&type=1
    def livestream_create_session(self, **kwargs):
        return self.shopee.livestream_create_session(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.update_session?module=125&type=1
    def livestream_update_session(self, **kwargs):
        return self.shopee.livestream_update_session(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.start_session?module=125&type=1
    def livestream_start_session(self, **kwargs):
        return self.shopee.livestream_start_session(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.end_session?module=125&type=1
    def livestream_end_session(self, **kwargs):
        return self.shopee.livestream_end_session(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_session_detail?module=125&type=1
    def livestream_get_session_detail(self, **kwargs):
        return self.shopee.livestream_get_session_detail(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.add_item_list?module=125&type=1
    def livestream_add_item_list(self, **kwargs):
        return self.shopee.livestream_add_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.delete_item_list?module=125&type=1
    def livestream_delete_item_list(self, **kwargs):
        return self.shopee.livestream_delete_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.update_item_list?module=125&type=1
    def livestream_update_item_list(self, **kwargs):
        return self.shopee.livestream_update_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_item_count?module=125&type=1
    def livestream_get_item_count(self, **kwargs):
        return self.shopee.livestream_get_item_count(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_item_list?module=125&type=1
    def livestream_get_item_list(self, **kwargs):
        return self.shopee.livestream_get_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.update_show_item?module=125&type=1
    def livestream_update_show_item(self, **kwargs):
        return self.shopee.livestream_update_show_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.delete_show_item?module=125&type=1
    def livestream_delete_show_item(self, **kwargs):
        return self.shopee.livestream_delete_show_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_show_item?module=125&type=1
    def livestream_get_show_item(self, **kwargs):
        return self.shopee.livestream_get_show_item(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_like_item_list?module=125&type=1
    def livestream_get_like_item_list(self, **kwargs):
        return self.shopee.livestream_get_like_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_recent_item_list?module=125&type=1
    def livestream_get_recent_item_list(self, **kwargs):
        return self.shopee.livestream_get_recent_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_item_set_list?module=125&type=1
    def livestream_get_item_set_list(self, **kwargs):
        return self.shopee.livestream_get_item_set_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_item_set_item_list?module=125&type=1
    def livestream_get_item_set_item_list(self, **kwargs):
        return self.shopee.livestream_get_item_set_item_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.apply_item_set?module=125&type=1
    def livestream_apply_item_set(self, **kwargs):
        return self.shopee.livestream_apply_item_set(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_session_metric?module=125&type=1
    def livestream_get_session_metric(self, **kwargs):
        return self.shopee.livestream_get_session_metric(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_session_item_metric?module=125&type=1
    def livestream_get_session_item_metric(self, **kwargs):
        return self.shopee.livestream_get_session_item_metric(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.get_latest_comment_list?module=125&type=1
    def livestream_get_latest_comment_list(self, **kwargs):
        return self.shopee.livestream_get_latest_comment_list(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.post_comment?module=125&type=1
    def livestream_post_comment(self, **kwargs):
        return self.shopee.livestream_post_comment(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.ban_user_comment?module=125&type=1
    def livestream_ban_user_comment(self, **kwargs):
        return self.shopee.livestream_ban_user_comment(**kwargs)
    
    # https://open.shopee.com/documents/v2/v2.livestream.unban_user_comment?module=125&type=1
    def livestream_unban_user_comment(self, **kwargs):
        return self.shopee.livestream_unban_user_comment(**kwargs)