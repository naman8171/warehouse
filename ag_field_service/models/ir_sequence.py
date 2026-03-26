# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
import calendar

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def _create_date_range_seq(self, date):
        year = fields.Date.from_string(date).strftime('%Y')
        month = fields.Date.from_string(date).strftime('%m')
        day = calendar.monthrange(int(year), int(month))[1]
        date_from = '{}-{}-01'.format(year, month)
        date_to = '{}-{}-{}'.format(year, month, day)
        date_range = self.env['ir.sequence.date_range'].search([('sequence_id', '=', self.id), ('date_from', '>=', date), ('date_from', '<=', date_to)], order='date_from desc', limit=1)
        if date_range:
            date_to = date_range.date_from + timedelta(days=-1)
        date_range = self.env['ir.sequence.date_range'].search([('sequence_id', '=', self.id), ('date_to', '>=', date_from), ('date_to', '<=', date)], order='date_to desc', limit=1)
        if date_range:
            date_from = date_range.date_to + timedelta(days=1)
        seq_date_range = self.env['ir.sequence.date_range'].sudo().create({
            'date_from': date_from,
            'date_to': date_to,
            'sequence_id': self.id,
        })
        return seq_date_range