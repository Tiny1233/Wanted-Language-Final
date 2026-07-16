# -*- coding: UTF-8 -*-

import os
import sys
import wcf

command = sys.argv[1]
BASE_DIR = os.path.dirname(os.path.abspath(command))

with open(command, 'r', encoding='utf-8') as f:
    # remove empty/whitespace-only lines and comment-only lines to avoid spurious tokens
    code_lines = [l for l in f.read().split('\n') if l.strip() != '' and not l.strip().startswith('#')]

def lex(line: str) -> list:
    '''
    e.g
    a = 1*2+3 -> ['a', '=', ['1','*', '2', '+', '3']]
    a = 1 + 2 * 3 -> ['a', '=', ['1', '+', ['2', '*', '3']]]
    rep 3: -> ['rep', '3', ':']
    rep num+1: -> ['rep', ['num', '+', '1'], ':']
    rep len('33')+1: -> ['rep', ['len', ["'33'"], '+', '1'], ':'] 
    tips:
        operations need to be surrounded with brackets if the original order is incorrect
        from keyword like if, rep, eif, else, to ':', the middle need to be packed into a list
        keyword 'getwcore' has 2 args, e.g. expected
        getwcore 'stdout' 2 + 3 + num
                        -> ['getwcore', ["'stdout'", ['2', '+', '3', '+', 'num']]]
    '''
    # simple lexer + parser with basic operator precedence and parentheses/calls
    import re

    # include braces so list literals can be written with { ... }
    TOK_RE = re.compile(r"\s*(?:(\+=|-=|\*=|/=|==|!=|>=|<=|\d+(?:\.\d+)?|\w+|[:=+\-*/()\[\]{},<>!&|])|('(\\'|[^'])*'))")

    # tokenize keeping quoted strings as one token
    tokens = []
    i = 0
    while i < len(line):
        m = TOK_RE.match(line, i)
        if not m:
            # unknown single char
            tokens.append(line[i])
            i += 1
            continue
        g1, g2 = m.group(1), m.group(2)
        if g1:
            tokens.append(g1)
        else:
            tokens.append(g2)
        i = m.end()

    # recursive descent parser
    idx = 0

    def peek():
        return tokens[idx] if idx < len(tokens) else None

    def consume(tok=None):
        nonlocal idx
        t = peek()
        if tok and t != tok:
            return None
        idx += 1
        return t

    def parse_primary(no_index=False):
        def maybe_parse_index(node):
            while peek() == '[':
                consume('[')
                index_expr = parse_compare()
                consume(']')
                node = ['index', node, index_expr]
            return node

        def maybe_index(node):
            return node if no_index else maybe_parse_index(node)

        t = peek()
        # list literal support: [a, b, 1] or {a, b, 1}
        if t == '[' or t == '{':
            opener = consume()
            closer = ']' if opener == '[' else '}'
            elems = []
            if peek() != closer:
                while True:
                    elems.append(parse_compare())
                    if peek() == ',':
                        consume(',')
                        continue
                    break
            consume(closer)
            return maybe_index(['list', elems])
        if t == '(':
            consume('(')
            expr = parse_compare()
            consume(')')
            return maybe_index(expr)
        if t == 'getwcore':
            consume()
            first = parse_primary()
            second = parse_compare()
            return maybe_index(['getwcore', [first, second]])
        if isinstance(t, str) and re.match(r"^'", t):
            return maybe_index(consume())
        if t and re.match(r"^\d+$", t) or (t and re.match(r"^\w+$", t)):
            # identifier or number
            name = consume()
            # function call
            if peek() == '(':
                consume('(')
                args = []
                if peek() != ')':
                    while True:
                        args.append(parse_compare())
                        if peek() == ',':
                            consume(',')
                            continue
                        break
                consume(')')
                return maybe_index([name, args])
            return maybe_index(name)
        return maybe_index(consume())

    def parse_term():
        node = parse_primary()
        parts = [node]
        while peek() in ('*', '/'):
            op = consume()
            right = parse_primary()
            parts.append(op)
            parts.append(right)
        # fold to right-associative nested binary operations: a*b/c -> [a, '*', [b, '/', c]]
        def fold_ops(p):
            if len(p) == 1:
                return p[0]
            return [p[0], p[1], fold_ops(p[2:])]

        return fold_ops(parts)

    def parse_expr():
        node = parse_term()
        parts = [node]
        while peek() in ('+', '-'):
            op = consume()
            right = parse_term()
            parts.append(op)
            parts.append(right)
        # fold to right-associative nested binary operations: a+b-c -> [a, '+', [b, '-', c]]
        def fold_ops(p):
            if len(p) == 1:
                return p[0]
            return [p[0], p[1], fold_ops(p[2:])]

        return fold_ops(parts)

    def parse_bitand():
        node = parse_expr()
        parts = [node]
        while peek() == '&':
            op = consume()
            right = parse_expr()
            parts.append(op)
            parts.append(right)

        def fold_ops(p):
            if len(p) == 1:
                return p[0]
            return [p[0], p[1], fold_ops(p[2:])]

        return fold_ops(parts)

    def parse_bitor():
        node = parse_bitand()
        parts = [node]
        while peek() == '|':
            op = consume()
            right = parse_bitand()
            parts.append(op)
            parts.append(right)

        def fold_ops(p):
            if len(p) == 1:
                return p[0]
            return [p[0], p[1], fold_ops(p[2:])]

        return fold_ops(parts)

    def parse_compare():
        node = parse_bitor()
        parts = [node]
        while peek() in ('==', '!=', '<', '>', '<=', '>='):
            op = consume()
            right = parse_bitor()
            parts.append(op)
            parts.append(right)

        def fold_ops(p):
            if len(p) == 1:
                return p[0]
            return [p[0], p[1], fold_ops(p[2:])]

        return fold_ops(parts)

    # special handling: for keywords until ':' pack into list
    # include 'assert' and 'func' and 'return' so assertions like: assert x == 1  -> ['assert', <expr>]
    if tokens and tokens[0] in ('rep', 'if', 'eif', 'else', 'assert', 'while', 'final', 'func', 'return'):
        # consume keyword
        kw = tokens[0]
        # build rest until ':'
        # find colon position
        try:
            colon_i = tokens.index(':')
        except ValueError:
            colon_i = len(tokens)
        # parse middle tokens
        mid_line = ''.join(tokens[1:colon_i])
        if mid_line:
            # naive: parse mid as expression
            inner = lex(mid_line)
            if kw == 'assert' or kw == 'return':
                return [kw, inner]

            return [kw, inner, ':']
        return [kw] if kw == 'assert' else [kw, ':']

    # getwcore special: first arg string then expression
    if tokens and tokens[0] == 'getwcore':
        consume()  # getwcore
        first = parse_primary()
        second = parse_compare()
        return ['getwcore', [first, second]]

    # ext import special: `ext name` -> ['ext', 'name']
    if tokens and tokens[0] == 'ext':
        # if next token exists and is an identifier or string, return pair
        if len(tokens) > 1:
            # join remaining tokens to preserve symbols like @ and . in module names
            name = ''.join(tokens[1:]).strip()
            return ['ext', name]
        return ['ext']

    # special only directive: `only ...` -> ['only', "..."]
    if tokens and tokens[0] == 'only':
        # preserve rest of line as a single string
        rest = line[len('only'):].strip()
        return ['only', rest]

    # compound assignment special: `a += 1`, `a -= 2`, etc.
    for op in ('+=', '-=', '*=', '/='):
        if op in tokens:
            op_i = tokens.index(op)
            left = ''.join(tokens[:op_i]).strip()
            rhs_tokens = ''.join(tokens[op_i+1:])
            rhs = lex(rhs_tokens) if rhs_tokens else []
            return [left, op, rhs]

    # default: parse whole line possibly assignment
    # look for '=' at top-level
    if '=' in tokens:
        eq_i = tokens.index('=')
        left = ''.join(tokens[:eq_i]).strip()
        # left may be a name
        rhs_tokens = ''.join(tokens[eq_i+1:])
        # parse the RHS separately to avoid parsing the LHS tokens
        rhs = lex(rhs_tokens) if tokens[eq_i+1:] else []
        return [left, '=', rhs]

    # otherwise parse as expression or plain tokens
    idx = 0
    return parse_compare() if tokens else []


