# coding: utf-8
import requests, json, logging
from tokenize import group
from werkzeug.urls import url_join

from odoo import api, fields, service, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'
    
    provider = fields.Selection(
        selection_add=[('paystack', "Paystack")], ondelete={'paystack': 'cascade'})
    # provider = fields.Selection(selection_add=[('flutterwave', 'Flutterwave')], ondelete={'flutterwave': 'set default'})
    pstack_public_key = fields.Char(required_if_provider='paystack', groups='base.group_user')
    pstack_secret_key = fields.Char(required_if_provider='paystack', groups='base.group_user')
    # rave_secret_hash = fields.Char(required_if_provider='rave', groups='base.group_user', string="Flutterwave Secret Hash")
    environment = fields.Char(required_if_provider='paystack', groups='base.group_user')

    @api.model
    def _get_paystack_api_url(self):
        self.ensure_one()
        """ PaystackURLs"""
        return 'https://api.paystack.co'

    def _pstack_make_request(self, endpoint, payload=None, method='POST', offline=False):
        """ Make a request to Paystack API at the specified endpoint.
        Note: self.ensure_one()
        :param str endpoint: The endpoint to be reached by the request
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :param bool offline: Whether the operation of the transaction being processed is 'offline'
        :return The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """
        self.ensure_one()

        url = url_join('https://api.paystack.co', endpoint)
        headers = {
            'Authorization': f'Bearer {self.pstack_secret_key}',
            "Content-Type": "application/json"
        }
        try:
            _logger.info("method: %s", method)
            _logger.info("payload: %s", payload)
            response = requests.request(method, url, data=payload, headers=headers, timeout=3600)
            # _logger.info("response: %s", response)
            response.raise_for_status()
            j = json.loads(response.text)
            _logger.info("response: %s", j)

            if j['status'] is not True:
                try:
                    _logger.info("I am not response true")
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    _logger.exception("invalid API request at %s with data %s", url, payload)
                    error_msg = response.json().get('error', {}).get('message', '')
                    raise ValidationError(
                        "Paystack: " + _(
                            "The communication with the API failed.\n"
                            "Paystack gave us the following info about the problem:\n'%s'", error_msg
                        )
                    )
        except requests.exceptions.RequestException as err:
            _logger.exception("unable to reach endpoint at %s", url)
            _logger.exception("unable to reach endpoint error: %s", err)
            raise ValidationError("Paystack: " + _("Could not establish the connection to the API."))
        _logger.info("Response json: %s", response.json())
        return response.json()

    def _pstack_get_request(self, endpoint, method='GET', offline=False):
        self.ensure_one()

        url = url_join('https://api.paystack.co', endpoint)
        headers = {
            'AUTHORIZATION': f'Bearer {self.pstack_secret_key}',
            "Content-Type": "application/json"
        }

        try:
            response = requests.request(method, url, data=None, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            _logger.exception("Unable to communicate with Paystack: %s", url)
            raise ValidationError("Paystack: " + _("Could not establish the connection to the API."))
        return response.json()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'paystack':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_paystack_ecommerce.payment_method_paystack').id


    def _should_build_inline_form(self, is_validation=False):
        """ Return whether the inline form should be instantiated if it exists.
        For an acquirer to handle both direct payments and payment with redirection, it should
        override this method and return whether the inline form should be instantiated (i.e. if the
        payment should be direct) based on the operation (online payment or validation).
        :param bool is_validation: Whether the operation is a validation
        :return: Whether the inline form should be instantiated
        :rtype: bool
        """
        return True





