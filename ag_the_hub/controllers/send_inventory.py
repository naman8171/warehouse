from odoo import fields as odoo_fields, http, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, AccessError, MissingError, UserError, AccessDenied
from odoo.http import content_disposition, Controller, request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools.misc import xlwt
from odoo.http import request, content_disposition
import uuid
import xlrd
# import tempfile
# import binascii
import io
import pandas as pd
from lxml import etree
import logging

_logger = logging.getLogger(__name__)

class SendInventoryPortal(CustomerPortal):

    # def _get_product_base_domain(self):
    #     search_domain_base = [
    #         ('responsible_id', '=', request.env.user.id),
    #     ]
    #     return search_domain_base

    # def _get_search_products(self, product_search):
    #     # TDE FIXME: make me generic (slides, event, ...)
    #     product_ids = set(request.httprequest.form.getlist('product_id'))
    #     try:
    #         product_ids.update(literal_eval(product_search))
    #     except Exception:
    #         pass
    #     # perform a search to filter on existing / valid tags implicitly
    #     return request.env['product.product'].sudo().search([('id', 'in', list(product_ids)), ('responsible_id', '=', request.env.user.id)])

    @route(['/send/inventory/portal', '/send/inventory/portal/<int:wro_id>'], type='http', auth="user", website=True)
    def send_inventory_portal(self, wro_id=False, **searches):
        # eeeeeeee
        warehouse_receive_id = False
        wro_line_ids = False
        wro_single_sku_per_box_ids = False
        wro_single_sku_per_pallet_ids = False
        if wro_id:
            warehouse_receive_id = request.env['warehouse.receive.order'].sudo().browse(wro_id)
            if warehouse_receive_id.wro_line_ids:
                wro_line_ids = warehouse_receive_id.wro_line_ids
            if warehouse_receive_id.shipping_type == 'parcel':
                if warehouse_receive_id.inventory_type_parcel == 'single':
                    wro_single_sku_per_box_ids = warehouse_receive_id.wro_single_sku_per_box_ids
            if warehouse_receive_id.shipping_type == 'pallet':
                if warehouse_receive_id.inventory_type_pallet == 'single':
                    wro_single_sku_per_pallet_ids = warehouse_receive_id.wro_single_sku_per_pallet_ids

        # eeeeee
        # searches.setdefault('search', '')
        # searches.setdefault('products', '')
        # search_domain_base = self._get_product_base_domain()
        # search_domain = search_domain_base

        # search on content
        # if searches.get('search'):
        #     search_domain = expression.AND([
        #         search_domain,
        #         [('name', 'ilike', searches['search'])]
        #     ])

        # search on products
        # search_product_ids = self._get_search_products(searches['products'])
        # print("*search_domain_base****************", search_domain_base)
        # print("*search_domain****************", search_domain)
        # print("*search_product_ids****************", search_product_ids)
        
        # if search_product_ids:
        #     search_domain = expression.AND([
        #         search_domain,
        #         [('sponsor_type_id', 'in', search_sponsorships.ids)]
        #     ])

        warehouse_ids = request.env['stock.warehouse'].sudo().search([])
        res_company = request.env.company
        product_ids = request.env['product.product'].sudo().search([('responsible_id', '=', request.env.user.id)])
        box_size_ids = request.env['box.size'].sudo().search([('type','=','box')],order='sequence asc')

        quantity_update = False
        if searches.get("next"):
            quantity_update = True    
        values = {
            'wro_id': warehouse_receive_id,
            'wro_name': warehouse_receive_id.name if warehouse_receive_id else False,
            'warehouse_ids': warehouse_ids,
            'wh_id' : warehouse_receive_id and warehouse_receive_id.warehouse_id or False,
            'res_company': res_company,
            'product_ids': product_ids,
            'box_size_ids':box_size_ids,
            'shipping_type': warehouse_receive_id and warehouse_receive_id.shipping_type or False,
            'quantity_update':quantity_update,
            'inventory_type_parcel': warehouse_receive_id and warehouse_receive_id.inventory_type_parcel or False,
            'inventory_type_pallet': warehouse_receive_id and warehouse_receive_id.inventory_type_pallet or False,
            # 'search_product_ids': search_product_ids,
            'wro_line_ids': wro_line_ids,
            'wro_single_sku_per_box_ids': wro_single_sku_per_box_ids,
            'wro_single_sku_per_pallet_ids': wro_single_sku_per_pallet_ids,
            'arrival_date': warehouse_receive_id and warehouse_receive_id.arrival_date or False,
            'pickup_method': warehouse_receive_id and warehouse_receive_id.pickup_method,
            'user_id':request.env.user,
            'current':'sendinve'
        }
        return request.render("ag_the_hub.portal_send_inventory_form", values)

    @route(['/print/label/<int:wro_line_id>'], type='http', auth="user", website=True)
    def print_label_portal(self, wro_line_id=False, **kw):
        wro_line_id = request.env['wro.lines'].sudo().browse(wro_line_id)
        if wro_line_id.wro_id.shipping_type == 'parcel':
            wro_single_sku_per_box_id = request.env['wro.single.sku.per.box'].search([('product_id', '=', wro_line_id.product_id.id), ('wro_id', '=', wro_line_id.wro_id.id)])
            return self._show_report(
                        model=wro_single_sku_per_box_id, 
                        report_type='pdf', 
                        report_ref='ag_the_hub.action_print_label_single_sku_per_box', 
                        download=False)
        if wro_line_id.wro_id.shipping_type == 'pallet':
            wro_single_sku_per_pallet_id = request.env['wro.single.sku.per.pallet'].search([('product_id', '=', wro_line_id.product_id.id), ('wro_id', '=', wro_line_id.wro_id.id)])
            return self._show_report(
                        model=wro_single_sku_per_pallet_id, 
                        report_type='pdf', 
                        report_ref='ag_the_hub.action_print_label_single_sku_per_pallet', 
                        download=False)


    @route(['/print/duplicate/box/label/<int:wro_line_id>'], type='http', auth="user", website=True)
    def print_label_portal_parcel(self, wro_line_id=False, **kw):
        wro_single_sku_per_box_id = request.env['wro.single.sku.per.box'].sudo().browse(wro_line_id)
        return self._show_report(
                    model=wro_single_sku_per_box_id, 
                    report_type='pdf', 
                    report_ref='ag_the_hub.action_print_label_single_sku_per_box_product_line', 
                    download=False)
    

    @route(['/print/duplicate/pallet/label/<int:wro_line_id>'], type='http', auth="user", website=True)
    def print_label_portal_pallet_with_storage(self, wro_line_id=False, **kw):
        wro_single_sku_per_pallet_id = request.env['wro.single.sku.per.pallet'].sudo().browse(wro_line_id)
        return self._show_report(
                        model=wro_single_sku_per_pallet_id, 
                        report_type='pdf', 
                        report_ref='ag_the_hub.action_print_label_single_sku_per_pallet_with_storage_location', 
                        download=False)



    @route(['/print/duplicate/box/label/storage/<int:wro_line_id>'], type='http', auth="user", website=True)
    def print_label_portal_box_with_storage(self, wro_line_id=False, **kw):
        wro_single_sku_per_pallet_id = request.env['wro.single.sku.per.pallet'].sudo().browse(wro_line_id)
        return self._show_report(
                        model=wro_single_sku_per_pallet_id, 
                        report_type='pdf', 
                        report_ref='ag_the_hub.action_print_label_single_sku_per_box', 
                        download=False)
        
