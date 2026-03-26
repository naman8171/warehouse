# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MailActivity(models.Model):
    _inherit = 'mail.activity'
 
    def activity_format(self):
        result = super(MailActivity, self).activity_format()
        activity_type_pay_process = self.env.ref('isn_approval_custom.mail_activity_pay_process').id
        for activity in result:
            if activity['activity_type_id'][0] == activity_type_pay_process and \
                    activity['res_model'] == 'approval.request':
                activity['can_write'] = False
        return result




