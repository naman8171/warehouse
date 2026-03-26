import logging
import requests
import pprint
import json

from werkzeug.urls import url_join, url_encode

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError
from odoo.addons.payment_paystack_ecommerce.controllers.controllers import PaystackController

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Paystack-specific processing values.
        Note: self.ensure_one() from `_get_processing_values`
        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider != 'paystack' or self.operation == 'online_token':
            return res
        # self.acquirer_reference = self.reference
        payload = self._paystack_prepare_payment_request_payload()
        payload.update({'pub_key': self.acquirer_id.pstack_public_key,})
        return payload
        

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Paystack-specific rendering values.
        Note: self.ensure_one() from `_get_processing_values`
        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific rendering values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'paystack':
            return res

        payload = self._paystack_prepare_payment_request_payload()
        payload.update({'pub_key': self.acquirer_id.pstack_public_key,})
        # payloads = json.dumps(payload)
        # _logger.info("sending '/transaction/initialize' request for link creation:\n%s", pprint.pformat(payloads))
        # payment_data = self.acquirer_id._pstack_make_request('/transaction/initialize', payload=payloads)
        _logger.info("Payment data: %s", payload)

        # The acquirer reference is set now to allow fetching the payment status after redirection
        self.acquirer_reference = self.reference
        # processing_values.update({
        #     'callback_url': payload['callback_url'],
        #     'pub_key': self.acquirer_id.pstack_public_key,
        #     'email': self.partner_email,
        #     'amount': str(self.amount),
        #     'reference': self.reference,
        # })

        # if payment_data.get('status') != True:
        #     raise ValidationError("Paystack " + _("Unable to generate Payment Link. Try again"))
        # return {'api_url': payment_data.get('data').get('authorization_url')}
        return payload


    def _paystack_prepare_payment_request_payload(self):
        """ Create the payload for the payment request based on the transaction values.
        :return: The request payload
        :rtype: dict
        """
        base_url = self.acquirer_id.get_base_url()
        return_url = PaystackController._checkout_return_url

        return {
            'reference': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'callback_url': str(url_join(base_url, return_url)),
            'email': self.partner_email,
        }    


    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Paystack data.
        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'paystack':
            return tx

        _logger.info("data stage get_tx_from_feedback_data: %s", data)
        data = data['data']
        
        reference = data.get('reference')
        self.acquirer_reference = reference
        transaction_id = data.get('transaction_id')
        from_paystack_status = data.get('status')

        if not reference:
            raise ValidationError("Paystack: " + _("Received data with missing merchant reference"))

        tx = self.search([('reference', '=', reference ), ('provider', '=', 'paystack')])
        if not tx:
            raise ValidationError(
                "Paystack: " + _("No transaction found matching reference %s.", reference )
            )
        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Paystack data.
        Note: self.ensure_one()
        :param dict data: The feedback data sent by the provider
        :return: None
        """
        super()._process_feedback_data(data)
        if self.provider != 'paystack':
            return

        _logger.info("reference stage process_feedback_data: %s", self.acquirer_reference)
        payment_data = self.acquirer_id._pstack_get_request(
            f'/transaction/verify/{self.reference}'
        )
        payment_status = payment_data.get('data').get('status') #confirm this is correct
        currency = payment_data.get('data').get('currency')
        amount = payment_data.get('data').get('amount')

        _logger.info("paystack verify endpoint: %s", payment_status)

        if payment_status == 'success' and (self.amount * 100) == amount and self.currency_id.name == currency:
            self._set_done()
        elif payment_status == 'failed':
            self._set_canceled("Paystack: " + _("Canceled payment with status: %s", payment_status))
        # elif payment_status == 'successful' and (self.amount * 100) != amount:
        elif payment_status == 'successful' and (self.amount * 100) != amount or payment_status == 'success' and self.currency_id.name == currency:
            _logger.info("Successful Partial Payment Made: %s", payment_status)
            _logger.info("amount: %s", amount)
            _logger.info("self.amount: %s", self.amount)
            _logger.info("currency: %s", currency)
            _logger.info("self.currency: %s", self.currency_id.name)
            self._set_pending(state_message="Partial Payment Made")
        else:
            _logger.info("Received data with invalid payment status: %s", payment_status)
            self._set_error(
                "Paystack: " + _("Received data with invalid payment status: %s", payment_status)
            )





