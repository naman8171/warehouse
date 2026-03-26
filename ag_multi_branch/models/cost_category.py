# -*- coding: utf-8 -*-

import logging
from odoo import models, fields


_logger = logging.getLogger(__name__)


class CostCategory(models.Model):
    _name = "cost.category"
    _description = 'Cost Category'

    name = fields.Char(string='Name', required=True)
