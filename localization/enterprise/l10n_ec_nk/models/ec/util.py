# coding: utf-8

import sys
import unicodedata


def _mk_char_map(mapping):
    for key, value in mapping.items():
        for char in key.split(','):
            try:
                yield unicodedata.lookup(char), value
            except KeyError:
                pass


_char_map = dict(_mk_char_map({
    'HYPHEN-MINUS,ARMENIAN HYPHEN,HEBREW PUNCTUATION MAQAF,HYPHEN,'
    'NON-BREAKING HYPHEN,FIGURE DASH,EN DASH,EM DASH,HORIZONTAL BAR,'
    'SMALL HYPHEN-MINUS,FULLWIDTH HYPHEN-MINUS,MONGOLIAN NIRUGU,OVERLINE,'
    'HYPHEN BULLET,MACRON,MODIFIER LETTER MINUS SIGN,FULLWIDTH MACRON,'
    'OGHAM SPACE MARK,SUPERSCRIPT MINUS,SUBSCRIPT MINUS,MINUS SIGN,'
    'HORIZONTAL LINE EXTENSION,HORIZONTAL SCAN LINE-1,HORIZONTAL SCAN LINE-3,'
    'HORIZONTAL SCAN LINE-7,HORIZONTAL SCAN LINE-9,STRAIGHTNESS':
        '-',
    'ASTERISK,ARABIC FIVE POINTED STAR,SYRIAC HARKLEAN ASTERISCUS,'
    'FLOWER PUNCTUATION MARK,VAI FULL STOP,SMALL ASTERISK,FULLWIDTH ASTERISK,'
    'ASTERISK OPERATOR,STAR OPERATOR,HEAVY ASTERISK,LOW ASTERISK,'
    'OPEN CENTRE ASTERISK,EIGHT SPOKED ASTERISK,SIXTEEN POINTED ASTERISK,'
    'TEARDROP-SPOKED ASTERISK,OPEN CENTRE TEARDROP-SPOKED ASTERISK,'
    'HEAVY TEARDROP-SPOKED ASTERISK,EIGHT TEARDROP-SPOKED PROPELLER ASTERISK,'
    'HEAVY EIGHT TEARDROP-SPOKED PROPELLER ASTERISK,'
    'ARABIC FIVE POINTED STAR':
        '*',
    'COMMA,ARABIC COMMA,SINGLE LOW-9 QUOTATION MARK,IDEOGRAPHIC COMMA,'
    'ARABIC DECIMAL SEPARATOR,ARABIC THOUSANDS SEPARATOR,PRIME,RAISED COMMA,'
    'PRESENTATION FORM FOR VERTICAL COMMA,SMALL COMMA,'
    'SMALL IDEOGRAPHIC COMMA,FULLWIDTH COMMA,CEDILLA':
        ',',
    'FULL STOP,MIDDLE DOT,GREEK ANO TELEIA,ARABIC FULL STOP,'
    'IDEOGRAPHIC FULL STOP,SYRIAC SUPRALINEAR FULL STOP,'
    'SYRIAC SUBLINEAR FULL STOP,SAMARITAN PUNCTUATION NEQUDAA,'
    'TIBETAN MARK INTERSYLLABIC TSHEG,TIBETAN MARK DELIMITER TSHEG BSTAR,'
    'RUNIC SINGLE PUNCTUATION,BULLET,ONE DOT LEADER,HYPHENATION POINT,'
    'WORD SEPARATOR MIDDLE DOT,RAISED DOT,KATAKANA MIDDLE DOT,'
    'SMALL FULL STOP,FULLWIDTH FULL STOP,HALFWIDTH KATAKANA MIDDLE DOT,'
    'AEGEAN WORD SEPARATOR DOT,PHOENICIAN WORD SEPARATOR,'
    'KHAROSHTHI PUNCTUATION DOT,DOT ABOVE,ARABIC SYMBOL DOT ABOVE,'
    'ARABIC SYMBOL DOT BELOW,BULLET OPERATOR,DOT OPERATOR':
        '.',
    'SOLIDUS,SAMARITAN PUNCTUATION ARKAANU,FULLWIDTH SOLIDUS,DIVISION SLASH,'
    'MATHEMATICAL RISING DIAGONAL,BIG SOLIDUS,FRACTION SLASH':
        '/',
    'COLON,ETHIOPIC WORDSPACE,RUNIC MULTIPLE PUNCTUATION,MONGOLIAN COLON,'
    'PRESENTATION FORM FOR VERTICAL COLON,FULLWIDTH COLON,'
    'PRESENTATION FORM FOR VERTICAL TWO DOT LEADER,SMALL COLON':
        ':',
    'SPACE,NO-BREAK SPACE,EN QUAD,EM QUAD,EN SPACE,EM SPACE,'
    'THREE-PER-EM SPACE,FOUR-PER-EM SPACE,SIX-PER-EM SPACE,FIGURE SPACE,'
    'PUNCTUATION SPACE,THIN SPACE,HAIR SPACE,NARROW NO-BREAK SPACE,'
    'MEDIUM MATHEMATICAL SPACE,IDEOGRAPHIC SPACE':
        ' ',
}))


def _clean_chars(number):
    return ''.join(_char_map.get(x, x) for x in number)


def clean(number, delete_chars=''):
    try:
        number = ''.join(x for x in number)
    except Exception:
        raise
    if sys.version < '3' and isinstance(number, str):
        try:
            number = _clean_chars(number.decode()).encode()
        except UnicodeError:
            try:
                number = _clean_chars(number.decode('utf-8')).encode('utf-8')
            except UnicodeError:
                pass
    else:
        number = _clean_chars(number)
    return ''.join(x for x in number if x not in delete_chars)