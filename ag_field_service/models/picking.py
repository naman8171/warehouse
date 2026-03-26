# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    project_task_id = fields.Many2one("project.task", string="Job Order", copy=False)

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.purchase_id:
            domain = [
                ('res_model', '=', 'purchase.order'),
                ('res_id', 'in', self.purchase_id.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_po_supply').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="Purchase Order Supply Validated")
            # group_id = self.env.ref('purchase.group_purchase_user')
            for user in self.env.company.account_payable_user_ids:
                domain = [
                    ('res_model', '=', 'purchase.order'),
                    ('res_id', 'in', self.purchase_id.ids),
                    ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_create_vendor_bill').id),
                    ('user_id', '=', user.id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if not activities:
                    self.purchase_id.activity_schedule('ag_field_service.mail_activity_create_vendor_bill', user_id=user.id)
        return res