from odoo import fields, http, tools, _, SUPERUSER_ID
from odoo.http import  Controller, request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request
import io
import pandas as pd
import logging
from markupsafe import Markup
from odoo.osv.expression import OR, AND
from odoo.tools import groupby as groupbyelem
from operator import attrgetter, itemgetter
from odoo.addons.website.controllers.main import QueryURL
_logger = logging.getLogger(__name__)


class CustomCustomerPortal(CustomerPortal):


    @route('/my/account/update', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def account_update(self, **post):
        if post.get('state_id'):
            post['state_id']=int(post['state_id'])
        request.env.user.partner_id.write(post)
        

        return request.redirect('/my/account/setting')

    @route(['/add/new/customer'], type='http', auth="user", website=True)
    def add_new_customer(self, **kw):
        customer_id = request.env['res.partner'].sudo().create({
                'name': kw.get('customer_name'),
                'company_name': kw.get('company_name'),
                'unit': kw.get('unit'),
                'email': kw.get('email'),
                'phone': kw.get('phone'),
                'street': kw.get('street'),
                'street2': kw.get('street2'),
                'city': kw.get('city'),
                'zip': kw.get('zip'),
                'state_id': int(kw.get('state_id')),
                'country_id': int(kw.get('country_id')),
                'merchant_user_id': request.env.user.id
            })
        return request.redirect('/my/customers')

    @route(['/my/customers', '/my/customers/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_customers(self, page=1, date_begin=None, date_end=None, sortby=None,groupby='none',search='',order='', **kw):
        values = self._prepare_portal_layout_values()
        Customers = request.env['res.partner'].sudo()
        States = request.env['res.country.state'].sudo().search([])
        Countries = request.env['res.country'].sudo().search([])
        domain = [('merchant_user_id', '=', request.env.user.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }



        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'City': {'input': 'city', 'label': _('City')},
            'State': {'input': 'state_id', 'label': _('State')},
        }
        if not sortby:
            sortby = 'date'
        # order = searchbar_sortings[sortby]['order']
        if order == 'None':
            order=searchbar_sortings[sortby]['order']

        if search:
            domain+=['|','|','|',('name','ilike',search),('email','=',search),('mobile','ilike',search),('merchant_sequence','=',search)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # Customers count
        customers_count = Customers.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/customers",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,'groupby':groupby},
            total=customers_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        partner_ids = Customers.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        # partner_id = Customers
        if groupby == 'City':
            grouped_customers = [request.env['res.partner'].sudo().concat(*g) for k, g in groupbyelem(partner_ids, itemgetter('city'))]
        elif groupby == 'State':
            grouped_customers = [request.env['res.partner'].sudo().concat(*g) for k, g in groupbyelem(partner_ids, itemgetter('state_id'))]
        
        else:
            grouped_customers = [partner_ids]

        
        request.session['my_customers_history'] = partner_ids.ids[:100]
        keep = QueryURL('/my/customers', page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, search=search)
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'customers': partner_ids,
            'state_ids': States,
            'country_ids': Countries,
            'page_name': 'customer',
            'default_url': '/my/customers',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'current':'customers',
            'search':search,
            'keep':keep,
            'order':order,
            'searchbar_groupby':searchbar_groupby,
            'groupby':groupby,
            'grouped_customers':grouped_customers
        })
        return request.render("ag_the_hub.portal_my_customers", values)



    @http.route(['/my/tickets', '/my/tickets/page/<int:page>','/my/tickets/filter/<string:ticketstatus>','/my/tickets/filter/<string:ticketstatus>/page/<int:page>'], type='http', auth="user", website=True)
    def my_helpdesk_tickets(self, page=1, date_begin=None, date_end=None, sortby=None, filterby='all', search=None, groupby='none', search_in='content',ticketstatus=None, **kw):
        values = self._prepare_portal_layout_values()
        current_month = fields.Date.today().month
        current_year = fields.Date.today().year
        month = fields.Date.today().strftime("%B, %Y")
        
        domain = self._prepare_helpdesk_tickets_domain()
        if ticketstatus=='open_cases':
            domain.append(('stage_id.is_close', '=', False))
        elif filter=='closed_cases':
            domain.append(('stage_id.is_close', '=', True))
        elif filter=='pending_cases':
            domain.append(('stage_id.is_close', '=', False))
        elif filter=='total_cases':
            domain.append(('stage_id.is_close', '=', True))
        

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Subject'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'reference': {'label': _('Reference'), 'order': 'id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'assigned': {'label': _('Assigned'), 'domain': [('user_id', '!=', False)]},
            'unassigned': {'label': _('Unassigned'), 'domain': [('user_id', '=', False)]},
            'open': {'label': _('Open'), 'domain': [('close_date', '=', False)]},
            'closed': {'label': _('Closed'), 'domain': [('close_date', '!=', False)]},
            'last_message_sup': {'label': _('Last message is from support')},
            'last_message_cust': {'label': _('Last message is from customer')},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': Markup(_('Search <span class="nolabel"> (in Content)</span>'))},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'id': {'input': 'id', 'label': _('Search in Reference')},
            'status': {'input': 'status', 'label': _('Search in Stage')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'stage': {'input': 'stage_id', 'label': _('Stage')},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if filterby in ['last_message_sup', 'last_message_cust']:
            discussion_subtype_id = request.env.ref('mail.mt_comment').id
            messages = request.env['mail.message'].search_read([('model', '=', 'helpdesk.ticket'), ('subtype_id', '=', discussion_subtype_id)], fields=['res_id', 'author_id'], order='date desc')
            last_author_dict = {}
            for message in messages:
                if message['res_id'] not in last_author_dict:
                    last_author_dict[message['res_id']] = message['author_id'][0]

            ticket_author_list = request.env['helpdesk.ticket'].search_read(fields=['id', 'partner_id'])
            ticket_author_dict = dict([(ticket_author['id'], ticket_author['partner_id'][0] if ticket_author['partner_id'] else False) for ticket_author in ticket_author_list])

            last_message_cust = []
            last_message_sup = []
            ticket_ids = set(last_author_dict.keys()) & set(ticket_author_dict.keys())
            for ticket_id in ticket_ids:
                if last_author_dict[ticket_id] == ticket_author_dict[ticket_id]:
                    last_message_cust.append(ticket_id)
                else:
                    last_message_sup.append(ticket_id)

            if filterby == 'last_message_cust':
                domain = AND([domain, [('id', 'in', last_message_cust)]])
            else:
                domain = AND([domain, [('id', 'in', last_message_sup)]])

        else:
            domain = AND([domain, searchbar_filters[filterby]['domain']])

        if date_begin and date_end:
            domain = AND([domain, [('create_date', '>', date_begin), ('create_date', '<=', date_end)]])

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('id', 'all'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                discussion_subtype_id = request.env.ref('mail.mt_comment').id
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search), ('message_ids.subtype_id', '=', discussion_subtype_id)]])
            if search_in in ('status', 'all'):
                search_domain = OR([search_domain, [('stage_id', 'ilike', search)]])
            domain = AND([domain, search_domain])

        # pager
        if ticketstatus in['open_cases','closed_cases']:
            tickets_count = len(request.env['helpdesk.ticket'].search(domain).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        else:
            tickets_count = request.env['helpdesk.ticket'].search_count(domain)
        if ticketstatus:
            url='/my/tickets/filter/'+ticketstatus
        else:
            url="/my/tickets"

        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby, 'filterby': filterby},
            total=tickets_count,
            page=page,
            step=self._items_per_page
        )
        if ticketstatus in['open_cases','closed_cases']:
            tickets = request.env['helpdesk.ticket'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset']).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year)
        else:
            tickets = request.env['helpdesk.ticket'].search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_tickets_history'] = tickets.ids[:100]

        if groupby == 'stage':
            grouped_tickets = [request.env['helpdesk.ticket'].concat(*g) for k, g in groupbyelem(tickets, itemgetter('stage_id'))]
        else:
            grouped_tickets = [tickets]

        values.update({
            'date': date_begin,
            'grouped_tickets': grouped_tickets,
            'page_name': 'ticket',
            'default_url': '/my/tickets',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'groupby': groupby,
            'search_in': search_in,
            'search': search,
            'filterby': filterby,
        })
        return request.render("helpdesk.portal_helpdesk_ticket", values)
