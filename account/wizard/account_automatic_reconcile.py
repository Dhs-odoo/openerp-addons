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

import netsvc
from osv import osv, fields
from tools.translate import _

class account_automatic_reconcile(osv.osv_memory):
    _name = 'account.automatic.reconcile'
    _description = 'Automatic Reconcile'

    _columns = {
        'account_ids': fields.many2many('account.account', 'reconcile_account_rel', 'reconcile_id', 'account_id', 'Account to reconcile', domain = [('reconcile','=',1)], \
                                        help = 'If no account is specified, the reconciliation will be made using every accounts that can be reconcilied'),
        'writeoff_acc_id': fields.many2one('account.account', 'Account', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'period_id': fields.many2one('account.period', 'Period', required=True),
        'max_amount': fields.float('Maximum write-off amount'),
        'power': fields.selection([(p, str(p)) for p in range(2, 10)], 'Power', required=True),
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True),
        'reconciled': fields.integer('Reconciled transactions', readonly=True),
        'unreconciled': fields.integer('Not reconciled transactions', readonly=True),
    }

    def _get_reconciled(self, cr, uid, context={}):
        return context.get('reconciled', 0)

    def _get_unreconciled(self, cr, uid, context={}):
        return context.get('unreconciled', 0)

    _defaults = {
        'date1': time.strftime('%Y-01-01'),
        'date2': time.strftime('%Y-%m-%d'),
        'reconciled': _get_reconciled,
        'unreconciled': _get_unreconciled,
    }

    #TODO: cleanup and comment this code... For now, it is awfulllll
    # (way too complex, and really slow)...
    def do_reconcile(self, cr, uid, credits, debits, max_amount, power, writeoff_acc_id, period_id, journal_id, context=None):
    # for one value of a credit, check all debits, and combination of them
    # depending on the power. It starts with a power of one and goes up
    # to the max power allowed
        move_line_obj = self.pool.get('account.move.line')
        if context is None:
            context = {}
        def check2(value, move_list, power):
            print "::::::check2::::::::::",value, move_list, power
            def check(value, move_list, power):
                for i in range(len(move_list)):
                    move = move_list[i]
                    print "::::::::::::::::::",value,max_amount,move,move[1]
                    if power == 1:
                        if abs(value - move[1]) <= max_amount + 0.00001:
                            print "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^6"
                            return [move[0]]
                    else:
                        del move_list[i]
                        res = check(value - move[1], move_list, power-1)
                        move_list[i:i] = [move]
                        if res:
                            res.append(move[0])
                            return res
                return False

            for p in range(1, power+1):
                res = check(value, move_list, p)
                if res:
                    return res
            return False

        # for a list of credit and debit and a given power, check if there
        # are matching tuples of credit and debits, check all debits, and combination of them
        # depending on the power. It starts with a power of one and goes up
        # to the max power allowed
        def check4(list1, list2, power):
            print "::::::check4::::::::::",list1, list2, power
            def check3(value, list1, list2, list1power, power):
                for i in range(len(list1)):
                    move = list1[i]
                    if list1power == 1:
                        res = check2(value + move[1], list2, power - 1)
                        if res:
                            return ([move[0]], res)
                    else:
                        del list1[i]
                        res = check3(value + move[1], list1, list2, list1power-1, power-1)
                        list1[i:i] = [move]
                        if res:
                            x, y = res
                            x.append(move[0])
                            return (x, y)
                return False

            for p in range(1, power):
                res = check3(0, list1, list2, p, power)
                if res:
                    return res
            return False

        def check5(list1, list2, max_power):
            print "\n\n%%%%%%%%check5%%%%%%%%%%%%%%%%%%%",list1,list2,max_power
            for p in range(2, max_power+1):
                res = check4(list1, list2, p)
                print "RRRRRRRcheck5RRRRRRRR",res
                if res:
                    print "RRRRRRcheck5REtrunrn...",res
                    return res

        ok = True
        reconciled = 0
        while credits and debits and ok:
            res = check5(credits, debits, power)
            if res:
                print "Finallllllllllll RES",res
                move_line_obj.reconcile(cr, uid, res[0] + res[1], 'auto', writeoff_acc_id, period_id, journal_id, context)
                reconciled += len(res[0]) + len(res[1])
                credits = [(id, credit) for (id, credit) in credits if id not in res[0]]
                debits = [(id, debit) for (id, debit) in debits if id not in res[1]]
                print "=================================",reconciled,credits,debits
            else:
                ok = False
        return (reconciled, len(credits)+len(debits))

    def reconcile(self, cr, uid, ids, context=None):
        service = netsvc.LocalService("object_proxy")
        move_line_obj = self.pool.get('account.move.line')
        obj_model = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        form = self.read(cr, uid, ids, [])[0]
        max_amount = form.get('max_amount', 0.0)
        power = form['power']
        reconciled = unreconciled = 0
        if not form['account_ids']:
            raise osv.except_osv(_('UserError'), _('You must select accounts to reconcile'))
        print ">>>>START<<<<\n",form['account_ids']
        for account_id in form['account_ids']:
            # reconcile automatically all transactions from partners whose balance is 0
            cr.execute(
                "SELECT partner_id " \
                "FROM account_move_line " \
                "WHERE account_id=%s " \
                "AND reconcile_id IS NULL " \
                "AND state <> 'draft' " \
                "GROUP BY partner_id " \
                "HAVING ABS(SUM(debit-credit)) < %s AND count(*)>0",
                (account_id, max_amount or 0.0))
            partner_ids = [id for (id,) in cr.fetchall()]
            print "partner_ids:::::::::::::::::::::::::>>>",partner_ids
            for partner_id in partner_ids:
                cr.execute(
                    "SELECT id " \
                    "FROM account_move_line " \
                    "WHERE account_id=%s " \
                    "AND partner_id=%s " \
                    "AND state <> 'draft' " \
                    "AND reconcile_id IS NULL",
                    (account_id, partner_id))
                line_ids = [id for (id,) in cr.fetchall()]
                print "LLLLLLLLLLLLLLLLLLLLline idsssss....",line_ids
                if len(line_ids):
                    move_line_obj.reconcile(cr, uid, line_ids, 'auto', form['writeoff_acc_id'], form['period_id'], form['journal_id'], context)
                    reconciled += len(line_ids)

            # get the list of partners who have more than one unreconciled transaction
            cr.execute(
                "SELECT partner_id " \
                "FROM account_move_line " \
                "WHERE account_id=%s " \
                "AND reconcile_id IS NULL " \
                "AND state <> 'draft' " \
                "AND partner_id IS NOT NULL " \
                "GROUP BY partner_id " \
                "HAVING count(*)>1",
                (account_id,))
            partner_ids = [id for (id,) in cr.fetchall()]
            print "second partner idssssssssssssss",partner_ids
            #filter?
            for partner_id in partner_ids:
                # get the list of unreconciled 'debit transactions' for this partner
                cr.execute(
                    "SELECT id, debit " \
                    "FROM account_move_line " \
                    "WHERE account_id=%s " \
                    "AND partner_id=%s " \
                    "AND reconcile_id IS NULL " \
                    "AND state <> 'draft' " \
                    "AND debit > 0",
                    (account_id, partner_id))
                debits = cr.fetchall()
                print "UUUUUUUUUUUUUUUUUU Debitssssssss",debits

                # get the list of unreconciled 'credit transactions' for this partner
                cr.execute(
                    "SELECT id, credit " \
                    "FROM account_move_line " \
                    "WHERE account_id=%s " \
                    "AND partner_id=%s " \
                    "AND reconcile_id IS NULL " \
                    "AND state <> 'draft' " \
                    "AND credit > 0",
                    (account_id, partner_id))
                credits = cr.fetchall()
                print "CCCCCCCCCCCCCCCCCCcreditttt.....",credits

                (rec, unrec) = self.do_reconcile(cr, uid, credits, debits, max_amount, power, form['writeoff_acc_id'], form['period_id'], form['journal_id'], context)
                print "()(()(((rec, unrec))((()()()",(rec, unrec)
                reconciled += rec
                unreconciled += unrec

            # add the number of transactions for partners who have only one
            # unreconciled transactions to the unreconciled count
            partner_filter = partner_ids and 'AND partner_id not in (%s)' % ','.join(map(str, filter(None, partner_ids))) or ''
            print "Partner fileterrrrrrrrrrrr",partner_filter
            cr.execute(
                "SELECT count(*) " \
                "FROM account_move_line " \
                "WHERE account_id=%s " \
                "AND reconcile_id IS NULL " \
                "AND state <> 'draft' " + partner_filter,
                (account_id,))
            additional_unrec = cr.fetchone()[0]
            print "^^^^^^^^^^^^^^^^^^^^^",additional_unrec
        context.update({'reconciled': reconciled, 'unreconciled': unreconciled + additional_unrec})
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','account_automatic_reconcile_view1')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])[0]['res_id']
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.automatic.reconcile',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy':True,
        }

account_automatic_reconcile()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: