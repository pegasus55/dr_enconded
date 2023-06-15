# coding: utf-8

from . import ci
import requests
from odoo.exceptions import ValidationError

__all__ = ['compact', 'validate', 'is_valid']


compact = ci.compact


def _checksum(number, weights):
    return sum(w * int(n) for w, n in zip(weights, number)) % 11


def validate(number):
    number = compact(number)
    ruc = 'https://srienlinea.sri.gob.ec/movil-servicios/api/v1.0/estadoTributario/{ruc}'.format(ruc=number)
    try:
        r = requests.get(ruc)
        if r and 'ruc' in r.json():
            ruc_num = r.json().get('ruc', False)
            if ruc_num:
                return True
        else:
            return False

    except requests.exceptions.HTTPError as e:
        raise ValidationError(e.response.text)
    except requests.exceptions.RequestException as e:
        raise ValidationError(e.response.text)


def is_valid(number):
    try:
        return bool(validate(number))
    except ValueError:
        return False