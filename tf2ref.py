# -*- coding: utf-8 -*-
from collections import OrderedDict
import decimal
from decimal import Decimal as D
from decimal import ROUND_DOWN
import re
import sys

__version__ = '1.2.0'

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


class Metal(object):

    scrap = None

    def __init__(self, ref='0', rec='0', scrap='0', weapon='0'):
        self.scrap = D('0')
        weapon = D(weapon).quantize(D('1'), rounding=ROUND_DOWN)
        self.scrap += weapon / D('2')
        scrap = (D(scrap) * D('2')).quantize(D('1')) / D('2')
        self.scrap += scrap
        rec3 = ((D(rec) * D('3')).quantize(D('1')) / D('3')).quantize(D('.01'), rounding=ROUND_DOWN)
        rec9 = ((D(rec) * D('9')).quantize(D('1')) / D('9')).quantize(D('.01'), rounding=ROUND_DOWN)
        self.scrap += D('3') * (rec3 // D('1'))
        self.scrap += rec3 % D('1') // D('0.33')
        if rec9 > rec3:
            self.scrap += D('0.5')
        if rec9 < rec3:
            self.scrap -= D('0.5')
        ref9 = ((D(ref) * D('9')).quantize(D('1')) / D('9')).quantize(D('.01'), rounding=ROUND_DOWN)
        ref18 = ((D(ref) * D('18')).quantize(D('1')) / D('18')).quantize(D('.01'), rounding=ROUND_DOWN)
        self.scrap += D('9') * (ref9 // D('1'))
        self.scrap += ref9 % D('1') // D('0.11')
        if ref18 > ref9:
            self.scrap += D('0.5')
        if ref18 < ref9:
            self.scrap -= D('0.5')

    def strfref(self, fmt):
        """
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
        scrap = self.scrap
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
        return self.strfref('Metal(%r)')

    def __neg__(self):
        data = -(self.scrap)
        return Metal(scrap=data)

    def __pos__(self):
        return Metal(scrap=self.scrap)

    def __add__(self, other):
        if isinstance(other, Metal):
            data = self.scrap + other.scrap
        elif isinstance(other, (int, float, D)) or isinstance(other, str):
            other = Metal(other)
            data = self.scrap + other.scrap
        else:
            return NotImplemented
        return Metal(scrap=data)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, Metal):
            data = self.scrap - other.scrap
        elif isinstance(other, (int, float, D)) or isinstance(other, str):
            other = Metal(other)
            data = self.scrap - other.scrap
        else:
            return NotImplemented
        return Metal(scrap=data)

    def __rsub__(self, other):
        metal = self.__sub__(other)
        metal.scrap = -(metal.scrap)
        return metal

    def __mul__(self, other):
        if isinstance(other, (int, float, D)) or isinstance(other, str):
            other = D(other)
            data = self.scrap * other
        else:
            return NotImplemented
        return Metal(scrap=data)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Metal):
            data = self.scrap / other.scrap
            data = normalize(data.quantize(D('.01')))
            return data
        elif isinstance(other, (int, float, D)) or isinstance(other, str):
            other = D(other)
            data = self.scrap / other
            return Metal(scrap=data)
        return NotImplemented

    def __div__(self, other):
        return self.__truediv__(other)

    def __eq__(self, other):
        if not isinstance(other, Metal):
            return NotImplemented
        return self.scrap == other.scrap

    def __ne__(self, other):
        if not isinstance(other, Metal):
            return NotImplemented
        return self.scrap != other.scrap

    def __ge__(self, other):
        if not isinstance(other, Metal):
            return NotImplemented
        return self.scrap >= other.scrap

    def __le__(self, other):
        if not isinstance(other, Metal):
            return NotImplemented
        return self.scrap <= other.scrap

    def __gt__(self, other):
        if not isinstance(other, Metal):
            return NotImplemented
        return self.scrap > other.scrap

    def __lt__(self, other):
        if not isinstance(other, Metal):
            return NotImplemented
        return self.scrap < other.scrap

    def __nonzero__(self):
        return self.scrap > D('0')

    def __bool__(self):
        return self.__nonzero__()


class ParserError(Exception):

    def __init__(self, message):
        super(ParserError, self).__init__()
        self.message = message

    def __repr__(self):
        classname = self.__class__.__name__
        return '{0}({1})'.format(classname, repr(self.message))

    def __str__(self):
        return self.message


def normalize(d):
    return d.quantize(D('1')) if d == d.to_integral() else d.normalize()


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
