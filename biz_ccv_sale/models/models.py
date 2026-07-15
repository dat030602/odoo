from odoo import api, fields, models, _
import json


class Base(models.AbstractModel):
    _inherit = 'base'

    def get_list_domain(self, domain):
        list_domain = []
        list_values = []
        for value in domain:
            if isinstance(value, list) and len(value) == 3 and value[1] == 'ilike':
                if value[2] not in list_values:
                    list_values.append(value[2])

        
        for v in list_values:
            domain_temp = [x.copy() if isinstance(x, list) else x for x in domain]
            for idx, value in enumerate(domain, 0):
                if isinstance(value, list) and len(value) == 3 and value[1] == 'ilike':
                    domain_temp[idx][2] = v
            list_domain.append(domain_temp)

        if len(list_domain) >= 2:
            return list_domain

        return domain

    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, count_limit=None):
        model_name = self._name

        results = super(Base, self).web_search_read(
                        domain=domain,
                        fields=fields,
                        offset=offset,
                        limit=limit,
                        order=order,
                        count_limit=count_limit
                    )
        
        if model_name in ['product.template', 'product.product']:
            limit = count_limit
            list_domain = self.get_list_domain(domain)
            if len(list_domain) >= 2 and isinstance(list_domain[0], list):
                results = super(Base, self).web_search_read(
                        domain=list_domain[0],
                        fields=fields,
                        offset=offset,
                        limit=limit,
                        order=order,
                        count_limit=count_limit
                    )
                
                if results and results['records']:
                    records = results['records']
                    for idx, next_domain  in enumerate(list_domain, 1):
                        results_temp = super(Base, self).web_search_read(
                            domain=next_domain,
                            fields=fields,
                            offset=offset,
                            limit=limit,
                            order=order,
                            count_limit=count_limit
                        )
                        
                        records_temp = results_temp['records']
                        if results_temp and results_temp['records']:
                            records = [record for record in records if any(record['id'] == record_temp['id'] for record_temp in records_temp)]
                        else:
                            records = records_temp
            
                    results['records'] = records
                    results['length'] = len(records)

        return results
    
