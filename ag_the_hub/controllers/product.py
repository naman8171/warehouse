from odoo import fields, http, tools, _, SUPERUSER_ID
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
from odoo.addons.website.controllers.main import QueryURL
from odoo.tools import groupby as groupbyelem
from operator import attrgetter, itemgetter
from datetime import date, timedelta


_logger = logging.getLogger(__name__)


class CustomProductPortal(CustomerPortal):
    _items_per_page=10

    @route('/report/product/template/xls', type='http', auth="user")
    def get_report_product_template_xls(self, **kw):
        token = str(uuid.uuid4())
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet', cell_overwrite_ok=True)
        worksheet.row(0).height = 10 * 50
        worksheet.col(0).width = 100 * 50
        worksheet.col(1).width = 100 * 50
        worksheet.col(2).width = 100 * 50
        worksheet.col(3).width = 100 * 50
        ###################  STYLES ###############################
        header_style = xlwt.easyxf("font: bold on, height 250; align: wrap on, vert center, horiz center;")
        
        plain = xlwt.easyxf()
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        ########################### EXCEL SHEET ##################################
        worksheet.write(0,0, 'ItemName', header_style)
        worksheet.write(0,1, 'SKU', header_style)
        worksheet.write(0,2, 'Barcode', header_style)
        worksheet.write(0,3, 'ItemDescription', header_style)
        worksheet.write(0,4, 'gender', header_style)
        worksheet.write(0,5, 'color', header_style)
        worksheet.write(0,6, 'size', header_style)

        worksheet.write(18,9, 'Gender', header_style)
        worksheet.write(18,10, 'male', header_style)
        worksheet.write(19,10, 'female', header_style)
        worksheet.write(20,10, 'unisex', header_style)


        response = request.make_response(None,
        headers=[
                    ('Content-Type', 'application/vnd.ms-excel'),
                    ('Content-Disposition', content_disposition('The_Hub_InventoryImportTemplate.xls'))
                ],
        cookies={'fileToken': token})
        workbook.save(response.stream)
        return response

    @route(['/import/product/excel'], type='http', auth="user", website=True)
    def import_product_excel(self, **kw):
        file = kw.get('file').read()
        fp = io.BytesIO()
        fp.write(file)
        fp.seek(0)
        df = pd.read_excel(fp)
        for ind in df.index:
            product_id = request.env['product.template'].sudo().create({
                    'name': str(df['ItemName'][ind]) if str(df['ItemName'][ind]) != 'nan' else False,
                    'default_code': str(df['SKU'][ind]) if str(df['SKU'][ind]) != 'nan' else False,
                    'detailed_type':'product',
                    'tracking':'lot',
                    'platform': "Excel Upload",
                    'responsible_id': request.env.user.id,
                    'barcode': str(df['Barcode'][ind]) if str(df['Barcode'][ind]) != 'nan' else False,
                    'description': str(df['ItemDescription'][ind]) if str(df['ItemDescription'][ind]) != 'nan' else False,
                    'gender': str(df['gender'][ind]) if str(df['gender'][ind]) != 'nan' else False,
                    'color': str(df['color'][ind]) if str(df['color'][ind]) != 'nan' else False,
                    'size': str(df['size'][ind]) if str(df['size'][ind]) != 'nan' else False
                })
        return request.redirect('/my/products')

    @route(['/add/product/manually'], type='http', auth="user", website=True)
    def add_product_manually(self, **kw):
        product_id = request.env['product.template'].sudo().create({
                'name': kw.get('product_name'),
                'default_code': kw.get('sku_number'),
                'platform': "Added Manually",
                'responsible_id': request.env.user.id,
                'detailed_type':'product',
                'tracking':'lot',
                'size':kw.get('size'),
                'color':kw.get('color'),
                'gender':kw.get('product_gender'),
                'barcode':kw.get('barcode')
            })
        return request.redirect('/my/products')


    @route(['/update/product/manually'], type='http', auth="user", website=True)
    def update_product_manually(self, **kw):
        product_id = request.env['product.template'].sudo().browse(int(kw.get('product_id')))
        if product_id.reorder_level!= kw.get('reorder_limit'):
            request.env['reorder.level.notification'].sudo().create({
                'merchand_id':request.env.user.partner_id.id,
                'product_id':product_id.id,
                'old_reorder_level':product_id.reorder_level,
                'new_reorder_level':kw.get('reorder_limit')
                })
        product_id.sudo().write({'name':kw.get('product_name'),'reorder_level':kw.get('reorder_limit')})
        return request.redirect('/my/products')

    @route(['/my/products', '/my/products/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_products(self, page=1, date_begin=None, date_end=None,order=None, sortby=None, search='',**kw):
        values = self._prepare_portal_layout_values()
        
        Products = request.env['product.template'].sudo()
        domain = [('responsible_id', '=', request.env.user.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        # if sortby ==
        order = order

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        if search:
            domain+=['|', '|', ('name','ilike',search), ('default_code','ilike',search), ('barcode','ilike',search)]

        # products count
        products_count = Products.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/products",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=products_count,
            page=page,
            step=self._items_per_page
        )
        keep = QueryURL('/my/products', page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, search=search)
        # content according to pager and archive selected
        products = Products.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_products_history'] = products.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'products': products,
            'page_name': 'product',
            'default_url': '/my/products',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'search':search,
            'sortby': sortby,
            'keep':keep,
            'current':'products',
            'products_count':products_count
        })
        return request.render("ag_the_hub.portal_my_products", values)



    @route(['/low/stock/products', '/low/stock/products/page/<int:page>'], type='http', auth="user", website=True)
    def portal_low_stock_products(self, page=1, date_begin=None, date_end=None,order=None, sortby=None, search='',**kw):
        values = self._prepare_portal_layout_values()
        
        Products = request.env['product.template'].sudo()
        domain = [('responsible_id', '=', request.env.user.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        # if sortby ==
        order = order

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        if search:
            domain+=[('name','ilike',search)]
        product_list=[]
        for product in Products.search(domain):
            if product.qty_available<=product.reorder_level:
                product_list.append(product.id)
                
        domain=[('id','in',product_list)]
        # products count
        products_count = Products.search_count(domain)
        # pager
        pager = portal_pager(
            url="/low/stock/products",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'search':search},
            total=products_count,
            page=page,
            step=self._items_per_page
        )
        keep = QueryURL('/low/stock/products', page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, search=search)
        # content according to pager and archive selected
        products = Products.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_products_history'] = products.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'products': products,
            'page_name': 'product',
            'default_url': '/low/stock/products',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'search':search,
            'sortby': sortby,
            'keep':keep,
            'current':'products',
            'products_count':products_count
        })
        return request.render("ag_the_hub.portal_my_products", values)



    @route(['/out/stock/products', '/out/stock/products/page/<int:page>'], type='http', auth="user", website=True)
    def portal_out_stock_products(self, page=1, date_begin=None, date_end=None,order=None, sortby=None, search='',**kw):
        values = self._prepare_portal_layout_values()
        
        Products = request.env['product.template'].sudo()
        domain = [('responsible_id', '=', request.env.user.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        # if sortby ==
        order = order

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        if search:
            domain+=[('name','ilike',search)]
        product_list=[]
        for product in Products.search(domain):
            if product.qty_available<=0:
                product_list.append(product.id)
                
        domain=[('id','in',product_list)]
        # products count
        products_count = Products.search_count(domain)
        # pager
        pager = portal_pager(
            url="/out/stock/products",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'search':search},
            total=products_count,
            page=page,
            step=self._items_per_page
        )
        keep = QueryURL('/out/stock/products', page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, search=search)
        # content according to pager and archive selected
        products = Products.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_products_history'] = products.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'products': products,
            'page_name': 'product',
            'default_url': '/out/stock/products',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'search':search,
            'sortby': sortby,
            'keep':keep,
            'current':'products',
            'products_count':products_count
        })
        return request.render("ag_the_hub.portal_my_products", values)


    @route(['/top/selling/products', '/top/selling/products/page/<int:page>'], type='http', auth="user", website=True)
    def portal_top_selling_products(self, page=1, date_begin=None, date_end=None,order=None, sortby=None, search='',**kw):
        values = self._prepare_portal_layout_values()
        
        Products = request.env['product.template'].sudo()
        domain = [('responsible_id', '=', request.env.user.id)]
        current_month = fields.Date.today().month
        current_year = fields.Date.today().year
        last_ten_days_date=fields.Datetime.now()- timedelta(days=10)
        # last_ten_days_day=last_ten_days_date.day
        # last_ten_days_month=last_ten_days_date.month
        month = fields.Date.today().strftime("%B, %Y")
        
        products = Products.search(domain)
        wo_line = request.env['thehub.workorder.lines'].sudo()
        
        record_data = wo_line.sudo().search([('product_id','in',products.ids),('workorder_id','!=',False)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year)
        grouped_data = [wo_line.sudo().concat(*g) for k, g in groupbyelem(record_data, itemgetter('product_id'))]
        data=[]
        for line in grouped_data:
            data.append([line[0].product_id.name,len(line.ids)])

        values.update({
            
            'product_data':data
        })
        return request.render("ag_the_hub.portal_top_selling_products", values)




    # @route(['/my/products/stockonhand', '/my/products/stockonhand/page/<int:page>'], type='http', auth="user", website=True)
    # def portal_onhand_products(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
    #     values = self._prepare_portal_layout_values()
    #     Products = request.env['product.template'].sudo()
    #     inventory_env = request.env['stock.quant'].sudo()
    #     current_month = fields.Date.today().month
    #     current_year = fields.Date.today().year
    #     month = fields.Date.today().strftime("%B, %Y")
        
        
    #     domain = [('responsible_id', '=', request.env.user.id)]


    #     searchbar_sortings = {
    #         'date': {'label': _('Newest'), 'order': 'create_date desc'},
    #         'name': {'label': _('Name'), 'order': 'name'},
    #     }
    #     if not sortby:
    #         sortby = 'date'
    #     order = searchbar_sortings[sortby]['order']

    #     if date_begin and date_end:
    #         domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
    #     domain=[('owner_id', '=', request.env.user.partner_id.id),('quantity','>',0),('location_id.usage','=','internal'),('product_id.active','=',True)]
    #     inventory_record = inventory_env.search(domain)
        
    #     inventory_ids_list =[]
    #     product_id=[]
    #     total_qty=0
    #     current_month_total_qty=0
    #     low_stock_product=[]
    #     zero_stock_product=[]
    #     for quant in inventory_record:

    #         if quant.product_id.responsible_id.id == request.env.user.id :
    #             if quant.create_date.month == current_month and quant.create_date.year == current_year:
    #                 quantity=quant.quantity - quant.reserved_quantity
    #                 current_month_total_qty+=quantity
                
    #             quantity=quant.quantity - quant.reserved_quantity
    #             total_qty+=quantity
    #             if quantity>0 and quant.product_id.id not in product_id:
    #                 inventory_ids_list.append(quant.id)
    #                 product_id.append(quant.product_id.id)
    #             # if quantity<quant.product_id.reorder_level and quant.product_id.id not in low_stock_product:
    #             #     low_stock_product.append(quant.product_id.id)
    #             # if quantity <=0 and quant.product_id.id not in zero_stock_product:
    #                 zero_stock_product.append(quant.product_id.id)
    #     domain=[('id','in',product_id)]

    #     # products count
    #     products_count = Products.search_count(domain)
    #     # pager
    #     pager = portal_pager(
    #         url="/my/products",
    #         url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
    #         total=products_count,
    #         page=page,
    #         step=self._items_per_page
    #     )
    #     # content according to pager and archive selected
    #     products = Products.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
    #     request.session['my_products_history'] = products.ids[:100]

    #     values.update({
    #         'date': date_begin,
    #         'date_end': date_end,
    #         'products': products,
    #         'page_name': 'product',
    #         'default_url': '/my/products',
    #         'pager': pager,
    #         'searchbar_sortings': searchbar_sortings,
    #         'sortby': sortby,
    #         'current':'products',
    #         'products_count':products_count
    #     })
    #     return request.render("ag_the_hub.portal_my_products", values)




    # 
