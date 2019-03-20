import decimal
from decimal import Decimal as D
# from decimal import ROUND_DOWN

decimal.setcontext(decimal.ExtendedContext)
decimal.getcontext().prec = 15


def _normalize(d: D):
    if d.is_finite():
        d = d.quantize(D('0.01'))
        if d == d.to_integral():
            return d.quantize(D('1'))
        return d
    return d.normalize()


class Metal:

    __scrap: D = None

    def __init__(self, ref='0', rec='0', scrap='0', weapon='0'):
        def push(scrap):
            self.__scrap += scrap
        self.__scrap = D('0')
        all_currency = (D(ref), D(rec), D(scrap), D(weapon))
        if D('Inf') in all_currency:
            self.__scrap += D('Inf')
        if D('-Inf') in all_currency:
            self.__scrap += D('-Inf')
        if self.__scrap == D('NaN') or D('NaN') in all_currency:
            raise ValueError('Metal must be a number')
        if self.__scrap != D('0'):
            return
        push(D(weapon) / D('2'))
        push(D(scrap))
        push(D(rec) // D('1') * D('3'))
        rec_decimal = D(rec) % D('1') / D('0.33')
        if rec_decimal > D('3'):
            rec_decimal = D('3')
        push(rec_decimal)
        push(D(ref) // D('1') * D('9'))
        ref_decimal = D(ref) % D('1') / D('0.11')
        if ref_decimal > D('9'):
            ref_decimal = D('9')
        push(ref_decimal)

    @property
    def scrap(self):
        return _normalize(self.__scrap)

    @property
    def reclaimed(self):
        return _normalize(self.__scrap / D('3'))

    @property
    def refined(self):
        return _normalize(self.__scrap / D('9'))

    @property
    def weapon(self):
        return _normalize(self.__scrap * D('2'))