def tokenize(code_lines, indent=0):
    res = []
    i = 0
    n = len(code_lines)
    while i < n:
        line = code_lines[i]
        c_indent = get_line_indent(line)
        stripped = line.strip()

        # If this line is more-indented than current block, it belongs to
        # the previous header; gather the whole indented block and attach.
        if c_indent > indent:
            # Should not happen for the very first line; treat as normal.
            if not res:
                # ensure we store parsed token (not raw string) so later
                # code can uniformly expect list tokens
                res.append(lex(stripped))
                i += 1
                continue

            # collect continuous lines that are more indented than current
            block = []
            j = i
            while j < n and get_line_indent(code_lines[j]) > indent:
                block.append(code_lines[j])
                j += 1

            child_indent = get_line_indent(block[0]) if block else indent
            res[-1] = [res[-1], tokenize(block, indent=child_indent)]
            i = j
            continue

        # normal line at or below current indent
        res.append(lex(stripped))
        i += 1

    return res
# expected: ['num = 0', ['rep num + 1:', ["getwcore 'stdout' (num + 1)", "getwcore 'stdout' (num + 1)"]]]
def get_line_indent(line):
    c_indent = 0
    for i in line:
        if i == ' ':
            c_indent += 1
        else:
            break
    return c_indent




[
    ['ext', '@builtin.wcc'],
    ['num', '=', '0'], 
    [
        ['rep', ['num', '+', '1'], ':'],
        [
            ['getwcore', ["'stdout'", ['num', '+', '1']]],
            ['getwcore', ["'stdout'", ['num', '+', '1']]],
            [
                ['if', 'num', ':'], 
                [['output', ['num', '+', '1']]]
            ], 
            [
                ['else', ':'], 
                [['getwcore', ["'sysexit'", '1']]]
            ]

        ]
    ]
]

