# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import calendar
from openerp import tools
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import relativedelta
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import workflow


class crm_case_section(osv.osv):
    _inherit = 'crm.case.section'

    def _get_sale_orders_data(self, cr, uid, ids, field_name, arg, context=None):
        obj = self.pool.get('sale.order')
        res = dict.fromkeys(ids, False)
        month_begin = date.today().replace(day=1)
        date_begin = (month_begin - relativedelta.relativedelta(months=self._period_number - 1)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        date_end = month_begin.replace(day=calendar.monthrange(month_begin.year, month_begin.month)[1]).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for id in ids:
            res[id] = dict()
            created_domain = [('section_id', '=', id), ('state', '=', ['draft']), ('date_order', '>=', date_begin), ('date_order', '<=', date_end)]
            res[id]['monthly_quoted'] = self.__get_bar_values(cr, uid, obj, created_domain, ['amount_total', 'date_order'], 'amount_total', 'date_order', context=context)
            validated_domain = [('section_id', '=', id), ('state', 'not in', ['draft', 'sent', 'cancel']), ('date_order', '>=', date_begin), ('date_order', '<=', date_end)]
            res[id]['monthly_confirmed'] = self.__get_bar_values(cr, uid, obj, validated_domain, ['amount_total', 'date_order'], 'amount_total', 'date_order', context=context)
        return res

    def _get_invoices_data(self, cr, uid, ids, field_name, arg, context=None):
        obj = self.pool.get('account.invoice.report')
        res = dict.fromkeys(ids, False)
        month_begin = date.today().replace(day=1)
        date_begin = (month_begin - relativedelta.relativedelta(months=self._period_number - 1)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        date_end = month_begin.replace(day=calendar.monthrange(month_begin.year, month_begin.month)[1]).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for id in ids:
            created_domain = [('section_id', '=', id), ('state', 'not in', ['draft', 'cancel']), ('date', '>=', date_begin), ('date', '<=', date_end)]
            res[id] = self.__get_bar_values(cr, uid, obj, created_domain, ['price_total', 'date'], 'price_total', 'date', context=context)
        return res

    _columns = {
        'invoiced_forecast': fields.integer(string='Invoice Forecast',
            help="Forecast of the invoice revenue for the current month. This is the amount the sales \n"
                    "team should invoice this month. It is used to compute the progression ratio \n"
                    " of the current and forecast revenue on the kanban view."),
        'invoiced_target': fields.integer(string='Invoice Target',
            help="Target of invoice revenue for the current month. This is the amount the sales \n"
                    "team estimates to be able to invoice this month."),
        'monthly_quoted': fields.function(_get_sale_orders_data,
            type='string', readonly=True, multi='_get_sale_orders_data',
            string='Rate of created quotation per duration'),
        'monthly_confirmed': fields.function(_get_sale_orders_data,
            type='string', readonly=True, multi='_get_sale_orders_data',
            string='Rate of validate sales orders per duration'),
        'monthly_invoiced': fields.function(_get_invoices_data,
            type='string', readonly=True,
            string='Rate of sent invoices per duration'),
    }

    def action_forecast(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'invoiced_forecast': round(float(value))}, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
