import decimal
from decimal import Decimal as D
# from decimal import ROUND_DOWN

decimal.setcontext(decimal.ExtendedContext)
decimal.getcontext().prec = 18


class _MetalInfo:
    reclaimed = (D('3'), D('0.33'), D('0.16'))
    refined = (D('9'), D('0.11'), D('0.05'))


def _normalize(d: D) -> D:
    if d.is_finite():
        d = d.quantize(D('0.01'))
    return d.normalize()


def _convert_to_scrap(d: D, metal_info) -> D:
    scrap_count, scrap_factor, weapon_factor = metal_info
    scrap = D('0')
    int_part = d // D('1')
    scrap += scrap_count * int_part
    dec_part = d % D('1')
    if dec_part > D('0.99'):
        dec_part = D('0.99')
    scrap_part = dec_part // scrap_factor
    weapon_part = dec_part % scrap_factor
    scrap += scrap_part
    if weapon_part > weapon_factor:
        scrap += D('0.5')
        weapon_part -= weapon_factor
        weapon_range = scrap_factor - weapon_factor
    else:
        weapon_range = weapon_factor
    scrap += (weapon_part / weapon_range) * D('0.5')
    return scrap


def _convert_from_scrap(scrap: D, metal_info) -> D:
    scrap_count, scrap_factor, weapon_factor = metal_info
    metal = D('0')
    metal += scrap // scrap_count
    scrap = scrap % scrap_count
    int_part = scrap // D('1')
    dec_part = scrap % D('1')
    metal += int_part * scrap_factor
    if dec_part > D('0.5'):
        metal += weapon_factor
        dec_part -= D('0.5')
        weapon_range = scrap_factor - weapon_factor
    else:
        weapon_range = weapon_factor
    metal += (dec_part / D('0.5')) * weapon_range
    return metal


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
        push(_convert_to_scrap(D(rec), _MetalInfo.reclaimed))
        push(_convert_to_scrap(D(ref), _MetalInfo.refined))

    @property
    def weapon(self):
        return _normalize(self.__scrap * D('2'))

    @property
    def scrap(self):
        return _normalize(self.__scrap)

    @property
    def reclaimed(self):
        return _normalize(_convert_from_scrap(self.__scrap, _MetalInfo.reclaimed))

    @property
    def refined(self):
        return _normalize(_convert_from_scrap(self.__scrap, _MetalInfo.refined))