from wcf import BinaryOperator as BinaryOperator, CodeBlock as CodeBlock, CodeLine as CodeLine, Error as Error, INF as INF, KeywordCodeLine as KeywordCodeLine, NumberType as NumberType, Operator as Operator, StringType as StringType, TINY as TINY, Type as Type, Variable as Variable, VariableDefinitionCodeLine as VariableDefinitionCodeLine, VariableSpace as VariableSpace, ListType as ListType, lib as lib, math as math, sys as sys, var_list as var_list

# Add ListType addition support: allow concatenation with scalars or other lists.
def _listtype_add(self, other):
    # helper to normalize an item into a Type instance
    def normalize_item(it):
        if isinstance(it, (NumberType, StringType, ListType, Type)):
            return it
        # python primitive -> wrap
        if isinstance(it, str):
            return StringType(it)
        if isinstance(it, (int, float)):
            return NumberType(it)
        # fallback: convert to string
        return StringType(str(it))

    # get current elements; prefer .get() if returns list of Type or primitives
    try:
        left_elems = self.get()
    except Exception:
        left_elems = []

    new_elems = []
    # ensure elements are Type objects
    for el in left_elems:
        if isinstance(el, (NumberType, StringType, ListType, Type)):
            new_elems.append(el)
        else:
            # wrap primitive
            new_elems.append(normalize_item(el))

    # handle other being a ListType -> extend, otherwise append
    if isinstance(other, ListType):
        try:
            right_elems = other.get()
        except Exception:
            right_elems = []
        for el in right_elems:
            new_elems.append(el if isinstance(el, (NumberType, StringType, ListType, Type)) else normalize_item(el))
    else:
        new_elems.append(other if isinstance(other, (NumberType, StringType, ListType, Type)) else normalize_item(other))

    return ListType(new_elems)

# attach to ListType if not present
ListType.__add__ = _listtype_add
ListType.__radd__ = _listtype_add

BreakLoop = wcf.BreakLoop

BREAK_DEPTH = 0
# when a break occurs, set this to skip executing any following 'final' blocks
WANTED_SKIP_FINAL = False

_original_keyword_get = KeywordCodeLine.get

