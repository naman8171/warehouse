# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    the_hub_account_activation = fields.Many2many('res.users', string='Account Activation')
    picker_user_ids = fields.Many2many('res.users', 'picker_rel', string='Pickers')
    receiver_user_ids = fields.Many2many('res.users', 'receiver_rel', string='Receivers')
    packer_user_ids = fields.Many2many('res.users', 'packer_rel', string='Packers')
    dispatch_user_ids = fields.Many2many('res.users', 'dispatch_rel', string='Dispatchers')
    supervisor_user_ids = fields.Many2many('res.users', 'supervisor_rel', string='Supervisors')
    wro_picker_user_ids = fields.Many2many('res.users', 'wro_picker_rel', string='WRO Pickers')



    incoming_pallet_cost_cons = fields.Float("Incoming Pallet Cost Consoladited")
    incoming_pallet_cost_cons_product = fields.Many2one('product.product' ,domain="[('type','=','service')]")


    incoming_pallet_cost_noncons = fields.Float("Incoming Pallet Cost Non-Consoladited")
    incoming_pallet_cost_noncons_product = fields.Many2one('product.product' ,domain="[('type','=','service')]")



    incoming_box_cost_cons = fields.Float("Incoming Box Cost Consoladited")
    incoming_box_cost_cons_product = fields.Many2one('product.product',domain="[('type','=','service')]")


    incoming_box_cost_noncons = fields.Float("Incoming Box Cost Non-Consoladited")
    incoming_box_cost_noncons_product = fields.Many2one('product.product' ,domain="[('type','=','service')]")


    outgoing_pallet_cost_cons = fields.Float("Outgoing Pallet Cost Consoladited")
    outgoing_pallet_cost_cons_product = fields.Many2one('product.product' ,domain="[('type','=','service')]")


    outgoing_pallet_cost_noncons = fields.Float("Outgoing Pallet Cost Non-Consoladited")
    outgoing_pallet_cost_noncons_product = fields.Many2one('product.product' ,domain="[('type','=','service')]")



    outgoing_box_cost_cons = fields.Float("Outgoing Box Cost Consoladited")
    outgoing_box_cost_cons_product = fields.Many2one('product.product' ,domain="[('type','=','service')]")


    outgoing_box_cost_noncons = fields.Float("Outgoing Box Cost Non-Consoladited")
    outgoing_box_cost_noncons_product = fields.Many2one('product.product' ,domain="[('type','=','service')]")



    thl_shipping_cost = fields.Float("THL Shipping COST")
    thl_shipping_product_id = fields.Many2one('product.product')
