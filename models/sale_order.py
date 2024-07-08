from odoo import models, fields, api
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_type = fields.Selection(
        [('percentage', 'Percentage'), ('amount', 'Amount')],
        string='Discount Type'
    )
    discount_rate = fields.Float(string='Discount Rate')
    discount_amount = fields.Float(string='Discount Amount', compute='_compute_discount_amount', store=True)
    untaxed_amount_before_discount = fields.Float(string='Untaxed Amount Before Discount', compute='_compute_amounts',
                                                  store=True)
    untaxed_amount_after_discount = fields.Float(string='Untaxed Amount After Discount', compute='_compute_amounts',
                                                 store=True)
    amount_due = fields.Monetary(string='Amount Due', compute='_compute_amount_due', store=True)

    @api.depends('order_line.price_subtotal', 'discount_type', 'discount_rate')
    def _compute_discount_amount(self):
        for order in self:
            if order.discount_type == 'percentage':
                order.discount_amount = sum(order.order_line.mapped('price_subtotal')) * (order.discount_rate / 100)
            elif order.discount_type == 'amount':
                order.discount_amount = order.discount_rate
            else:
                order.discount_amount = 0.0

    @api.depends('order_line.price_subtotal', 'discount_amount')
    def _compute_amounts(self):
        for order in self:
            untaxed_amount = sum(order.order_line.mapped('price_subtotal'))
            order.untaxed_amount_before_discount = untaxed_amount
            order.untaxed_amount_after_discount = untaxed_amount - order.discount_amount

    @api.depends('invoice_ids.amount_residual', 'invoice_ids.amount_total', 'invoice_count')
    def _compute_amount_due(self):
        for order in self:
            invoices = order.order_line.invoice_lines.move_id.filtered(
                lambda r: r.move_type in ('out_invoice', 'out_refund'))

            total_due = 0.0
            if order.invoice_count > 0:
                for invoice in invoices:
                    total_due += invoice.amount_residual - invoice.amount_total

            else:
                total_due = order.amount_total

            order.amount_due = total_due

    @api.depends_context('lang')
    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'untaxed_amount_before_discount',
                 'discount_amount', 'untaxed_amount_after_discount')
    def _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            price = order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
            order = order_line.order_id
            return order_line.tax_id._origin.compute_all(price, order.currency_id, order_line.product_uom_qty,
                                                         product=order_line.product_id,
                                                         partner=order.partner_shipping_id)

        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.order_line,
                                                                                         compute_taxes)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total,
                                                      order.untaxed_amount_after_discount, order.currency_id)
            tax_totals.update({
                'untaxed_amount_before_discount': order.untaxed_amount_before_discount,
                'discount_amount': order.discount_amount,
                'untaxed_amount_after_discount': order.untaxed_amount_after_discount,
            })
            order.tax_totals_json = json.dumps(tax_totals)
