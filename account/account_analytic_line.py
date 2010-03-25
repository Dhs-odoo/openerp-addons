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

import time

from osv import fields
from osv import osv
from tools.translate import _
import tools
from tools import config

class account_analytic_line(osv.osv):
    _name = 'account.analytic.line'
    _description = 'Analytic lines'
    
    def _amount_currency(self, cr, uid, ids, field_name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            cmp_cur_id=rec.company_id.currency_id.id
            aa_cur_id=rec.account_id.currency_id.id
            # Always provide the amount in currency
            if cmp_cur_id != aa_cur_id:
                cur_obj = self.pool.get('res.currency')
                ctx = {}
                if rec.date and rec.amount:
                    ctx['date'] = rec.date
                    result[rec.id] = cur_obj.compute(cr, uid, rec.company_id.currency_id.id,
                        rec.account_id.currency_id.id, rec.amount,
                        context=ctx)
            else:
                result[rec.id]=rec.amount
        return result
        
    def _get_account_currency(self, cr, uid, ids, field_name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            # Always provide second currency
            result[rec.id] = (rec.account_id.currency_id.id,rec.account_id.currency_id.code)
        return result
    
    def _get_account_line(self, cr, uid, ids, context={}):
        aac_ids = {}
        for acc in self.pool.get('account.analytic.account').browse(cr, uid, ids):
            aac_ids[acc.id] = True
        aal_ids = []
        if aac_ids:
            aal_ids = self.pool.get('account.analytic.line').search(cr, uid, [('account_id','in',aac_ids.keys())], context=context)
        return aal_ids

    _columns = {
        'name' : fields.char('Description', size=256, required=True),
        'date' : fields.date('Date', required=True),
        'amount' : fields.float('Amount', required=True, help='Calculated by multiplying the quantity and the price given in the Product\'s cost price.'),
        'unit_amount' : fields.float('Quantity', help='Specifies the amount of quantity to count.'),
        'product_uom_id' : fields.many2one('product.uom', 'UoM'),
        'product_id' : fields.many2one('product.product', 'Product'),
        'account_id' : fields.many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='cascade', select=True),
        'general_account_id' : fields.many2one('account.account', 'General Account', required=True, ondelete='cascade'),
        'move_id' : fields.many2one('account.move.line', 'Move Line', ondelete='cascade', select=True),
        'journal_id' : fields.many2one('account.analytic.journal', 'Analytic Journal', required=True, ondelete='cascade', select=True),
        'code' : fields.char('Code', size=8),
        'user_id' : fields.many2one('res.users', 'User',),
        'currency_id': fields.function(_get_account_currency, method=True, type='many2one', relation='res.currency', string='Account currency',
                store={
                    'account.analytic.account': (_get_account_line, ['company_id'], 50),
                    'account.analytic.line': (lambda self,cr,uid,ids,c={}: ids, ['amount','unit_amount'],10),
                },
                help="The related account currency if not equal to the company one."),
        'company_id': fields.many2one('res.company','Company',required=True),
        'amount_currency': fields.function(_amount_currency, method=True, digits=(16, int(config['price_accuracy'])), string='Amount currency',
                store={
                    'account.analytic.account': (_get_account_line, ['company_id'], 50),
                    'account.analytic.line': (lambda self,cr,uid,ids,c={}: ids, ['amount','unit_amount'],10),
                },
                help="The amount expressed in the related account currency if not equal to the company one."),
        'ref': fields.char('Reference', size=32),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.analytic.line', c),
    }
    _order = 'date'
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}

        if context.get('from_date',False):
            args.append(['date', '>=',context['from_date']])
            
        if context.get('to_date',False):
            args.append(['date','<=',context['to_date']])
            
        return super(account_analytic_line, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
        
    def _check_company(self, cr, uid, ids):
        lines = self.browse(cr, uid, ids)
        for l in lines:
            if l.move_id and not l.account_id.company_id.id == l.move_id.account_id.company_id.id:
                return False
        return True
    _constraints = [
#        (_check_company, 'You can not create analytic line that is not in the same company than the account line', ['account_id'])
    ]
    
    # Compute the cost based on the price type define into company
    # property_valuation_price_type property
    def on_change_unit_amount(self, cr, uid, id, prod_id, unit_amount,company_id,
            unit=False, context=None):
        if context==None:
            context={}
        uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')
        company_obj=self.pool.get('res.company')
        if  prod_id:
            prod = product_obj.browse(cr, uid, prod_id)
            a = prod.product_tmpl_id.property_account_expense.id
            if not a:
                a = prod.categ_id.property_account_expense_categ.id
            if not a:
                raise osv.except_osv(_('Error !'),
                        _('There is no expense account defined ' \
                                'for this product: "%s" (id:%d)') % \
                                (prod.name, prod.id,))
            if not company_id:
                company_id=company_obj._company_default_get(cr, uid, 'account.analytic.line', context)
      
            # Compute based on pricetype
            pricetype=self.pool.get('product.price.type').browse(cr,uid,company_obj.browse(cr,uid,company_id).property_valuation_price_type.id)
            # Take the company currency as the reference one
            context['currency_id']=company_obj.browse(cr,uid,company_id).currency_id.id
            amount_unit=prod.price_get(pricetype.field, context)[prod.id]
            amount=amount_unit*unit_amount or 1.0
            return {'value': {
                'amount': - round(amount, 2),
                'general_account_id': a,
                }}
        return {}

    def view_header_get(self, cr, user, view_id, view_type, context):
        if context.get('account_id', False):
            # account_id in context may also be pointing to an account.account.id
            cr.execute('select name from account_analytic_account where id=%s', (context['account_id'],))
            res = cr.fetchone()
            if res:
                res = _('Entries: ')+ (res[0] or '')
            return res
        return False

account_analytic_line()


class timesheet_invoice(osv.osv):
    _name = "report.hr.timesheet.invoice.journal"
    _description = "Analytic account costs and revenues"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'account_id':fields.many2one('account.analytic.account', 'Analytic Account', readonly=True, select=True),
        'journal_id': fields.many2one('account.analytic.journal', 'Journal', readonly=True),
        'quantity': fields.float('Quantities', readonly=True),
        'cost': fields.float('Credit', readonly=True),
        'revenue': fields.float('Debit', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
    }
    _order = 'name desc, account_id'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_hr_timesheet_invoice_journal')
        cr.execute("""
        create or replace view report_hr_timesheet_invoice_journal as (
            select
                min(l.id) as id,
                to_char(l.date, 'YYYY') as name,
                to_char(l.date,'MM') as month,
                sum(
                    CASE WHEN l.amount>0 THEN 0 ELSE l.amount
                    END
                ) as cost,
                sum(
                    CASE WHEN l.amount>0 THEN l.amount ELSE 0
                    END
                ) as revenue,
                sum(l.unit_amount* COALESCE(u.factor, 1)) as quantity,
                journal_id,
                account_id
            from account_analytic_line l
                LEFT OUTER join product_uom u on (u.id=l.product_uom_id)
            group by
                to_char(l.date, 'YYYY'),
                to_char(l.date,'MM'),
                journal_id,
                account_id
        )""")
timesheet_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

