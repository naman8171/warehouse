from odoo import fields, http, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, AccessError, MissingError, UserError, AccessDenied
from odoo.http import content_disposition, Controller, request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools.misc import xlwt
from odoo.http import request, content_disposition
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
import uuid
import xlrd
import tempfile
import binascii
import io
import pandas as pd
from lxml import etree
import logging
import datetime
import base64
import json
import openpyxl
from io import BytesIO
logger = logging.getLogger(__name__)
from odoo.addons.website.controllers.main import QueryURL

import time
try:
    # For Python 3.3+
    time.clock = time.time
except AttributeError:
    pass


class WorkOrderPortal(CustomerPortal):


    @route(['/my/wo/<int:wor_id>'], type='http', auth="user", website=True)
    def portal_wo_id(self, wor_id=None, **post):
        wo_id=request.env['thehub.workorder'].sudo().browse(wor_id)
        
        

        return request.render('ag_the_hub.workorder_form',{'wo_id':wo_id})

    def slicedict(self, d, s):
        return {k: v for k, v in d.items() if k.startswith(s)}



    @route(['/update/user'],type='json', auth='user', website=True)
    def UpdateUser(self, **kw):
        user_id = request.env['res.users'].sudo().search([('id', '=', kw.get('user_id'))])
        user_id.sudo().write({'welcome_done':True})
        return {}

    @route(['/get/product'],type='json', auth='public', website=True)
    def GetProduct(self, **kw):
        product_ids = request.env['product.product'].sudo().search_read([('responsible_id', '=', request.env.user.id)], ['id', 'name'])
        return {'product_ids': product_ids}

    @route(['/add/new/workorder'], type='http', auth="user", website=True)
    def add_new_workorder(self, **kw):
        product_id = self.slicedict(kw, 'product_')
        quantity = self.slicedict(kw, 'quantity_')
        workorder_line_rec = []
        for item in product_id.keys():
            wo_line_dic = {}
            rec = int(item.split('_')[2])
            quant_id = request.env['stock.quant'].sudo().browse(rec)
            if kw.get('quantity_{}'.format(rec)):
                wo_line_dic.update({'product_qty': kw.pop('quantity_{}'.format(rec))})
            package_id = request.env['single.sku.per.box.line'].sudo().search([('package_number','=',quant_id.lot_id.name)])
            if not package_id:
                package_id = request.env['single.sku.per.box.product.line'].sudo().search([('package_number','=',quant_id.lot_id.name)])
                if not package_id:
                    package_id = request.env['single.sku.per.pallet.line'].sudo().search([('package_number','=',quant_id.lot_id.name)])
                    shiping_type = 'pallet'
                else:
                    if package_id.wro_single_sku_per_box_line_id:
                        shiping_type = 'parcel'
                    else:
                        shiping_type = 'pallet'
                    
            else:
                shiping_type = 'parcel'
            #print("33333333333333333",package_id)
            #print("333333333333-----------3333333",shiping_type,package_id.send_as)
            
            wo_line_dic.update({
                'package_id':quant_id.lot_id.id,
                'source_location':quant_id.location_id.id,
                'product_id': quant_id.product_id.id,
                'send_qty':quant_id.quantity,
                'send_as':package_id.send_as,
                'wro_shipping_type':shiping_type,
                'send_as_new':package_id.send_as,
                'wro_shipping_type_new':shiping_type,
                'delivery_address':kw.pop('delivery_address_{}'.format(rec))
                })
            if wo_line_dic:
                workorder_line_rec.append((0,0,wo_line_dic))
            #print("2222222222222222222",workorder_line_rec)
        datetime_obj=False
        if kw.get('scheduled_date') and kw.get('scheduled_date') != '':
            format_str = '%Y-%m-%d' # The format
            datetime_obj = datetime.datetime.strptime(kw.get('scheduled_date'), format_str).date()
            #print(datetime_obj.date())
        #sds
        
        if workorder_line_rec:
            workorder_id = request.env['thehub.workorder'].sudo().create({
                'whom_to_ship': kw.get('whom_to_ship'),
                'merchand_id': int(kw.get('merchand_id')),
                'third_party_ref': kw.get('third_party_ref'),
                'partner_id': int(kw.get('partner_id')),
                'shipping_type': kw.get('shipping_type'),
                'payment_type': kw.get('payment_type'),
                'schedule_pickup':datetime_obj,
                'three_plcompany':int(kw.get('multi_pl_company')) if kw.get('payment_type') == 'My own 3PL Arrangement' else False,
                'packaging_instructions': kw.get('packaging_instructions'),
                'wo_line_ids':workorder_line_rec
            })
        else:
            raise UserError('Please Add Product First')
        
            # except (AccessError, MissingError, ValidationError) as e:
            #     raise UserError(_(e))
        return request.redirect('/my/workorders')


    @route(['/wo/download/sample/template'], type='http', auth="user", website=True)
    def wo_download_sample_template(self, **kw):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet', cell_overwrite_ok=True)
        worksheet.row(0).height = 10 * 50
        worksheet.col(0).width = 100 * 50
        worksheet.col(1).width = 100 * 50
        worksheet.col(2).width = 100 * 50
        worksheet.col(3).width = 100 * 50
        worksheet.col(4).width = 100 * 100
        worksheet.col(5).width = 100 * 100
        worksheet.col(6).width = 100 * 50
        worksheet.col(7).width = 100 * 100
        worksheet.col(8).width = 100 * 100
        worksheet.col(9).width = 100 * 100
        
        ###################  STYLES ###############################
        header_style = xlwt.easyxf("font: bold on, height 250; align: wrap on, vert center, horiz center;")
        
        plain = xlwt.easyxf()
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        ########################### EXCEL SHEET ##################################
        worksheet.write(0,0, 'Product SKU', header_style)
        worksheet.write(0,1, 'Transfer QTY', header_style)
        worksheet.write(0,2, 'Delivery Address', header_style)
        worksheet.write(0,3, 'Weight', header_style)
        worksheet.write(0,4, 'Consolidated Type', header_style)
        worksheet.write(0,5, 'Stock Type', header_style)
        worksheet.write(0,6, 'Location Name', header_style)
        worksheet.write(0,7, 'Package Name', header_style)
        
        worksheet.write(18,9, 'Consolidate Type', header_style)
        worksheet.write(18,10, 'consolidated', header_style)
        worksheet.write(19,10, 'non_consolidated', header_style)

        worksheet.write(20,9, 'Stock Type', header_style)
        worksheet.write(20,10, 'LIFO', header_style)
        worksheet.write(21,10, 'FIFO', header_style)
        
        file_data = BytesIO()
        workbook.save(file_data)
        file_data.seek(0)
        
        # Return the file directly as a response
        return request.make_response(
            file_data.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition('sample_report.xls'))
            ]
        )

    @route(['/import/new/workorder'], type='http', auth="user", website=True)
    def import_new_workorder(self, **kw):
        product_id = self.slicedict(kw, 'product_')
        quantity = self.slicedict(kw, 'quantity_')
        workorder_line_rec = []
        if kw.get('att'):
            file = base64.b64encode(kw.get('att').read())
            file_name = kw.get('att')
            # try:
            fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
            fp.write(binascii.a2b_base64(file)) # self.xls_file is your binary field
            fp.seek(0)
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            product_list=[]
            stock_not_list=[]
            # wo_lines=[]
            merchant_id = request.env['res.partner'].sudo().browse(int(kw.get('merchand_id')))
            if not merchant_id:
                merchant_id = request.env.user.partner_id
            datetime_obj=False
            if kw.get('scheduled_date') and kw.get('scheduled_date') != '':
                format_str = '%Y-%m-%d' # The format
                datetime_obj = datetime.datetime.strptime(kw.get('scheduled_date'), format_str).date()
            workorder_id = request.env['thehub.workorder'].sudo().create({
                'whom_to_ship': kw.get('whom_to_ship'),
                'partner_id': int(kw.get('partner_id')),
                'merchand_id': merchant_id.id,
                'third_party_ref': kw.get('third_party_ref'),
                'shipping_type': kw.get('shipping_type'),
                'payment_type': kw.get('payment_type'),
                'schedule_pickup':datetime_obj,
                'three_plcompany':int(kw.get('multi_pl_company')) if kw.get('payment_type') == 'My own 3PL Arrangement' else False,
                'packaging_instructions': kw.get('packaging_instructions'),
                # 'wo_line_ids':wo_lines,
            })

            for row_no in range(sheet.nrows):
                if row_no <= 0:
                    fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
                else:
                    line = list(map(
                                    lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                        row.value), sheet.row(row_no)))
                    if line[0]:
                        product_id = request.env['product.product'].sudo().search([('default_code','=',line[0]),'|', ('partner_id','=',merchant_id.id), ('partner_id.child_ids','in',merchant_id.ids)],limit=1)
                        if not product_id:
                            product_list.append(line[0])
                            continue

                        if line[5] == 'LIFO':
                            stock_product = request.env['stock.quant'].sudo().search(['|', ('owner_id','=',merchant_id.id), ('owner_id.child_ids','in',merchant_id.ids),('product_id','=',product_id.id),('consolidated_type','=',line[4])],order='create_date desc')
                        else:
                            stock_product = request.env['stock.quant'].sudo().search(['|', ('owner_id','=',merchant_id.id), ('owner_id.child_ids','in',merchant_id.ids), ('product_id','=',product_id.id),('consolidated_type','=',line[4])],order='create_date asc')
                        
                        total_qty =0
                        quant_ids =[]
                        total_qty=0
                        location_ids=[]
                        total_qty =0
                        stock_available_qty=0
                        for quant in stock_product:
                            quantity=quant.quantity - quant.reserved_quantity
                            if quantity>0:
                                stock_available_qty+=quantity

                        if stock_available_qty<float(line[1]):
                            stock_not_list.append(line[0])
                            continue
                        for quant in stock_product:
                            quantity=quant.quantity - quant.reserved_quantity
                            if quantity>0 and float(line[1])>total_qty:
                                total_qty+=quantity
                                quant_ids.append(quant.id)
                                location_ids.append(quant.location_id.id)
                        required_quantity=float(line[1])
                        for quant in quant_ids:
                            stock_product = request.env['stock.quant'].sudo().browse(quant)
                            required_quantity=float(line[1])
                            required_quantity=required_quantity-(stock_product.quantity - stock_product.reserved_quantity)
                            qty=0
                            if required_quantity>0:
                                qty=stock_product.quantity - stock_product.reserved_quantity
                            else:
                                qty=float(line[1])


                            wo_line_id = request.env['thehub.workorder.lines'].sudo().create({
                                'package_id':stock_product.lot_id.id,
                                'product_qty':qty,
                                'product_id': product_id.id,
                                'send_qty':stock_available_qty,
                                'send_as':line[4],
                                'send_as_new':line[4],
                                'source_location':stock_product.location_id.id,
                                'delivery_address':line[2] if line[2] else '',
                                'weight':line[3] if line[2] else '',
                                'location_label':line[6] if line[6] else '',
                                'scan_package_number':line[7] if line[7] else '',
                                'workorder_id': workorder_id.id,
                            })
                            logger.info("Workorder LINE ID*********** :%s" %(wo_line_id))
        logger.info("Workorder ID*********** :%s" %(workorder_id.name))
        return request.redirect('/my/workorders')

    @route(['/my/analytics'], type='http', auth="user", website=True)
    def portal_analytics(self, **kw):
        Workorders = request.env['thehub.workorder'].sudo()
        wro_env = request.env['warehouse.receive.order'].sudo()
        current_month = fields.Date.today().month
        month = fields.Date.today().strftime("%B, %Y")
        # domain = [('merchand_id', '=', request.env.user.partner_id.id)]
        domain = ['|', ('merchand_id', '=', request.env.user.partner_id.id), ('merchand_id', 'in', request.env.user.partner_id.child_ids.ids)]
        wo_pending_count = Workorders.search_count(domain + [('status', '=', 'Pending')])
        wo_awaiting_count = Workorders.search_count(domain + [('status', '=', 'Awaiting')])
        wo_delivered_count = Workorders.search_count(domain + [('status', '=', 'Delivered')])
        wo_returned_count = Workorders.search_count(domain + [('status', '=', 'Returned')])
        cm_wo_pending_count = len(Workorders.search(domain + [('status', '=', 'Pending')]).filtered(lambda x: x.create_date.month == current_month))
        cm_wo_awaiting_count = len(Workorders.search(domain + [('status', '=', 'Awaiting')]).filtered(lambda x: x.create_date.month == current_month))
        cm_wo_delivered_count = len(Workorders.search(domain + [('status', '=', 'Delivered')]).filtered(lambda x: x.create_date.month == current_month))
        cm_wo_returned_count = len(Workorders.search(domain + [('status', '=', 'Returned')]).filtered(lambda x: x.create_date.month == current_month))
        values = {
            'wo_pending_count': wo_pending_count,
            'wo_awaiting_count': wo_awaiting_count,
            'wo_delivered_count': wo_delivered_count,
            'wo_returned_count': wo_returned_count,
            'cm_wo_pending_count': cm_wo_pending_count,
            'cm_wo_awaiting_count': cm_wo_awaiting_count,
            'cm_wo_delivered_count': cm_wo_delivered_count,
            'cm_wo_returned_count': cm_wo_returned_count,
            'month': month,
            'year':fields.Date.today().year

        }



        wro_submitted_count = wro_env.search_count(domain + [('status', '=', 'request_submitted')])
        wro_received_count = wro_env.search_count(domain + [('status', '=', 'received')])
        wro_stored_count = wro_env.search_count(domain + [('status', '=', 'stored')])
        cm_wro_submitted_count = len(wro_env.search(domain + [('status', '=', 'request_submitted')]).filtered(lambda x: x.create_date.month == current_month))
        cm_wro_received_count = len(wro_env.search(domain + [('status', '=', 'received')]).filtered(lambda x: x.create_date.month == current_month))
        cm_wro_stored_count = len(wro_env.search(domain + [('status', '=', 'stored')]).filtered(lambda x: x.create_date.month == current_month))
        values.update({
            
            'wro_submitted_count': wro_submitted_count,
            'wro_received_count': wro_received_count,
            'wro_stored_count': wro_stored_count,
            'cm_wro_submitted_count': cm_wro_submitted_count,
            'cm_wro_received_count': cm_wro_received_count,
            'cm_wro_stored_count': cm_wro_stored_count,
            }
            )
        return request.render("ag_the_hub.portal_my_analytics", values)

    @route(['/my/workorders', '/my/workorders/page/<int:page>','/my/workorders/filter/<string:filter>/page/<int:page>','/my/workorders/filter/<string:filter>','/my/workorders/filter/current_month/<string:monthfilter>','/my/workorders/filter/current_month/<string:monthfilter>/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_workorders(self, page=1, date_begin=None, date_end=None, sortby=None,filter=False,monthfilter=False,search='',order='',groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        partner_ids = request.env['res.partner'].sudo().search(['|', ('merchant_partner_id', '=', request.env.user.partner_id.id), ('merchant_partner_id', 'in', request.env.user.partner_id.child_ids.ids)])
        merchant_ids = request.env['res.partner'].sudo().search([('contact_type','=','Merchant'), '|', ('id', '=', request.env.user.partner_id.id), ('id', 'in', request.env.user.partner_id.child_ids.ids)])
        Workorders = request.env['thehub.workorder'].sudo()
        domain = ['|', ('merchand_id', '=', request.env.user.partner_id.id), ('merchand_id', 'in', request.env.user.partner_id.child_ids.ids)]
        current_month = fields.Date.today().month
        month = fields.Date.today().strftime("%B, %Y")
        current_month_first_date = fields.Date.today().replace(day=1)
        #print("33333333333333333333",current_month_first_date)
        default_url="/my/workorders"
        

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }



        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'Customer': {'input': 'partner_id', 'label': _('Customer')},
            'Merchant': {'input': 'merchand_id', 'label': _('Merchant')},
            'Ship Date': {'input': 'date_create', 'label': _('Ship Date')},
            'Shipping Type': {'input': 'shiping_type', 'label': _('Shipping Type')},
            'Status': {'input': 'status', 'label': _('Status')},
        }
        
        if not sortby:
            sortby = 'date'
        if order=='None':
            order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # Workorders count
        if filter=='pending':
            domain.append(('status', '=', 'Pending'))
        elif filter=='awaiting':
            domain.append(('status', '=', 'Awaiting'))
        elif filter=='returned':
            domain.append(('status', '=', 'Returned'))
        elif filter=='delivered':
            domain.append(('status', '=', 'Delivered'))
        elif filter=='dispatched':
            domain.append(('status', '=', 'Dispatched'))


        elif monthfilter=='pending':
            domain.append(('status', '=', 'Pending'))
            domain.append(('create_date','>=',current_month_first_date))
        elif monthfilter=='awaiting':
            domain.append(('status', '=', 'Awaiting'))
            domain.append(('create_date','>=',current_month_first_date))
        elif monthfilter=='returned':
            domain.append(('status', '=', 'Returned'))
            domain.append(('create_date','>=',current_month_first_date))
        elif monthfilter=='delivered':
            domain.append(('status', '=', 'Delivered'))
            domain.append(('create_date','>=',current_month_first_date))
        elif monthfilter=='dispatched':
            domain.append(('status', '=', 'Dispatched'))
            domain.append(('create_date','>=',current_month_first_date))
        elif monthfilter=='all':
            domain.append(('create_date','>=',current_month_first_date))

        if filter:
            default_url+="/filter/"+filter
        elif monthfilter:
            default_url+="/filter/current_month/"+monthfilter


        if search:
            domain +=['|', '|', '|', ('name','=',search), ('merchand_id', 'ilike', search), ('third_party_ref', 'ilike', search), ('partner_id', 'ilike', search)]
        
        workorders_count = Workorders.search_count(domain)
        # pager
        pager = portal_pager(
            url=default_url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'search':search,'order':order},
            total=workorders_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        workorders = Workorders.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_workorders_history'] = workorders.ids
        pl_companies = request.env['thehub.3plcompanies'].search([('responsible_id','=',request.env.user.id)])
        stock_product = request.env['stock.quant'].sudo().search([('owner_id','=',request.env.user.partner_id.id),('quantity','>',0)], limit=20)
        # stock_product = request.env['stock.quant'].sudo().search([('owner_id','=',request.env.user.partner_id.id)])
        # inventory_ids_list =[]
        # for quant in stock_product:
        #     quantity=quant.quantity - quant.reserved_quantity
        #     if quantity>0:
        #         inventory_ids_list.append(quant.id)
        # stock_product = request.env['stock.quant'].sudo().search([('id','in',inventory_ids_list)])
        keep = QueryURL(default_url, page=page, date_begin=date_begin, date_end=date_end, sortby=sortby,filter=filter,monthfilter=monthfilter,search=search,order=order)
        if groupby == 'Customer':
            grouped_wo = [request.env['thehub.workorder'].sudo().concat(*g) for k, g in groupbyelem(workorders, itemgetter('partner_id'))]
        elif groupby == 'Merchant':
            grouped_wo = [request.env['thehub.workorder'].sudo().concat(*g) for k, g in groupbyelem(workorders, itemgetter('merchand_id'))]
        elif groupby == 'Ship Date':
            grouped_wo = [request.env['thehub.workorder'].sudo().concat(*g) for k, g in groupbyelem(workorders, itemgetter('date_create'))]
        elif groupby == 'Shipping Type':
            grouped_wo = [request.env['thehub.workorder'].sudo().concat(*g) for k, g in groupbyelem(workorders, itemgetter('shipping_type'))]
        elif groupby == 'Status':
            grouped_wo = [request.env['thehub.workorder'].sudo().concat(*g) for k, g in groupbyelem(workorders, itemgetter('status'))]
        else:
            grouped_wo=[workorders]

        
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'workorders': workorders,
            'partner_ids': partner_ids,
            'merchant_ids': merchant_ids,
            'page_name': 'workorder',
            'default_url': '/my/workorders',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'current_user_id':request.env.user,
            'pl_companies':pl_companies,
            'stock_products':stock_product,
            'workorders_count':workorders_count,
            'current':'wo',
            'search':search,
            'default_url':default_url,
            'keep':keep,
            'searchbar_groupby':searchbar_groupby,
            'groupby':groupby,
            'grouped_wo':grouped_wo
        })
        return request.render("ag_the_hub.portal_my_workorders", values)

    @http.route(['/my/wo/search/stock_product'], type='json', auth="user")
    def search_stock_product(self, **post):
        # Debug the raw request body
        raw_data = request.httprequest.data

        # Manually parse the JSON data if post is empty
        if not post and raw_data:
            try:
                post = json.loads(raw_data)
                print("Manually parsed post data:", post)
            except json.JSONDecodeError as e:
                print("Failed to parse JSON:", e)

        search_term = post.get('query', '').strip()

        domain = [
            ('owner_id', '=', request.env.user.partner_id.id),
            ('quantity', '>', 0)
        ]

        if search_term:
            domain+=['|', '|', ('product_id.name','ilike',search_term), ('product_id.default_code','ilike',search_term), ('product_id.barcode','ilike',search_term)]
            # domain.append(('product_id.name', 'ilike', search_term))  # Search by product name
            stock_products = request.env['stock.quant'].sudo().search(domain, limit=20)
        else:
            stock_products = request.env['stock.quant'].sudo().search(domain, limit=20)  # Limit results

        result = [{
                'id': product.id,
                'name': f"{product.product_id.barcode or ''} - {product.product_id.size or ''} - "
                        f"{product.product_id.color or ''} - {product.product_id.name or ''} - "
                        f"{product.product_id.gender or ''}"
            } for product in stock_products]

        return result




    @route(['/print/shipping/label/<int:wo_line_id>'], type='http', auth="user", website=True)
    def print_shipping_label(self, wo_line_id=False, **kw):
        wo_line_id = request.env['thehub.workorder.lines'].sudo().browse(wo_line_id)
        return self._show_report(
                        model=wo_line_id, 
                        report_type='pdf', 
                        report_ref='ag_the_hub.action_print_shipping_label', 
                        download=False)


    @route(['/print/shipping/label/package/<int:wo_line_id>'], type='http', auth="user", website=True)
    def print_shipping_label_package(self, wo_line_id=False, **kw):
        wo_line_id = request.env['thehub.workorder.lines'].sudo().browse(wo_line_id)
        return self._show_report(
                        model=wo_line_id, 
                        report_type='pdf', 
                        report_ref='ag_the_hub.action_print_shipping_label_package', 
                        download=False)


