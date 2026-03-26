# -*- coding: utf-8 -*-
import logging
import pprint

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaystackController(http.Controller):
    _checkout_return_url = "/payment/paystack/checkout/return"
    _notify_url = "/payment/paystack/notify"
    
    @http.route(
        _checkout_return_url, type='json', auth='public', methods=['GET','POST'], csrf=False,
        save_session=False
    )
    def paystack_return(self, **data):
        """ Process the data returned by Paystack after redirection."""
        _logger.info("Paystack return data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_feedback_data('paystack', data)
        return '/payment/status'
        # return request.redirect('/payment/status')

    
    @http.route(_notify_url, type='http', auth='public', methods=['POST'], csrf=False)
    def paystack_notify(self, **data):
        """ Process the data sent by Paystack to the webhook.
        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        _logger.info("Paystack notify data:\n%s", pprint.pformat(data))
        try:
            request.env['payment.transaction'].sudo()._handle_feedback_data('paystack', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the notification data; skipping to acknowledge")
        return ''  # Acknowledge the notification with an HTTP 200 response