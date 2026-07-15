# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class BonusHistoryReportWizard(models.TransientModel):
    _name = 'bonus.history.report.wizard'
    _description = 'Wizard Báo cáo quỹ dự phòng'