def _wanted_keyword_get(self):
    # support 'break' keyword to interrupt execution and avoid running final blocks
    if self.name == 'break':
        # mark to skip final blocks and raise to unwind loop
        globals()['WANTED_SKIP_FINAL'] = True
        raise BreakLoop()
    if self.name == 'ext':
   
        if len(self.arg) != 1:
            cnt = len(self.arg)
            plural = 'was' if cnt < 2 else 'were'
            Error('Ext Error', f"1 argument was expected, but {cnt} {plural} given.", self.line).emit()

        path_arg = self.arg[0]
        path = path_arg.get() if hasattr(path_arg, 'get') else path_arg
        if isinstance(path, StringType) or isinstance(path, NumberType):
            path = path.get() if hasattr(path, 'get') else path
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
 
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as ext_file:
                ext_lines = [l for l in ext_file.read().split('\n') if l.strip() != '' and not l.strip().startswith('#')]
            ext_tokens = tokenize(ext_lines)
            ext_cb = interpret(ext_tokens, the_first_time_running=False)
    
            ext_cb.run()
            return None

        Error('Ext Error', f"Included file '{path}' not found.", self.line).emit()
        return None

    if self.name == 'getwcore':
        if len(self.arg) != 2:
            cnt = len(self.arg)
            plural = 'was' if cnt < 2 else 'were'
            Error('GetWCore Error', f"2 sub arguments were expected, but {cnt} {plural} given.", self.line).emit()

        subcommand = self.arg[0]
        subcontent = self.arg[1]
        command = subcommand.get()

        # do not cache stdin reads across repeated executions of the same line
        # so each prompt occurs every time the code reaches getwcore 'stdin'.
        match command:
            case 'stdout':
                # attempt to evaluate subcontent robustly; some composite
                # subcontent nodes may return None on first try, so try
                # calling get() repeatedly / fallback to resolving wrapped
                # values to obtain a printable result.
                try:
                    result = subcontent.get()
                except Exception:
                    # fallback: try resolving via repeated .get()
                    result = subcontent
                    try:
                        while hasattr(result, 'get'):
                            result = result.get()
                    except Exception:
                        pass
                    
                # respect global ONLY_FILTER: if set, only allow prints that equal this value
                out_val = result.get() if isinstance(result, (StringType, NumberType)) else result
                if globals().get('ONLY_FILTER') is None or str(out_val) == str(globals().get('ONLY_FILTER')):
                    import lib.wcore.wsfilter as ws
                    def format_wcore_output(item):
                        if isinstance(item, ListType):
                            return '{' + ', '.join(format_wcore_output(sub_item) for sub_item in item.get()) + '}'
                        if isinstance(item, NumberType):
                            return str(ws.wsfilter(str(item.get())))
                        if isinstance(item, StringType):
                            return "'" + str(ws.wsfilter(item.get())) + "'"
                        if hasattr(item, 'get'):
                            return format_wcore_output(item.get())
                        return "'" + str(ws.wsfilter(str(item))) + "'"
                    if isinstance(out_val, ListType):
                        print('{' + ', '.join(format_wcore_output(item) for item in out_val.get()) + '}', end='')
                    else:
                        print(ws.wsfilter(str(out_val)), end='')
                return result

            case 'stdin':
                prompt = subcontent.get()
                if isinstance(prompt, (StringType, NumberType)):
                    prompt = prompt.get()
                result = StringType(input(prompt))
                return result

    return _original_keyword_get(self)

KeywordCodeLine.get = _wanted_keyword_get

_original_variable_definition_get = VariableDefinitionCodeLine.get

def _wanted_variable_definition_get(self):
    t = self.arg[0]
    while not isinstance(t, (NumberType, StringType, ListType)):
        if not hasattr(t, 'get'):
            break
        t = t.get()

    if isinstance(t, str):
        t = StringType(t)
    elif isinstance(t, (int, float)):
        t = NumberType(t)
    elif isinstance(t, list):
        t = ListType([StringType(str(item)) if not isinstance(item, (NumberType, StringType, ListType, Type)) else item for item in t])

    for var in var_list:
        if var.name == self.name:
            var.value = t
            return t.get() if hasattr(t, 'get') else t

    var_list.append(VariableSpace(self.name, t))
    return t.get() if hasattr(t, 'get') else t

