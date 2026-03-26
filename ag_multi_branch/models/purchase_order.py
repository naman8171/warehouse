# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    """inherited purchase order"""
    _inherit = 'purchase.order'

    branch_id = fields.Many2one("res.branch", string='Country Region', store=True,
                                readonly=False,
                                compute="_compute_branch")
    rfq_type = fields.Selection([('not_common_area_direct', 'Not Common Area Direct'), ('common_area_direct', 'Common Area Direct')], string="RFQ Type", copy=False, default="not_common_area_direct")
    cost_category_id = fields.Many2one("cost.category", string="Cost Category")

    @api.depends('company_id')
    def _compute_branch(self):
        for order in self:
            company = self.env.company
            so_company = order.company_id if order.company_id else self.env.company
            branch_ids = self.env.user.branch_ids
            branch = branch_ids.filtered(
                lambda branch: branch.company_id == so_company)
            if branch:
                order.branch_id = branch.ids[0]
            else:
                order.branch_id = False

    @api.model
    def _get_picking_type(self, company_id):
        """methode to set default picking type"""
        if len(self.env.user.branch_ids) == 1:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'incoming'),
                 ('warehouse_id.branch_id', '=', company_id)])
            if not picking_type:
                picking_type = self.env['stock.picking.type'].search(
                    [('code', '=', 'incoming'),
                     ('warehouse_id.branch_id', '=', False)])
            if not picking_type:
                error_msg = _(
                    "No warehouse could be found in the '%s' branch",
                    self.env.user.branch_id.name
                )
                raise UserError(error_msg)
            return picking_type[:1]
        else:
            res = super(PurchaseOrder, self)._get_picking_type(company_id)
            return res

    @api.model
    def _default_picking_type(self):
        """methode to get default picking type"""
        if len(self.env.user.branch_ids) == 1:
            branch = self.env.user.branch_id
            if branch:
                return self._get_picking_type(branch.id)
        else:
            return self._get_picking_type(self.env.context.get('company_id')
                                          or self.env.company.id)

    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Deliver To',
        states=Purchase.READONLY_STATES,
        required=True,
        default=_default_picking_type,
        domain="[('code','=','incoming'), "
               "('warehouse_id.company_id', '=', company_id),"
               "'|', ('warehouse_id.branch_id', '=', branch_id),"
               "('warehouse_id.branch_id', '=', False),]",
        help="This will determine operation type"
             " of incoming shipment")

    allowed_branch_ids = fields.Many2many('res.branch', string="Allowed Country Regions", compute='_compute_allowed_branch_ids')

    @api.depends('company_id')
    def _compute_allowed_branch_ids(self):
        for po in self:
            po.allowed_branch_ids = self.env.user.branch_ids.ids

    @api.constrains('branch_id', 'partner_id')
    def _check_partner_branch_id(self):
        """methode to check branch of partner and purchase order"""
        for order in self:
            branch = order.partner_id.branch_id
            if branch and branch != order.branch_id:
                raise ValidationError(_(
                    "Your quotation vendor is from %(partner_branch)s "
                    "branch whereas your quotation belongs to %(quote_branch)s"
                    " branch \n Please change the "
                    "branch of your quotation or remove the vendor from "
                    "other branch.",
                    partner_branch=branch.name,
                    quote_branch=order.branch_id.name,
                ))

    @api.constrains('branch_id', 'order_line')
    def _check_order_line_branch_id(self):
        """methode to check branch of products and purchase order"""
        for order in self:
            branches = order.order_line.product_id.branch_id
            if branches and branches != order.branch_id:
                bad_products = order.order_line.product_id.filtered(
                    lambda p: p.branch_id and p.branch_id != order.branch_id)
                raise ValidationError(_(
                    "Your quotation contains products from %(product_branch)s "
                    "branch whereas your quotation belongs to %(quote_branch)s"
                    " branch \n Please change the "
                    "branch of your quotation or remove the products from "
                    "other branches (%(bad_products)s).",
                    product_branch=', '.join(branches.mapped('name')),
                    quote_branch=order.branch_id.name,
                    bad_products=', '.join(bad_products.mapped('display_name')),
                ))

    def _prepare_invoice(self):
        """override prepare_invoice function to include branch"""
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        branch_id = self.branch_id.id
        domain = [('branch_id', '=', branch_id),
                  ('type', '=', 'purchase'), ('company_id', '=', self.company_id.id)]
        journal = None

        if self._context.get('default_currency_id'):
            currency_domain = domain + [
                ('currency_id', '=', self._context['default_currency_id'])]
            journal = self.env['account.journal'].search(currency_domain,
                                                         limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)
        if not journal:
            domain = [('type', '=', 'purchase'),
                      ('branch_id', '=', False), ('company_id', '=', self.company_id.id)]
            journal = self.env['account.journal'].search(domain, limit=1)
        if not journal:
            error_msg = _(
                "No journal could be found in the'%s' branch"
                " for any of those types: purchase", self.branch_id.name,)
            raise UserError(error_msg)
        invoice_vals['branch_id'] = self.branch_id.id or False
        invoice_vals['journal_id'] = journal.id
        invoice_vals['cost_category_id'] = self.cost_category_id.id
        return invoice_vals

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        """onchange function"""
        if self.branch_id and self.branch_id not in self.env.user.branch_ids and self.env.user.branch_ids:
            raise UserError("Unauthorised Branch")
        self.picking_type_id = False
        if self.branch_id:
            picking_type = self.env['stock.picking.type'].sudo().search(
                [('branch_id', '=', self.branch_id.id), ('company_id', '=', self.company_id.id)], limit=1)
            self.picking_type_id = picking_type
            if not picking_type:
                picking_type = self.env['stock.picking.type'].sudo().search(
                    [('branch_id', '=', False), ('company_id', '=', self.company_id.id)], limit=1)
            self.picking_type_id = picking_type
            if not picking_type:
                error_msg = _(
                    "No warehouse could be found in the '%s' branch",
                    self.branch_id.name
                )
                raise UserError(error_msg)
        else:
            self.picking_type_id = self.env['stock.picking.type'].sudo().search(
                [('branch_id', '=', False), ('company_id', '=', self.company_id.id)], limit=1)


class PurchaseOrderLine(models.Model):
    """inherited purchase order line"""
    _inherit = 'purchase.order.line'

    branch_id = fields.Many2one(related='order_id.branch_id', string='Country Region',
                                store=True)

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        res.update({
            'branch_id': self.branch_id.id,
            'account_id': self.product_id.property_account_expense_id.id
            })
        return res


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"
    
    branch_id = fields.Many2one("res.branch", string='Site', store=True, readonly=False, compute="_compute_branch")
    allowed_branch_ids = fields.Many2many('res.branch', string="Allowed Country Regions", compute='_compute_allowed_branch_ids')

    @api.depends('company_id')
    def _compute_branch(self):
        for rec in self:
            company = self.env.company
            so_company = rec.company_id if rec.company_id else self.env.company
            branch_ids = self.env.user.branch_ids
            branch = branch_ids.filtered(
                lambda branch: branch.company_id == so_company)
            if branch:
                rec.branch_id = branch.ids[0]
            else:
                rec.branch_id = False



    @api.depends('company_id')
    def _compute_allowed_branch_ids(self):
        for pa in self:
            pa.allowed_branch_ids = self.env.user.branch_ids.ids

class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    branch_id = fields.Many2one(related='requisition_id.branch_id', string='Country Region', store=True)
