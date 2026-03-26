
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, time, datetime

class UpdateLocationNumber(models.TransientModel):
    _name = "update.package.number"
    

    line_ids = fields.Many2many('thehub.workorder.lines','workorder_line_rel')
    scan_location = fields.Char('Scan location Name')



    def update_location_name(self):
        for line in self.line_ids:
            line.write({'location_label':self.scan_location})
            # line.location_label=self.scan_location


