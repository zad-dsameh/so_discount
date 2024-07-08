# -*- coding: utf-8 -*-
{
    'name': 'Sale Order Discount',
    'version': '15.1',
    'category': 'SO Discount',
    'author': 'Zadsolutions, Dina Sameh',
    'website': "http://zadsolutions.com",
    'summary': """
    Sales Order Discount
    """,
    'depends': ['account', 'sale'],
    'data': [
        # 'security/ir.model.access.csv',
        'security/groups_security.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False
}
