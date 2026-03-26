# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    wro_id = fields.Many2one('warehouse.receive.order')
    wo_id = fields.Many2one('thehub.workorder')
    wo_dispute_id = fields.Many2one('thehub.workorder')
    
    resolution_feedback = fields.Html('Resolution Feedback')
    delivery_status  = fields.Selection([('delivery', 'Delivery'),
                                ('failed', 'Delivery Failed')
                                    ], string="Delivery Status")



    category_id = fields.Many2one('helpdesk.ticket.type',store="Category",domain="[('parent_id','=',False)]")
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Type",domain="[('parent_id','=',category_id)]")



    def get_portal_info_ticket(self):
        current_month = fields.Date.today().month
        current_year = fields.Date.today().year
        month = fields.Date.today().strftime("%B, %Y")
        domain=[('partner_id','=',self.env.user.partner_id.id)]


        overall_ticket_count_closed = self.search_count(domain+[('stage_id.is_close', '=', True)])
        current_ticket_count_closed = len(self.search(domain+[('stage_id.is_close', '=', True)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        overall_ticket_count_open = self.search_count(domain+[('stage_id.is_close', '=', False)])
        current_ticket_count_open = len(self.search(domain+[('stage_id.is_close', '=', False)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year))
        data=[current_ticket_count_open,current_ticket_count_closed,overall_ticket_count_open,overall_ticket_count_closed]
        
        
        

        return [data]

        
    # wallet_balance = fields.Float(compute="_compute_wallet_balance",store=True,string="Wallet Balance")


    # @api.depends('partner_id')
    # def _compute_wallet_balance(self):
    #     for rec in self:
    #         wallet_data = self.env['pos.wallet.transaction'].search([('partner_id', 'in', rec.partner_id.ids)])
    #         rec.wallet_balance = 0.0
    #         for trns in wallet_data : 
    #             if trns.status == 'done' :
    #                 if trns.wallet_type == 'credit' :
    #                     rec.wallet_balance += float(trns.amount)

    #                 if trns.wallet_type == 'debit' :
    #                     rec.wallet_balance -= float(trns.amount)

    #         partner.wallet_transaction_count = len(wallet_data)


    

    def write(self,vals):
        res = super(HelpdeskTicket, self).write(vals)
        if 'stage_id' in vals:
            if self.stage_id.is_close and self.wro_id:
                body = _("<strong>Your request Dispute - %s has been Resolved and The Resolution Feedback of your ticket is :- </div><div style='color:red;'>%s</div>",self.name,self.resolution_feedback)
                

                self.wro_id.message_post(body=body)
                for user in self.team_id.visibility_member_ids:
                    domain = [
                        ('res_model', '=', 'helpdesk.ticket'),
                        ('res_id', 'in', self.ids),
                        ('user_id', '=', user.id),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_wro_dispute').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        activities.sudo().action_feedback(feedback="Dispute Solved")
                        #print("333333333333.............",activities)
            elif self.wro_id:
                body = _("<strong>Your request Dispute - %s is in progress and Now is in State :- </div><div style='color:red;'>%s</div>",self.name,self.stage_id.name)
                

                self.wro_id.message_post(body=body)
            elif self.stage_id.is_close and self.wo_id:
                if self.delivery_status == 'delivery':
                    body = _("<strong>Your request Dispatch - %s has been Resolved and The Resolution Feedback of your ticket is :- </div><div style='color:red;'>%s</div>",self.name,self.resolution_feedback)
                    

                    self.wo_id.message_post(body=body)
                    self.wo_id.action_delivery_done()
                    for user in self.team_id.visibility_member_ids:
                        domain = [
                            ('res_model', '=', 'helpdesk.ticket'),
                            ('res_id', 'in', self.ids),
                            ('user_id', '=', user.id),
                            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_wo_dispatch').id),
                        ]
                        activities = self.env['mail.activity'].sudo().search(domain)
                        if activities:
                            activities.sudo().action_feedback(feedback="Delivered Done")
                    self.wo_id.message_post(body=body)
                else:
                    if self.wo_id.return_wo_id:
                        raise ValidationError("Return Already Generate Please check")
                    self.wo_id.action_delivery_return()
                    for user in self.team_id.visibility_member_ids:
                        domain = [
                            ('res_model', '=', 'helpdesk.ticket'),
                            ('res_id', 'in', self.ids),
                            ('user_id', '=', user.id),
                            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_wo_dispatch').id),
                        ]
                        activities = self.env['mail.activity'].sudo().search(domain)
                        if activities:
                            activities.sudo().action_feedback(feedback="Delivered Failed")

                    body = _("<strong>Your request Dispatch - %s was not successfully delivered and a return order has been activated and the feedback of your ticket is :- </div><div style='color:red;'>%s</div>",self.name,self.resolution_feedback)
                    

                    
                    self.wo_id.message_post(body=body)

            elif self.wo_id:
                body = _("<strong>Your request Dispatch - %s is in progress and Now is in State :- </div><div style='color:red;'>%s</div>",self.name,self.stage_id.name)
            
                self.wo_id.message_post(body=body)
            elif self.stage_id.is_close and self.wo_dispute_id:
                body = _("<strong>Your request WO Dispute - %s has been Resolved and The Resolution Feedback of your ticket is :- </div><div style='color:red;'>%s</div>",self.name,self.resolution_feedback)
                

                self.wo_dispute_id.message_post(body=body)
                #self.wo_id.action_delivery_done()
                for user in self.team_id.visibility_member_ids:
                    domain = [
                        ('res_model', '=', 'helpdesk.ticket'),
                        ('res_id', 'in', self.ids),
                        ('user_id', '=', user.id),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_wo_dispute').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        activities.sudo().action_feedback(feedback="Dispute Solved")
            elif self.wo_dispute_id:
                body = _("<strong>Your request WO Dispute - %s is in progress and Now is in State :- </div><div style='color:red;'>%s</div>",self.name,self.stage_id.name)
            
                self.wo_dispute_id.message_post(body=body)


        return res

    # @api.onchange('stage_id')
    # def _onchange_state_custom(self):

    #     if self.stage_id.is_close and self.wro_id and self.resolution_feedback:
    #         body = _("<strong>Your request Dispute - %s has been Resolved and The Resolution Feedback of your ticket is :- </div><div style='color:red;'>%s</div>",self.name,self.resolution_feedback)
            

    #         self.wro_id.message_post(body=body)
    #         for user in self.team_id.visibility_member_ids:
    #             domain = [
    #                 ('res_model', '=', 'helpdesk.ticket'),
    #                 ('res_id', 'in', self.ids),
    #                 ('user_id', '=', user.id),
    #                 ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_wro_dispute').id),
    #             ]
    #             print("3333333333333333333333333333")
    #             activities = self.env['mail.activity'].sudo().search(domain)
    #             print("333333333333.............",activities)
    #             # if activities:
    #             #     print("333333333333.............",activities)
    #             #     activities.sudo().action_feedback(feedback="Dispute Solved")
    #             #     print("333333333333.............",activities)
    #     elif self.wro_id:
    #         body = _("<strong>Your request Dispute - %s is in progress and Now is in State :- </div><div style='color:red;'>%s</div>",self.name,self.stage_id.name)
            

    #         self.wro_id.message_post(body=body)
            


class HelpdeskTicketType(models.Model):
    _inherit = "helpdesk.ticket.type"


    parent_id = fields.Many2many("helpdesk.ticket.type","rel_helpdesk_ticket_type","rel_helpdesk_ticket_type_model",store="Parent")

