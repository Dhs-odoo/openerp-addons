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

from base_calendar import base_calendar
from crm import crm_case
from datetime import datetime, timedelta
from osv import fields, osv
from tools.translate import _
import time

class crm_lead(osv.osv, crm_case):
    """ CRM Leads """
    _name = 'crm.lead'
crm_lead()

class crm_phonecall(osv.osv, crm_case):
    """ CRM Phonecall """
    _name = 'crm.phonecall'
crm_phonecall()


class crm_meeting(osv.osv, crm_case):
    """ CRM Meeting Cases """

    _name = 'crm.meeting'
    _description = "Meeting"
    _order = "id desc"
    _inherit = ['mailgate.thread',"calendar.event"]
    _columns = {
        # From crm.case
        'name': fields.char('Summary', size=124, required=True, states={'done': [('readonly', True)]}), 
        'partner_id': fields.many2one('res.partner', 'Partner', states={'done': [('readonly', True)]}), 
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                 domain="[('partner_id','=',partner_id)]", states={'done': [('readonly', True)]}), 
        'section_id': fields.many2one('crm.case.section', 'Sales Team', states={'done': [('readonly', True)]}, \
                        select=True, help='Sales team to which Case belongs to.'), 
        'email_from': fields.char('Email', size=128, states={'done': [('readonly', True)]}, help="These people will receive email."),
        'id': fields.integer('ID'),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'write_date': fields.datetime('Write Date' , readonly=True),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        # Meeting fields
        'categ_id': fields.many2one('crm.case.categ', 'Meeting Type', \
                        domain="[('object_id.model', '=', 'crm.meeting')]", \
            ),
        'phonecall_id': fields.many2one ('crm.phonecall', 'Phonecall'),
        'opportunity_id': fields.many2one ('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]"),
        'attendee_ids': fields.many2many('calendar.attendee', 'meeting_attendee_rel',\
                                 'event_id', 'attendee_id', 'Attendees', states={'done': [('readonly', True)]}),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date_deadline': fields.datetime('Deadline', states={'done': [('readonly', True)]}),
        'message_ids': fields.one2many('mailgate.message', 'res_id', 'Messages', domain=[('history', '=', True),('model','=',_name)]),
        'log_ids': fields.one2many('mailgate.message', 'res_id', 'Logs', domain=[('history', '=', False),('model','=',_name)]),
        'state': fields.selection([('open', 'Confirmed'),
                                    ('draft', 'Unconfirmed'),
                                    ('cancel', 'Cancelled'),
                                    ('done', 'Done')], 'State', \
                                    size=16, readonly=True)
    }

    _defaults = {
        'state': lambda *a: 'draft', 
        'active': lambda *a: 1,
        'user_id': lambda self, cr, uid, ctx: uid,
    }

    def open_meeting(self, cr, uid, ids, context=None):
        """
        Open Crm Meeting Form for Crm Meeting.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm meeting’s IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value which open Crm Meeting form.
        """

        if not context:
            context = {}

        data_obj = self.pool.get('ir.model.data')

        value = {}

        id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
        id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
        id4 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id
        if id4:
            id4 = data_obj.browse(cr, uid, id4, context=context).res_id
        for id in ids:
            value = {
                    'name': _('Meeting'),
                    'view_type': 'form',
                    'view_mode': 'form,tree',
                    'res_model': 'crm.meeting',
                    'view_id': False,
                    'views': [(id2, 'form'), (id3, 'tree'), (id4, 'calendar')],
                    'type': 'ir.actions.act_window',
                    'res_id': base_calendar.base_calendar_id2real_id(id),
                    'nodestroy': True
                    }

        return value
    
crm_meeting()

class calendar_attendee(osv.osv):
    """ Calendar Attendee """

    _inherit = 'calendar.attendee'
    _description = 'Calendar Attendee'

    def _compute_data(self, cr, uid, ids, name, arg, context):
       """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of compute data’s IDs
        @param context: A standard dictionary for contextual values
        """
       name = name[0]
       result = super(calendar_attendee, self)._compute_data(cr, uid, ids, name, arg, context)

       for attdata in self.browse(cr, uid, ids, context=context):
            id = attdata.id
            result[id] = {}
            if name == 'categ_id':
                if attdata.ref and 'categ_id' in attdata.ref._columns:
                    result[id][name] = (attdata.ref.categ_id.id, attdata.ref.categ_id.name,)
                else:
                    result[id][name] = False
       return result

    _columns = {
        'categ_id': fields.function(_compute_data, method=True, \
                        string='Event Type', type="many2one", \
                        relation="crm.case.categ", multi='categ_id'),
    }

calendar_attendee()

class res_users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'

    def create(self, cr, uid, data, context={}):
        user_id = super(res_users, self).create(cr, uid, data, context)
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'crm', 'ir_ui_view_sc_calendar0')
        view_id  = data_obj.browse(cr, uid, data_id, context=context).res_id
        copy_id = self.pool.get('ir.ui.view_sc').copy(cr, uid, view_id, default = {
                                    'user_id': user_id}, context=context)
        return user_id

res_users()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
