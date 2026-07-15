# -*- coding: utf-8 -*-

from ast import literal_eval
from operator import itemgetter
import time
import requests
import threading
import json

from odoo import api, fields, models, _

GHN_TOKEN = '6857738e-cfed-11ea-9423-66dcad34373e'
GHN_ENPOINT = 'https://online-gateway.ghn.vn/shiip/public-api'

class ResCountryState(models.Model):
    _inherit = 'res.country.state'
    
    name = fields.Char(string='State Name', required=True, index=True,
               help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton')
    accents = fields.Char('Accents')
    active = fields.Boolean(default=True)
    district_ids = fields.One2many('res.country.district', 'state_id', 'District')
    name_extension = fields.Char(string="Name Extension", index=True)
    ghn_id = fields.Char('Origin ID', index=True)

    def check_existing(self, name, ghn_id, NameExtension):
        country_id = self.env.ref('base.vn')
        check_id = self.search(['|', ('ghn_id','=',ghn_id),('name','in',NameExtension),('country_id', '=', country_id.id),('active','in',[True,False])], limit=1)
        return check_id

    def _procure_ghn_province(self):
        payload = ""
        url = GHN_ENPOINT + '/master-data/province'
        response = requests.request("GET", url, data=payload, headers={'Content-Type': "application/json", 'Token': GHN_TOKEN })
        value = json.loads(response.text)
        if value.get('code') == 200 and value.get('data'):
            state_ids = []
            state_ghn_available = []
            for item in value.get('data'):
                ProvinceID = item.get('ProvinceID')
                ProvinceName = item.get('ProvinceName').strip().replace("  ", " ")
                NameExtension = item.get('NameExtension',[]) or []
                Code = item.get('Code')
                country_id = self.env.ref('base.vn').id
                state_id = self.env['res.country.state'].check_existing(ProvinceName,ProvinceID,NameExtension)
                state_ghn_available.append(str(ProvinceID))
                NameExtension = NameExtension and ','.join(NameExtension) or ""
                if not state_id:
                    state_id = self.env['res.country.state'].create({
                        'name': ProvinceName, 
                        'ghn_id': int(ProvinceID), 
                        'country_id': country_id,
                        'code': 'ghn%s'%Code,
                        'name_extension': NameExtension,
                        'active': True,
                    })
                else:
                    if state_id.ghn_id !=  int(ProvinceID):
                        state_id.write({
                            'ghn_id': int(ProvinceID),
                            'active': True,
                            'name_extension': NameExtension,
                        })
                state_ids.append(state_id)
                # self._procure_ghn_district(state_id)
            self.search([('country_id', '=', country_id),('ghn_id', 'not in', state_ghn_available)]).active = False
            self.env.cr.commit()
            self._procure_ghn_all_district(state_ids)
        
        print("Lay xong")
        return True

    def check_existing_district(self, state_id,name, ghn_id,NameExtension):
        check_id = self.env['res.country.district'].search(['|','|', ('name','ilike',name), ('name','in',NameExtension), ('ghn_id', '=', ghn_id), ('state_id', '=', state_id.id),('active','in',[True,False])], limit=1)
        return check_id

    def _procure_ghn_all_district(self, state_ids):
        if GHN_TOKEN and GHN_ENPOINT:
            district_value = []
            for state_id in state_ids:
                payload = """{"province_id": %s}"""%(state_id.ghn_id)
                url = GHN_ENPOINT + '/master-data/district'
                response = requests.request("GET", url, data=payload, headers={'Content-Type': "application/json", 'token': GHN_TOKEN})
                value = json.loads(response.text)
                value.update({'local_state_id': state_id})
                district_value.append(value)

            district_ids = []
            for value in district_value:
                district_available_id = []
                if value.get('code') == 200 and value.get('data'):
                    for item in value.get('data'):
                    
                        code = item.get('Code')
                        DistrictName = item.get('DistrictName').strip().replace("  ", " ")
                        DistrictID = item.get('DistrictID')
                        province_id = value.get('local_state_id')
                        NameExtension = item.get('NameExtension',[]) or []
                        #check district
                        district_id = self.check_existing_district(province_id,DistrictName, DistrictID,NameExtension)
                        district_available_id.append(DistrictID)
                        NameExtension = NameExtension and ','.join(NameExtension) or ""
                        if not district_id:
                            district_id = self.env['res.country.district'].create({
                                'name': DistrictName,
                                'state_id': province_id.id,
                                'code': 'ghn%s'%code,
                                'ghn_id': DistrictID,
                                'name_extension': NameExtension,
                                'active': True,
                            })
                        else:
                            if district_id.ghn_id !=  int(DistrictID):
                                district_id.write({
                                    'ghn_id': DistrictID,
                                    'name_extension': NameExtension,
                                    'active': True,
                                })
                        district_ids.append(district_id)

                    self.env['res.country.district'].search([('state_id', '=', province_id.id),('ghn_id', 'not in', district_available_id)]).active = False

            self.env['res.country.district'].search([('state_id.active', '=', False)]).active = False
            self.env.cr.commit()
            self._procure_ghn_all_ward(district_ids)
                
        return True
    
    def check_existing_ward(self, name, ghn_id, district_id,NameExtension):
        check_id = self.env['res.country.wards'].search(['|', '|', ('name','ilike',name),('name','in',NameExtension), ('ghn_id','=',ghn_id), ('district_id', '=', district_id.id),('active','in',[True,False])], limit=1)
        return check_id

    #11730 / 482
    def _procure_ghn_all_ward(self, district_ids):
        if GHN_TOKEN and GHN_ENPOINT:
            ward_value = []
            for district_id in district_ids:
                payload = """{"district_id": %s}"""%(district_id.ghn_id)
                url = GHN_ENPOINT + '/master-data/ward?district_id'
                response = requests.request("GET", url, data=payload, headers={'Content-Type': "application/json", 'token': GHN_TOKEN})
                value = json.loads(response.text)
                value.update({'local_district_id': district_id})
                ward_value.append(value)
            wards_ids = []
            for value in ward_value:
                wards_available_id = []
                if value.get('code') == 200 and value.get('data'):
                    for item in value.get('data'):
                        ghn_id = item.get('WardCode')
                        district_id = value.get('local_district_id')
                        name = item.get('WardName').strip().replace("  ", " ")
                        NameExtension = item.get('NameExtension',[]) or []
                        #check ward
                        ward_id = self.check_existing_ward(name,ghn_id, district_id,NameExtension)
                        if ghn_id and ghn_id != '':
                            wards_available_id.append(ghn_id)
                            wards_ids.append(ghn_id)
                        NameExtension = NameExtension and ','.join(NameExtension) or ""
                        if not ward_id:
                            if ghn_id:
                                ward_id = self.env['res.country.wards'].create({
                                    'ghn_id': ghn_id, 
                                    'name': name, 
                                    'code': 'ghn%s'%ghn_id,
                                    'district_id': district_id.id, 
                                    'state_id' : district_id.state_id.id,
                                    'name_extension': NameExtension,
                                    'active': True,
                                })
                        else:
                            if ward_id.ghn_id !=  ghn_id:
                                ward_id.write({
                                    'ghn_id': ghn_id,
                                    'name_extension': NameExtension,
                                    'active': True, 
                                })
                    self.env['res.country.wards'].search([('district_id', '=', district_id.id),('ghn_id', 'not in', wards_available_id)]).active = False
                    self.env.cr.commit()
            self.env['res.country.wards'].search([('district_id.active', '=', False)]).active = False
        return True

    def _schedule_province_thread(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            self.sudo()._procure_ghn_province()
            # district_ids = self.env['res.country.district'].sudo().search([('ghn_id', '!=', False)])
            print('=============>debug', district_ids)
            self.env['res.country.state'].sudo()._procure_ghn_all_ward(district_ids)
            self.env.cr.commit()
            new_cr.close()
    
    def GetGhnProvince(self):
        global GHN_TOKEN
        global GHN_ENPOINT
        threaded = threading.Thread(name='GHN get address', target=self._schedule_province_thread)
        threaded.start()