VariableDefinitionCodeLine.get = _wanted_variable_definition_get

# global only filter: when set, only allow stdout prints that equal this value
ONLY_FILTER = None

def interpret(tokens: list, the_first_time_running: True):
    keyword_list = ['ext', 'rep', 'getwcore', 'if', 'else', 'eif', 'final']
    def has_child(li: list):
        for el in li:
            if isinstance(el, list):
                return True

        return False
    line = 0
    cb = CodeBlock([])
    class IndexType(Type):
        def __init__(self, base, index):
            self.base = base
            self.index = index

        def get(self):
            def resolve_value(value):
                # unwrap any nested wrapper objects to get the underlying value
                while hasattr(value, 'get') and not isinstance(value, (NumberType, StringType, ListType)):
                    value = value.get()
                if hasattr(value, 'value') and not isinstance(value, (NumberType, StringType, ListType)):
                    value = value.value
                return value

            base_val = resolve_value(self.base)
            index_val = resolve_value(self.index)
            # normalize NumberType/StringType index to raw python values
            if isinstance(index_val, (NumberType, StringType, ListType)):
                index_val = index_val.get() if hasattr(index_val, 'get') else index_val
            if isinstance(index_val, (NumberType, StringType, ListType)):
                index_val = index_val.get() if hasattr(index_val, 'get') else index_val

            try:
                # Prefer any ListType-provided indexing helper if available
                # (some ListType implementations expose get_index to return
                # the stored Type object correctly).
                if isinstance(base_val, ListType):
                    # prefer ListType.get_index if available
                    if hasattr(base_val, 'get_index') and not isinstance(index_val, (int, float, str)):
                        return base_val.get_index(index_val)
                    # get underlying list
                    elems = base_val.get() if hasattr(base_val, 'get') else base_val
                    try:
                        idx = index_val
                        if isinstance(idx, (NumberType,)):
                            idx = idx.get()
                        idx = int(idx)
                        el = elems[idx]
                        # if element is wrapped Type, return it; otherwise wrap
                        if isinstance(el, (NumberType, StringType, ListType, Type)):
                            return el
                        if isinstance(el, (int, float)):
                            return NumberType(el)
                        return StringType(str(el))
                    except Exception:
                        return None
                elif hasattr(base_val, 'get_index'):
                    return base_val.get_index(index_val)

                # string indexing: support both StringType and plain python str
                if isinstance(base_val, StringType) or isinstance(base_val, str):
                    s = base_val.get() if isinstance(base_val, StringType) else base_val
                    try:
                        # coerce index to int from NumberType, StringType or primitives
                        if hasattr(index_val, 'get') and not isinstance(index_val, (int, float, str)):
                            index_val = index_val.get()
                        if isinstance(index_val, (NumberType,)):
                            index_val = index_val.get()
                        if not isinstance(index_val, int):
                            index_val = int(index_val)
                        return StringType(s[index_val])
                    except Exception:
                        return None

                if hasattr(base_val, 'get') and not isinstance(base_val, (NumberType, StringType, ListType)):
                    base_val = base_val.get()
                return base_val[index_val]
            except Exception:
                # fallback: coerce to python str/list and index if possible
                try:
                    b = base_val.get() if hasattr(base_val, 'get') else base_val
                    i = index_val.get() if hasattr(index_val, 'get') else index_val
                    if not isinstance(i, int):
                        i = int(i)
                    # string fallback
                    if isinstance(b, (str, StringType)):
                        s = b.get() if isinstance(b, StringType) else b
                        return StringType(s[i])
                    # list fallback
                    return b[i]
                except Exception:
                    return None
    
    def tag(name):
        # print(name)
        if isinstance(name, list):
            if name and name[0] == 'index' and len(name) == 3:
                return IndexType(tag(name[1]), tag(name[2]))
            # list literal: ['list', elems]
            if name and name[0] == 'list' and len(name) > 1:
                elems = name[1]
                return ListType([tag(el) for el in elems])
            # handle binary operators including arithmetic, comparison and bit ops
            if len(name) == 3 and isinstance(name[1], str) and name[1] in ['+', '-', '*', '/', '==', '!=', '<', '>', '<=', '>=', '&', '|']:
                return BinaryOperator(name[1], tag(name[0]), tag(name[2]))
            if name and name[0] == 'getwcore' and len(name) == 2:
                arg = name[1]
                if isinstance(arg, list) and len(arg) == 2:
                    return KeywordCodeLine('getwcore', [tag(arg[0]), tag(arg[1])], line)
   
            
            if len(name) == 1:
                return tag(name[0])
            return tag(name[0])
        if len(name) == 2 and isinstance(name[0], str) and isinstance(name[1], list):
            return wcf.FunctionCall(name[0], name[1], line)
        try:
            float(name)
            return NumberType(int(float(name)) if int(float(name)) == float(name) else float(name))
        except Exception:
            if isinstance(name, str) and name.startswith("'") and name.endswith("'"):
                return StringType(name[1:-1])
            return Variable(name)

    def parse_token(token):
        if token == 'break':
            cb.code_lines.append(KeywordCodeLine('break', [], line))
            return
        if not isinstance(token, list):
            return

        # only directive: set global filter
        if token and token[0] == 'only' and len(token) > 1:
            # strip surrounding quotes if present
            val = token[1]
            if isinstance(val, str) and val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            globals()['ONLY_FILTER'] = val
            return

        # assert directive: produce a KeywordCodeLine so wcf.assert handling runs
        if token and token[0] == 'assert':
            # token expected like ['assert', <expr>]
            arg = token[1] if len(token) > 1 else NumberType(0)
            cb.code_lines.append(KeywordCodeLine('assert', [tag(arg)], line))
            return

        # nested block, e.g. ['rep', ['num', '+', '1'], ':'] with child body
        if token and isinstance(token[0], list):
            header = token[0]
            body = token[1] if len(token) > 1 else []
            # support rep and conditional blocks: if / eif / else
            if header and (header[-1] == ':' or header[0] == 'final'):
                kw = header[0]
                # rep block
                if kw == 'rep':
                    count = tag(header[1]) if len(header) > 1 else NumberType(0)
                    body_block = interpret(body, the_first_time_running=False)
                    cb.code_lines.append(KeywordCodeLine('rep', [count, body_block], line))
                    return

                # while block
                if kw == 'while':
                    cond = tag(header[1]) if len(header) > 1 else NumberType(0)
                    body_block = interpret(body, the_first_time_running=False)
                    cb.code_lines.append(KeywordCodeLine('while', [cond, body_block], line))
                    return

                # final blocks after loops
                if kw == 'final':
                    body_block = interpret(body, the_first_time_running=False)
                    prev_loop = None
                    for prev in reversed(cb.code_lines):
                        if isinstance(prev, KeywordCodeLine) and prev.name in ('rep', 'while'):
                            prev_loop = prev
                            break
                    if prev_loop:
                        prev_loop.arg.append(body_block)
                    else:
                        cb.code_lines.append(KeywordCodeLine('final', [body_block], line))
                    return

                # function definition: func name(args):
                if kw == 'func':
                    # header[1] expected like ['name', args] or 'name'
                    name_part = header[1] if len(header) > 1 else None
                    func_name = None
                    func_args = []
                    if isinstance(name_part, list) and len(name_part) >= 1:
                        func_name = name_part[0]
                        if len(name_part) > 1:
                            arg_part = name_part[1]
                            if isinstance(arg_part, list):
                                func_args = [arg for arg in arg_part if isinstance(arg, str)]
                            elif isinstance(arg_part, str):
                                func_args = [arg_part]
                    elif isinstance(name_part, str):
                        func_name = name_part

                    body_block = interpret(body, the_first_time_running=False)
                    if func_name:
                        # register as a VariableSpace so calls can find it
               
                        var_list.append(VariableSpace(func_name, (body_block, func_args)))
         
                    return

                # if / eif (else-if) / else blocks
                if kw in ('if', 'eif', 'else'):
                    body_block = interpret(body, the_first_time_running=False)
                    # search backwards for the most recent if/eif to attach else/eif branches correctly
                    prev_conditional = None
                    for prev in reversed(cb.code_lines):
                        if isinstance(prev, KeywordCodeLine) and prev.name in ('if', 'eif'):
                            prev_conditional = prev
                            break

                    if kw == 'else':
                        if prev_conditional:
                            prev_conditional.arg.append(body_block)
                        else:
                            cb.code_lines.append(KeywordCodeLine(kw, [body_block], line))
                        return

                    # 'if' and 'eif' have a condition expression in header[1]
                    cond = tag(header[1]) if len(header) > 1 else NumberType(0)
                    if kw == 'eif':
                        if prev_conditional:
                            prev_conditional.arg.append(KeywordCodeLine('eif', [cond, body_block], line))
                        else:
                            cb.code_lines.append(KeywordCodeLine('eif', [cond, body_block], line))
                        return

                    cb.code_lines.append(KeywordCodeLine('if', [cond, body_block], line))
                    return
            return

        if len(token) == 3 and token[1] in ('+=', '-=', '*=', '/='):
            op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
            op = op_map[token[1]]
            cb.code_lines.append(VariableDefinitionCodeLine(token[0], [BinaryOperator(op, Variable(token[0]), tag(token[2]))], line))
            return

        if len(token) == 3 and token[1] == '=':
            cb.code_lines.append(VariableDefinitionCodeLine(token[0], [tag(token[2])], line))
            return

        if token[0] == 'getwcore' and len(token) > 1:
            arg = token[1]
            if isinstance(arg, list) and len(arg) == 2:
                cb.code_lines.append(KeywordCodeLine('getwcore', [tag(arg[0]), tag(arg[1])], line))
            return

        # handle external includes: ['ext', '@file:filename'] or ['ext', 'filename']
        if token[0] == 'ext' and len(token) > 1:
      
            arg = token[1]
            if isinstance(arg, str):
                path = arg.strip()
                if path.startswith("'") and path.endswith("'"):
                    path = path[1:-1]
                if path.startswith('@file:'):
                    path = path[len('@file:'):]
                elif path.startswith('@'):
                    path = 'lib\\interior\\' + path[1:]
                if not os.path.isabs(path):
                    path = os.path.join(BASE_DIR, path)
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as ext_file:
                        ext_lines = [l for l in ext_file.read().split('\n') if l.strip() != '' and not l.strip().startswith('#')]
                    # print(ext_lines, path)
                    ext_tokens = tokenize(ext_lines)
                    ext_cb = interpret(ext_tokens, the_first_time_running=True)
                    # cb.code_lines.extend(ext_cb.code_lines)
                else:
                    Error('Ext Error', f"Included file '{arg}' not found.", line).emit()

            return

        # ignore unsupported keywords: ext, if, else, eif

        # simple function call execution: ['name', args] or ['name', arg]
        if isinstance(token, list) and token and isinstance(token[0], str):
            func_name = token[0]
            # find variable by name
            for var in var_list:
                if var.name == func_name:
                    # if it's a CodeBlock (function), run it when interpreting first time
                    try:
                        if isinstance(var.value, CodeBlock) and the_first_time_running:
                            # allow optional args ignored for now
                            var.value.run()
                            return
                    except Exception:
                        pass

                    # support user-defined functions stored as (CodeBlock, arg_names)
                    try:
                        val = var.value
                        if isinstance(val, tuple) and isinstance(val[0], CodeBlock):
                            body_block, arg_names = val
                            # evaluate provided args from token[1] if present
                            provided = []
                            if len(token) > 1 and isinstance(token[1], list):
                                provided = token[1]

                            # create temporary VariableSpace entries for args
                            saved_len = len(var_list)
                            try:
                                for i, name in enumerate(arg_names):
                                    arg_expr = provided[i] if i < len(provided) else NumberType(0)
                                    # tag the expression to get a Type instance
                                    arg_val = tag(arg_expr) if not isinstance(arg_expr, (NumberType, StringType, ListType)) else arg_expr
                                    var_list.append(VariableSpace(name, arg_val))
                                # run function body
                                body_block.run()
                            finally:
                                # remove temporary args
                                while len(var_list) > saved_len:
                                    var_list.pop()
                            return
                    except Exception:
                        pass

    for token in tokens:
        line += 1
        parse_token(token)

    if the_first_time_running:
        cb.run()
    else:
        return cb
        


interpret(tokenize(code_lines), True)