# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class MeterReading(models.Model):
    _name = "meter.reading"
    _description = "Meter Reading"

    partner_id = fields.Many2one("res.partner", string="Partner")
    date = fields.Date("Date")
    previous_reading = fields.Float("Previous Reading")
    present_reading = fields.Float("Present Reading")
    consume_reading = fields.Float("Consume Reading", compute="_compute_consume_reading", store=True)
    remarks = fields.Text("Remarks")
    is_editable = fields.Boolean("Is Editable?", compute="_compute_is_editable")
    common_equipment_id = fields.Many2one("common.equipment", string="Equipment")

    @api.onchange('date')
    def onchange_date(self):
        for rec in self:
            previous_meter_reading_id = self.search([('partner_id', '=', int(str(rec.partner_id.id).split('_')[1]))], order="date desc", limit=1)
            if previous_meter_reading_id:
                rec.previous_reading = previous_meter_reading_id.present_reading

    @api.depends('previous_reading', 'present_reading')
    def _compute_consume_reading(self):
        for rec in self:
            rec.consume_reading = rec.present_reading - rec.previous_reading

    @api.depends('partner_id')
    def _compute_is_editable(self):
        user_ids = []
        facility_manager_id = self.partner_id.branch_id.facility_manager_id
        if facility_manager_id:
            user_ids.append(facility_manager_id.id)
        general_manager_id = self.env.company.general_manager_id
        if general_manager_id:
            user_ids.append(general_manager_id.id)
        engineering_manager_id = self.env.company.engineering_manager_id
        if engineering_manager_id:
            user_ids.append(engineering_manager_id.id)
        current_user = self.env.user
        for rec in self:
            if current_user.has_group('base.user_admin'):
                rec.is_editable = True
            elif current_user.id in user_ids:
                rec.is_editable = True
            elif not rec.date or rec.previous_reading <= 0 or rec.present_reading <= 0:
                rec.is_editable = True
            else:
                rec.is_editable = False
                