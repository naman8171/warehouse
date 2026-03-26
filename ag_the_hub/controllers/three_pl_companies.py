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


class WroPortal(CustomerPortal):


    @route(['/add/3PLCompany/manually'], type='http', auth="user", website=True)
    def add_3PL_Company(self, **kw):
        kw.update({
            'responsible_id':request.env.user.id,
            'merchand_id':request.env.user.partner_id.id
            })
        product_id = request.env['thehub.3plcompanies'].sudo().create(kw)
        return request.redirect('/my/3plcompanies')

    @route(['/my/3plcompanies', '/my/3plcompanies/page/<int:page>'], type='http', auth="user", website=True)
    def portal_3pl_companies(self, page=1, date_begin=None, date_end=None, sortby=None,search='', **kw):
        values = self._prepare_portal_layout_values()
        pl_company = request.env['thehub.3plcompanies'].sudo()
        domain = [('responsible_id', '=', request.env.user.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        if search:
            domain+=['|','|',('name','ilike',search),('email','=',search),('phone','ilike',search)]



        # products count
        pl_company_count = pl_company.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/3plcompanies",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=pl_company_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        pl_companies = pl_company.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_pl_companies_history'] = pl_companies.ids[:100]
        
        values.update({
            'date': date_begin,
            'date_end': date_end,
            'pl_companies': pl_companies,
            'page_name': '3PL Companies',
            'default_url': '/my/3plcompanies',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'current':'3pl',
            'pl_company_count':pl_company_count,
            'search':search
        })
        return request.render("ag_the_hub.portal_my_3PL_companies", values)


    # @route(['/my/3plcompanies'], type='http', auth="user", website=True)
    # def my_3pl_companies(self, wor_id=None, **post):
        

    #     return request.render('ag_the_hub.portal_my_3PL_companies')
