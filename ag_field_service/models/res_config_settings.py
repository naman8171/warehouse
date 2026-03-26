# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_default_branch(self):
        branch = self.env.user.branch_id
        return branch

    portal_allow_api_keys = fields.Char()
    branch_id = fields.Many2one('res.branch', string='Country Region', required=True, default=_get_default_branch, store=True)
    store_user_ids = fields.Many2many(related='branch_id.store_user_ids', string='Store Officer', readonly=False)
    procurement_user_ids = fields.Many2many(related='company_id.procurement_user_ids', string='Procurement Officer', readonly=False)
    procurement_manager_id = fields.Many2one(related='company_id.procurement_manager_id', string='Procurement Manager', readonly=False)
    mgt_user_ids = fields.Many2many(related='company_id.mgt_user_ids', string='MGT Rep', readonly=False)
    facility_manager_id = fields.Many2one(related='branch_id.facility_manager_id', string='Facility Manager', readonly=False)
    account_receviable_user_ids = fields.Many2many(related='company_id.account_receviable_user_ids', string='Account Receviable Officer', readonly=False)
    account_payable_user_ids = fields.Many2many(related='company_id.account_payable_user_ids', string='Account Payable Officer', readonly=False)
    head_of_account = fields.Many2one(related='company_id.head_of_account', string='Head of Accounts', readonly=False)
    hoa_authorizer = fields.Many2one(related='company_id.hoa_authorizer', string='HOA Authorizer', readonly=False)
    general_manager_id = fields.Many2one(related='company_id.general_manager_id', string='COO', readonly=False)
    engineering_manager_id = fields.Many2one(related='company_id.engineering_manager_id', string='Engineering Manager', readonly=False)


    functional_vps_ids = fields.Many2many(related='company_id.functional_vps_ids', string='Functional VPs', readonly=False)
    country_managers_ids = fields.Many2many(related='company_id.country_managers_ids', string='Country Managers', readonly=False)
    csuite_functional_leads_id = fields.Many2one(related='company_id.csuite_functional_leads_id', string='C-Suite Functional Leads', readonly=False)
    eds_ids = fields.Many2many(related='company_id.eds_ids', string='EDs', readonly=False)
    ceo_group_id = fields.Many2one(related='company_id.ceo_group_id', string='Group CEO', readonly=False)


    vp_finance_id = fields.Many2one(related='company_id.vp_finance_id', string='VP Finance', readonly=False)
    treasury_users_ids = fields.Many2many(related='company_id.treasury_users_ids', string='Treasury', readonly=False)
    cfo_id = fields.Many2one(related='company_id.cfo_id', string='CFO', readonly=False)
    eds_bank_ids = fields.Many2many(related='company_id.eds_bank_ids', string='EDs', readonly=False)