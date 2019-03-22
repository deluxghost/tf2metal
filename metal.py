import collections
import decimal
from decimal import Decimal as D

decimal.setcontext(decimal.ExtendedContext)
decimal.getcontext().prec = 18

NormalizedMetal = collections.namedtuple('NormalizedMetal', ['sign', 'key', 'refined', 'reclaimed', 'scrap', 'weapon'])


class _MetalInfo:
    reclaimed = (D('3'), D('0.33'), D('0.16'))
    refined = (D('9'), D('0.11'), D('0.05'))


def _is_number(obj) -> bool:
    try:
        D(obj)
        return True
    except Exception:
        return False


def _normalize(d: D, more: bool = False) -> D:
    if d.is_finite():
        if more:
            d = d.quantize(D('0.001'))
        else:
            d = d.quantize(D('0.01'))
        if d == d // D('0.01'):
            d = d.quantize(D('0.01'))
        if d == d // D('0.1'):
            d = d.quantize(D('0.1'))
        if d == d // D('1'):
            d = d.quantize(D('1'))
        if d == D('-0'):
            d = D('0')
        return d
    return d.normalize()


def _convert_to_scrap(d: D, metal_info) -> D:
    if not d.is_finite():
        return d
    sign = D('1') if d > D('0') else D('-1')
    d = abs(d)
    scrap_amount, scrap_factor, weapon_factor = metal_info
    scrap = D('0')
    int_part = d // D('1')
    scrap += scrap_amount * int_part
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
    return scrap * sign


def _convert_from_scrap(scrap: D, metal_info) -> D:
    if not scrap.is_finite():
        return scrap
    sign = D('1') if scrap > D('0') else D('-1')
    scrap = abs(scrap)
    scrap_amount, scrap_factor, weapon_factor = metal_info
    metal = D('0')
    metal += scrap // scrap_amount
    scrap = scrap % scrap_amount
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
    return metal * sign


def _validate_key_rate(key_rate):
    if isinstance(key_rate, Metal):
        if key_rate.scrap <= D('0'):
            raise ValueError('Key rate must be positive')
        return
    if isinstance(key_rate, RangeMetal):
        if key_rate.start.scrap <= D('0') or key_rate.end.scrap <= D('0'):
            raise ValueError('Key rate must be positive')
        return
    raise TypeError('Key rate must be either Metal or RangeMetal')


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
        for d in all_currency:
            if self.__scrap.is_nan() or d.is_nan():
                raise ValueError('Metal must be a number')
        if self.__scrap != D('0'):
            return
        push(D(weapon) / D('2'))
        push(D(scrap))
        push(_convert_to_scrap(D(rec), _MetalInfo.reclaimed))
        push(_convert_to_scrap(D(ref), _MetalInfo.refined))

    @property
    def _internal_scrap(self) -> D:
        return self.__scrap

    @property
    def weapon(self) -> D:
        return _normalize(self.__scrap * D('2'))

    @property
    def scrap(self) -> D:
        return _normalize(self.__scrap)

    @property
    def reclaimed(self) -> D:
        return _normalize(_convert_from_scrap(self.__scrap, _MetalInfo.reclaimed))

    @property
    def refined(self) -> D:
        return _normalize(_convert_from_scrap(self.__scrap, _MetalInfo.refined))

    @property
    def normalized(self):
        metal = self.__scrap
        sign = D('1') if metal > D('0') else D('-1')
        metal = abs(metal)
        if metal.is_infinite():
            return NormalizedMetal(sign=sign, key=D('0'), refined=metal, reclaimed=metal, scrap=metal, weapon=metal)
        ref = _normalize(metal // D('9'))
        metal = metal % D('9')
        rec = _normalize(metal // D('3'))
        metal = metal % D('3')
        scrap = _normalize(metal // D('1'))
        wep = _normalize(metal % D('1'))
        return NormalizedMetal(sign=sign, key=D('0'), refined=ref, reclaimed=rec, scrap=scrap, weapon=wep)

    def to_key(self, key_rate):
        _validate_key_rate(key_rate)
        if self.__scrap.is_infinite():
            return self.__scrap
        if isinstance(key_rate, Metal):
            return _normalize(self / key_rate, more=True)
        if isinstance(key_rate, RangeMetal):
            start = _normalize(self / key_rate.end, more=True)
            end = _normalize(self / key_rate.start, more=True)
            if start > end:
                start, end = end, start
            if start == end:
                return start
            return (start, end)
        return

    def to_normalized_key(self, key_rate):
        _validate_key_rate(key_rate)
        metal = self.__scrap
        sign = D('1') if metal > D('0') else D('-1')
        metal = abs(metal)
        if metal.is_infinite():
            return NormalizedMetal(sign=sign, key=metal, refined=metal, reclaimed=metal, scrap=metal, weapon=metal)
        if isinstance(key_rate, Metal):
            key = _normalize(metal // key_rate.scrap, more=True)
            pure_metal = Metal(scrap=metal % key_rate.scrap)
            _, _, ref, rec, scrap, wep = pure_metal.normalized
            return NormalizedMetal(sign=sign, key=key, refined=ref, reclaimed=rec, scrap=scrap, weapon=wep)
        if isinstance(key_rate, RangeMetal):
            start_val = self / key_rate.end
            end_val = self / key_rate.start
            start = self.to_normalized_key(key_rate.end)
            end = self.to_normalized_key(key_rate.start)
            if start_val > end_val:
                start, end = end, start
            if start == end:
                return start
            return (start, end)
        return

    def __str__(self):
        return f'{self.refined} ref'

    def __repr__(self):
        if self.__scrap < D('0'):
            return f'-Metal({-self.refined})'
        return f'Metal({self.refined})'

    def __neg__(self):
        return Metal(scrap=-self.__scrap)

    def __pos__(self):
        return Metal(scrap=self.__scrap)

    def __abs__(self):
        return Metal(scrap=abs(self.__scrap))

    def __add__(self, other):
        if isinstance(other, Metal):
            scrap = self.__scrap + other._internal_scrap
            return Metal(scrap=scrap)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Metal):
            return self + (-other)
        return NotImplemented

    def __mul__(self, other):
        if _is_number(other):
            scrap = self.__scrap * D(other)
            return Metal(scrap=scrap)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Metal):
            scale = self.__scrap / other._internal_scrap
            return _normalize(scale, more=True)
        elif _is_number(other):
            scrap = self.__scrap / D(other)
            return Metal(scrap=scrap)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Metal):
            return self.__scrap == other._internal_scrap
        if isinstance(other, RangeMetal):
            return False
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Metal):
            return self.__scrap != other._internal_scrap
        if isinstance(other, RangeMetal):
            return True
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Metal):
            return self.__scrap >= other._internal_scrap
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Metal):
            return self.__scrap <= other._internal_scrap
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Metal):
            return self.__scrap > other._internal_scrap
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Metal):
            return self.__scrap < other._internal_scrap
        return NotImplemented

    def __bool__(self):
        return self.__scrap != D('0')


