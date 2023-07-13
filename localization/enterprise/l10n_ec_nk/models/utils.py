# -*- coding: utf-8 -*-

from . import ec


def additional_check_vat(vat, identification_type):
    if identification_type == 'Cédula':
        return ec.ci.is_valid(vat)
    elif identification_type == 'RUC':
        return ec.ruc.is_valid(vat)
    else:
        return True