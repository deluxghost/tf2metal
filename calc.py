# -*- coding: utf-8 -*-
from collections import OrderedDict
import decimal
from decimal import Decimal as D
from decimal import ROUND_DOWN
import re
import sys

__version__ = '2.0.0'

EXCHANGE_RATE = None

decimal.setcontext(decimal.ExtendedContext)
decimal.getcontext().prec = 18

try:
    import colorama
    colorama.init()
    COLOR = True
except ImportError:
    COLOR = False

operations = OrderedDict([
    ("+", lambda x, y: x + y),
    ("-", lambda x, y: x - y),
    ("/", lambda x, y: x / y),
    ("*", lambda x, y: x * y)
])

symbols = operations.keys()


class Metal:

    __scrap = None

    def __init__(self, ref='0', rec='0', scrap='0', weapon='0'):
        # init with 0 metal
        self.__scrap = D('0')
        # init infinity
        all_currency = (D(ref), D(rec), D(scrap), D(weapon))
        if D('inf') in all_currency:
            self.__scrap += D('inf')
        if D('-inf') in all_currency:
            self.__scrap += D('-inf')
        if self.__scrap == D('NaN') or D('NaN') in all_currency:
            raise ValueError('Metal can not be NaN')
        if self.__scrap != D('0'):
            return
        # load weapon arg
        weapon = D(weapon).quantize(D('1'), rounding=ROUND_DOWN)
        # put 0.5 scrap per weapon into metal storage
        self.__scrap += weapon / D('2')
        # load scrap arg, rounding to 0.5 scrap
        scrap = (D(scrap) * D('2')).quantize(D('1')) / D('2')
        # put scrap into storage
        self.__scrap += scrap
        # rec3 stands for reclaimed rounding to 0.33
        rec3 = ((D(rec) * D('3')).quantize(D('1')) / D('3')).quantize(D('.01'), rounding=ROUND_DOWN)
        # rec9 stands for reclaimed rounding to 0.11
        rec9 = ((D(rec) * D('9')).quantize(D('1')) / D('9')).quantize(D('.01'), rounding=ROUND_DOWN)
        # put integer part of rec3 into storage, 3 scrap per reclaimed
        self.__scrap += D('3') * (rec3 // D('1'))
        # put decimal part of rec3 into storage, 1 scrap per 0.33 reclaimed
        self.__scrap += rec3 % D('1') // D('0.33')
        # adjust storage with 0.5 scrap, that's the part of reclaimed over 0.33
        if rec9 > rec3:
            self.__scrap += D('0.5')
        if rec9 < rec3:
            self.__scrap -= D('0.5')
        # ref9 stands for refined rounding to 0.11
        ref9 = ((D(ref) * D('9')).quantize(D('1')) / D('9')).quantize(D('.01'), rounding=ROUND_DOWN)
        # ref18 stands for refined rounding to 0.05
        ref18 = ((D(ref) * D('18')).quantize(D('1')) / D('18')).quantize(D('.01'), rounding=ROUND_DOWN)
        # put integer part of ref9 into storage, 9 scrap per refined
        self.__scrap += D('9') * (ref9 // D('1'))
        # put decimal part of ref9 into storage, 1 scrap per 0.11 reclaimed
        self.__scrap += ref9 % D('1') // D('0.11')
        # adjust storage with 0.5 scrap, that's the part of refined over 0.11
        if ref18 > ref9:
            self.__scrap += D('0.5')
        if ref18 < ref9:
            self.__scrap -= D('0.5')

    @property
    def scrap(self):
        return self.__scrap

    def strfref(self, fmt):
        """
        formatting string:

        %w - metal value in weapon
        %s - metal value in scrap
        %c - metal value in reclaimed
        %r - metal value in refined
        %W - weapon amount in normalize form (e.g. 2 ref 1 rec 2 scrap 1 weapon)
        %S - scrap amount in normalize form
        %C - reclaimed amount in normalize form
        %R - refined amount in normalize form
        %% - % character
        """
        scrap = self.__scrap
        if scrap.is_infinite():
            ref_w = ref_W = scrap
            ref_s = ref_S = scrap
            ref_c = ref_C = scrap
            ref_r = ref_R = scrap
        else:
            ref_w = (scrap * D('2')).quantize(D('1'))
            ref_W = (scrap % D('1') * D('2')).quantize(D('1'))
            ref_s = scrap.quantize(D('.1'))
            ref_S = (scrap % D('3')).quantize(D('1'), rounding=ROUND_DOWN)
            ref_c = (scrap // D('3') + ref_S * D('0.33') + ref_W * D('0.16')).quantize(D('.01'))
            ref_C = (scrap % D('9') // D('3')).quantize(D('.01'))
            ref_r = (scrap // D('9') + ref_C * D('0.33') + ref_S * D('0.11') + ref_W * D('0.05')).quantize(D('.01'))
            ref_R = (scrap // D('9')).quantize(D('.01'))
        i = 0
        n = len(fmt)
        output = list()
        push = output.append
        while i < n:
            char = fmt[i]
            i += 1
            if char == '%':
                if i < n:
                    char = fmt[i]
                    i += 1
                    if char == 'w':
                        push(str(normalize(ref_w)))
                    elif char == 'W':
                        push(str(normalize(ref_W)))
                    elif char == 's':
                        push(str(normalize(ref_s)))
                    elif char == 'S':
                        push(str(normalize(ref_S)))
                    elif char == 'c':
                        push(str(normalize(ref_c)))
                    elif char == 'C':
                        push(str(normalize(ref_C)))
                    elif char == 'r':
                        push(str(normalize(ref_r)))
                    elif char == 'R':
                        push(str(normalize(ref_R)))
                    elif char == '%':
                        push('%')
                    else:
                        push('%')
                        push(char)
                else:
                    push('%')
            else:
                push(char)
        output = ''.join(output)
        return output

    def __str__(self):
        return self.strfref('%r ref')

    def __repr__(self):
        ref = self.strfref('%r')
        if self.__scrap < 0:
            return f'-Metal({-ref})'
        return f'Metal({ref})'

    def __neg__(self):
        data = -(self.__scrap)
        return Metal(scrap=data)

    def __pos__(self):
        return Metal(scrap=self.__scrap)

    def __abs__(self):
        return Metal(scrap=abs(self.__scrap))

    def __add__(self, other):
        if _is_single_metal(other):
            scrap = self.__scrap + other.scrap
            return Metal(scrap=scrap)
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        return self.__add__(-other)

    def __rsub__(self, other):
        return -self.__sub__(other)

    def __mul__(self, other):
        if _is_number(other):
            scrap = self.__scrap * D(other)
            return Metal(scrap=scrap)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if _is_single_metal(other):
            data = self.__scrap / other.scrap
            if data.is_finite():
                data = normalize(data.quantize(D('.01')))
            return data
        elif _is_number(other):
            scrap = self.__scrap / D(other)
            return Metal(scrap=scrap)
        return NotImplemented

    def __rtruediv__(self, other):
        if _is_single_metal(other):
            return other.__truediv__(self)
        return NotImplemented

    def __eq__(self, other):
        if _is_single_metal(other):
            return self.__scrap == other.scrap
        return NotImplemented

    def __ne__(self, other):
        if _is_single_metal(other):
            return self.__scrap != other.scrap
        return NotImplemented

    def __ge__(self, other):
        if _is_single_metal(other):
            return self.__scrap >= other.scrap
        return NotImplemented

    def __le__(self, other):
        if _is_single_metal(other):
            return self.__scrap <= other.scrap
        return NotImplemented

    def __gt__(self, other):
        if _is_single_metal(other):
            return self.__scrap > other.scrap
        return NotImplemented

    def __lt__(self, other):
        if _is_single_metal(other):
            return self.__scrap < other.scrap
        return NotImplemented

    def __bool__(self):
        return self.__scrap != D('0')


class RangeMetal(Metal):

    __start = None
    __end = None
    __median = None

    def __new__(cls, start, end):
        if not _is_single_metal(start) or not _is_single_metal(end):
            raise TypeError('RangeMetal accepts Metal arguments only')
        if start == end:
            return start
        return super().__new__(cls)

    def __init__(self, start, end):
        if start > end:
            start, end = end, start
        self.__start = start
        self.__end = end
        self.__median = (start + end) / D('2')

    @property
    def start(self):
        return self.__start

    @property
    def end(self):
        return self.__end

    @property
    def median(self):
        return self.__median

    @property
    def scrap(self):
        raise NotImplementedError('RangeMetal does not support scrap property')

    def strfref(self, *args, **kwargs):
        raise NotImplementedError('RangeMetal does not support formatting string')

    def __str__(self):
        start = self.__start.strfref('%r')
        end = self.__end.strfref('%r')
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

    def __abs__(self):
        return NotImplemented

    def __add__(self, other):
        if _is_single_metal(other):
            start = self.__start + other
            end = self.__end + other
        elif isinstance(other, RangeMetal):
            start = self.__start + other.start
            end = self.__end + other.end
        else:
            return NotImplemented
        return RangeMetal(start, end)

    def __mul__(self, other):
        if _is_number(other):
            start = self.__start * D(other)
            end = self.__end * D(other)
            return RangeMetal(start, end)
        return NotImplemented

    def __truediv__(self, other):
        if _is_single_metal(other):
            start = self.__start / other
            if start.is_finite():
                start = normalize(start.quantize(D('.01')))
            end = self.__end / other
            if end.is_finite():
                end = normalize(end.quantize(D('.01')))
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
            start = min(answers)
            end = max(answers)
            if start.is_finite():
                start = normalize(start.quantize(D('.01')))
            if end.is_finite():
                end = normalize(end.quantize(D('.01')))
            if start == end:
                return start
            return (start, end)
        elif _is_number(other):
            start = self.__start / D(other)
            end = self.__end / D(other)
            return RangeMetal(start, end)
        return NotImplemented

    def __rtruediv__(self, other):
        if _is_single_metal(other):
            start = other / self.__start
            if start.is_finite():
                start = normalize(start.quantize(D('.01')))
            end = other / self.__end
            if end.is_finite():
                end = normalize(end.quantize(D('.01')))
            if start == end:
                return start
            if start > end:
                start, end = end, start
            return (start, end)
        elif isinstance(other, RangeMetal):
            return other.__truediv__(self)
        return NotImplemented

    def __eq__(self, other):
        if _is_single_metal(other):
            return False
        if isinstance(other, RangeMetal):
            if self.__start == other.start and self.__end == other.end:
                return True
            return False
        return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return NotImplemented

    def __le__(self, other):
        return NotImplemented

    def __gt__(self, other):
        return NotImplemented

    def __lt__(self, other):
        return NotImplemented

    def __bool__(self):
        return True


class ParserError(Exception):

    def __init__(self, message):
        super(ParserError, self).__init__()
        self.message = message

    def __repr__(self):
        classname = self.__class__.__name__
        return f'{classname}({repr(self.message)})'

    def __str__(self):
        return self.message


def _is_single_metal(obj):
    return isinstance(obj, Metal) and not isinstance(obj, RangeMetal)


def _is_number(obj):
    try:
        D(obj)
        return True
    except Exception:
        return False


def normalize(d):
    return d.quantize(D('1')) if d.is_finite() and d == d.to_integral() else d.normalize()


def convert(expr):
    words = [
        'ref',
        'refined',
        'rec',
        'reclaimed',
        'scrap',
        'wep',
        'weapon'
    ]
    expr = ''.join(expr.lower().split())
    keywords = re.sub(r'[\d.]', ' ', expr).split()
    for w in keywords:
        if w not in words:
            raise ParserError('Bad Currency')
    if not keywords:
        return D(expr)
    ref = D('0')
    rec = D('0')
    scrap = D('0')
    wep = D('0')
    for w in keywords:
        index = expr.find(w)
        value = expr[:index]
        if not value:
            raise ParserError('Bad Number')
        expr = expr[index + len(w):]
        if w == 'ref' or w == 'refined':
            ref += D(value)
        elif w == 'rec' or w == 'reclaimed':
            rec += D(value)
        elif w == 'scrap':
            scrap += D(value)
        elif w == 'wep' or w == 'weapon':
            wep += D(value)
    if expr:
        raise ParserError('Bad Currency')
    return Metal(ref, rec, scrap, wep)


def lex(expr):
    tokens = []
    while expr:
        char = expr[0]
        expr = expr[1:]
        if char == "(":
            try:
                paren, expr = lex(expr)
                tokens.append(paren)
            except ValueError:
                raise ParserError('Paren Mismatch')
        elif char == ")":
            for i, v in enumerate(tokens):
                if not isinstance(v, list) and v not in symbols:
                    tokens[i] = convert(v)
            return tokens, expr
        elif char in symbols:
            tokens.append(char)
        elif char.isspace():
            pass
        else:
            try:
                if tokens[-1] in symbols:
                    tokens.append(char)
                elif isinstance(tokens[-1], list):
                    raise ParserError('Invalid Syntax')
                else:
                    tokens[-1] += char
            except IndexError:
                tokens.append(char)
    for i, v in enumerate(tokens):
        if not isinstance(v, list) and v not in symbols:
            tokens[i] = convert(v)
    return tokens


def evaluate(tokens):
    for symbol, func in operations.items():
        try:
            pos = tokens.index(symbol)
            leftTerm = evaluate(tokens[:pos])
            if leftTerm is None:
                if symbol in '+-' and pos + 1 < len(tokens) and tokens[pos + 1] not in ['+', '-', '*', '/']:
                    leftTerm = D('0')
                else:
                    raise ParserError('Bad Expression')
            rightTerm = evaluate(tokens[pos + 1:])
            if rightTerm is None:
                raise ParserError('Bad Expression')
            return func(leftTerm, rightTerm)
        except ValueError:
            pass
    if len(tokens) is 1:
        if isinstance(tokens[0], list):
            return evaluate(tokens[0])
        return tokens[0]
    elif not tokens:
        return None
    else:
        raise ParserError('Bad Expression')


def calc(expr):
    try:
        ans = evaluate(lex(expr))
        if isinstance(ans, D):
            ans = normalize(ans.quantize(D('.01')))
    except decimal.InvalidOperation:
        raise ParserError('Precision Overflow')
    except decimal.DivisionByZero:
        raise ParserError('Division by Zero')
    except TypeError:
        raise ParserError('Meaningless Operation')
    return ans


def calc_str(expr):
    try:
        return calc(expr)
    except ParserError as e:
        return 'Error: {}'.format(e.message)
    except Exception as e:
        return 'Error: {}'.format(e.__class__.__name__)


def _print_color(color, *args, **kw):
    args = list(args)
    if args:
        args[0] = colorama.Style.RESET_ALL + color + args[0]
        args[-1] = args[-1] + colorama.Style.RESET_ALL
    else:
        args = [color + colorama.Style.RESET_ALL]
    print(*args, **kw)


def _print_func(mode, *args, **kw):
    if COLOR:
        mode_list = {
            'title': colorama.Fore.LIGHTBLUE_EX,
            'info': colorama.Fore.LIGHTYELLOW_EX,
            'error': colorama.Fore.LIGHTRED_EX,
            'input': colorama.Style.RESET_ALL,
            'output': colorama.Fore.LIGHTGREEN_EX,
            'prompt': colorama.Fore.LIGHTMAGENTA_EX,
            'equal': colorama.Fore.LIGHTBLUE_EX
        }
        _print_color(mode_list[mode], *args, **kw)
    else:
        print(*args, **kw)


def _term_handler(signal, frame):
    sys.exit(0)


if __name__ == '__main__':
    tool_name = 'TF2 Metal Calculator {}'.format(__version__)
    import platform
    import signal
    signal.signal(signal.SIGINT, _term_handler)
    if '--nocolor' in sys.argv:
        COLOR = False
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a != '-']
    args = [a for a in args if not a.startswith('-') or len(a) != 2 or a[1] in '0123456789']
    if args:
        for expr in args:
            answer = calc_str(expr)
            if isinstance(answer, Metal):
                print(answer.strfref('%rref'))
            elif isinstance(answer, D):
                print('{}'.format(answer))
            elif isinstance(answer, str):
                print(answer)
        sys.exit(0)
    if platform.system() == 'Windows' and getattr(sys, 'frozen', False):
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(tool_name)
    _print_func('title', '{} by deluxghost\nType "quit" to exit.\nType "help" to get more information.'.format(tool_name))
    while True:
        try:
            _print_func('prompt', '>> ', end='')
            expr = input().strip()
        except EOFError:
            break
        if not expr:
            continue
        if expr.lower() == 'q' or expr.lower() == 'quit' or expr.lower() == 'exit':
            break
        elif expr.lower() == 'h' or expr.lower() == 'help' or expr == '?':
            _print_func(
                'info',
                'Use ref, rec, scrap or wep as metal unit.\n'
                'Examples:'
            )
            _print_func('prompt', '>> ', end='')
            _print_func('input', '(2.33ref1rec * 3 + 3scrap) / 2')
            _print_func('equal', '= ', end='')
            _print_func('output', '4.16ref')
            _print_func('prompt', '>> ', end='')
            _print_func('input', '2.55ref * 4')
            _print_func('equal', '= ', end='')
            _print_func('output', '10.22ref')
            continue
        answer = calc_str(expr)
        if isinstance(answer, Metal):
            _print_func('equal', '= ', end='')
            _print_func('output', answer.strfref('%rref'))
        elif isinstance(answer, D):
            _print_func('equal', '= ', end='')
            _print_func('output', '{}'.format(answer))
        elif isinstance(answer, str):
            _print_func('error', answer)