class RangeMetal:

    __start = None
    __end = None

    def __new__(cls, start, end):
        if not isinstance(start, Metal) or not isinstance(end, Metal):
            raise TypeError('RangeMetal accepts Metal arguments only')
        if start == end:
            return start
        return super().__new__(cls)

    def __init__(self, start, end):
        if start > end:
            start, end = end, start
        self.__start = start
        self.__end = end

    @property
    def start(self) -> Metal:
        return self.__start

    @property
    def end(self) -> Metal:
        return self.__end

    def to_key(self, key_rate):
        _validate_key_rate(key_rate)
        if isinstance(key_rate, Metal):
            start = self.start.to_key()
            end = self.end.to_key()
            if start > end:
                start, end = end, start
            if start == end:
                return start
            return (start, end)
        if isinstance(key_rate, RangeMetal):
            answers = [
                self.start.to_key(key_rate.start),
                self.end.to_key(key_rate.start),
                self.start.to_key(key_rate.end),
                self.end.to_key(key_rate.end)
            ]
            start = min(answers)
            end = max(answers)
            if start == end:
                return start
            return (start, end)
        return

    def to_normalized_key(self, key_rate):
        _validate_key_rate(key_rate)
        if isinstance(key_rate, Metal):
            start_val = self.start / key_rate
            end_val = self.end / key_rate
            start = self.start.to_normalized_key()
            end = self.end.to_normalized_key()
            if start_val > end_val:
                start, end = end, start
            if start == end:
                return start
            return (start, end)
        if isinstance(key_rate, RangeMetal):
            vals = [
                self.start / key_rate.start,
                self.end / key_rate.start,
                self.start / key_rate.end,
                self.end / key_rate.end
            ]
            answers = [
                self.start.to_normalized_key(key_rate.start),
                self.end.to_normalized_key(key_rate.start),
                self.start.to_normalized_key(key_rate.end),
                self.end.to_normalized_key(key_rate.end)
            ]
            start = answers[vals.index(min(vals))]
            end = answers[vals.index(max(vals))]
            if start == end:
                return start
            return (start, end)
        return

    def __str__(self):
        start = self.__start.refined
        end = self.__end.refined
        return f'{start} ~ {end} ref'

    def __repr__(self):
        start = repr(self.__start)
        end = repr(self.__end)
        return f'RangeMetal({start}, {end})'

    def __iter__(self):
        yield self.__start
        yield self.__end

    def __neg__(self):
        return RangeMetal(-self.__end, -self.__start)

    def __pos__(self):
        return RangeMetal(self.__start, self.__end)

    def __add__(self, other):
        if isinstance(other, Metal):
            start = self.__start + other
            end = self.__end + other
        elif isinstance(other, RangeMetal):
            start = self.__start + other.start
            end = self.__end + other.end
        else:
            return NotImplemented
        return RangeMetal(start, end)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        return self.__add__(-other)

    def __rsub__(self, other):
        return -self.__sub__(other)

    def __mul__(self, other):
        if _is_number(other):
            start = self.__start * D(other)
            end = self.__end * D(other)
            return RangeMetal(start, end)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Metal):
            start = _normalize(self.__start / other, more=True)
            end = _normalize(self.__end / other, more=True)
            if start == end:
                return start
            if start > end:
                start, end = end, start
            return (start, end)
        elif isinstance(other, RangeMetal):
            answers = [
                self.__start / other.start,
                self.__start / other.end,
                self.__end / other.start,
                self.__end / other.end
            ]
            start = _normalize(min(answers), more=True)
            end = _normalize(max(answers), more=True)
            if start == end:
                return start
            return (start, end)
        elif _is_number(other):
            start = self.__start / D(other)
            end = self.__end / D(other)
            return RangeMetal(start, end)
        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, Metal):
            start = _normalize(other / self.__start, more=True)
            end = _normalize(other / self.__end, more=True)
            if start == end:
                return start
            if start > end:
                start, end = end, start
            return (start, end)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Metal):
            return False
        if isinstance(other, RangeMetal):
            if self.__start == other.start and self.__end == other.end:
                return True
            return False
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Metal):
            return True
        if isinstance(other, RangeMetal):
            if self.__start == other.start and self.__end == other.end:
                return False
            return True
        return NotImplemented

    def __bool__(self):
        return True
