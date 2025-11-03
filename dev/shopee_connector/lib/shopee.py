import logging
from .request import Request

_logger = logging.getLogger(__name__)


class Shopee:
    def __init__(self, connector):
        self.request = Request(connector)

    def _call_api(self, path, name_request, required_params=None, default_params=None, method='POST', **kwargs):
        # Check required parameters
        if required_params:
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"{param} is a required parameter")
        
        # Start with default parameters
        body = default_params.copy() if default_params else {}
        
        # Add all kwargs to body
        body.update(kwargs)
        
        # Remove empty parameters
        body = {k: v for k, v in body.items() if v}
        
        _logger.info(f"{name_request} with params: {body}")
        
        try:
            result = self.request._make_api_request(path, body, method, name_request=name_request)
            _logger.info(f"Successfully completed {name_request}")
            return result
            
        except Exception as e:
            _logger.error(f"Failed {name_request}: {e}")
            raise

    # Product APIs
    def product_get_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_item_list",
            name_request='Get item list from Shopee API',
            method='GET',
            **kwargs
        )

    def product_get_item_base_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_item_base_info",
            name_request='Get item base info from Shopee API',
            required_params=['item_id_list'],
            method='GET',
            **kwargs
        )
    
    def product_get_category(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_category",
            name_request='Get category list from Shopee API',
            method='GET',
            default_params={
                "language": 'vi',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_attribute_tree(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_attribute_tree",
            name_request='Get attribute tree from Shopee API',
            required_params=['category_id'],
            method='GET',
            default_params={
                "language": 'vi',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_brand_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_brand_list",
            name_request='Get brand list from Shopee API',
            required_params=['category_id'],
            method='GET',
            default_params={
                "language": 'vi',
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_item_limit(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_item_limit",
            name_request='Get item limit from Shopee API',
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_item_extra_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_item_extra_info",
            name_request='Get item extra info from Shopee API',
            required_params=['item_id_list'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_add_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/add_item",
            name_request='Add item to Shopee API',
            required_params=['item_name', 'description', 'category_id', 'price', 'stock'],
            method='POST',
            **kwargs
        )

    def product_update_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/update_item",
            name_request='Update item in Shopee API',
            required_params=['item_id'],
            method='PUT',
            **kwargs
        )

    def product_delete_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/delete_item",
            name_request='Delete item from Shopee API',
            required_params=['item_id_list'],
            method='DELETE',
            **kwargs
        )

    def product_init_tier_variation(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/init_tier_variation",
            name_request='Initialize tier variation in Shopee API',
            required_params=['item_id'],
            method='POST',
            **kwargs
        )

    def product_update_tier_variation(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/update_tier_variation",
            name_request='Update tier variation in Shopee API',
            required_params=['item_id'],
            method='PUT',
            **kwargs
        )

    def product_get_model_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_model_list",
            name_request='Get model list from Shopee API',
            required_params=['item_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_add_model(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/add_model",
            name_request='Add model to Shopee API',
            required_params=['item_id', 'model_list'],
            method='POST',
            **kwargs
        )

    def product_update_model(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/update_model",
            name_request='Update model in Shopee API',
            required_params=['item_id', 'model_list'],
            method='PUT',
            **kwargs
        )

    def product_delete_model(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/delete_model",
            name_request='Delete model from Shopee API',
            required_params=['item_id', 'model_id_list'],
            method='DELETE',
            **kwargs
        )

    def product_unlist_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/unlist_item",
            name_request='Unlist item from Shopee API',
            required_params=['item_id_list'],
            method='DELETE',
            **kwargs
        )

    def product_update_price(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/update_price",
            name_request='Update price in Shopee API',
            required_params=['item_id', 'price_list'],
            method='PATCH',
            **kwargs
        )

    def product_update_stock(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/update_stock",
            name_request='Update stock in Shopee API',
            required_params=['item_id', 'stock_list'],
            method='PATCH',
            **kwargs
        )

    def product_boost_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/boost_item",
            name_request='Boost item in Shopee API',
            required_params=['item_id_list'],
            method='POST',
            **kwargs
        )

    def product_get_boosted_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_boosted_list",
            name_request='Get boosted list from Shopee API',
            method='GET',
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_item_promotion(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_item_promotion",
            name_request='Get item promotion from Shopee API',
            required_params=['item_id_list'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_update_sip_item_price(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/update_sip_item_price",
            name_request='Update SIP item price in Shopee API',
            required_params=['item_id', 'sip_item_price_list'],
            method='PATCH',
            **kwargs
        )

    def product_search_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/search_item",
            name_request='Search item in Shopee API',
            required_params=['keyword'],
            method='GET',
            **kwargs
        )

    def product_get_comment(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_comment",
            name_request='Get comment from Shopee API',
            required_params=['item_id'],
            method='GET',
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_reply_comment(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/reply_comment",
            name_request='Reply comment in Shopee API',
            required_params=['comment_id', 'reply'],
            method='POST',
            **kwargs
        )

    def product_category_recommend(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/category_recommend",
            name_request='Get category recommendation from Shopee API',
            required_params=['item_name'],
            method='GET',
            **kwargs
        )

    def product_register_brand(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/register_brand",
            name_request='Register brand in Shopee API',
            required_params=['brand_name'],
            method='POST',
            **kwargs
        )

    def product_get_recommend_attribute(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_recommend_attribute",
            name_request='Get recommend attribute from Shopee API',
            required_params=['category_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_weight_recommendation(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_weight_recommendation",
            name_request='Get weight recommendation from Shopee API',
            required_params=['category_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_size_chart_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_size_chart_list",
            name_request='Get size chart list from Shopee API',
            required_params=['category_id'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_size_chart_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_size_chart_detail",
            name_request='Get size chart detail from Shopee API',
            required_params=['size_chart_id'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_item_violation_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_item_violation_info",
            name_request='Get item violation info from Shopee API',
            required_params=['item_id_list'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_variations(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_variations",
            name_request='Get variations from Shopee API',
            required_params=['item_id'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_all_vehicle_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_all_vehicle_list",
            name_request='Get all vehicle list from Shopee API',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_vehicle_list_by_compatibility_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_vehicle_list_by_compatibility_detail",
            name_request='Get vehicle list by compatibility detail from Shopee API',
            required_params=['compatibility_detail'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_item_content_diagnosis_result(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_item_content_diagnosis_result",
            name_request='Get item content diagnosis result from Shopee API',
            required_params=['item_id'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_item_list_by_content_diagnosis(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_item_list_by_content_diagnosis",
            name_request='Get item list by content diagnosis from Shopee API',
            default_params={
                "diagnosis_status": '',
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_kit_item_limit(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_kit_item_limit",
            name_request='Get kit item limit from Shopee API',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_add_kit_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/add_kit_item",
            name_request='Add kit item to Shopee API',
            required_params=['kit_name', 'kit_description', 'kit_item_list'],
            method='POST',
            **kwargs
        )

    def product_update_kit_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/update_kit_item",
            name_request='Update kit item in Shopee API',
            required_params=['kit_id'],
            method='GET',
            **kwargs
        )

    def product_get_kit_item_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_kit_item_info",
            name_request='Get kit item info from Shopee API',
            required_params=['kit_id_list'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_ssp_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_ssp_list",
            name_request='Get SSP list from Shopee API',
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_ssp_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_ssp_info",
            name_request='Get SSP info from Shopee API',
            required_params=['ssp_id_list'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_add_ssp_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/add_ssp_item",
            name_request='Add SSP item to Shopee API',
            required_params=['ssp_id', 'item_id'],
            method='POST',
            **kwargs
        )

    def product_link_ssp(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/link_ssp",
            name_request='Link SSP in Shopee API',
            required_params=['ssp_id', 'item_id'],
            method='POST',
            **kwargs
        )

    def product_unlink_ssp(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/unlink_ssp",
            name_request='Unlink SSP in Shopee API',
            required_params=['ssp_id', 'item_id'],
            method='DELETE',
            **kwargs
        )

    def product_get_aitem_by_pitem_id(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_aitem_by_pitem_id",
            name_request='Get aitem by pitem ID from Shopee API',
            required_params=['pitem_id_list'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_search_attribute_value_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/search_attribute_value_list",
            name_request='Search attribute value list from Shopee API',
            required_params=['category_id', 'attribute_id', 'keyword'],
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_main_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_main_item_list",
            name_request='Get main item list from Shopee API',
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_direct_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_direct_item_list",
            name_request='Get direct item list from Shopee API',
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_direct_shop_recommended_price(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_direct_shop_recommended_price",
            name_request='Get direct shop recommended price from Shopee API',
            required_params=['item_id_list'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_get_product_certification_rule(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/get_product_certification_rule",
            name_request='Get product certification rule from Shopee API',
            required_params=['category_id'],
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def product_search_unpackaged_model_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/product/search_unpackaged_model_list",
            name_request='Search unpackaged model list from Shopee API',
            required_params=['keyword'],
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    # Global Product APIs
    def global_product_get_category(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_category",
            name_request='Get global product category from Shopee API',
            method='GET',
            default_params={
                "language": 'vi',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_attribute_tree(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_attribute_tree",
            name_request='Get global product attribute tree from Shopee API',
            required_params=['category_id'],
            method='GET',
            default_params={
                "language": 'vi',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_brand_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_brand_list",
            name_request='Get global product brand list from Shopee API',
            required_params=['category_id'],
            method='GET',
            default_params={
                "language": 'vi',
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_global_item_limit(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_global_item_limit",
            name_request='Get global product item limit from Shopee API',
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_global_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_global_item_list",
            name_request='Get global product item list from Shopee API',
            method='GET',
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_global_item_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_global_item_info",
            name_request='Get global product item info from Shopee API',
            required_params=['global_item_id_list'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_add_global_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/add_global_item",
            name_request='Add global item to Shopee API',
            required_params=['global_item_name', 'description', 'category_id', 'price', 'stock'],
            method='POST',
            **kwargs
        )

    def global_product_update_global_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/update_global_item",
            name_request='Update global item in Shopee API',
            required_params=['global_item_id'],
            method='PUT',
            **kwargs
        )

    def global_product_delete_global_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/delete_global_item",
            name_request='Delete global item from Shopee API',
            required_params=['global_item_id_list'],
            method='DELETE',
            **kwargs
        )

    def global_product_init_tier_variation(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/init_tier_variation",
            name_request='Initialize global product tier variation in Shopee API',
            required_params=['global_item_id'],
            method='POST',
            **kwargs
        )

    def global_product_update_tier_variation(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/update_tier_variation",
            name_request='Update global product tier variation in Shopee API',
            required_params=['global_item_id'],
            method='PUT',
            **kwargs
        )

    def global_product_add_global_model(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/add_global_model",
            name_request='Add global model to Shopee API',
            required_params=['global_item_id', 'global_model_list'],
            method='POST',
            **kwargs
        )

    def global_product_update_global_model(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/update_global_model",
            name_request='Update global model in Shopee API',
            required_params=['global_item_id', 'global_model_list'],
            method='PUT',
            **kwargs
        )

    def global_product_delete_global_model(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/delete_global_model",
            name_request='Delete global model from Shopee API',
            required_params=['global_item_id', 'global_model_id_list'],
            method='DELETE',
            **kwargs
        )

    def global_product_get_global_model_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_global_model_list",
            name_request='Get global model list from Shopee API',
            required_params=['global_item_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_support_size_chart(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/support_size_chart",
            name_request='Support size chart for global product from Shopee API',
            required_params=['global_item_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_update_size_chart(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/update_size_chart",
            name_request='Update size chart for global product in Shopee API',
            required_params=['global_item_id'],
            method='PUT',
            **kwargs
        )

    def global_product_create_publish_task(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/create_publish_task",
            name_request='Create publish task for global product in Shopee API',
            required_params=['global_item_id', 'shop_id_list'],
            method='POST',
            **kwargs
        )

    def global_product_get_publishable_shop(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_publishable_shop",
            name_request='Get publishable shop for global product from Shopee API',
            required_params=['global_item_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_publish_task_result(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_publish_task_result",
            name_request='Get publish task result for global product from Shopee API',
            required_params=['task_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_published_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_published_list",
            name_request='Get published list for global product from Shopee API',
            method='GET',
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_update_price(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/update_price",
            name_request='Update price for global product in Shopee API',
            required_params=['global_item_id', 'price_list'],
            method='PATCH',
            **kwargs
        )

    def global_product_update_stock(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/update_stock",
            name_request='Update stock for global product in Shopee API',
            required_params=['global_item_id', 'stock_list'],
            method='PATCH',
            **kwargs
        )

    def global_product_set_sync_field(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/set_sync_field",
            name_request='Set sync field for global product in Shopee API',
            required_params=['global_item_id', 'sync_field_list'],
            method='POST',
            **kwargs
        )

    def global_product_get_global_item_id(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_global_item_id",
            name_request='Get global item ID from Shopee API',
            required_params=['item_id_list'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_category_recommend(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/category_recommend",
            name_request='Get category recommendation for global product from Shopee API',
            required_params=['global_item_name'],
            method='GET',
            **kwargs
        )

    def global_product_get_recommend_attribute(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_recommend_attribute",
            name_request='Get recommend attribute for global product from Shopee API',
            required_params=['category_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_shop_publishable_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_shop_publishable_status",
            name_request='Get shop publishable status for global product from Shopee API',
            required_params=['global_item_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_variations(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_variations",
            name_request='Get variations for global product from Shopee API',
            required_params=['global_item_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_size_chart_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_size_chart_detail",
            name_request='Get size chart detail for global product from Shopee API',
            required_params=['size_chart_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_size_chart_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_size_chart_list",
            name_request='Get size chart list for global product from Shopee API',
            required_params=['category_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_search_global_attribute_value_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/search_global_attribute_value_list",
            name_request='Search global attribute value list from Shopee API',
            required_params=['category_id', 'attribute_id', 'keyword'],
            method='GET',
            default_params={
                "page_size": 20,
                "cursor": '',
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_get_local_adjustment_rate(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/get_local_adjustment_rate",
            name_request='Get local adjustment rate for global product from Shopee API',
            required_params=['global_item_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def global_product_update_local_adjustment_rate(self, **kwargs):
        return self._call_api(
            path="/api/v2/global_product/update_local_adjustment_rate",
            name_request='Update local adjustment rate for global product in Shopee API',
            required_params=['global_item_id', 'adjustment_rate_list'],
            method='POST',
            **kwargs
        )

    # Media Space APIs
    def media_space_init_video_upload(self, **kwargs):
        return self._call_api(
            path="/api/v2/media_space/init_video_upload",
            name_request='Initialize video upload in Shopee API',
            required_params=['video_size'],
            method='POST',
            **kwargs
        )

    def media_space_upload_video_part(self, **kwargs):
        return self._call_api(
            path="/api/v2/media_space/upload_video_part",
            name_request='Upload video part in Shopee API',
            required_params=['upload_id', 'part_number', 'video_part'],
            method='POST',
            **kwargs
        )

    def media_space_complete_video_upload(self, **kwargs):
        return self._call_api(
            path="/api/v2/media_space/complete_video_upload",
            name_request='Complete video upload in Shopee API',
            required_params=['upload_id'],
            method='POST',
            **kwargs
        )

    def media_space_get_video_upload_result(self, **kwargs):
        return self._call_api(
            path="/api/v2/media_space/get_video_upload_result",
            name_request='Get video upload result from Shopee API',
            required_params=['upload_id'],
            method='GET',
            default_params={
                "response_optional_fields": '',
            },
            **kwargs
        )

    def media_space_cancel_video_upload(self, **kwargs):
        return self._call_api(
            path="/api/v2/media_space/cancel_video_upload",
            name_request='Cancel video upload in Shopee API',
            required_params=['upload_id'],
            method='POST',
            **kwargs
        )

    def media_space_upload_image(self, **kwargs):
        return self._call_api(
            path="/api/v2/media_space/upload_image",
            name_request='Upload image in Shopee API',
            required_params=['image'],
            method='POST',
            **kwargs
        )

    # Media APIs
    def media_upload_image(self, **kwargs):
        return self._call_api(
            path="/api/v2/media/upload_image",
            name_request='Upload image in Shopee Media API',
            required_params=['image'],
            method='POST',
            **kwargs
        )

    # Shop APIs
    def shop_get_shop_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop/get_shop_info",
            name_request='Get shop info from Shopee API',
            method='GET',
            **kwargs
        )

    def shop_get_profile(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop/get_profile",
            name_request='Get shop profile from Shopee API',
            method='GET',
            **kwargs
        )

    def shop_update_profile(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop/update_profile",
            name_request='Update shop profile in Shopee API',
            method='PUT',
            **kwargs
        )

    def shop_get_warehouse_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop/get_warehouse_detail",
            name_request='Get warehouse detail from Shopee API',
            method='GET',
            **kwargs
        )

    def shop_get_shop_notification(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop/get_shop_notification",
            name_request='Get shop notification from Shopee API',
            method='GET',
            **kwargs
        )

    def shop_get_authorised_reseller_brand(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop/get_authorised_reseller_brand",
            name_request='Get authorised reseller brand from Shopee API',
            method='GET',
            **kwargs
        )

    # Merchant APIs
    def merchant_get_merchant_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/merchant/get_merchant_info",
            name_request='Get merchant info from Shopee API',
            method='GET',
            **kwargs
        )

    def merchant_get_shop_list_by_merchant(self, **kwargs):
        return self._call_api(
            path="/api/v2/merchant/get_shop_list_by_merchant",
            name_request='Get shop list by merchant from Shopee API',
            method='GET',
            **kwargs
        )

    def merchant_get_merchant_warehouse_location_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/merchant/get_merchant_warehouse_location_list",
            name_request='Get merchant warehouse location list from Shopee API',
            method='GET',
            **kwargs
        )

    def merchant_get_merchant_warehouse_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/merchant/get_merchant_warehouse_list",
            name_request='Get merchant warehouse list from Shopee API',
            method='GET',
            **kwargs
        )

    def merchant_get_warehouse_eligible_shop_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/merchant/get_warehouse_eligible_shop_list",
            name_request='Get warehouse eligible shop list from Shopee API',
            method='GET',
            **kwargs
        )

    def merchant_get_merchant_prepaid_account_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/merchant/get_merchant_prepaid_account_list",
            name_request='Get merchant prepaid account list from Shopee API',
            method='GET',
            **kwargs
        )

    # Order APIs
    def order_get_order_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_order_list",
            name_request='Get order list from Shopee API',
            method='GET',
            **kwargs
        )

    def order_get_order_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_order_detail",
            name_request='Get order detail from Shopee API',
            required_params=['order_sn_list'],
            method='GET',
            **kwargs
        )

    def order_get_shipment_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_shipment_list",
            name_request='Get shipment list from Shopee API',
            method='GET',
            **kwargs
        )

    def order_search_package_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/search_package_list",
            name_request='Search package list from Shopee API',
            method='GET',
            **kwargs
        )

    def order_get_package_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_package_detail",
            name_request='Get package detail from Shopee API',
            required_params=['package_number'],
            method='GET',
            **kwargs
        )

    def order_split_order(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/split_order",
            name_request='Split order in Shopee API',
            required_params=['order_sn', 'item_list'],
            method='POST',
            **kwargs
        )

    def order_unsplit_order(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/unsplit_order",
            name_request='Unsplit order in Shopee API',
            required_params=['order_sn'],
            method='POST',
            **kwargs
        )

    def order_cancel_order(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/cancel_order",
            name_request='Cancel order in Shopee API',
            required_params=['order_sn', 'cancel_reason'],
            method='POST',
            **kwargs
        )

    def order_handle_buyer_cancellation(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/handle_buyer_cancellation",
            name_request='Handle buyer cancellation in Shopee API',
            required_params=['order_sn', 'action'],
            method='POST',
            **kwargs
        )

    def order_set_note(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/set_note",
            name_request='Set note for order in Shopee API',
            required_params=['order_sn', 'note'],
            method='POST',
            **kwargs
        )

    def order_get_pending_buyer_invoice_order_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_pending_buyer_invoice_order_list",
            name_request='Get pending buyer invoice order list from Shopee API',
            method='GET',
            **kwargs
        )

    def order_get_buyer_invoice_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_buyer_invoice_info",
            name_request='Get buyer invoice info from Shopee API',
            required_params=['order_sn'],
            method='GET',
            **kwargs
        )

    def order_upload_invoice_doc(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/upload_invoice_doc",
            name_request='Upload invoice document in Shopee API',
            required_params=['order_sn', 'invoice_doc'],
            method='POST',
            **kwargs
        )

    def order_download_invoice_doc(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/download_invoice_doc",
            name_request='Download invoice document from Shopee API',
            required_params=['order_sn'],
            method='GET',
            **kwargs
        )

    def order_handle_prescription_check(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/handle_prescription_check",
            name_request='Handle prescription check in Shopee API',
            required_params=['order_sn', 'action'],
            method='POST',
            **kwargs
        )

    def order_get_warehouse_filter_config(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_warehouse_filter_config",
            name_request='Get warehouse filter config from Shopee API',
            method='GET',
            **kwargs
        )

    def order_get_booking_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_booking_list",
            name_request='Get booking list from Shopee API',
            method='GET',
            **kwargs
        )

    def order_get_booking_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_booking_detail",
            name_request='Get booking detail from Shopee API',
            required_params=['booking_id'],
            method='GET',
            **kwargs
        )

    def order_generate_fbs_invoices(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/generate_fbs_invoices",
            name_request='Generate FBS invoices in Shopee API',
            required_params=['order_sn_list'],
            method='POST',
            **kwargs
        )

    def order_get_fbs_invoices_result(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/get_fbs_invoices_result",
            name_request='Get FBS invoices result from Shopee API',
            required_params=['task_id'],
            method='GET',
            **kwargs
        )

    def order_download_fbs_invoices(self, **kwargs):
        return self._call_api(
            path="/api/v2/order/download_fbs_invoices",
            name_request='Download FBS invoices from Shopee API',
            required_params=['task_id'],
            method='GET',
            **kwargs
        )

    # Logistics APIs
    def logistics_get_shipping_parameter(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_shipping_parameter",
            name_request='Get shipping parameter from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_get_mass_shipping_parameter(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_mass_shipping_parameter",
            name_request='Get mass shipping parameter from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_ship_order(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/ship_order",
            name_request='Ship order in Shopee API',
            required_params=['order_sn', 'package_number'],
            method='POST',
            **kwargs
        )

    def logistics_mass_ship_order(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/mass_ship_order",
            name_request='Mass ship order in Shopee API',
            required_params=['order_list'],
            method='POST',
            **kwargs
        )

    def logistics_update_shipping_order(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/update_shipping_order",
            name_request='Update shipping order in Shopee API',
            required_params=['order_sn', 'package_number'],
            method='POST',
            **kwargs
        )

    def logistics_get_tracking_number(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_tracking_number",
            name_request='Get tracking number from Shopee API',
            required_params=['order_sn', 'package_number'],
            method='GET',
            **kwargs
        )

    def logistics_get_mass_tracking_number(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_mass_tracking_number",
            name_request='Get mass tracking number from Shopee API',
            required_params=['order_list'],
            method='GET',
            **kwargs
        )

    def logistics_get_shipping_document_parameter(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_shipping_document_parameter",
            name_request='Get shipping document parameter from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_create_shipping_document(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/create_shipping_document",
            name_request='Create shipping document in Shopee API',
            required_params=['order_list'],
            method='POST',
            **kwargs
        )

    def logistics_get_shipping_document_result(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_shipping_document_result",
            name_request='Get shipping document result from Shopee API',
            required_params=['request_id'],
            method='GET',
            **kwargs
        )

    def logistics_download_shipping_document(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/download_shipping_document",
            name_request='Download shipping document from Shopee API',
            required_params=['request_id'],
            method='GET',
            **kwargs
        )

    def logistics_get_shipping_document_data_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_shipping_document_data_info",
            name_request='Get shipping document data info from Shopee API',
            required_params=['request_id'],
            method='GET',
            **kwargs
        )

    def logistics_get_tracking_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_tracking_info",
            name_request='Get tracking info from Shopee API',
            required_params=['tracking_number'],
            method='GET',
            **kwargs
        )

    def logistics_get_address_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_address_list",
            name_request='Get address list from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_set_address_config(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/set_address_config",
            name_request='Set address config in Shopee API',
            required_params=['address_id'],
            method='POST',
            **kwargs
        )

    def logistics_delete_address(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/delete_address",
            name_request='Delete address in Shopee API',
            required_params=['address_id'],
            method='POST',
            **kwargs
        )

    def logistics_get_channel_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_channel_list",
            name_request='Get channel list from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_update_channel(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/update_channel",
            name_request='Update channel in Shopee API',
            required_params=['channel_id'],
            method='POST',
            **kwargs
        )

    def logistics_get_operating_hours(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_operating_hours",
            name_request='Get operating hours from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_get_operating_hour_restrictions(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_operating_hour_restrictions",
            name_request='Get operating hour restrictions from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_update_operating_hours(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/update_operating_hours",
            name_request='Update operating hours in Shopee API',
            required_params=['operating_hours'],
            method='POST',
            **kwargs
        )

    def logistics_delete_special_operating_hour(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/delete_special_operating_hour",
            name_request='Delete special operating hour in Shopee API',
            required_params=['date'],
            method='POST',
            **kwargs
        )

    def logistics_batch_update_tpf_warehouse_tracking_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/batch_update_tpf_warehouse_tracking_status",
            name_request='Batch update TPF warehouse tracking status in Shopee API',
            required_params=['tracking_number_list'],
            method='POST',
            **kwargs
        )

    def logistics_batch_ship_order(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/batch_ship_order",
            name_request='Batch ship order in Shopee API',
            required_params=['order_list'],
            method='POST',
            **kwargs
        )

    def logistics_update_tracking_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/update_tracking_status",
            name_request='Update tracking status in Shopee API',
            required_params=['tracking_number', 'status'],
            method='POST',
            **kwargs
        )

    def logistics_get_booking_shipping_parameter(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_booking_shipping_parameter",
            name_request='Get booking shipping parameter from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_ship_booking(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/ship_booking",
            name_request='Ship booking in Shopee API',
            required_params=['booking_id'],
            method='POST',
            **kwargs
        )

    def logistics_get_booking_tracking_number(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_booking_tracking_number",
            name_request='Get booking tracking number from Shopee API',
            required_params=['booking_id'],
            method='GET',
            **kwargs
        )

    def logistics_get_booking_shipping_document_parameter(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_booking_shipping_document_parameter",
            name_request='Get booking shipping document parameter from Shopee API',
            method='GET',
            **kwargs
        )

    def logistics_create_booking_shipping_document(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/create_booking_shipping_document",
            name_request='Create booking shipping document in Shopee API',
            required_params=['booking_list'],
            method='POST',
            **kwargs
        )

    def logistics_get_booking_shipping_document_result(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_booking_shipping_document_result",
            name_request='Get booking shipping document result from Shopee API',
            required_params=['request_id'],
            method='GET',
            **kwargs
        )

    def logistics_download_booking_shipping_document(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/download_booking_shipping_document",
            name_request='Download booking shipping document from Shopee API',
            required_params=['request_id'],
            method='GET',
            **kwargs
        )

    def logistics_get_booking_shipping_document_data_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_booking_shipping_document_data_info",
            name_request='Get booking shipping document data info from Shopee API',
            required_params=['request_id'],
            method='GET',
            **kwargs
        )

    def logistics_get_booking_tracking_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_booking_tracking_info",
            name_request='Get booking tracking info from Shopee API',
            required_params=['tracking_number'],
            method='GET',
            **kwargs
        )

    def logistics_download_to_label(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/download_to_label",
            name_request='Download to label from Shopee API',
            required_params=['order_list'],
            method='GET',
            **kwargs
        )

    def logistics_create_shipping_document_job(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/create_shipping_document_job",
            name_request='Create shipping document job in Shopee API',
            required_params=['order_list'],
            method='POST',
            **kwargs
        )

    def logistics_get_shipping_document_job_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/get_shipping_document_job_status",
            name_request='Get shipping document job status from Shopee API',
            required_params=['job_id'],
            method='GET',
            **kwargs
        )

    def logistics_download_shipping_document_job(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/download_shipping_document_job",
            name_request='Download shipping document job from Shopee API',
            required_params=['job_id'],
            method='GET',
            **kwargs
        )

    def logistics_update_self_collection_order_logistics(self, **kwargs):
        return self._call_api(
            path="/api/v2/logistics/update_self_collection_order_logistics",
            name_request='Update self collection order logistics in Shopee API',
            required_params=['order_sn'],
            method='POST',
            **kwargs
        )

    # First Mile APIs
    def first_mile_get_unbind_order_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_unbind_order_list",
            name_request='Get unbind order list from Shopee API',
            method='GET',
            **kwargs
        )

    def first_mile_get_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_detail",
            name_request='Get first mile detail from Shopee API',
            required_params=['tracking_number'],
            method='GET',
            **kwargs
        )

    def first_mile_generate_first_mile_tracking_number(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/generate_first_mile_tracking_number",
            name_request='Generate first mile tracking number in Shopee API',
            method='POST',
            **kwargs
        )

    def first_mile_bind_first_mile_tracking_number(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/bind_first_mile_tracking_number",
            name_request='Bind first mile tracking number in Shopee API',
            required_params=['tracking_number', 'order_list'],
            method='POST',
            **kwargs
        )

    def first_mile_unbind_first_mile_tracking_number(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/unbind_first_mile_tracking_number",
            name_request='Unbind first mile tracking number in Shopee API',
            required_params=['tracking_number', 'order_list'],
            method='POST',
            **kwargs
        )

    def first_mile_get_tracking_number_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_tracking_number_list",
            name_request='Get tracking number list from Shopee API',
            method='GET',
            **kwargs
        )

    def first_mile_get_waybill(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_waybill",
            name_request='Get waybill from Shopee API',
            required_params=['tracking_number'],
            method='GET',
            **kwargs
        )

    def first_mile_get_channel_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_channel_list",
            name_request='Get channel list from Shopee API',
            method='GET',
            **kwargs
        )

    def first_mile_get_courier_delivery_channel_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_courier_delivery_channel_list",
            name_request='Get courier delivery channel list from Shopee API',
            method='GET',
            **kwargs
        )

    def first_mile_get_transit_warehouse_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_transit_warehouse_list",
            name_request='Get transit warehouse list from Shopee API',
            method='GET',
            **kwargs
        )

    def first_mile_generate_and_bind_first_mile_tracking_number(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/generate_and_bind_first_mile_tracking_number",
            name_request='Generate and bind first mile tracking number in Shopee API',
            required_params=['order_list'],
            method='POST',
            **kwargs
        )

    def first_mile_bind_courier_delivery_first_mile_tracking_number(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/bind_courier_delivery_first_mile_tracking_number",
            name_request='Bind courier delivery first mile tracking number in Shopee API',
            required_params=['tracking_number', 'order_list'],
            method='POST',
            **kwargs
        )

    def first_mile_unbind_first_mile_tracking_number_all(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/unbind_first_mile_tracking_number_all",
            name_request='Unbind first mile tracking number all in Shopee API',
            required_params=['tracking_number'],
            method='POST',
            **kwargs
        )

    def first_mile_get_courier_delivery_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_courier_delivery_detail",
            name_request='Get courier delivery detail from Shopee API',
            required_params=['tracking_number'],
            method='GET',
            **kwargs
        )

    def first_mile_get_courier_delivery_waybill(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_courier_delivery_waybill",
            name_request='Get courier delivery waybill from Shopee API',
            required_params=['tracking_number'],
            method='GET',
            **kwargs
        )

    def first_mile_get_courier_delivery_tracking_number_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/first_mile/get_courier_delivery_tracking_number_list",
            name_request='Get courier delivery tracking number list from Shopee API',
            method='GET',
            **kwargs
        )

    # Payment APIs
    def payment_get_escrow_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_escrow_detail",
            name_request='Get escrow detail from Shopee API',
            required_params=['escrow_id'],
            method='GET',
            **kwargs
        )

    def payment_set_shop_installment_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/set_shop_installment_status",
            name_request='Set shop installment status in Shopee API',
            required_params=['is_enabled'],
            method='POST',
            **kwargs
        )

    def payment_get_shop_installment_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_shop_installment_status",
            name_request='Get shop installment status from Shopee API',
            method='GET',
            **kwargs
        )

    def payment_get_payout_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_payout_detail",
            name_request='Get payout detail from Shopee API',
            required_params=['payout_id'],
            method='GET',
            **kwargs
        )

    def payment_set_item_installment_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/set_item_installment_status",
            name_request='Set item installment status in Shopee API',
            required_params=['item_id', 'is_enabled'],
            method='POST',
            **kwargs
        )

    def payment_get_item_installment_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_item_installment_status",
            name_request='Get item installment status from Shopee API',
            required_params=['item_id'],
            method='GET',
            **kwargs
        )

    def payment_get_payment_method_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_payment_method_list",
            name_request='Get payment method list from Shopee API',
            method='GET',
            **kwargs
        )

    def payment_get_wallet_transaction_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_wallet_transaction_list",
            name_request='Get wallet transaction list from Shopee API',
            method='GET',
            **kwargs
        )

    def payment_get_escrow_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_escrow_list",
            name_request='Get escrow list from Shopee API',
            method='GET',
            **kwargs
        )

    def payment_get_payout_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_payout_info",
            name_request='Get payout info from Shopee API',
            method='GET',
            **kwargs
        )

    def payment_get_billing_transaction_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_billing_transaction_info",
            name_request='Get billing transaction info from Shopee API',
            required_params=['transaction_id'],
            method='GET',
            **kwargs
        )

    def payment_get_escrow_detail_batch(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_escrow_detail_batch",
            name_request='Get escrow detail batch from Shopee API',
            required_params=['escrow_id_list'],
            method='GET',
            **kwargs
        )

    def payment_generate_income_statement(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/generate_income_statement",
            name_request='Generate income statement in Shopee API',
            required_params=['start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def payment_get_income_statement(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_income_statement",
            name_request='Get income statement from Shopee API',
            required_params=['task_id'],
            method='GET',
            **kwargs
        )

    def payment_generate_income_report(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/generate_income_report",
            name_request='Generate income report in Shopee API',
            required_params=['start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def payment_get_income_report(self, **kwargs):
        return self._call_api(
            path="/api/v2/payment/get_income_report",
            name_request='Get income report from Shopee API',
            required_params=['task_id'],
            method='GET',
            **kwargs
        )

    # Discount APIs
    def discount_add_discount(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/add_discount",
            name_request='Add discount in Shopee API',
            required_params=['discount_name', 'start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def discount_add_discount_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/add_discount_item",
            name_request='Add discount item in Shopee API',
            required_params=['discount_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def discount_delete_discount(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/delete_discount",
            name_request='Delete discount in Shopee API',
            required_params=['discount_id'],
            method='POST',
            **kwargs
        )

    def discount_delete_discount_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/delete_discount_item",
            name_request='Delete discount item in Shopee API',
            required_params=['discount_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def discount_get_discount(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/get_discount",
            name_request='Get discount from Shopee API',
            required_params=['discount_id'],
            method='GET',
            **kwargs
        )

    def discount_get_discount_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/get_discount_list",
            name_request='Get discount list from Shopee API',
            method='GET',
            **kwargs
        )

    def discount_update_discount(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/update_discount",
            name_request='Update discount in Shopee API',
            required_params=['discount_id'],
            method='POST',
            **kwargs
        )

    def discount_update_discount_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/update_discount_item",
            name_request='Update discount item in Shopee API',
            required_params=['discount_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def discount_end_discount(self, **kwargs):
        return self._call_api(
            path="/api/v2/discount/end_discount",
            name_request='End discount in Shopee API',
            required_params=['discount_id'],
            method='POST',
            **kwargs
        )

    # Bundle Deal APIs
    def bundle_deal_add_bundle_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/add_bundle_deal",
            name_request='Add bundle deal in Shopee API',
            required_params=['bundle_deal_name', 'start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def bundle_deal_add_bundle_deal_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/add_bundle_deal_item",
            name_request='Add bundle deal item in Shopee API',
            required_params=['bundle_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def bundle_deal_get_bundle_deal_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/get_bundle_deal_list",
            name_request='Get bundle deal list from Shopee API',
            method='GET',
            **kwargs
        )

    def bundle_deal_get_bundle_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/get_bundle_deal",
            name_request='Get bundle deal from Shopee API',
            required_params=['bundle_deal_id'],
            method='GET',
            **kwargs
        )

    def bundle_deal_get_bundle_deal_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/get_bundle_deal_item",
            name_request='Get bundle deal item from Shopee API',
            required_params=['bundle_deal_id'],
            method='GET',
            **kwargs
        )

    def bundle_deal_update_bundle_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/update_bundle_deal",
            name_request='Update bundle deal in Shopee API',
            required_params=['bundle_deal_id'],
            method='POST',
            **kwargs
        )

    def bundle_deal_update_bundle_deal_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/update_bundle_deal_item",
            name_request='Update bundle deal item in Shopee API',
            required_params=['bundle_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def bundle_deal_end_bundle_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/end_bundle_deal",
            name_request='End bundle deal in Shopee API',
            required_params=['bundle_deal_id'],
            method='POST',
            **kwargs
        )

    def bundle_deal_delete_bundle_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/delete_bundle_deal",
            name_request='Delete bundle deal in Shopee API',
            required_params=['bundle_deal_id'],
            method='POST',
            **kwargs
        )

    def bundle_deal_delete_bundle_deal_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/bundle_deal/delete_bundle_deal_item",
            name_request='Delete bundle deal item in Shopee API',
            required_params=['bundle_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    # Add On Deal APIs
    def add_on_deal_add_add_on_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/add_add_on_deal",
            name_request='Add add on deal in Shopee API',
            required_params=['add_on_deal_name', 'start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def add_on_deal_add_add_on_deal_main_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/add_add_on_deal_main_item",
            name_request='Add add on deal main item in Shopee API',
            required_params=['add_on_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def add_on_deal_add_add_on_deal_sub_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/add_add_on_deal_sub_item",
            name_request='Add add on deal sub item in Shopee API',
            required_params=['add_on_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def add_on_deal_delete_add_on_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/delete_add_on_deal",
            name_request='Delete add on deal in Shopee API',
            required_params=['add_on_deal_id'],
            method='POST',
            **kwargs
        )

    def add_on_deal_delete_add_on_deal_main_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/delete_add_on_deal_main_item",
            name_request='Delete add on deal main item in Shopee API',
            required_params=['add_on_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def add_on_deal_delete_add_on_deal_sub_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/delete_add_on_deal_sub_item",
            name_request='Delete add on deal sub item in Shopee API',
            required_params=['add_on_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def add_on_deal_get_add_on_deal_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/get_add_on_deal_list",
            name_request='Get add on deal list from Shopee API',
            method='GET',
            **kwargs
        )

    def add_on_deal_get_add_on_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/get_add_on_deal",
            name_request='Get add on deal from Shopee API',
            required_params=['add_on_deal_id'],
            method='GET',
            **kwargs
        )

    def add_on_deal_get_add_on_deal_main_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/get_add_on_deal_main_item",
            name_request='Get add on deal main item from Shopee API',
            required_params=['add_on_deal_id'],
            method='GET',
            **kwargs
        )

    def add_on_deal_get_add_on_deal_sub_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/get_add_on_deal_sub_item",
            name_request='Get add on deal sub item from Shopee API',
            required_params=['add_on_deal_id'],
            method='GET',
            **kwargs
        )

    def add_on_deal_update_add_on_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/update_add_on_deal",
            name_request='Update add on deal in Shopee API',
            required_params=['add_on_deal_id'],
            method='POST',
            **kwargs
        )

    def add_on_deal_update_add_on_deal_main_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/update_add_on_deal_main_item",
            name_request='Update add on deal main item in Shopee API',
            required_params=['add_on_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def add_on_deal_update_add_on_deal_sub_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/update_add_on_deal_sub_item",
            name_request='Update add on deal sub item in Shopee API',
            required_params=['add_on_deal_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def add_on_deal_end_add_on_deal(self, **kwargs):
        return self._call_api(
            path="/api/v2/add_on_deal/end_add_on_deal",
            name_request='End add on deal in Shopee API',
            required_params=['add_on_deal_id'],
            method='POST',
            **kwargs
        )

    # Voucher APIs
    def voucher_add_voucher(self, **kwargs):
        return self._call_api(
            path="/api/v2/voucher/add_voucher",
            name_request='Add voucher in Shopee API',
            required_params=['voucher_name', 'start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def voucher_delete_voucher(self, **kwargs):
        return self._call_api(
            path="/api/v2/voucher/delete_voucher",
            name_request='Delete voucher in Shopee API',
            required_params=['voucher_id'],
            method='POST',
            **kwargs
        )

    def voucher_end_voucher(self, **kwargs):
        return self._call_api(
            path="/api/v2/voucher/end_voucher",
            name_request='End voucher in Shopee API',
            required_params=['voucher_id'],
            method='POST',
            **kwargs
        )

    def voucher_update_voucher(self, **kwargs):
        return self._call_api(
            path="/api/v2/voucher/update_voucher",
            name_request='Update voucher in Shopee API',
            required_params=['voucher_id'],
            method='POST',
            **kwargs
        )

    def voucher_get_voucher(self, **kwargs):
        return self._call_api(
            path="/api/v2/voucher/get_voucher",
            name_request='Get voucher from Shopee API',
            required_params=['voucher_id'],
            method='GET',
            **kwargs
        )

    def voucher_get_voucher_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/voucher/get_voucher_list",
            name_request='Get voucher list from Shopee API',
            method='GET',
            **kwargs
        )

    # Shop Flash Sale APIs
    def shop_flash_sale_get_time_slot_id(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/get_time_slot_id",
            name_request='Get time slot id from Shopee API',
            method='GET',
            **kwargs
        )

    def shop_flash_sale_create_shop_flash_sale(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/create_shop_flash_sale",
            name_request='Create shop flash sale in Shopee API',
            required_params=['time_slot_id', 'start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def shop_flash_sale_get_item_criteria(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/get_item_criteria",
            name_request='Get item criteria from Shopee API',
            method='GET',
            **kwargs
        )

    def shop_flash_sale_add_shop_flash_sale_items(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/add_shop_flash_sale_items",
            name_request='Add shop flash sale items in Shopee API',
            required_params=['shop_flash_sale_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def shop_flash_sale_get_shop_flash_sale_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/get_shop_flash_sale_list",
            name_request='Get shop flash sale list from Shopee API',
            method='GET',
            **kwargs
        )

    def shop_flash_sale_get_shop_flash_sale(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/get_shop_flash_sale",
            name_request='Get shop flash sale from Shopee API',
            required_params=['shop_flash_sale_id'],
            method='GET',
            **kwargs
        )

    def shop_flash_sale_get_shop_flash_sale_items(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/get_shop_flash_sale_items",
            name_request='Get shop flash sale items from Shopee API',
            required_params=['shop_flash_sale_id'],
            method='GET',
            **kwargs
        )

    def shop_flash_sale_update_shop_flash_sale(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/update_shop_flash_sale",
            name_request='Update shop flash sale in Shopee API',
            required_params=['shop_flash_sale_id'],
            method='POST',
            **kwargs
        )

    def shop_flash_sale_update_shop_flash_sale_items(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/update_shop_flash_sale_items",
            name_request='Update shop flash sale items in Shopee API',
            required_params=['shop_flash_sale_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def shop_flash_sale_delete_shop_flash_sale(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/delete_shop_flash_sale",
            name_request='Delete shop flash sale in Shopee API',
            required_params=['shop_flash_sale_id'],
            method='POST',
            **kwargs
        )

    def shop_flash_sale_delete_shop_flash_sale_items(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_flash_sale/delete_shop_flash_sale_items",
            name_request='Delete shop flash sale items in Shopee API',
            required_params=['shop_flash_sale_id', 'item_list'],
            method='POST',
            **kwargs
        )

    # Follow Prize APIs
    def follow_prize_add_follow_prize(self, **kwargs):
        return self._call_api(
            path="/api/v2/follow_prize/add_follow_prize",
            name_request='Add follow prize in Shopee API',
            required_params=['follow_prize_name', 'start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def follow_prize_delete_follow_prize(self, **kwargs):
        return self._call_api(
            path="/api/v2/follow_prize/delete_follow_prize",
            name_request='Delete follow prize in Shopee API',
            required_params=['follow_prize_id'],
            method='POST',
            **kwargs
        )

    def follow_prize_end_follow_prize(self, **kwargs):
        return self._call_api(
            path="/api/v2/follow_prize/end_follow_prize",
            name_request='End follow prize in Shopee API',
            required_params=['follow_prize_id'],
            method='POST',
            **kwargs
        )

    def follow_prize_update_follow_prize(self, **kwargs):
        return self._call_api(
            path="/api/v2/follow_prize/update_follow_prize",
            name_request='Update follow prize in Shopee API',
            required_params=['follow_prize_id'],
            method='POST',
            **kwargs
        )

    def follow_prize_get_follow_prize_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/follow_prize/get_follow_prize_detail",
            name_request='Get follow prize detail from Shopee API',
            required_params=['follow_prize_id'],
            method='GET',
            **kwargs
        )

    def follow_prize_get_follow_prize_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/follow_prize/get_follow_prize_list",
            name_request='Get follow prize list from Shopee API',
            method='GET',
            **kwargs
        )

    # Top Picks APIs
    def top_picks_get_top_picks_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/top_picks/get_top_picks_list",
            name_request='Get top picks list from Shopee API',
            method='GET',
            **kwargs
        )

    def top_picks_add_top_picks(self, **kwargs):
        return self._call_api(
            path="/api/v2/top_picks/add_top_picks",
            name_request='Add top picks in Shopee API',
            required_params=['item_list'],
            method='POST',
            **kwargs
        )

    def top_picks_update_top_picks(self, **kwargs):
        return self._call_api(
            path="/api/v2/top_picks/update_top_picks",
            name_request='Update top picks in Shopee API',
            required_params=['item_list'],
            method='POST',
            **kwargs
        )

    def top_picks_delete_top_picks(self, **kwargs):
        return self._call_api(
            path="/api/v2/top_picks/delete_top_picks",
            name_request='Delete top picks in Shopee API',
            required_params=['item_list'],
            method='POST',
            **kwargs
        )

    # Shop Category APIs
    def shop_category_add_shop_category(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_category/add_shop_category",
            name_request='Add shop category in Shopee API',
            required_params=['category_name'],
            method='POST',
            **kwargs
        )

    def shop_category_get_shop_category_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_category/get_shop_category_list",
            name_request='Get shop category list from Shopee API',
            method='GET',
            **kwargs
        )

    def shop_category_delete_shop_category(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_category/delete_shop_category",
            name_request='Delete shop category in Shopee API',
            required_params=['category_id'],
            method='POST',
            **kwargs
        )

    def shop_category_update_shop_category(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_category/update_shop_category",
            name_request='Update shop category in Shopee API',
            required_params=['category_id'],
            method='POST',
            **kwargs
        )

    def shop_category_add_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_category/add_item_list",
            name_request='Add item list in Shopee API',
            required_params=['category_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def shop_category_get_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_category/get_item_list",
            name_request='Get item list from Shopee API',
            required_params=['category_id'],
            method='GET',
            **kwargs
        )

    def shop_category_delete_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/shop_category/delete_item_list",
            name_request='Delete item list in Shopee API',
            required_params=['category_id', 'item_list'],
            method='POST',
            **kwargs
        )

    # Returns APIs
    def returns_get_return_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/get_return_detail",
            name_request='Get return detail from Shopee API',
            required_params=['return_id'],
            method='GET',
            **kwargs
        )

    def returns_get_return_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/get_return_list",
            name_request='Get return list from Shopee API',
            method='GET',
            **kwargs
        )

    def returns_confirm(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/confirm",
            name_request='Confirm return in Shopee API',
            required_params=['return_id'],
            method='POST',
            **kwargs
        )

    def returns_dispute(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/dispute",
            name_request='Dispute return in Shopee API',
            required_params=['return_id', 'dispute_reason'],
            method='POST',
            **kwargs
        )

    def returns_get_available_solutions(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/get_available_solutions",
            name_request='Get available solutions from Shopee API',
            required_params=['return_id'],
            method='GET',
            **kwargs
        )

    def returns_offer(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/offer",
            name_request='Offer return in Shopee API',
            required_params=['return_id', 'solution'],
            method='POST',
            **kwargs
        )

    def returns_accept_offer(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/accept_offer",
            name_request='Accept offer in Shopee API',
            required_params=['return_id'],
            method='POST',
            **kwargs
        )

    def returns_convert_image(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/convert_image",
            name_request='Convert image in Shopee API',
            required_params=['image_url'],
            method='POST',
            **kwargs
        )

    def returns_upload_proof(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/upload_proof",
            name_request='Upload proof in Shopee API',
            required_params=['return_id', 'proof_type', 'image_url'],
            method='POST',
            **kwargs
        )

    def returns_query_proof(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/query_proof",
            name_request='Query proof from Shopee API',
            required_params=['return_id'],
            method='GET',
            **kwargs
        )

    def returns_get_return_dispute_reason(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/get_return_dispute_reason",
            name_request='Get return dispute reason from Shopee API',
            method='GET',
            **kwargs
        )

    def returns_cancel_dispute(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/cancel_dispute",
            name_request='Cancel dispute in Shopee API',
            required_params=['return_id'],
            method='POST',
            **kwargs
        )

    def returns_get_shipping_carrier(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/get_shipping_carrier",
            name_request='Get shipping carrier from Shopee API',
            method='GET',
            **kwargs
        )

    def returns_upload_shipping_proof(self, **kwargs):
        return self._call_api(
            path="/api/v2/returns/upload_shipping_proof",
            name_request='Upload shipping proof in Shopee API',
            required_params=['return_id', 'tracking_number', 'carrier_id'],
            method='POST',
            **kwargs
        )

    # Account Health APIs
    def account_health_get_shop_performance(self, **kwargs):
        return self._call_api(
            path="/api/v2/account_health/get_shop_performance",
            name_request='Get shop performance from Shopee API',
            method='GET',
            **kwargs
        )

    def account_health_get_metric_source_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/account_health/get_metric_source_detail",
            name_request='Get metric source detail from Shopee API',
            required_params=['metric_type'],
            method='GET',
            **kwargs
        )

    def account_health_get_penalty_point_history(self, **kwargs):
        return self._call_api(
            path="/api/v2/account_health/get_penalty_point_history",
            name_request='Get penalty point history from Shopee API',
            method='GET',
            **kwargs
        )

    def account_health_get_punishment_history(self, **kwargs):
        return self._call_api(
            path="/api/v2/account_health/get_punishment_history",
            name_request='Get punishment history from Shopee API',
            method='GET',
            **kwargs
        )

    def account_health_get_listings_with_issues(self, **kwargs):
        return self._call_api(
            path="/api/v2/account_health/get_listings_with_issues",
            name_request='Get listings with issues from Shopee API',
            method='GET',
            **kwargs
        )

    def account_health_get_late_orders(self, **kwargs):
        return self._call_api(
            path="/api/v2/account_health/get_late_orders",
            name_request='Get late orders from Shopee API',
            method='GET',
            **kwargs
        )

    # Ads APIs
    def ads_get_total_balance(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_total_balance",
            name_request='Get total balance from Shopee API',
            method='GET',
            **kwargs
        )

    def ads_get_shop_toggle_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_shop_toggle_info",
            name_request='Get shop toggle info from Shopee API',
            method='GET',
            **kwargs
        )

    def ads_get_recommended_keyword_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_recommended_keyword_list",
            name_request='Get recommended keyword list from Shopee API',
            required_params=['item_id'],
            method='GET',
            **kwargs
        )

    def ads_get_recommended_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_recommended_item_list",
            name_request='Get recommended item list from Shopee API',
            method='GET',
            **kwargs
        )

    def ads_get_all_cpc_ads_hourly_performance(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_all_cpc_ads_hourly_performance",
            name_request='Get all CPC ads hourly performance from Shopee API',
            required_params=['start_date', 'end_date'],
            method='GET',
            **kwargs
        )

    def ads_get_all_cpc_ads_daily_performance(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_all_cpc_ads_daily_performance",
            name_request='Get all CPC ads daily performance from Shopee API',
            required_params=['start_date', 'end_date'],
            method='GET',
            **kwargs
        )

    def ads_create_auto_product_ads(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/create_auto_product_ads",
            name_request='Create auto product ads in Shopee API',
            required_params=['item_id', 'budget'],
            method='POST',
            **kwargs
        )

    def ads_edit_auto_product_ads(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/edit_auto_product_ads",
            name_request='Edit auto product ads in Shopee API',
            required_params=['campaign_id'],
            method='POST',
            **kwargs
        )

    def ads_get_product_campaign_daily_performance(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_product_campaign_daily_performance",
            name_request='Get product campaign daily performance from Shopee API',
            required_params=['campaign_id', 'start_date', 'end_date'],
            method='GET',
            **kwargs
        )

    def ads_get_product_campaign_hourly_performance(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_product_campaign_hourly_performance",
            name_request='Get product campaign hourly performance from Shopee API',
            required_params=['campaign_id', 'start_date', 'end_date'],
            method='GET',
            **kwargs
        )

    def ads_get_product_level_campaign_id_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_product_level_campaign_id_list",
            name_request='Get product level campaign id list from Shopee API',
            method='GET',
            **kwargs
        )

    def ads_get_product_level_campaign_setting_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_product_level_campaign_setting_info",
            name_request='Get product level campaign setting info from Shopee API',
            required_params=['campaign_id'],
            method='GET',
            **kwargs
        )

    def ads_create_manual_product_ads(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/create_manual_product_ads",
            name_request='Create manual product ads in Shopee API',
            required_params=['item_id', 'budget', 'keyword_list'],
            method='POST',
            **kwargs
        )

    def ads_edit_manual_product_ad_keywords(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/edit_manual_product_ad_keywords",
            name_request='Edit manual product ad keywords in Shopee API',
            required_params=['campaign_id', 'keyword_list'],
            method='POST',
            **kwargs
        )

    def ads_edit_manual_product_ads(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/edit_manual_product_ads",
            name_request='Edit manual product ads in Shopee API',
            required_params=['campaign_id'],
            method='POST',
            **kwargs
        )

    def ads_get_create_product_ad_budget_suggestion(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_create_product_ad_budget_suggestion",
            name_request='Get create product ad budget suggestion from Shopee API',
            required_params=['item_id'],
            method='GET',
            **kwargs
        )

    def ads_get_product_recommended_roi_target(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_product_recommended_roi_target",
            name_request='Get product recommended ROI target from Shopee API',
            required_params=['item_id'],
            method='GET',
            **kwargs
        )

    def ads_get_ads_facil_shop_rate(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_ads_facil_shop_rate",
            name_request='Get ads facil shop rate from Shopee API',
            method='GET',
            **kwargs
        )

    def ads_check_create_gms_product_campaign_eligibility(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/check_create_gms_product_campaign_eligibility",
            name_request='Check create GMS product campaign eligibility from Shopee API',
            required_params=['item_id'],
            method='GET',
            **kwargs
        )

    def ads_create_gms_product_campaign(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/create_gms_product_campaign",
            name_request='Create GMS product campaign in Shopee API',
            required_params=['item_id', 'budget'],
            method='POST',
            **kwargs
        )

    def ads_edit_gms_product_campaign(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/edit_gms_product_campaign",
            name_request='Edit GMS product campaign in Shopee API',
            required_params=['campaign_id'],
            method='POST',
            **kwargs
        )

    def ads_list_gms_user_deleted_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/list_gms_user_deleted_item",
            name_request='List GMS user deleted item from Shopee API',
            method='GET',
            **kwargs
        )

    def ads_edit_gms_item_product_campaign(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/edit_gms_item_product_campaign",
            name_request='Edit GMS item product campaign in Shopee API',
            required_params=['campaign_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def ads_get_gms_campaign_performance(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_gms_campaign_performance",
            name_request='Get GMS campaign performance from Shopee API',
            required_params=['campaign_id', 'start_date', 'end_date'],
            method='GET',
            **kwargs
        )

    def ads_get_gms_item_performance(self, **kwargs):
        return self._call_api(
            path="/api/v2/ads/get_gms_item_performance",
            name_request='Get GMS item performance from Shopee API',
            required_params=['item_id', 'start_date', 'end_date'],
            method='GET',
            **kwargs
        )

    # Public APIs
    def public_get_shops_by_partner(self, **kwargs):
        return self._call_api(
            path="/api/v2/public/get_shops_by_partner",
            name_request='Get shops by partner from Shopee API',
            method='GET',
            **kwargs
        )

    def public_get_merchants_by_partner(self, **kwargs):
        return self._call_api(
            path="/api/v2/public/get_merchants_by_partner",
            name_request='Get merchants by partner from Shopee API',
            method='GET',
            **kwargs
        )

    def public_get_access_token(self, **kwargs):
        return self._call_api(
            path="/api/v2/public/get_access_token",
            name_request='Get access token from Shopee API',
            required_params=['code', 'shop_id'],
            method='POST',
            **kwargs
        )

    def public_refresh_access_token(self, **kwargs):
        return self._call_api(
            path="/api/v2/public/refresh_access_token",
            name_request='Refresh access token from Shopee API',
            required_params=['refresh_token', 'shop_id'],
            method='POST',
            **kwargs
        )

    def public_get_shopee_ip_range(self, **kwargs):
        return self._call_api(
            path="/api/v2/public/get_shopee_ip_range",
            name_request='Get Shopee IP range from Shopee API',
            method='GET',
            **kwargs
        )

    # SBS APIs
    def sbs_get_warehouse_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/sbs/get_warehouse_info",
            name_request='Get warehouse info from Shopee API',
            method='GET',
            **kwargs
        )

    def sbs_get_inventory(self, **kwargs):
        return self._call_api(
            path="/api/v2/sbs/get_inventory",
            name_request='Get inventory from Shopee API',
            method='GET',
            **kwargs
        )

    def sbs_get_expiry_report(self, **kwargs):
        return self._call_api(
            path="/api/v2/sbs/get_expiry_report",
            name_request='Get expiry report from Shopee API',
            method='GET',
            **kwargs
        )

    def sbs_get_stock_aging(self, **kwargs):
        return self._call_api(
            path="/api/v2/sbs/get_stock_aging",
            name_request='Get stock aging from Shopee API',
            method='GET',
            **kwargs
        )

    def sbs_get_stock_movement(self, **kwargs):
        return self._call_api(
            path="/api/v2/sbs/get_stock_movement",
            name_request='Get stock movement from Shopee API',
            method='GET',
            **kwargs
        )

    # FBS Shop APIs
    def fbs_shop_get_enrollment_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/fbs_shop/get_enrollment_status",
            name_request='Get enrollment status from Shopee API',
            method='GET',
            **kwargs
        )

    def fbs_shop_get_invoice_error(self, **kwargs):
        return self._call_api(
            path="/api/v2/fbs_shop/get_invoice_error",
            name_request='Get invoice error from Shopee API',
            method='GET',
            **kwargs
        )

    def fbs_shop_get_sku_block_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/fbs_shop/get_sku_block_status",
            name_request='Get SKU block status from Shopee API',
            method='GET',
            **kwargs
        )

    # Livestream APIs
    def livestream_upload_image(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/upload_image",
            name_request='Upload image in Shopee API',
            required_params=['image'],
            method='POST',
            **kwargs
        )

    def livestream_create_session(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/create_session",
            name_request='Create session in Shopee API',
            required_params=['title', 'start_time', 'end_time'],
            method='POST',
            **kwargs
        )

    def livestream_update_session(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/update_session",
            name_request='Update session in Shopee API',
            required_params=['session_id'],
            method='POST',
            **kwargs
        )

    def livestream_end_session(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/end_session",
            name_request='End session in Shopee API',
            required_params=['session_id'],
            method='POST',
            **kwargs
        )

    def livestream_get_session_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_session_list",
            name_request='Get session list from Shopee API',
            method='GET',
            **kwargs
        )

    def livestream_get_session_detail(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_session_detail",
            name_request='Get session detail from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_add_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/add_item",
            name_request='Add item in Shopee API',
            required_params=['session_id', 'item_id'],
            method='POST',
            **kwargs
        )

    def livestream_delete_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/delete_item",
            name_request='Delete item in Shopee API',
            required_params=['session_id', 'item_id'],
            method='POST',
            **kwargs
        )

    def livestream_update_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/update_item",
            name_request='Update item in Shopee API',
            required_params=['session_id', 'item_id'],
            method='POST',
            **kwargs
        )

    def livestream_get_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_item_list",
            name_request='Get item list from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_get_metrics(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_metrics",
            name_request='Get metrics from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_get_comment_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_comment_list",
            name_request='Get comment list from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_get_latest_comment_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_latest_comment_list",
            name_request='Get latest comment list from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_post_comment(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/post_comment",
            name_request='Post comment in Shopee API',
            required_params=['session_id', 'comment'],
            method='POST',
            **kwargs
        )

    def livestream_ban_user_comment(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/ban_user_comment",
            name_request='Ban user comment in Shopee API',
            required_params=['session_id', 'user_id'],
            method='POST',
            **kwargs
        )

    def livestream_unban_user_comment(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/unban_user_comment",
            name_request='Unban user comment in Shopee API',
            required_params=['session_id', 'user_id'],
            method='POST',
            **kwargs
        )

    # Additional Public APIs
    def public_get_token_by_resend_code(self, **kwargs):
        return self._call_api(
            path="/api/v2/public/get_token_by_resend_code",
            name_request='Get token by resend code from Shopee API',
            required_params=['code', 'shop_id'],
            method='POST',
            **kwargs
        )

    def public_get_shopee_ip_ranges(self, **kwargs):
        return self._call_api(
            path="/api/v2/public/get_shopee_ip_ranges",
            name_request='Get Shopee IP ranges from Shopee API',
            method='GET',
            **kwargs
        )

    # Additional SBS APIs
    def sbs_get_bound_whs_info(self, **kwargs):
        return self._call_api(
            path="/api/v2/sbs/get_bound_whs_info",
            name_request='Get bound warehouse info from Shopee API',
            method='GET',
            **kwargs
        )

    def sbs_get_current_inventory(self, **kwargs):
        return self._call_api(
            path="/api/v2/sbs/get_current_inventory",
            name_request='Get current inventory from Shopee API',
            method='GET',
            **kwargs
        )

    # Additional FBS Shop APIs
    def fbs_query_br_shop_enrollment_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/fbs/query_br_shop_enrollment_status",
            name_request='Query BR shop enrollment status from Shopee API',
            method='GET',
            **kwargs
        )

    def fbs_query_br_shop_invoice_error(self, **kwargs):
        return self._call_api(
            path="/api/v2/fbs/query_br_shop_invoice_error",
            name_request='Query BR shop invoice error from Shopee API',
            method='GET',
            **kwargs
        )

    def fbs_query_br_shop_block_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/fbs/query_br_shop_block_status",
            name_request='Query BR shop block status from Shopee API',
            method='GET',
            **kwargs
        )

    def fbs_query_br_sku_block_status(self, **kwargs):
        return self._call_api(
            path="/api/v2/fbs/query_br_sku_block_status",
            name_request='Query BR SKU block status from Shopee API',
            method='GET',
            **kwargs
        )

    # Additional Livestream APIs
    def livestream_start_session(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/start_session",
            name_request='Start session in Shopee API',
            required_params=['session_id'],
            method='POST',
            **kwargs
        )

    def livestream_add_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/add_item_list",
            name_request='Add item list in Shopee API',
            required_params=['session_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def livestream_delete_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/delete_item_list",
            name_request='Delete item list in Shopee API',
            required_params=['session_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def livestream_update_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/update_item_list",
            name_request='Update item list in Shopee API',
            required_params=['session_id', 'item_list'],
            method='POST',
            **kwargs
        )

    def livestream_get_item_count(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_item_count",
            name_request='Get item count from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_update_show_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/update_show_item",
            name_request='Update show item in Shopee API',
            required_params=['session_id', 'item_id'],
            method='POST',
            **kwargs
        )

    def livestream_delete_show_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/delete_show_item",
            name_request='Delete show item in Shopee API',
            required_params=['session_id', 'item_id'],
            method='POST',
            **kwargs
        )

    def livestream_get_show_item(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_show_item",
            name_request='Get show item from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_get_like_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_like_item_list",
            name_request='Get like item list from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_get_recent_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_recent_item_list",
            name_request='Get recent item list from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_get_item_set_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_item_set_list",
            name_request='Get item set list from Shopee API',
            method='GET',
            **kwargs
        )

    def livestream_get_item_set_item_list(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_item_set_item_list",
            name_request='Get item set item list from Shopee API',
            required_params=['item_set_id'],
            method='GET',
            **kwargs
        )

    def livestream_apply_item_set(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/apply_item_set",
            name_request='Apply item set in Shopee API',
            required_params=['session_id', 'item_set_id'],
            method='POST',
            **kwargs
        )

    def livestream_get_session_metric(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_session_metric",
            name_request='Get session metric from Shopee API',
            required_params=['session_id'],
            method='GET',
            **kwargs
        )

    def livestream_get_session_item_metric(self, **kwargs):
        return self._call_api(
            path="/api/v2/livestream/get_session_item_metric",
            name_request='Get session item metric from Shopee API',
            required_params=['session_id', 'item_id'],
            method='GET',
            **kwargs
        )
