# -*- coding: utf-8 -*-
from collections import OrderedDict
from decimal import Decimal as D
import re
import sys

import colorama

import metal as m

__version__ = '2.0.0'
rate_pat = re.compile(r'^[\d.]+(?:ref)?$')
KEY_RATE = None

colorama.init()

operations = OrderedDict([
    ('+', lambda x, y: x + y),
    ('-', lambda x, y: x - y),
    ('/', lambda x, y: x / y),
    ('*', lambda x, y: x * y)
])
symbols = list(operations.keys())


class ParserError(Exception):

    def __init__(self, message):
        super(ParserError, self).__init__()
        self.message = message

    def __repr__(self):
        classname = self.__class__.__name__
        return f'{classname}({repr(self.message)})'

    def __str__(self):
        return self.message


def convert(expr: str):
    words = [
        'key',
        'ref',
        'rec',
        'scrap',
        'wep'
    ]
    expr = ''.join(expr.lower().split())
    keywords = re.sub(r'[\d.]', ' ', expr).split()
    for w in keywords:
        if w not in words:
            raise ParserError('Bad currency')
    if not keywords:
        return D(expr)
    metal = m.Metal('0')
    for w in keywords:
        index = expr.find(w)
        value = expr[:index]
        if not value:
            raise ParserError('Bad number')
        expr = expr[index + len(w):]
        if w == 'key':
            if KEY_RATE is None:
                raise ParserError('You must set exchange rate before using key')
            metal = metal + value * KEY_RATE
        elif w == 'ref':
            metal = metal + m.Metal(ref=D(value))
        elif w == 'rec':
            metal = metal + m.Metal(rec=D(value))
        elif w == 'scrap':
            metal = metal + m.Metal(scrap=D(value))
        elif w == 'wep':
            metal = metal + m.Metal(wep=D(value))
    if expr:
        raise ParserError('Bad currency')
    return metal


def lex(expr):
    tokens = []
    while expr:
        char = expr[0]
        expr = expr[1:]
        if char == '(':
            try:
                paren, expr = lex(expr)
                tokens.append(paren)
            except ValueError:
                raise ParserError('Paren mismatch')
        elif char == ')':
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
                    raise ParserError('Invalid syntax')
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
            right_term = evaluate(tokens[pos + 1:])
            if right_term is None:
                raise ParserError('Bad expression')
            left_term = evaluate(tokens[:pos])
            if left_term is None:
                if symbol in '+-' and pos + 1 < len(tokens) and tokens[pos + 1] not in symbols:
                    left_term = m.Metal('0') if isinstance(right_term, (m.Metal, m.RangeMetal)) else D('0')
                else:
                    raise ParserError('Bad expression')
            return func(left_term, right_term)
        except ValueError:
            pass
    if len(tokens) is 1:
        if isinstance(tokens[0], list):
            return evaluate(tokens[0])
        return tokens[0]
    elif not tokens:
        return None
    else:
        raise ParserError('Bad expression')


def calc(expr):
    try:
        return evaluate(lex(expr))
    except ParserError as e:
        return f'Error: {e.message}'
    except Exception as e:
        return f'Error: {e.__class__.__name__}'


def _print_color(color, *args, **kw):
    args = list(args)
    if args:
        args[0] = colorama.Style.RESET_ALL + color + args[0]
        args[-1] = args[-1] + colorama.Style.RESET_ALL
    else:
        args = [color + colorama.Style.RESET_ALL]
    print(*args, **kw)


def _print_func(mode, *args, **kw):
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


def _term_handler(signal, frame):
    sys.exit(0)


def _set_key_rate(expr):
    global KEY_RATE
    bad_rate_expr = 'Bad exchange rate expression'
    expr = ''.join(expr.split())
    if not expr.startswith('key='):
        _print_func('error', bad_rate_expr)
    rate = expr.split('=', 1)[1]
    if '-' in expr or '~' in expr:
        spl = '-' if '-' in expr else '~'
        left, right = rate.split(spl, 1)
        if not rate_pat.match(left) or not rate_pat.match(right):
            _print_func('error', bad_rate_expr)
            return
        left, right = left.replace('ref', ''), right.replace('ref', '')
        KEY_RATE = m.RangeMetal(m.Metal(left), m.Metal(right))
    else:
        if not rate_pat.match(rate):
            _print_func('error', bad_rate_expr)
            return
        rate = rate.replace('ref', '')
        KEY_RATE = m.Metal(rate)
    _print_func('output', f'You set exchange rate to 1 key = {KEY_RATE}')


def _is_int(d: D) -> bool:
    return d // D('1') == d


def _normalized_metal_str(metal):
    sign, key, ref, rec, scrap, wep = metal
    output = list()
    if key:
        output.append(f'{key} key')
    if ref:
        output.append(f'{ref} ref')
    if rec:
        output.append(f'{rec} rec')
    if scrap:
        output.append(f'{scrap} scrap')
    if wep:
        output.append(f'{wep} wep')
    output = ' '.join(output)
    if sign < D('0'):
        output = '-' + output
    return output


def _parse_key(metal):
    if KEY_RATE is None:
        return
    key = metal.to_key(KEY_RATE)
    if isinstance(key, tuple):
        key_line = f'{key[0]} ~ {key[1]} key'
    else:
        key_line = f'{key} key'
    _show_answer(key_line)


def _parse_answer(expr):
    answer = calc(expr)
    if isinstance(answer, m.Metal):
        metal_line = str(answer)
        _show_answer(metal_line)
        if not _is_int(answer.refined):
            normalized = _normalized_metal_str(answer.normalized)
            metal_line = f'{normalized}'
            _show_answer(metal_line)
        _parse_key(answer)
    if isinstance(answer, m.RangeMetal):
        metal_line = str(answer)
        _show_answer(metal_line)
        if not _is_int(answer.start.refined) or not _is_int(answer.end.refined):
            normalized_start = _normalized_metal_str(answer.start.normalized)
            normalized_end = _normalized_metal_str(answer.end.normalized)
            metal_line = f'{normalized_start} ~ {normalized_end}'
            _show_answer(metal_line)
        _parse_key(answer)
    elif isinstance(answer, D):
        _show_answer(answer)
    elif isinstance(answer, tuple):
        _show_answer(f'{answer[0]} ~ {answer[1]}')
    elif isinstance(answer, str):
        _print_func('error', answer)


def _show_answer(answer):
    _print_func('equal', '= ', end='')
    _print_func('output', f'{answer}')


def _show_help():
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


if __name__ == '__main__':
    tool_name = f'TF2 Metal Calculator {__version__}'
    import platform
    import signal
    signal.signal(signal.SIGINT, _term_handler)
    if platform.system() == 'Windows' and getattr(sys, 'frozen', False):
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(tool_name)
    _print_func('title', f'{tool_name} by deluxghost\nType "quit" to exit.\nType "help" to get more information.')
    while True:
        try:
            _print_func('prompt', '\n>> ', end='')
            expr = input().strip()
        except EOFError:
            break
        if not expr:
            continue
        if expr.lower() in ['q', 'quit', 'exit']:
            break
        elif expr.lower() in ['h', 'help', '?']:
            _show_help()
            continue
        elif expr.lower().startswith('key'):
            _set_key_rate(expr)
            continue
        _parse_answer(expr)
