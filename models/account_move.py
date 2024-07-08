from odoo import models, fields, api
import json


class AccountMove(models.Model):
    _inherit = 'account.move'

    discount_type = fields.Selection(
        [('percentage', 'Percentage'), ('amount', 'Amount')],
        string='Discount Type',
        readonly=True, states={'draft': [('readonly', False)]}
    )
    discount_rate = fields.Float(string='Discount Rate', readonly=True, states={'draft': [('readonly', False)]})
    discount_amount = fields.Float(string='Discount Amount', compute='_compute_discount_amount', store=True)

    untaxed_amount_before_discount = fields.Float(string='Untaxed Amount Before Discount', compute='_compute_amounts',
                                                  store=True)
    untaxed_amount_after_discount = fields.Float(string='Untaxed Amount After Discount', compute='_compute_amounts',
                                                 store=True)
    # down_payment = fields.Monetary(string='Down Payment', compute='_compute_down_payment', store=True)
    down_payment = fields.Monetary(string='Down Payment', store=True)
    amount_due = fields.Monetary(string='Amount Due', compute='_compute_amount_due', store=True)

    @api.depends('invoice_line_ids.price_subtotal', 'discount_type', 'discount_rate')
    def _compute_discount_amount(self):
        for move in self:
            if move.discount_type == 'percentage':
                move.discount_amount = sum(move.invoice_line_ids.mapped('price_subtotal')) * (move.discount_rate / 100)
            elif move.discount_type == 'amount':
                move.discount_amount = move.discount_rate
            else:
                move.discount_amount = 0.0

    @api.depends('invoice_line_ids.price_subtotal', 'discount_amount')
    def _compute_amounts(self):
        for move in self:
            untaxed_amount = sum(move.invoice_line_ids.mapped('price_subtotal'))
            move.untaxed_amount_before_discount = untaxed_amount
            move.untaxed_amount_after_discount = untaxed_amount - move.discount_amount

    @api.depends('untaxed_amount_after_discount', 'amount_tax', 'down_payment')
    def _compute_amount_due(self):
        for move in self:
            move.amount_due = (move.untaxed_amount_after_discount + move.amount_tax) - move.down_payment

    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)
        # Logic to copy discount fields from quotation if applicable
        if res.move_type in ['out_invoice', 'out_refund']:
            sale_orders = self.env['sale.order'].search([('name', '=', res.invoice_origin)])
            if sale_orders:
                sale_order = sale_orders[0]
                res.update({
                    'discount_type': sale_order.discount_type,
                    'discount_rate': sale_order.discount_rate
                })
        return res

    @api.depends_context('lang')
    @api.depends('line_ids.amount_currency', 'line_ids.tax_base_amount', 'line_ids.tax_line_id', 'partner_id',
                 'currency_id', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals_json(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if not move.is_invoice(include_receipts=True):
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals_json = None
                continue

            tax_lines_data = move._prepare_tax_lines_data_for_totals_from_invoice()

            tax_totals = move._get_tax_totals(move.partner_id, tax_lines_data, move.amount_total,
                                              move.untaxed_amount_after_discount, move.currency_id)
            tax_totals.update({
                'untaxed_amount_before_discount': move.untaxed_amount_before_discount,
                'discount_amount': move.discount_amount,
                'untaxed_amount_after_discount': move.untaxed_amount_after_discount,
            })
            move.tax_totals_json = json.dumps(tax_totals)
