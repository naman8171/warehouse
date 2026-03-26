# -*- coding: utf-8 -*-

import logging
import werkzeug

from odoo import http, _
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.web.controllers.main import ensure_db, Home
from odoo.addons.base_setup.controllers.main import BaseSetup
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)



class Home(Home):

    def _login_redirect(self, uid, redirect=None):
        res=super(Home, self)._login_redirect(uid, redirect=redirect)
        if not redirect and not request.env['res.users'].sudo().browse(uid).has_group('base.group_user'):
            res = '/my/analytic'
        return res


class AuthSignupInh(AuthSignupHome):

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        if kw:
            if 'name' not in qcontext:
                qcontext['name'] = kw.get('first_name') + ' ' + kw.get('last_name')
            if 'name' not in qcontext:
                qcontext['name'] = kw.get('first_name') + ' ' + kw.get('last_name')
            if 'phone' not in qcontext:
                qcontext['phone'] = kw.get('phone_number')
            if 'website' not in qcontext:
                qcontext['website'] = kw.get('business_website')
            if 'business_name' not in qcontext:
                qcontext['business_name'] = kw.get('business_name')
            if 'order_count' not in qcontext:
                qcontext['order_count'] = int(kw.get('order_count'))
            if 'terms_condition' not in qcontext:
                if int(kw.get('terms_and_condition')) == 1:
                    qcontext['terms_and_condition'] = True
                else:
                    qcontext['terms_and_condition'] = False
        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()
        
        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                # Send an account creation confirmation email
                if qcontext.get('token'):
                    User = request.env['res.users']
                    
                    user_sudo = User.sudo().search(
                        User._get_login_domain(qcontext.get('login')), order=User._get_login_order(), limit=1
                    )
                    template = request.env.ref('ag_the_hub.mail_template_user_signup_account_created_new', raise_if_not_found=False)
                    if user_sudo and template:
                        template.sudo().send_mail(user_sudo.id, force_send=True)
                return self.web_login(*args, **kw)
            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _("Another user is already registered using this email address.")
                else:
                    _logger.error("%s", e)
                    qcontext['error'] = _("Could not create a new account.")

        response = request.render('auth_signup.signup', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    def _prepare_signup_values(self, qcontext):
        values = { key: qcontext.get(key) for key in ('login', 'name', 'password', 'business_name', 'website', 'order_count', 'phone','terms_and_condition') }
        if not values:
            raise UserError(_("The form was not properly filled in."))
        if values.get('password') != qcontext.get('confirm_password'):
            raise UserError(_("Passwords do not match; please retype them."))
        supported_lang_codes = [code for code, _ in request.env['res.lang'].get_installed()]
        lang = request.context.get('lang', '')
        if lang in supported_lang_codes:
            values['lang'] = lang
        return values
