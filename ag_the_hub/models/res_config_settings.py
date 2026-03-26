# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    the_hub_account_activation = fields.Many2many(related='company_id.the_hub_account_activation', string='Account Activation', readonly=False)
    picker_user_ids = fields.Many2many(related='company_id.picker_user_ids', string='Pickers', readonly=False)
    receiver_user_ids = fields.Many2many(related='company_id.receiver_user_ids', string='Receivers', readonly=False)
    packer_user_ids = fields.Many2many(related='company_id.packer_user_ids', string='Packers', readonly=False)
    dispatch_user_ids = fields.Many2many(related='company_id.dispatch_user_ids', string='Dispatchers', readonly=False)
    supervisor_user_ids = fields.Many2many(related='company_id.supervisor_user_ids', string='Supervisors', readonly=False)
    wro_picker_user_ids = fields.Many2many(related='company_id.wro_picker_user_ids', string='WRO Pickers', readonly=False)





    incoming_pallet_cost_cons = fields.Float( related='company_id.incoming_pallet_cost_cons',string="Incoming Pallet Cost Consoladited", readonly=False)
    incoming_pallet_cost_cons_product = fields.Many2one( related='company_id.incoming_pallet_cost_cons_product',readonly=False)



    incoming_pallet_cost_noncons = fields.Float(related='company_id.incoming_pallet_cost_noncons',string="Incoming Pallet Cost Non-Consoladited", readonly=False)
    incoming_pallet_cost_noncons_product = fields.Many2one(related='company_id.incoming_pallet_cost_noncons_product',readonly=False)


    incoming_box_cost_cons = fields.Float(related='company_id.incoming_box_cost_cons',string="Incoming Box Cost Consoladited", readonly=False)
    incoming_box_cost_cons_product = fields.Many2one(related='company_id.incoming_box_cost_cons_product',readonly=False)


    incoming_box_cost_noncons = fields.Float(related='company_id.incoming_box_cost_noncons',string="Incoming Box Cost Non-Consoladited", readonly=False)
    incoming_box_cost_noncons_product = fields.Many2one(related='company_id.incoming_box_cost_noncons_product',readonly=False)


    outgoing_pallet_cost_cons = fields.Float(related='company_id.outgoing_pallet_cost_cons',string="Outgoing Pallet Cost Consoladited", readonly=False)
    outgoing_pallet_cost_cons_product = fields.Many2one(related='company_id.outgoing_pallet_cost_cons_product',readonly=False)


    outgoing_pallet_cost_noncons = fields.Float(related='company_id.outgoing_pallet_cost_noncons',string="Outgoing Pallet Cost Non-Consoladited", readonly=False)
    outgoing_pallet_cost_noncons_product = fields.Many2one(related='company_id.outgoing_pallet_cost_noncons_product',readonly=False)


    outgoing_box_cost_cons = fields.Float(related='company_id.outgoing_box_cost_cons',string="Outgoing Box Cost Consoladited", readonly=False)
    outgoing_box_cost_cons_product = fields.Many2one(related='company_id.outgoing_box_cost_cons_product',readonly=False)


    outgoing_box_cost_noncons = fields.Float(related='company_id.outgoing_box_cost_noncons',string="Outgoing Box Cost Non-Consoladited", readonly=False)
    outgoing_box_cost_noncons_product = fields.Many2one(related='company_id.outgoing_box_cost_noncons_product',readonly=False)

    
    thl_shipping_cost = fields.Float(related="company_id.thl_shipping_cost",string="THL Shipping COST", readonly=False)
    thl_shipping_product_id = fields.Many2one(related="company_id.thl_shipping_product_id",string="THL Shipping Product", readonly=False)

