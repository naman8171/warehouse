# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    branch_id = fields.Many2one("res.branch", string="Country Region")
    # store_user_ids = fields.Many2many('res.users', 'store_branch_rel', string='Store Officer')
    procurement_user_ids = fields.Many2many('res.users', 'procurement_rel', string='Procurement Officer')
    procurement_manager_id = fields.Many2one('res.users', string='Procurement Manager')
    mgt_user_ids = fields.Many2many('res.users', 'mgt_rep_rel', string='MGT Rep')
    # facility_manager_id = fields.Many2one('res.users', string='Facility Manager')
    account_receviable_user_ids = fields.Many2many('res.users', 'account_receviable_rel', string='Account Receviable Officer')
    account_payable_user_ids = fields.Many2many('res.users', 'account_payable_rel', string='Account Payable Officer')
    general_manager_id = fields.Many2one('res.users', string='COO')
    engineering_manager_id = fields.Many2one('res.users', string='Engineering Manager')
    head_of_account = fields.Many2one('res.users', string='Head of Accounts')
    hoa_authorizer = fields.Many2one('res.users', string='HOA Authorizer')


    functional_vps_ids = fields.Many2many('res.users', 'functional_vps_rel', string='Functional VPs')
    country_managers_ids = fields.Many2many('res.users', 'country_manager_rel', string='Country Managers')
    csuite_functional_leads_id = fields.Many2one('res.users', string='C-Suite Functional Leads')
    eds_ids = fields.Many2many('res.users', 'eds_users_rel', string='EDs')
    ceo_group_id = fields.Many2one('res.users', string='Group CEO')


    vp_finance_id = fields.Many2one('res.users', string='VP Finance')
    treasury_users_ids = fields.Many2many('res.users', 'eds_users_rel', string='Treasury')
    cfo_id = fields.Many2one('res.users', string='CFO')
    eds_bank_ids = fields.Many2many('res.users', 'eds_users_rel', string='EDs')