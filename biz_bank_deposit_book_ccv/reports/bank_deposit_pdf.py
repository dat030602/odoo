# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
import logging

_logger = logging.getLogger(__name__)

def split_string_to_lines(s, sep_char, count):
    result = []
    counter = 0
    start = 0
    for i, c in enumerate(s):
        if c == sep_char:
            counter += 1
            if counter % count == 0:
                result.append(s[start:i+1])
                start = i+1
    if start < len(s):
        result.append(s[start:])
    return '\n'.join(result)

class rp_bank_deposit_book_pdf(models.AbstractModel):
    _inherit = 'report.biz_bank_deposit_book.rp_bank_deposit_book_pdf'
    
    def get_initial_balance_usd(self, doc):
        domain = [('parent_state','=', 'posted')]
        if doc.from_date:
            domain += [('date','<', doc.from_date)]
        if doc.journal_id and doc.journal_id.default_account_id:
            domain += [('account_id','=', doc.journal_id.default_account_id.id)]

        initial = 0
        move_lines = self.env['account.move.line'].search(domain)
        for line in move_lines:
            amount_currency = abs(line.amount_currency)
            if amount_currency:
                if line.debit != 0:
                    initial += amount_currency
                else:
                    initial -= amount_currency
        return initial

    def get_lines(self, doc):
        if  doc.type_print == 'vnd':
            return super(rp_bank_deposit_book_pdf, self).get_lines(doc)

        domain = [('parent_state','=', 'posted')]
        if doc.from_date:
            domain += [('date','>=', doc.from_date)]

        if doc.to_date:
            domain += [('date','<=', doc.to_date)]

        if doc.journal_id:
            domain += [('journal_id','=', doc.journal_id.id)]

            if doc.journal_id.default_account_id:
                domain += [('account_id','=', doc.journal_id.default_account_id.id)]

        sum_credit  = sum_debit = 0
        sum_pcredit  = sum_pdebit = 0
        move_lines = self.env['account.move.line'].search(domain)

        lines = []

        for line in move_lines.sorted(lambda x: (x.date, self.sorted_move(x.move_id), x.move_id.name)):
            move = line.move_id
            if len(move.line_ids) >= 3:
                exit_debit = move.line_ids.filtered(lambda x: x.id != line.id)
                if line.debit > 0 and not any(ed.debit > 0 for ed in exit_debit):
                    for edeb in exit_debit:
                        amount_currency = abs(edeb.amount_currency)
                        a = edeb.credit
                        b = edeb.debit
                        if amount_currency:
                            c1 = b/amount_currency if a == 0 else a/amount_currency
                            c2 = amount_currency if a != 0 else 0
                            c3 = 0
                            if a == 0:
                                c3 = amount_currency
                            elif b == 0:
                                c3 = 0
                        else:
                            c1 = c2 = c3 = 0
                        tygia = c1
                        if edeb.move_id.apply_manual_currency_exchange:
                            tygia = edeb.move_id.inverse_manural_currency_exchange_rate
                                                   
                        lines.append({
                            'date': edeb.move_id.date and edeb.move_id.date.strftime('%d/%m/%Y') or '',
                            'move_name': edeb.move_id.name,
                            'name': edeb.name,
                            'cpt_code': edeb.account_id.code,
                            'tygia': tygia,
                            'pdebit': c2,
                            'debit': a,
                            'pcredit':c3,
                            'credit': b,
                        })

                        sum_pdebit += c2
                        sum_debit += a
                        sum_pcredit += c3
                        sum_credit += b

                    continue

                if line.credit > 0 and not any(ec.credit > 0 for ec in exit_debit):
                    for ecre in exit_debit:
                        amount_currency = abs(ecre.amount_currency)
                        a = ecre.credit
                        b = ecre.debit
                        if amount_currency:
                            c1 = b/amount_currency if a == 0 else a/amount_currency
                            c2 = amount_currency if a != 0 else 0
                            c3 = 0
                            if a == 0:
                                c3 = amount_currency
                        else:
                            c1 = c2 = c3 = 0
                        tygia = c1
                        if ecre.move_id.apply_manual_currency_exchange:
                            tygia = ecre.move_id.inverse_manural_currency_exchange_rate
                        
                        lines.append({
                            'date': ecre.move_id.date and ecre.move_id.date.strftime('%d/%m/%Y') or '',
                            'move_name': ecre.move_id.name,
                            'name': ecre.name,
                            'cpt_code': ecre.account_id.code,
                            'tygia': tygia,
                            'pdebit': c2,
                            'debit': a,
                            'pcredit':c3,
                            'credit': b,
                        })

                        sum_pdebit += c2
                        sum_debit += a
                        sum_pcredit += c3
                        sum_credit += b

                    continue

            amount_currency = abs(line.amount_currency)
            a = line.debit
            b = line.credit
            if amount_currency:
                c1 = a / amount_currency if a !=0 else b/amount_currency
                c2 = amount_currency if a!=0 else 0
                c3 = 0
                if a == 0:
                    c3 = amount_currency
            else:
                c1 = c2 = c3 = 0
            tygia = c1
            if line.move_id.apply_manual_currency_exchange:
                tygia = line.move_id.inverse_manural_currency_exchange_rate
                
            lines.append({
                'date': line.move_id.date and line.move_id.date.strftime('%d/%m/%Y') or '',
                'move_name': line.move_id.name,
                'name': line.name,
                'cpt_code': self.get_cpt_code(line),
                'tygia': tygia,
                'pdebit': c2,
                'debit': a,
                'pcredit': c3,
                'credit': b,
            })

            sum_pdebit += c2
            sum_debit += a
            sum_pcredit += c3
            sum_credit += b


        return {
            'sum_credit': sum_credit,
            'sum_debit': sum_debit,
            'sum_pdebit': sum_pdebit,
            'sum_pcredit': sum_pcredit,
            'lines': lines
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super(rp_bank_deposit_book_pdf, self)._get_report_values(docids,data)
        res['get_initial_balance_usd'] = self.get_initial_balance_usd
        res['split_string_to_lines'] = split_string_to_lines
        return res
