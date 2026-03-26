# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import http, SUPERUSER_ID
from odoo import _
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
import werkzeug
# from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.http import content_disposition, Controller, request, route


class CustomerPortalWalletTransaction(CustomerPortal):

    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'website_sale_current_pl': False,
        })

    def sale_get_payment_term(self, partner):
        pt = request.env.ref('account.account_payment_term_immediate', False).sudo()
        if pt:
            pt = (not pt.company_id.id or request.env.company.id == pt.company_id.id) and pt
        return (
            partner.property_payment_term_id or
            pt or
            request.env['account.payment.term'].sudo().search([('company_id', '=', request.env.company.id)], limit=1)
        ).id

    def _prepare_sale_order_values(self, partner, pricelist):
        addr = partner.address_get(['delivery'])
        default_user_id = partner.parent_id.user_id.id or partner.user_id.id
        values = {
            'partner_id': partner.id,
            'pricelist_id': pricelist.id,
            'payment_term_id': self.sale_get_payment_term(partner),
            'team_id': partner.parent_id.team_id.id or partner.team_id.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': addr['delivery'],
            'user_id': default_user_id,
            'company_id': request.env.company.id,
        }
        return values

    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        """ Return the current sales order after mofications specified by params.
        :param bool force_create: Create sales order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sales order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one
        :returns: browse record for the current sales order
        """
        # self.ensure_one()
        partner = request.env.user.partner_id
        sale_order_id = request.session.get('sale_order_id')
        check_fpos = False
        # if not sale_order_id and not self.env.user._is_public():
        #     last_order = partner.last_website_so_id
        #     if last_order:
        #         available_pricelists = self.get_pricelist_available()
        #         # Do not reload the cart of this user last visit if the cart uses a pricelist no longer available.
        #         sale_order_id = last_order.pricelist_id in available_pricelists and last_order.id
        #         check_fpos = True

        # Test validity of the sale_order_id
        sale_order = request.env['sale.order'].with_company(request.env.company.id).sudo().browse(sale_order_id).exists() if sale_order_id else None

        # Ignore the current order if a payment has been initiated. We don't want to retrieve the
        # cart and allow the user to update it when the payment is about to confirm it.
        if sale_order and sale_order.get_portal_last_transaction().state in ('pending', 'authorized', 'done'):
            sale_order = None

        # Do not reload the cart of this user last visit if the Fiscal Position has changed.
        if check_fpos and sale_order:
            fpos_id = (
                request.env['account.fiscal.position'].sudo()
                .with_company(sale_order.company_id.id)
                .get_fiscal_position(sale_order.partner_id.id, delivery_id=sale_order.partner_shipping_id.id)
            ).id
            if sale_order.fiscal_position_id.id != fpos_id:
                sale_order = None

        if not (sale_order or force_create or code):
            if request.session.get('sale_order_id'):
                request.session['sale_order_id'] = None
            return request.env['sale.order']

        if request.env['product.pricelist'].browse(force_pricelist).exists():
            pricelist_id = force_pricelist
            request.session['website_sale_current_pl'] = pricelist_id
            update_pricelist = True
        else:
            pricelist_id = request.session.get('website_sale_current_pl') or partner.property_product_pricelist.id

        # if not request._context.get('pricelist'):
        #     self = request.with_context(pricelist=pricelist_id)

        # cart creation was requested (either explicitly or to configure a promo code)
        if not sale_order:
            # TODO cache partner_id session
            pricelist = request.env['product.pricelist'].browse(pricelist_id).sudo()
            so_data = self._prepare_sale_order_values(partner, pricelist)
            sale_order = request.env['sale.order'].with_company(request.env.company.id).with_user(SUPERUSER_ID).create(so_data)

            # set fiscal position
            # if request.website.partner_id.id != partner.id:
            sale_order.onchange_partner_shipping_id()
            # else: # For public user, fiscal position based on geolocation
            #     country_code = request.session['geoip'].get('country_code')
            #     if country_code:
            #         country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1).id
            #         sale_order.fiscal_position_id = request.env['account.fiscal.position'].sudo().with_company(request.website.company_id.id)._get_fpos_by_region(country_id)
            #     else:
            #         # if no geolocation, use the public user fp
            #         sale_order.onchange_partner_shipping_id()

            request.session['sale_order_id'] = sale_order.id

            # The order was created with SUPERUSER_ID, revert back to request user.
            sale_order = sale_order.with_user(request.env.user).sudo()

        # case when user emptied the cart
        if not request.session.get('sale_order_id'):
            request.session['sale_order_id'] = sale_order.id

        # check for change of pricelist with a coupon
        pricelist_id = pricelist_id or partner.property_product_pricelist.id

        # check for change of partner_id ie after signup
        if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
            flag_pricelist = False
            if pricelist_id != sale_order.pricelist_id.id:
                flag_pricelist = True
            fiscal_position = sale_order.fiscal_position_id.id

            # change the partner, and trigger the onchange
            sale_order.write({'partner_id': partner.id})
            sale_order.with_context(not_self_saleperson=True).onchange_partner_id()
            sale_order.write({'partner_invoice_id': partner.id})
            sale_order.onchange_partner_shipping_id() # fiscal position
            sale_order['payment_term_id'] = self.sale_get_payment_term(partner)

            # check the pricelist : update it if the pricelist is not the 'forced' one
            values = {}
            if sale_order.pricelist_id:
                if sale_order.pricelist_id.id != pricelist_id:
                    values['pricelist_id'] = pricelist_id
                    update_pricelist = True

            # if fiscal position, update the order lines taxes
            if sale_order.fiscal_position_id:
                sale_order._compute_tax_id()

            # if values, then make the SO update
            if values:
                sale_order.write(values)

            # check if the fiscal position has changed with the partner_id update
            recent_fiscal_position = sale_order.fiscal_position_id.id
            # when buying a free product with public user and trying to log in, SO state is not draft
            if (flag_pricelist or recent_fiscal_position != fiscal_position) and sale_order.state == 'draft':
                update_pricelist = True

        if code and code != sale_order.pricelist_id.code:
            code_pricelist = request.env['product.pricelist'].sudo().search([('code', '=', code)], limit=1)
            if code_pricelist:
                pricelist_id = code_pricelist.id
                update_pricelist = True
        elif code is not None and sale_order.pricelist_id.code and code != sale_order.pricelist_id.code:
            # code is not None when user removes code and click on "Apply"
            pricelist_id = partner.property_product_pricelist.id
            update_pricelist = True

        # update the pricelist
        if update_pricelist:
            request.session['website_sale_current_pl'] = pricelist_id
            values = {'pricelist_id': pricelist_id}
            sale_order.write(values)
            for line in sale_order.order_line:
                if line.exists():
                    sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

        return sale_order

    @http.route('/payment/confirmation', type='http', methods=['GET'], auth='public', website=True)
    def payment_confirm(self, tx_id, access_token, **kwargs):
        """ Display the payment confirmation page with the appropriate status message to the user.

        :param str tx_id: The transaction to confirm, as a `payment.transaction` id
        :param str access_token: The access token used to verify the user
        :param dict kwargs: Optional data. This parameter is not used here
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """
        tx_id = self._cast_as_int(tx_id)
        order = self.sale_get_order()
        if tx_id:
            tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id)
            if not order and tx_sudo.sale_order_ids:
                order = tx_sudo.sale_order_ids[0]
            # Raise an HTTP 404 if the access token is invalid
            if not payment_utils.check_access_token(
                access_token, tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id
            ):
                raise werkzeug.exceptions.NotFound  # Don't leak info about existence of an id
            # Fetch the appropriate status message configured on the acquirer
            if tx_sudo.state == 'draft':
                status = 'info'
                message = tx_sudo.state_message \
                          or _("This payment has not been processed yet.")
                return request.redirect('/wallet')
            elif tx_sudo.state == 'pending':
                status = 'warning'
                message = tx_sudo.acquirer_id.pending_msg
                order.with_context(send_email=True).action_confirm()
            elif tx_sudo.state in ('authorized', 'done'):
                status = 'success'
                message = tx_sudo.acquirer_id.done_msg
                product = request.env.company.wallet_product_id
                # if payment.acquirer is credit payment provider
                for line in order.order_line:
                    if len(order.order_line) == 1:
                        if product and  line.product_id.id == product.id:
                            wallet_transaction_obj = request.env['website.wallet.transaction']
                            if tx_sudo.acquirer_id.need_approval:
                                wallet_create = wallet_transaction_obj.sudo().create({ 
                                    'wallet_type': 'credit', 
                                    'partner_id': order.partner_id.id, 
                                    'sale_order_id': order.id, 
                                    'reference': 'sale_order', 
                                    'amount': order.order_line.price_unit * order.order_line.product_uom_qty,
                                    'currency_id': order.pricelist_id.currency_id.id, 
                                    'status': 'draft' 
                                })
                            else:
                                wallet_create = wallet_transaction_obj.sudo().create({ 
                                    'wallet_type': 'credit', 
                                    'partner_id': order.partner_id.id, 
                                    'sale_order_id': order.id, 
                                    'reference': 'sale_order', 
                                    'amount': order.order_line.price_unit * order.order_line.product_uom_qty,
                                    'currency_id': order.pricelist_id.currency_id.id, 
                                    'status': 'done' 
                                })
                                wallet_create.wallet_transaction_email_send() #Mail Send to Customer
                                order.partner_id.update({
                                    'wallet_balance': order.partner_id.wallet_balance + order.order_line.price_unit * order.order_line.product_uom_qty})
                            order.with_context(send_email=True).action_confirm()
            elif tx_sudo.state == 'cancel':
                status = 'danger'
                message = tx_sudo.acquirer_id.cancel_msg
                order.action_cancel()
            else:
                status = 'danger'
                message = tx_sudo.state_message \
                          or _("An error occurred during the processing of this payment.")

            # Display the payment confirmation page to the user
            PaymentPostProcessing.remove_transactions(tx_sudo)
            render_values = {
                'tx': tx_sudo,
                'status': status,
                'message': message
            }
            return request.render('payment.confirm', render_values)
        else:
            # Display the portal homepage to the user
            return request.redirect('/my/home')

    @http.route(['/wallet'], type='http', auth="user", website=True)
    def wallet_balance(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        partner = request.env.user.partner_id
        WalletTransaction = request.env['website.wallet.transaction'].sudo()
        domain = [('partner_id', '=', partner.id)]
        company_currency = request.env.company.currency_id
        # web_currency = request.website.get_current_pricelist().currency_id
        price = float(partner.wallet_balance)
        values = {
                    'wallet_balance':price, 
                    'currency_id': company_currency
                }
        wallets = WalletTransaction.sudo().search(domain)
        # if company_currency.id != web_currency.id:
        #   new_rate = (price*web_currency.rate)/company_currency.rate
        #   price = round(new_rate,2)
        invoice_ids = request.env['account.move'].sudo().search([('partner_id','=',request.env.user.partner_id.id)],limit=2)
        values.update({
            'wallets': wallets.sudo(),
            'invoice_ids':invoice_ids,
            'current':'wallet'
        })
        return request.render("odoo_website_wallet.wallet_balance", values)


    @http.route(['/add/wallet/balance'], type='http', auth="user", website=True)
    def add_wallet_balance(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        return request.render("odoo_website_wallet.add_wallet_balance")
        
    
    @http.route(['/wallet/balance/confirm'], type='http', auth="public")
    def wallet_balance_confirm(self, **post):
    
        product = request.env.company.wallet_product_id
        if product:
            product_id = product.id
            prd_price=0
            company_currency = request.env.company.currency_id
            # web_currency = request.website.get_current_pricelist().currency_id      
            # if company_currency.id != web_currency.id:
            #   amount = post['amount']
            #   amount_replace = amount.replace(',', '')
            #   price = float(amount_replace)
            #   new_rate = (price*company_currency.rate)/web_currency.rate
            #   prd_price = new_rate 
            # else:
            amount = post['amount']
            amount_replace = amount.replace(',', '')
            prd_price = float(amount_replace)   
            order = self.sale_get_order(force_create=1)
            order.is_wallet = True
            if not order.order_line:
                request.env['sale.order.line'].sudo().create({
                    "order_id":order.id,
                    "product_id":product_id,
                    "product_uom_qty":1,
                    "price_unit":prd_price,
                    "line_wallet_amount" : prd_price,
                })
            else:
                for line in order.order_line:
                    if line.product_id.id == product_id:
                        line.update({
                                "product_uom_qty":1,
                                "price_unit":prd_price,
                                "line_wallet_amount" : prd_price,
                            }) 
            payment_link_wizard = request.env['payment.link.wizard'].sudo().create({
                    'res_id': order.id,
                    'res_model': 'sale.order',
                    'description': order.name,
                    'amount': order.amount_total - sum(order.invoice_ids.filtered(lambda x: x.state != 'cancel').mapped('amount_total')),
                    'currency_id': order.currency_id.id,
                    'partner_id': order.partner_invoice_id.id,
                    'amount_max': order.amount_total,
                })
            url = payment_link_wizard.link
            # return {
            #     'type': 'ir.actions.act_url',
            #     'target': 'self',
            #     'url': self.get_portal_url(),
            # }
            return request.redirect(url)
        else:
            return request.render("odoo_website_wallet.wallet_product_error")

    
    def _prepare_portal_layout_values(self):
        values = super(CustomerPortalWalletTransaction, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        WalletTransaction = request.env['website.wallet.transaction'].sudo()
        wallet_count = WalletTransaction.sudo().search_count([
            ('partner_id', '=', partner.id)])
        values.update({
            'wallet_count': wallet_count,
        })
        return values   
    
    @http.route(['/my/wallet-transactions', '/my/quotes/page/<int:page>'], type='http', auth="user")
    def portal_my_wallet_transaction(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        WalletTransaction = request.env['website.wallet.transaction'].sudo()
        domain = [
            ('partner_id', '=', partner.id)]
            
        searchbar_sortings = {
            'id': {'label': _('Wallet Transactions'), 'order': 'id desc'},
            
        }
        if not sortby:
            sortby = 'id'
        sort_wallet_transaction = searchbar_sortings[sortby]['order']
        # count for pager
        wallet_count = WalletTransaction.sudo().search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/wallet-transactions",
            total=wallet_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        wallets = WalletTransaction.sudo().search(domain, order=sort_wallet_transaction, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_wallet_transaction_history'] = wallets.ids[:100]
        values.update({
            'wallets': wallets.sudo(),
            'page_name': 'wallet',
            'pager': pager,
            'default_url': '/my/subcontractor-job-order',
        })
        return request.render("odoo_website_wallet.portal_my_wallet_transactions", values)

   # @http.route('/shop/payment/wallet', type='json', auth="public", methods=['POST'])
    # def wallet(self, wallet, **post):
    #     cr, uid, context = request.cr, request.uid, request.context
    #     order = request.website.sale_get_order()
    #     if wallet:
    #         order.write({
    #             'is_wallet' : False,
    #             'amount_total': (order.amount_untaxed + order.amount_tax)
    #         })
    #     if wallet == False:
    #         order.write({'is_wallet' : True})
    #         web_currency = request.website.get_current_pricelist().currency_id
    #         wallet_balance = request.website.get_wallet_balance(web_currency)
    #         if wallet_balance >= order.amount_total:
    #             order.write({'amount_total': 0.0 })

    #         if order.amount_total > wallet_balance:
    #             deduct_amount = order.amount_total - wallet_balance
    #             order.write({'amount_total': deduct_amount})
    #     return True

    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        res = super(CustomerPortalWalletTransaction, self).home(**kw)
        res.qcontext.update({'current':'home'})
        return res


# @http.route(['/shop/confirmation'], type='http', auth="public")
    # def shop_payment_confirmation(self, **post):
    #     sale_order_id = request.session.get('sale_last_order_id')
    #     if sale_order_id:
    #         order = request.env['sale.order'].sudo().browse(sale_order_id)
    #         if order.is_wallet == True:
    #             wallet_obj = request.env['website.wallet.transaction']
    #             partner = request.env['res.partner'].search([('id','=',order.partner_id.id)])      
    #             wallet_balance = order.partner_id.wallet_balance
    #             amount_total = (order.amount_untaxed + order.amount_tax)

    #             company_currency = request.website.company_id.currency_id
    #             web_currency = order.pricelist_id.currency_id
    #             price = float(amount_total)

    #             if company_currency.id != web_currency.id:
    #                 new_rate = (price*company_currency.rate)/web_currency.rate
    #                 price = round(new_rate,2)

    #             wallet_create = wallet_obj.sudo().create({ 
    #                 'wallet_type': 'debit', 
    #                 'partner_id': order.partner_id.id, 
    #                 'sale_order_id': order.id, 
    #                 'reference': 'sale_order', 
    #                 'amount': price, 
    #                 'currency_id': company_currency.id, 
    #                 'status': 'done' 
    #             })
                
    #             if wallet_balance >= price:
    #                 amount = wallet_balance - price
    #                 order.write({'wallet_used':float(amount_total),'wallet_transaction_id':wallet_create.id })
    #                 partner.sudo().write({'wallet_balance':amount})

    #             if price > wallet_balance:
    #                 p_wlt = request.website.get_wallet_balance(web_currency)
    #                 order.write({'wallet_used':p_wlt,'wallet_transaction_id':wallet_create.id})
    #                 partner.sudo().write({'wallet_balance':0.0})
    #                 order.wallet_transaction_id.update({'amount':p_wlt})
    #             wallet_create.wallet_transaction_email_send()
    #             return request.render("website_sale.confirmation", {'order': order})
    #         else:
    #             return super(WebsiteWalletPayment, self).shop_payment_confirmation(**post)
    #     return super(WebsiteWalletPayment, self).shop_payment_confirmation(**post)

