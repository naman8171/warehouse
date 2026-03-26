from odoo import fields, http, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, AccessError, MissingError, UserError, AccessDenied
from odoo.http import content_disposition, Controller, request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
# import tempfile
# import binascii
from odoo.tools import groupby as groupbyelem
from operator import attrgetter, itemgetter

import logging
from odoo.addons.website.controllers.main import QueryURL


_logger = logging.getLogger(__name__)


class WroPortal(CustomerPortal):

    @route(['/my/wros/<int:wor_id>'], type='http', auth="user", website=True)
    def portal_wor_id(self, wor_id=None, **post):
        wor_id=request.env['warehouse.receive.order'].sudo().browse(wor_id)
        if not wor_id.status:
            return request.redirect('/send/inventory/portal/'+str(wor_id.id))
        

        return request.render('ag_the_hub.workorder_receive_order_form',{'wor_id':wor_id})
    

    @route(['/my/wros','/my/wro/filter/<string:filter>','/my/wro/filter/<string:filter>/page/<int:page>','/my/wros/page/<int:page>','/my/wro/filter/current_month/<string:monthfilter>','/my/wro/filter/current_month/<string:monthfilter>/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_wro(self, page=1, date_begin=None, date_end=None, sortby=None,filter=False,monthfilter=False,order='',groupby='none',search='', **kw):
        values = self._prepare_portal_layout_values()
        WROs = request.env['warehouse.receive.order'].sudo()
        current_month = fields.Date.today().month
        current_year = fields.Date.today().year
        month = fields.Date.today().strftime("%B, %Y")
        domain = ['|', ('merchand_id', '=', request.env.user.partner_id.id), ('merchand_id', 'in', request.env.user.partner_id.child_ids.ids)]

        current_month_first_date = fields.Date.today().replace(day=1)
        default_url="/my/wros"

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'Warehouse': {'input': 'warehouse_id', 'label': _('Warehouse')},
            'Merchant': {'input': 'merchand_id', 'label': _('Merchant')},
            'Picking Method': {'input': 'pickup_method', 'label': _('Picking Method')},
            'Shipping Type': {'input': 'shipping_type', 'label': _('Shipping Type')},
            'Status': {'input': 'status', 'label': _('Status')}
        }
        
        

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        # order = searchbar_sortings[sortby]['order']
        if order== 'None':
            order=searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        if search:
            domain+=['|', '|', ('name','=',search), ('merchand_id', 'ilike', search), ('third_party_ref', 'ilike', search)]


        if filter=='submitted':
            domain.append(('status', '=', 'request_submitted'))
        elif filter=='received':
            domain.append(('status', '=', 'received'))
        elif filter=='stored':
            domain.append(('status', '=', 'stored'))


        
        

        elif monthfilter=='submitted':
            domain.append(('status', '=', 'request_submitted'))
            domain.append(('create_date','>=',current_month_first_date))
        elif monthfilter=='received':
            domain.append(('status', '=', 'received'))
            domain.append(('create_date','>=',current_month_first_date))
        elif monthfilter=='stored':
            domain.append(('status', '=', 'stored'))
            domain.append(('create_date','>=',current_month_first_date))
        elif monthfilter=='all':
            domain.append(('create_date','>=',current_month_first_date))

        if filter:
            default_url="/my/wro/filter/"+filter
        elif monthfilter:
            default_url="/my/wro/filter/current_month/"+monthfilter
        

        # products count
        
        wro_count = WROs.search_count(domain)
        # pager
        pager = portal_pager(
            url=default_url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'search':search,'groupby':groupby},
            total=wro_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        wros = WROs.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        if groupby == 'Warehouse':
            grouped_wros = [request.env['warehouse.receive.order'].sudo().concat(*g) for k, g in groupbyelem(wros, itemgetter('warehouse_id'))]
        elif groupby == 'Merchant':
            grouped_wros = [request.env['warehouse.receive.order'].sudo().concat(*g) for k, g in groupbyelem(wros, itemgetter('merchand_id'))]
        elif groupby == 'Picking Method':
            grouped_wros = [request.env['warehouse.receive.order'].sudo().concat(*g) for k, g in groupbyelem(wros, itemgetter('pickup_method'))]
        elif groupby == 'Shipping Type':
            grouped_wros = [request.env['warehouse.receive.order'].sudo().concat(*g) for k, g in groupbyelem(wros, itemgetter('shipping_type'))]
        elif groupby == 'Status':
            grouped_wros = [request.env['warehouse.receive.order'].sudo().concat(*g) for k, g in groupbyelem(wros, itemgetter('status'))]


        else:
            grouped_wros=[wros]
        
        request.session['my_wros_history'] = wros.ids[:100]
        keep = QueryURL(default_url, page=page, date_begin=date_begin, date_end=date_end, sortby=sortby,filter=filter,monthfilter=monthfilter,order=order,search=search)
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'wros': wros,
            'page_name': 'wro',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'wro_count':wro_count,
            'current':'wro',
            'search':search,
            'keep':keep,
            'default_url':default_url,
            'searchbar_groupby':searchbar_groupby,
            'groupby':groupby,
            'grouped_wros':grouped_wros
        })
        return request.render("ag_the_hub.portal_my_wros", values)
