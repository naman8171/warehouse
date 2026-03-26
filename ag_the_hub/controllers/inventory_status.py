from odoo import fields as odoo_fields, http, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, AccessError, MissingError, UserError, AccessDenied
from odoo.http import  Controller, request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request
import xlrd
from datetime import date, timedelta

# import tempfile
# import binascii
import io
import logging
from odoo import fields, models, api, _
from odoo.addons.website.controllers.main import QueryURL



_logger = logging.getLogger(__name__)


class WroPortal(CustomerPortal):

    # @route(['/my/wros/<int:wor_id>'], type='http', auth="user", website=True)
    # def portal_wor_id(self, wor_id=None, **post):
    #     wor_id=request.env['warehouse.receive.order'].sudo().browse(wor_id)
        

    #     return request.render('ag_the_hub.workorder_receive_order_form',{'wor_id':wor_id})

    # @route(['/my/wallet/transaction'], type='http', auth="user", website=True)
    # def portal_my_wallet_transaction_custom(self, **kw):
    #     invoice_ids = request.env['account.move'].sudo().search([('partner_id','=',request.env.user.partner_id.id)])
    #     partner = request.env.user.partner_id
    #     WalletTransaction = request.env['website.wallet.transaction'].sudo()
    #     domain = [('partner_id', '=', partner.id)]
    #     company_currency = request.env.company.currency_id
    #     # web_currency = request.website.get_current_pricelist().currency_id
    #     price = float(partner.wallet_balance)
    #     values = {
    #                 'wallet_balance':price, 
    #                 'currency_id': company_currency
    #             }
    #     wallets = WalletTransaction.sudo().search(domain)
    #     values.update({
    #         'wallets': wallets.sudo(),
    #         #'invoice_ids':invoice_ids
    #     })
        
    #     return request.render("ag_the_hub.my_wallet_transaction", values)

    @route(['/my/wallet/transaction','/my/wallet/transaction/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_wallet_transaction_custom(self, page=1, date_begin=None, date_end=None, sortby=None,filter=False,monthfilter=False, **kw):
        invoice_ids = request.env['account.move'].sudo().search([('partner_id','=',request.env.user.partner_id.id)])
        partner = request.env.user.partner_id
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        WalletTransaction = request.env['website.wallet.transaction'].sudo()
        domain = [('partner_id', '=', partner.id)]
        company_currency = request.env.company.currency_id
        # web_currency = request.website.get_current_pricelist().currency_id
        price = float(partner.wallet_balance)
        values = {
                    'wallet_balance':price, 
                    'currency_id': company_currency
                }
        wallets = WalletTransaction.sudo().search_count(domain)
        pager = portal_pager(
            url="/my/wallet/transaction",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=wallets,
            page=page,
            step=10
        )
        wallets = WalletTransaction.sudo().search(domain,order=order, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'wallets': wallets.sudo(),
            'pager':pager
            #'invoice_ids':invoice_ids
        })
        
        return request.render("ag_the_hub.my_wallet_transaction", values)

    @route(['/my/reorder/level/notifications'], type='http', auth="user", website=True)
    def portal_my_reorder_level(self,page=1, date_begin=None, date_end=None, sortby=None,filter=False,monthfilter=False,search='',order='',groupby='none', **kw):
        user_id = request.env.user
        values = self._prepare_portal_layout_values()
        reorder_level_notifications_env=request.env['reorder.level.notification'].sudo()
        domain=[('merchand_id','=',user_id.partner_id.id)]
        
        reorder_level_notifications_count = reorder_level_notifications_env.search_count(domain)
        # pager
        pager = portal_pager(
            url='/my/reorder/level/notifications',
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'search':search,'order':order},
            total=reorder_level_notifications_count,
            page=page,
            step=10
        )
        reorder_level_notifications_ids = reorder_level_notifications_env.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'pager': pager,
            'reorder_level_notifications_ids':reorder_level_notifications_ids
            })
        return request.render("ag_the_hub.my_reorder_level_notifications", values)


    @route(['/my/hold/receiving'], type='http', auth="user", website=True)
    def portal_my_hold_receiving(self, **kw):
        user_id = request.env.user
        ticket_ids = request.env['helpdesk.ticket'].sudo().search([('partner_id','=',user_id.partner_id.id),('partner_id','!=',False)])
        return request.render("ag_the_hub.my_receiving_hold", {'user_id':user_id,'ticket_ids':ticket_ids,'current':'onhand'})


    @route(['/my/account/setting'], type='http', auth="user", website=True)
    def portal_my_account_setting(self, **kw):
        user_id = request.env.user
        country_states = request.env['res.country.state'].sudo().search([('country_id','=',user_id.partner_id.country_id.id)])
        return request.render("ag_the_hub.my_account", {'user_id':user_id,'country_states':country_states})

    @route(['/update/dashboard'], type='http', auth="user", website=True)
    def portal_update_dashboard(self, **kw):
        dashboard = request.env['dashboard.dynamics'].sudo().search([('merchand_id','=',request.env.user.partner_id.id)])
        if dashboard:
            dashboard.update_specific_merchant_dashboard()
        else:
            dashboard=request.env['dashboard.dynamics'].sudo().create({'merchand_id':request.env.user.partner_id.id})
            dashboard.update_specific_merchant_dashboard()
        return request.redirect('/my/analytic')

    @route(['/my/analytic'], type='http', auth="user", website=True)
    def portal_my_analytic(self, **kw):
        Workorders = request.env['thehub.workorder'].sudo()
        wro_env = request.env['warehouse.receive.order'].sudo()
        ticket_env = request.env['helpdesk.ticket'].sudo()
        wo_line = request.env['thehub.workorder.lines'].sudo()
        
        current_month = fields.Date.today().month
        current_year = fields.Date.today().year
        last_ten_days_date=fields.Datetime.now()- timedelta(days=10)
        # last_ten_days_day=last_ten_days_date.day
        # last_ten_days_month=last_ten_days_date.month
        month = fields.Date.today().strftime("%B, %Y")
        # domain = [('merchand_id', '=', request.env.user.partner_id.id)]
        domain = ['|', ('merchand_id', '=', request.env.user.partner_id.id), ('merchand_id', 'in', request.env.user.partner_id.child_ids.ids)]
        domain_product = [('responsible_id', '=', request.env.user.id)]
        wo_pending_count = Workorders.search_count(domain + [('status', '=', 'Pending')])
        wo_awaiting_count = Workorders.search_count(domain + [('status', '=', 'Awaiting')])
        wo_delivered_count = Workorders.search_count(domain + [('status', '=', 'Delivered')])
        wo_returned_count = Workorders.search_count(domain + [('status', '=', 'Returned')])
        wo_dispatched_count = Workorders.search_count(domain + [('status', '=', 'Dispatched')])
        
        cm_wo_pending_count = len(Workorders.search(domain + [('status', '=', 'Pending')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        cm_wo_awaiting_count = len(Workorders.search(domain + [('status', '=', 'Awaiting')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        cm_wo_delivered_count = len(Workorders.search(domain + [('status', '=', 'Delivered')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        cm_wo_returned_count = len(Workorders.search(domain + [('status', '=', 'Returned')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        cm_wo_dispatched_count = len(Workorders.search(domain + [('status', '=', 'Dispatched')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        cm_wo_ids=Workorders.search(domain).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year)
        month_list=[]
        
        values = {
            'wo_pending_count': wo_pending_count,
            'wo_awaiting_count': wo_awaiting_count,
            'wo_delivered_count': wo_delivered_count,
            'wo_returned_count': wo_returned_count,
            'wo_dispatched_count':wo_dispatched_count,
            'cm_wo_pending_count': cm_wo_pending_count,
            'cm_wo_awaiting_count': cm_wo_awaiting_count,
            'cm_wo_delivered_count': cm_wo_delivered_count,
            'cm_wo_returned_count': cm_wo_returned_count,
            'cm_wo_dispatched_count':cm_wo_dispatched_count,
            'month': month,
            
            'cm_wo_ids':cm_wo_ids,
            
            
            }
        wro_submitted_count = wro_env.search_count(domain + [('status', '=', 'request_submitted')])
        wro_received_count = wro_env.search_count(domain + [('status', '=', 'received')])
        wro_stored_count = wro_env.search_count(domain + [('status', '=', 'stored')])
        cm_wro_submitted_count = len(wro_env.search(domain + [('status', '=', 'request_submitted')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        cm_wro_received_count = len(wro_env.search(domain + [('status', '=', 'received')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        cm_wro_stored_count = len(wro_env.search(domain + [('status', '=', 'stored')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        cm_wro_ids = wro_env.search(domain).filtered(lambda x: x.create_date.month == current_month)
        
        most_wo_pending_count = len(Workorders.search(domain).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        most_wro_received_count = len(wro_env.search(domain + []).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        most_wo_returned_count = len(Workorders.search(domain + [('status', '=', 'Returned')]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))    
        values.update({
            
            'wro_submitted_count': wro_submitted_count,
            'wro_received_count': wro_received_count,
            'wro_stored_count': wro_stored_count,
            'cm_wro_submitted_count': cm_wro_submitted_count,
            'cm_wro_received_count': cm_wro_received_count,
            'cm_wro_stored_count': cm_wro_stored_count,
            'cm_wro_ids':cm_wro_ids,
            
            'current':'analytic'
            }
            )




        domain=[('partner_id','=',request.env.user.partner_id.id)]
        overall_ticket_count_closed = ticket_env.search_count(domain+[('stage_id.is_close', '=', True)])
        current_ticket_count_closed = len(ticket_env.search(domain+[('stage_id.is_close', '=', True)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        overall_ticket_count_open = ticket_env.search_count(domain+[('stage_id.is_close', '=', False)])
        current_ticket_count_open = len(ticket_env.search(domain+[('stage_id.is_close', '=', False)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        dashboard_id = request.env['dashboard.dynamics'].sudo().search(['|', ('merchand_id', '=', request.env.user.partner_id.id), ('merchand_id', 'in', request.env.user.partner_id.child_ids.ids)])
        reorder_notifications = request.env['reorder.level.notification'].sudo().search(['|', ('merchand_id', '=', request.env.user.partner_id.id), ('merchand_id', 'in', request.env.user.partner_id.child_ids.ids)])
                        
            
        values.update({
            'overall_ticket_count_closed':overall_ticket_count_closed,
            'current_ticket_count_closed':current_ticket_count_closed,
            'overall_ticket_count_open':overall_ticket_count_open,
            'current_ticket_count_open':current_ticket_count_open,
            'most_wo_pending_count':most_wo_pending_count,
            'most_wro_received_count':most_wro_received_count,
            'most_wo_returned_count':most_wo_returned_count,
            'current_overall_stock':dashboard_id.stock_one_hand if dashboard_id else 0,
            'zero_stock_product':dashboard_id.out_stock_product if dashboard_id else 0,
            'low_stock_product':dashboard_id.low_stock_product if dashboard_id else 0,
            'ten_wro_ids':dashboard_id.most_recent_wro if dashboard_id else 0,
            'ten_wo_ids':dashboard_id.most_recent_wo if dashboard_id else 0,
            'products_count':dashboard_id.total_products if dashboard_id else 0,
            'top_selling_product':dashboard_id.top_stock_product if dashboard_id else 0,
            'current_month_total_qty':dashboard_id.current_month_total_qty if dashboard_id else 0,
            'cm_products_count':dashboard_id.total_products if dashboard_id else 0,
            'reorder_notifications':len(reorder_notifications.ids)


            })
        values['wallet_balance']=request.env.user.partner_id.wallet_balance
        return request.render("ag_the_hub.my_analytics", values)


    @route(['/my/invoices/custom','/my/invoices/custom/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices_custom(self, page=1, date_begin=None, date_end=None, sortby=None,search='',order='', **kw):
        invoice_ids = request.env['account.move'].sudo().search([('partner_id','=',request.env.user.partner_id.id),('state','=','posted')])
        invoice_data=[]
        invoice_env=request.env['account.move'].sudo()
        invoice_ids_list =[]
        for invoice in invoice_ids:
            if invoice.invoice_line_ids[0].sale_line_ids and invoice.invoice_line_ids[0].sale_line_ids[0].order_id:
                if invoice.invoice_line_ids[0].sale_line_ids[0].order_id.wro_id:
                    invoice_data.append({
                        'order_id':invoice.invoice_line_ids[0].sale_line_ids[0].order_id.wro_id.name,
                        'invoice_id':invoice
                        })
                    invoice_ids_list.append(invoice.id) 
                elif invoice.invoice_line_ids[0].sale_line_ids[0].order_id.wo_id:
                    invoice_data.append({
                        'order_id':invoice.invoice_line_ids[0].sale_line_ids[0].order_id.wo_id.name,
                        'invoice_id':invoice
                        }) 
                    invoice_ids_list.append(invoice.id) 


        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        if order=='None':
            order = searchbar_sortings[sortby]['order']
        domain=[]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        domain.append(('id','in',invoice_ids_list))
        if search:
            domain+=['|',('partner_id.name','ilike',search),('name','ilike',search)]
        

        # Customers count

        invoice_count = invoice_env.search_count(domain)
        pager = portal_pager(
            url="/my/invoices/custom",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'search':search},
            total=invoice_count,
            page=page,
            step=10
        )
        invoice_ids = request.env['account.move'].sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        invoice_data=[]
        invoice_ids_list =[]
        for invoice in invoice_ids:
            if invoice.invoice_line_ids[0].sale_line_ids and invoice.invoice_line_ids[0].sale_line_ids[0].order_id:
                if invoice.invoice_line_ids[0].sale_line_ids[0].order_id.wro_id:
                    invoice_data.append({
                        'order_id':invoice.invoice_line_ids[0].sale_line_ids[0].order_id.wro_id.name,
                        'invoice_id':invoice,
                        
                        })
                    invoice_ids_list.append(invoice.id) 
                elif invoice.invoice_line_ids[0].sale_line_ids[0].order_id.wo_id:
                    invoice_data.append({
                        'order_id':invoice.invoice_line_ids[0].sale_line_ids[0].order_id.wo_id.name,
                        'invoice_id':invoice,
                         
                        }) 
                    invoice_ids_list.append(invoice.id) 
        #invoice_data.update({'pager':pager})
        keep = QueryURL('/my/invoices/custom', page=page, date_begin=date_begin, date_end=date_end, sortby=sortby,search=search,order=order)
        
        data={
        'pager':pager,
        'invoice_ids':invoice_data,
        'current':'invoicepage',
        'search':search,
        'order':order,
        'keep':keep
        }
        


        return request.render("ag_the_hub.my_invoices_custom", data)


    
    @route(['/my/inventory/detail/<int:product_id>','/my/inventory/detail/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_inventory_detail(self,product_id=False, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        inventory_env = request.env['stock.quant'].sudo()
        domain = [('owner_id', '=', request.env.user.partner_id.id),('product_id','=',product_id)]
        #group_by_fields=['package_number']
        # record_data = request.env['single.sku.per.box.line'].sudo().search([])
        # grouped_data = record_data.read_group(fields=group_by_fields, groupby=group_by_fields, orderby='id')

        # unique_records = []
        # for group in grouped_data:
        #     print("sssssssssssssssss",group)

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # products count
        wro_count = inventory_env.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/inventory",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=wro_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        inventory_record = inventory_env.search(domain)
        request.session['my_inventory_status'] = inventory_record.ids[:100]
        inventory_ids_list =[]
        product_id=[]
        for quant in inventory_record:
            quantity=quant.quantity - quant.reserved_quantity
            if quantity>0:
                inventory_ids_list.append(quant.id)
                product_id.append(quant.product_id.id)
        domain=[('id','in',inventory_ids_list)]
        wro_count = inventory_env.search_count(domain)
        pager = portal_pager(
            url="/my/inventory",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=wro_count,
            page=page,
            step=self._items_per_page
        )
        inventory_record = inventory_env.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        inventory_ids_list=[]
        for quant in inventory_record:
            quantity=quant.quantity - quant.reserved_quantity
            if quantity>0:
                inventory_ids_list.append(quant.id)

        domain=[('id','in',inventory_ids_list)]

        inventory_record = inventory_env.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        


        values.update({
            'date': date_begin,
            'date_end': date_end,
            'inventory_ids': inventory_record,
            'page_name': 'inventory_status',
            'default_url': '/my/inventory/detail/'+str(product_id),
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("ag_the_hub.portal_my_inventory_detail", values)


    @route(['/my/inventory','/my/inventory/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_inventory(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        # Prepare base values for the portal layout
        values = self._prepare_portal_layout_values()

        # Initialize the inventory environment
        inventory_env = request.env['stock.quant'].sudo()
        partner_id = request.env.user.partner_id.id

        # Base domain for inventory records
        domain = [
            ('owner_id', '=', partner_id),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal'),
            ('product_id.active', '=', True)
        ]

        # Add date filters if provided
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # Define sorting options
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        sortby = sortby or 'date'
        order = searchbar_sortings[sortby]['order']

        # Fetch inventory records
        inventory_records = inventory_env.search(domain)
        # Filter and process inventory records
        # filtered_records = [
        #     quant for quant in inventory_records
        #     if quant.product_id.responsible_id.id == request.env.user.id
        #     and (quant.quantity - quant.reserved_quantity) > 0
        # ]

        # Extract unique product IDs and calculate total quantity
        # product_ids_set = {quant.product_id.id for quant in filtered_records}
        # total_qty = sum(
        #     quant.quantity - quant.reserved_quantity
        #     for quant in filtered_records
        # )
        total_qty = sum(inventory_records.mapped('quantity'))

        # Prepare domain for product search
        # product_domain = [('id', 'in', list(product_ids_set))]
        product_domain = [('id', 'in', inventory_records.mapped('product_id').ids)]
        # wro_count = request.env['product.product'].sudo().search_count(product_domain)
        wro_count = len(inventory_records)
        # Pagination
        pager = portal_pager(
            url="/my/inventory",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=wro_count,
            page=page,
            step=10
        )

        # Fetch product data with pagination
        product_ids = request.env['product.product'].sudo().search(
            product_domain, order=order, limit=10, offset=pager['offset']
        )
        # Prepare inventory data for the template
        inventory_data = []
        for product in product_ids:
            # product_quantities = inventory_env.search([
            #     ('owner_id', '=', partner_id),
            #     ('quantity', '>', 0),
            #     ('product_id', '=', product.id)
            # ])

            # total_quantity = sum(
            #     quant.quantity - quant.reserved_quantity
            #     for quant in product_quantities
            #     if (quant.quantity - quant.reserved_quantity) > 0
            # )

            inventory_data.append({
                'product_id': product.id,
                'id': product.id,
                'product_name': product.name,
                'barcode': product.barcode,
                'size': product.size,
                'color': product.color,
                'gender': product.gender,
                'product_reorder_level': product.reorder_level,
                'on_hand_qty': product.qty_available
            })

        # Update values for the template
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'inventory_ids': inventory_data,
            'page_name': 'inventory_status',
            'default_url': '/my/inventory',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'wro_count': wro_count,
            'total_quantity_products': total_qty,
            'current': 'invenstat'
        })
        return request.render("ag_the_hub.portal_my_inventory", values)



    @route(['/my/inventory/history','/my/inventory/history/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_inventory_history(self, page=1, date_begin=None, date_end=None, sortby=None, search='', order='', **kw):
        # Prepare base values for the portal layout
        values = self._prepare_portal_layout_values()

        # Initialize the inventory environment
        inventory_env = request.env['stock.quant'].sudo()
        partner_id = request.env.user.partner_id.id

        # Base domain for inventory records
        domain = [
            ('owner_id', '=', partner_id),
            ('quantity', '>', 0)
        ]

        # Add date filters if provided
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # Define sorting options
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        sortby = sortby or 'date'
        order = searchbar_sortings[sortby]['order']

        # Add search filters if a search term is provided
        if search:
            product_ids = request.env['product.product'].sudo().search([('name', 'ilike', search)]).ids
            lot_ids = request.env['stock.production.lot'].sudo().search([('name', 'ilike', search)]).ids
            wro_ids = request.env['thehub.workorder'].sudo().search([('name', 'ilike', search)]).ids
            domain += ['|', '|', ('product_id', 'in', product_ids), ('lot_id', 'in', lot_ids), ('wro_id', 'in', wro_ids)]

        # Count total records for pagination
        wro_count = inventory_env.search_count(domain)

        # Pagination
        pager = portal_pager(
            url="/my/inventory/history",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search': search, 'order': order},
            total=wro_count,
            page=page,
            step=self._items_per_page
        )

        # Fetch inventory records with pagination
        inventory_record = inventory_env.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        # # Filter records with positive available quantity
        # inventory_ids_list = [
        #     quant.id for quant in inventory_record
        #     if (quant.quantity - quant.reserved_quantity) > 0
        # ]

        # # Update domain to include only valid inventory IDs
        # domain = [('id', 'in', inventory_ids_list)]

        # Update values for the template
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'inventory_ids': inventory_record,
            'page_name': 'inventory_status',
            'default_url': '/my/inventory/history',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'current': 'invenhis',
            'search': search
        })
        return request.render("ag_the_hub.portal_my_inventory_history", values)



        

    # def portal_my_inventory_history(self, page=1, date_begin=None, date_end=None, sortby=None,search='',order='', **kw):
    #     values = self._prepare_portal_layout_values()
    #     inventory_env = request.env['stock.quant'].sudo()
    #     domain = [('owner_id', '=', request.env.user.partner_id.id),('quantity','>',0)]

    #     searchbar_sortings = {
    #         'date': {'label': _('Newest'), 'order': 'create_date desc'},
    #         'name': {'label': _('Name'), 'order': 'name'},
    #     }
    #     if not sortby:
    #         sortby = 'date'
    #     # if order == 'None':
    #     order = searchbar_sortings[sortby]['order']

    #     if date_begin and date_end:
    #         domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

    #     # products count
    #     if search:
    #         product_ids = request.env['product.product'].sudo().search([('name', 'ilike',search)])
    #         lot_ids = request.env['stock.production.lot'].sudo().search([('name', 'ilike',search)])
    #         wro_ids = request.env['thehub.workorder'].sudo().search([('name', 'ilike',search)])
    #         domain+=['|','|',('product_id','in',product_ids.ids),('lot_id','in',lot_ids.ids),('wro_id','in',wro_ids.ids)]
    #     wro_count = inventory_env.search_count(domain)
    #     # pager
    #     pager = portal_pager(
    #         url="/my/inventory/history",
    #         url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'search':search,'order':order},
    #         total=wro_count,
    #         page=page,
    #         step=self._items_per_page
    #     )

    #     # content according to pager and archive selected
    #     inventory_record = inventory_env.search(domain)
    #     request.session['my_inventory_status'] = inventory_record.ids[:100]
    #     inventory_ids_list =[]
    #     for quant in inventory_record:
    #         quantity=quant.quantity - quant.reserved_quantity
    #         if quantity>0:
    #             inventory_ids_list.append(quant.id)
    #     domain=[('id','in',inventory_ids_list)]
    #     wro_count = inventory_env.search_count(domain)
    #     # pager
    #     pager = portal_pager(
    #         url="/my/inventory/history",
    #         url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'search':search,'order':order},
    #         total=wro_count,
    #         page=page,
    #         step=self._items_per_page
    #     )
    #     if search:
    #         product_ids = request.env['product.product'].sudo().search([('name', 'ilike',search)])
    #         lot_ids = request.env['stock.production.lot'].sudo().search([('name', 'ilike',search)])
    #         wro_ids = request.env['thehub.workorder'].sudo().search([('name', 'ilike',search)])
    #         domain+=['|','|',('product_id','in',product_ids.ids),('lot_id','in',lot_ids.ids),('wro_id','in',wro_ids.ids)]
    #     inventory_record = inventory_env.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
    #     values.update({
    #         'date': date_begin,
    #         'date_end': date_end,
    #         'inventory_ids': inventory_record,
    #         'page_name': 'inventory_status',
    #         'default_url': '/my/inventory/history',
    #         'pager': pager,
    #         'searchbar_sortings': searchbar_sortings,
    #         # 'sortby': sortby,
    #         'current':'invenhis',
    #         'search':search
    #     })
    #     print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    #     return request.render("ag_the_hub.portal_my_inventory_history", values)

