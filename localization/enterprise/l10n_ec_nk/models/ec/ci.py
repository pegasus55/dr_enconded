# coding: utf-8

from .util import clean


def compact(number):
    return clean(number, ' -').upper().strip()


def _checksum(number):
    fold = lambda x: x - 9 if x > 9 else x
    return sum(fold((2, 1)[i % 2] * int(n))
               for i, n in enumerate(number)) % 10


def validate(number):
    number = compact(number)
    if len(number) != 10:
        return False 
    if not number.isdigit():
        return False 
    if number[:2] < '01' or number[:2] > '24':
        if number[:2] != '30':
            return False
    if number[2] > '6':
        return False
    if _checksum(number) != 0:
        return False
    return True


def is_valid(number):
    try:
        return bool(validate(number))
    except ValueError:
        return False