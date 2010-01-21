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
from operator import itemgetter

from osv import osv, fields
import netsvc
import tools

class base_setup_company(osv.osv_memory):
    """
    """
    _name = 'base.setup.company'
    _inherit = 'res.config'
    logger = netsvc.Logger()

    def _get_all(self, cr, uid, model, context=None):
        models = self.pool.get(model)
        all_model_ids = models.search(cr, uid, [])

        output = [(False, '')]
        output.extend(
            sorted([(o.id, o.name)
                    for o in models.browse(cr, uid, all_model_ids,
                                           context=context)],
                   key=itemgetter(1)))
        return output

    def _get_all_states(self, cr, uid, context=None):
        return self._get_all(
            cr, uid, 'res.country.state', context=context)
    def _get_all_countries(self, cr, uid, context=None):
        return self._get_all(cr, uid, 'res.country', context=context)
    def _get_all_currencies(self, cr, uid, context=None):
        return self._get_all(cr, uid, 'res.currency', context=context)

    def default_get(self, cr, uid, fields_list=None, context=None):
        """ get default company if any, and the various other fields
        from the company's fields
        """
        defaults = super(base_setup_company, self)\
              .default_get(cr, uid, fields_list=fields_list, context=context)

        companies = self.pool.get('res.company')
        company_id = companies.search(cr, uid, [], limit=1, order="id")
        if not company_id or 'company_id' not in fields_list:
            return defaults
        company = companies.browse(cr, uid, company_id[0])

        defaults['company_id'] = company.id
        defaults['currency'] = company.currency_id.id
        for field in ['name','logo','rml_header1','rml_footer1','rml_footer2']:
            defaults[field] = company[field]

        if company.partner_id.address:
            address = company.partner_id.address[0]
            for field in ['street','street2','zip','city','email','phone']:
                defaults[field] = address[field]
            for field in ['country_id','state_id']:
                if address[field]:
                    defaults[field] = address[field].id

        return defaults

    _columns = {
        'company_id':fields.many2one('res.company', 'Company'),
        'name':fields.char('Company Name', size=64, required=True),
        'street':fields.char('Street', size=128),
        'street2':fields.char('Street 2', size=128),
        'zip':fields.char('Zip Code', size=24),
        'city':fields.char('City', size=128),
        'state_id':fields.selection(_get_all_states, 'States'),
        'country_id':fields.selection(_get_all_countries, 'Countries'),
        'email':fields.char('E-mail', size=64),
        'phone':fields.char('Phone', size=64),
        'currency':fields.selection(_get_all_currencies, 'Currency', required=True),
        'rml_header1':fields.char('Report Header', size=200,
            help='''This sentence will appear at the top right corner of your reports.
We suggest you to put a slogan here:
"Open Source Business Solutions".'''),
        'rml_footer1':fields.char('Report Footer 1', size=200,
            help='''This sentence will appear at the bottom of your reports.
We suggest you to write legal sentences here:
Web: http://openerp.com - Fax: +32.81.73.35.01 - Fortis Bank: 126-2013269-07'''),
        'rml_footer2':fields.char('Report Footer 2', size=200,
            help='''This sentence will appear at the bottom of your reports.
We suggest you to put bank information here:
IBAN: BE74 1262 0121 6907 - SWIFT: CPDF BE71 - VAT: BE0477.472.701'''),
        'logo':fields.binary('Logo'),
    }

base_setup_company()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
