# -*- coding: UTF-8 -*-

import os
import sys
import wcf
from lib.dbg import print_debug as print_debug, set_debug_mode as set_debug_mode

# enable debug temporarily to trace variable binding issues
set_debug_mode(False)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
code_lines = []


# command = sys.argv[1]
# BASE_DIR = os.path.dirname(os.path.abspath(command))

# with open(command, 'r', encoding='utf-8') as f:
#     # remove empty/whitespace-only lines and comment-only lines to avoid spurious tokens
#     code_lines = [l for l in f.read().split('\n') if l.strip() != '' and not l.strip().startswith('#')]

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
    TOK_RE = re.compile(r"\s*(?:(\+=|-=|\*=|/=|->|==|!=|>=|<=|\d+(?:\.\d+)?|//|@?\w+|[:=+\-*/^()\[\]{},.<>!&|])|(\$?'(\\'|[^'])*'))")

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
        t = peek()
        
        # unary minus support: treat leading '-' as 0 - <expr>
        if t == '-':
            consume('-')
            node = parse_primary()
            return maybe_index(['0', '-', node])
        # list literal support: [a, b, 1] or {a, b, 1}
        if t == '[' or t == '{':
            opener = consume()
            closer = ']' if opener == '[' else '}'
            elems = []
            if peek() != closer:
                while peek() != closer:
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
        if isinstance(t, str) and re.match(r"^\$?'", t):
            return maybe_index(consume())
        
        if t and re.match(r"^\d+$", t) or (t and re.match(r"^@?\w+$", t)):
            # identifier or number
            name = consume()
            node = name
            while True:
                if peek() == '.':
                    consume('.')
                    member = consume()
                    node = ['member', node, member]
                    continue
                if peek() == '(':
                    consume('(')
                    args = []
                    if peek() != ')':
                        while peek() != ')':
                            if isinstance(peek(), str) and re.match(r"^@?\w+$", peek()):
                                head = peek()
                                lookahead = tokens[idx + 1] if idx + 1 < len(tokens) else None
                                if lookahead == '=':
                                    consume(head)
                                    consume('=')
                                    args.append(['kwarg', head, parse_compare()])
                                    if peek() == ',':
                                        consume(',')
                                        continue
                                    break
                            args.append(parse_compare())
                            if peek() == ',':
                                consume(',')
                                continue
                            break
                    consume(')')
                    node = ["call", node, args]
                    continue
                break
            return maybe_index(node)
        return maybe_index(consume())

    def parse_power():
        node = parse_primary()
        if peek() == '^':
            consume('^')
            node = [node, '^', parse_power()]
        return node

    def parse_term():
        node = parse_power()
        parts = [node]
        while peek() in ('*', '/', '//'):
            op = consume()
            right = parse_power()
            parts.append(op)
            parts.append(right)
        # fold to right-associative nested binary operations: a*b/c -> [a, '*', [b, '/', c]]
        def fold_ops(p):
            # a op1 b op2 c op3 d → (((a op1 b) op2 c) op3 d)

            if len(p) == 1:
                return p[0]
            res = [p[0], p[1], p[2]]
            pos = 3
            while pos < len(p):
                res = [res, p[pos], p[pos+1]]
                pos +=2
            return res

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
            # a op1 b op2 c op3 d → (((a op1 b) op2 c) op3 d)
        
            if len(p) == 1:
                return p[0]
            res = [p[0], p[1], p[2]]
            pos = 3
            while pos < len(p):
                res = [res, p[pos], p[pos+1]]
                pos +=2
            return res

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
        while peek() in ('==', '!=', '<', '>', '<=', '>=', 'is'):
            op = consume()
            right = parse_bitor()
            parts.append(op)
            parts.append(right)

        def fold_ops(p):
            if len(p) == 1:
                return p[0]
            return [p[0], p[1], fold_ops(p[2:])]

        node = fold_ops(parts)
        if peek() == '->':
            consume('->')
            node = [node, '->', parse_compare()]
        return node

    # special handling: for keywords until ':' pack into list
    # include 'assert' and 'func' and 'return' so assertions like: assert x == 1  -> ['assert', <expr>]
    if tokens and tokens[0] in ('rep', 'if', 'eif', 'else', 'assert', 'while', 'please', 'final', 'func', 'return', 'type'):
        # consume keyword
        kw = tokens[0]
        # build rest until ':'
        # find colon position
        try:
            colon_i = tokens.index(':')
        except ValueError:
            colon_i = len(tokens)

        if kw == 'func':
            raw = line.strip()
            rest = raw[len('func'):].strip()
            stored = False
            if rest.startswith('stored'):
                stored = True
                rest = rest[len('stored'):].strip()

            name_end = rest.find('(')
            if name_end == -1:
                return ['func', [rest.strip(), []], ':']

            func_name = rest[:name_end].strip()
            param_block = rest[name_end + 1:]
            closing = param_block.rfind(')')
            if closing == -1:
                return ['func', [func_name, []], ':']
            param_block = param_block[:closing]

            def split_top_level_commas(s: str):
                items = []
                buf = []
                depth = 0
                in_string = None
                escape = False
                for ch in s:
                    if in_string is not None:
                        buf.append(ch)
                        if escape:
                            escape = False
                        elif ch == '\\':
                            escape = True
                        elif ch == in_string:
                            in_string = None
                        continue
                    if ch in ("'", '"'):
                        in_string = ch
                        buf.append(ch)
                    elif ch in '([{':
                        depth += 1
                        buf.append(ch)
                    elif ch in ')]}':
                        depth = max(0, depth - 1)
                        buf.append(ch)
                    elif ch == ',' and depth == 0:
                        item = ''.join(buf).strip()
                        if item:
                            items.append(item)
                        buf = []
                    else:
                        buf.append(ch)
                tail = ''.join(buf).strip()
                if tail:
                    items.append(tail)
                return items

            def parse_param_text(item: str):
                item = item.strip()
                if not item:
                    return None
                left, default_expr = item, None
                if '=' in item:
                    left, default_expr = item.split('=', 1)
                    default_expr = default_expr.strip()
                left = left.strip()
                if ':' in left:
                    left = left.split(':', 1)[0].strip()
                left = left.strip()
                if left.startswith('@'):
                    left = left[1:]
                if default_expr is None:
                    return left
                return (left, default_expr)

            params = []
            for item in split_top_level_commas(param_block):
                parsed = parse_param_text(item)
                if parsed is not None:
                    params.append(parsed)

            if stored:
                return ['func', ['stored', [func_name, params]], ':']
            return ['func', [func_name, params], ':']

        if kw == 'type':
            return ['type', tokens[1] if len(tokens) > 1 else '', ':']

        # parse middle tokens
        mid_line = ' '.join(tokens[1:colon_i])
        if mid_line:
            # naive: parse mid as expression
            inner = lex(mid_line)
            print_debug("[LEX DEBUG] Keyword:", kw, "Inner tokens:", inner)
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
        if '=' in tokens:
            eq_i = tokens.index('=')
            path = ''.join(tokens[1:eq_i]).strip()
            alias = ''.join(tokens[eq_i + 1:]).strip()
            return ['ext', path, alias]
        if len(tokens) > 1:
            name = ''.join(tokens[1:]).strip()
            return ['ext', name]
        return ['ext']

    # special only directive: `only ...` -> ['only', "..."]
    if tokens and tokens[0] == 'only':
        # preserve rest of line as a single string
        rest = line[len('only'):].strip()
        return ['only', rest]

    # abstract constant definition: `abstract name = expr`
    if tokens and tokens[0] == 'abstract':
        if len(tokens) > 2 and tokens[2] == '=':
            name = tokens[1]
            rhs_tokens = ''.join(tokens[3:])
            rhs = lex(rhs_tokens) if rhs_tokens else []
            return ['abstract', name, '=', rhs]
        return ['abstract']

    # compound assignment special: `a += 1`, `a -= 2`, etc.
    for op in ('+=', '-=', '*=', '/='):
        if op in tokens:
            op_i = tokens.index(op)
            left = ''.join(tokens[:op_i]).strip()
            rhs_tokens = ''.join(tokens[op_i+1:])
            rhs = lex(rhs_tokens) if rhs_tokens else []
            return [left, op, rhs]
    idx = 0
    left_ast = parse_compare()
    # 消耗完左侧后，peek 是否为 =
    if peek() == '=':
        consume('=')
        # 剩下全部作为右侧
        rhs_tokens = tokens[idx:]
        rhs_text = ''.join(rhs_tokens)
        rhs = lex(rhs_text) if rhs_text else []
        # 判断左侧是不是 index 节点
        if isinstance(left_ast, list) and left_ast[0] == "index":
            # 输出 index_assign 语法树
            return ["index_assign", left_ast[1], left_ast[2], rhs]
        if isinstance(left_ast, list) and left_ast[0] == "member":
            return ["member_assign", left_ast, rhs]
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


def _expand_anonymous_functions(code_lines):
    """Expand `func(args)(...)` expressions into named internal functions."""
    import re

    expanded = []
    anonymous_id = 0
    index = 0
    while index < len(code_lines):
        source_line = code_lines[index]
        match = re.search(r"\bfunc\s*(stored\s*)?\(([^()]*)\)\s*\(", source_line)
        if not match:
            expanded.append(source_line)
            index += 1
            continue

        base_indent = len(source_line) - len(source_line.lstrip(' '))
        body_start = index + 1
        body_end = body_start
        while body_end < len(code_lines):
            candidate = code_lines[body_end]
            candidate_indent = len(candidate) - len(candidate.lstrip(' '))
            if candidate.strip().startswith(')') and candidate_indent <= base_indent:
                break
            body_end += 1
        if body_end == len(code_lines):
            expanded.append(source_line)
            index += 1
            continue

        function_name = f'__anonymous_{anonymous_id}'
        anonymous_id += 1
        is_stored = bool(match.group(1))
        params = match.group(2).strip()
        body = code_lines[body_start:body_end]
        # Inside an anonymous function, `.(...)` refers to that function.
        body = [
            re.sub(r"(?<![\w.])\.(?=\s*\()", function_name, body_line)
            for body_line in body
        ]
        prefix = source_line[:match.start()]
        suffix = source_line[match.end():]

        stored_prefix = 'stored ' if is_stored else ''
        expanded.append(' ' * base_indent + f'func {stored_prefix}{function_name}({params}):')
        expanded.extend(body)
        if '=' in prefix and not suffix.strip():
            variable_name = prefix.split('=', 1)[0].strip()
            expanded.append(' ' * base_indent + f'{variable_name} = {function_name}')
        else:
            expanded.append(prefix + function_name + suffix + ')')
        index = body_end + 1

    return expanded


def _merge_continuation_lines(code_lines):
    """Join logical statements split across multiple physical lines.

    Example:
        add(
            1,
            2,
            3 + 4,
            6
        )
    should be treated as one statement, even though it spans several source lines.
    """
    merged = []
    current = ''

    def _is_continuation(line: str) -> bool:
        text = line.rstrip()
        if not text:
            return False

        stripped = text.strip()
        if stripped.endswith(':'):
            # Block headers like `func name():` or `if cond:` are complete
            # statements and must not consume the next indented body line.
            return False
        if stripped.endswith(','):
            return True
        if stripped.endswith(('+', '-', '*', '/', '//', '^', '->', '%', '&', '|', '==', '!=', '<', '>', '<=', '>=', '=', '+=', '-=', '*=', '/=')):
            return True

        stack = []
        in_string = None
        escape = False
        for ch in text:
            if in_string is not None:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == in_string:
                    in_string = None
                continue

            if ch in ("'", '"'):
                in_string = ch
            elif ch in '([{':
                stack.append(ch)
            elif ch in ')]}':
                pair = {'}': '{', ')': '(', ']': '['}
                if stack and stack[-1] == pair[ch]:
                    stack.pop()
                else:
                    stack.append(ch)
        return bool(stack)

    def _needs_arg_separator(line: str) -> bool:
        text = line.rstrip()
        if not text:
            return False
        if text.endswith(('(', '[', '{')):
            return False
        if text.strip().endswith(','):
            return False
        if text.strip().endswith(('+', '-', '*', '/', '//', '^', '->', '%', '&', '|', '==', '!=', '<', '>', '<=', '>=', '=', '+=', '-=', '*=', '/=')):
            return False

        stack = []
        in_string = None
        escape = False
        for ch in text:
            if in_string is not None:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == in_string:
                    in_string = None
                continue

            if ch in ("'", '"'):
                in_string = ch
            elif ch in '([{':
                stack.append(ch)
            elif ch in ')]}':
                pair = {'}': '{', ')': '(', ']': '['}
                if stack and stack[-1] == pair[ch]:
                    stack.pop()
                else:
                    stack.append(ch)
        return bool(stack)

    for raw in code_lines:
        if raw.strip() == '' or raw.lstrip().startswith('#'):
            if current:
                merged.append(current)
                current = ''
            continue
        line = raw.rstrip()
        if not current:
            current = line
            continue
        if _is_continuation(current):
            separator = ', ' if _needs_arg_separator(current) and not line.strip().startswith((')', ']', '}')) else ' '
            current = f'{current}{separator}{line.strip()}'
            continue
        merged.append(current)
        current = line

    if current:
        merged.append(current)

    return merged


def tokenize(code_lines, indent=0):
    if indent == 0:
        code_lines = _merge_continuation_lines(code_lines)
        code_lines = _expand_anonymous_functions(code_lines)
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


from wcf import BinaryOperator as BinaryOperator, BoundMethod as BoundMethod, CodeBlock as CodeBlock, CodeLine as CodeLine, Error as Error, INF as INF, InstanceType as InstanceType, KeywordCodeLine as KeywordCodeLine, MemberAccess as MemberAccess, MemberAssignCodeLine as MemberAssignCodeLine, NumberType as NumberType, Operator as Operator, StringType as StringType, TINY as TINY, Type as Type, TypeDefinition as TypeDefinition, Variable as Variable, VariableDefinitionCodeLine as VariableDefinitionCodeLine, VariableSpace as VariableSpace, ListType as ListType, lib as lib, math as math, sys as sys, var_list as var_list, IndexAssignCodeLine as IndexAssignCodeLine

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
CURRENT_TYPE_DEFINITION = None

_original_keyword_get = KeywordCodeLine.get

def resolve_arg_value(node, local_vars: list | None = None, global_vars: list | None = None):
    if local_vars is None:
        local_vars = []
    if global_vars is None:
        global_vars = var_list

    if isinstance(node, (Variable, BinaryOperator)):
        return node.get(local_vars, global_vars)
    
    if hasattr(node, "get") and isinstance(node, (CodeLine, Type)):
        return node.get(local_vars, global_vars)
    return node


def build_type_from_value(value):
    """Convert a Python primitive or existing Type into a wcf Type instance."""
    # already a Type
    if isinstance(value, Type):
        return value
    if isinstance(value, StringType) or isinstance(value, NumberType) or isinstance(value, ListType):
        return value
    if isinstance(value, str):
        return StringType(value)
    if isinstance(value, (int, float)):
        return NumberType(value)
    if isinstance(value, list):
        elems = []
        for it in value:
            if isinstance(it, Type):
                elems.append(it)
            elif isinstance(it, str):
                elems.append(StringType(it))
            elif isinstance(it, (int, float)):
                elems.append(NumberType(it))
            else:
                elems.append(StringType(str(it)))
        return ListType(elems)
    # fallback: stringify
    return StringType(str(value))

def _wanted_keyword_get_impl(self, local_vars: list, global_vars: list):
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
        path_node = resolve_arg_value(path_arg, local_vars, global_vars)
        path = resolve_arg_value(path_node, local_vars, global_vars)

        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)

        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as ext_file:
                ext_lines = [l for l in ext_file.read().split('\n') if l.strip() != '' and not l.strip().startswith('#')]
            ext_tokens = tokenize(ext_lines)
            ext_cb = interpret(ext_tokens, the_first_time_running=False)
            ext_cb.run(local_vars, global_vars)
            return None

        Error('Ext Error', f"Included file '{path}' not found.", self.line).emit()
        return None

    if self.name == 'abstract':
        if len(self.arg) != 2:
            Error('Const Definition Error', "abstract requires a name and a value.", self.line).emit()
            return None

        var_name = self.arg[0]
        if hasattr(var_name, 'name'):
            var_name = var_name.name
        if not isinstance(var_name, str):
            Error('Const Definition Error', "abstract variable name must be an identifier.", self.line).emit()
            return None

        value_node = self.arg[1]
        value = resolve_arg_value(value_node, local_vars, global_vars)
        value = build_type_from_value(value)

        target_list = local_vars if local_vars else global_vars
        for var in target_list:
            if var.name == var_name:
                Error('Const Definition Error', f"Cannot redefine constant '{var_name}'.", self.line).emit()
                return None

        const_var = VariableSpace(var_name, value)
        try:
            const_var.readonly = True
        except Exception:
            pass
        target_list.append(const_var)
        return resolve_arg_value(value, local_vars, global_vars)

    if self.name == 'getwcore':
        if len(self.arg) != 2:
            cnt = len(self.arg)
            plural = 'was' if cnt < 2 else 'were'
            Error('GetWCore Error', f"2 sub arguments were expected, but {cnt} {plural} given.", self.line).emit()

        subcommand_node = self.arg[0]
        subcontent_node = self.arg[1]

        command = resolve_arg_value(subcommand_node, local_vars, global_vars)
        command = resolve_arg_value(command, local_vars, global_vars)

        if command == 'typename':
            value = resolve_arg_value(subcontent_node, local_vars, global_vars)
            if isinstance(value, InstanceType):
                return StringType(f'<type: {value.definition.name}>')
            if isinstance(value, TypeDefinition):
                return StringType(f'<type: {value.name}>')
            return StringType(f'<type: {type(value).__name__}>')

        # do not cache stdin reads across repeated executions of the same line
        # so each prompt occurs every time the code reaches getwcore 'stdin'.
        match command:
            case 'stdout':
                result = resolve_arg_value(subcontent_node, local_vars, global_vars)
                out_val = resolve_arg_value(result, local_vars, global_vars)

                if globals().get('ONLY_FILTER') is None or str(out_val) == str(globals().get('ONLY_FILTER')):
                    import lib.wcore.wsfilter as ws

                    def format_wcore_output(item):
                        item_val = resolve_arg_value(item, local_vars, global_vars)
                        if isinstance(item_val, InstanceType):
                            text_value = wcf.invoke_magic(item_val, '_to_str', [], local_vars, global_vars)
                            if text_value is not None:
                                return format_wcore_output(text_value)
                        if isinstance(item_val, ListType):
                            inner = [resolve_arg_value(sub_item, local_vars, global_vars) for sub_item in item_val.get()]
                            return '{' + ', '.join(format_wcore_output(sub_item) for sub_item in inner) + '}'
                        if isinstance(item_val, NumberType):
                            return str(ws.wsfilter(str(item_val.get())))
                        if isinstance(item_val, StringType):
                            return "'" + str(ws.wsfilter(str(item_val.get()))) + "'"
                        if isinstance(item_val, (int, float, str)):
                            return str(ws.wsfilter(str(item_val)))
                        return "'" + str(ws.wsfilter(str(item_val))) + "'"

                    if isinstance(out_val, ListType):
                        list_items = [resolve_arg_value(it, local_vars, global_vars) for it in out_val.get()]
                        print('{' + ', '.join(format_wcore_output(item) for item in list_items) + '}', end='')
                    else:
                        print(format_wcore_output(out_val) if out_val is not None else 'Nothing', end='')
                return None

            case 'stdin':
                prompt_raw = resolve_arg_value(subcontent_node, local_vars, global_vars)
                prompt = resolve_arg_value(prompt_raw, local_vars, global_vars)
                result = StringType(input(prompt))
                return result

    if self.name == 'return':
        print_debug('[RETURN CALLED]')
        return_value = NumberType(0)
        if self.arg:
            return_value = resolve_arg_value(self.arg[0], local_vars, global_vars)
        raise wcf.ReturnException(return_value)

    return _original_keyword_get(self, local_vars, global_vars)


# 包装层：适配统一get接口，接收 self + local_vars + global_vars
def _keyword_code_line_get(self, local_vars: list | None = None, global_vars: list | None = None):
    if local_vars is None:
        local_vars = []
    if global_vars is None:
        global_vars = var_list
    return _wanted_keyword_get_impl(self, local_vars, global_vars)


KeywordCodeLine.get = _keyword_code_line_get

_original_function_call_get = wcf.FunctionCall.get

def _wanted_function_call_get(self, *args, **kwargs):
    try:
        return _original_function_call_get(self, *args, **kwargs)
    except wcf.ReturnException as e:
        return e.value

wcf.FunctionCall.get = _wanted_function_call_get

_original_variable_definition_get = VariableDefinitionCodeLine.get

def _wanted_variable_definition_get(self, local_vars: list | None = None, global_vars: list | None = None):
    if local_vars is None:
        local_vars = []
    if global_vars is None:
        global_vars = var_list

    t = self.arg[0]
    # 改用 resolve_arg_value 做求值，自动透传上下文，不要再手写while+t.get()
    t = resolve_arg_value(t, local_vars, global_vars)

    if isinstance(t, str):
        t = StringType(t)
    elif isinstance(t, (int, float)):
        t = NumberType(t)
    elif isinstance(t, list):
        t = ListType([
            StringType(str(item))
            if not isinstance(item, (NumberType, StringType, ListType, Type))
            else item
            for item in t
        ])

   
    target_list = local_vars if local_vars else global_vars

    for var in target_list:
        if var.name == self.name:
            if getattr(var, 'readonly', False):
                Error('Const Assignment Error', f"Cannot assign to constant '{self.name}'.", self.line).emit()
                return None
            var.value = t
            return resolve_arg_value(t, local_vars, global_vars)

    target_list.append(VariableSpace(self.name, t))
    return resolve_arg_value(t, local_vars, global_vars)

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
            self.name = 'index'

        def get(self, local_vars, global_vars):
            def resolve_value(value):
                # unwrap any nested wrapper objects to get the underlying value
                while hasattr(value, 'get') and not isinstance(value, (NumberType, StringType, ListType)):
                    value = value.get(local_vars, global_vars)
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

    class InterpolatedString(StringType):
        def __init__(self, parts):
            super().__init__('')
            self.parts = parts

        def get(self, local_vars=None, global_vars=None):
            result = []
            for part in self.parts:
                if isinstance(part, str):
                    result.append(part)
                    continue
                value = part
                while hasattr(value, 'get') and not isinstance(value, (NumberType, StringType, ListType, InstanceType, TypeDefinition)):
                    value = value.get(local_vars, global_vars)
                if isinstance(value, InstanceType):
                    converted = wcf.invoke_magic(value, '_to_str', [], local_vars, global_vars)
                    value = converted if converted is not None else value
                if isinstance(value, (NumberType, StringType)):
                    value = value.get(local_vars, global_vars)
                result.append(str(value))
            return ''.join(result)

        def __repr__(self):
            return repr(self.get())
    
    def tag(name):
        # print(name)
        def resolve_binary_operand(node):
            # if hasattr(node, 'get'):
            #     try:
            #         return node.get()
            #     except Exception as e:
            #         print('[BINOPR ERROR] Failed to resolve binary operand:', e)
            #         return node
            return node

        if isinstance(name, list):
            # handle index literal first: ['index', base, idx]
            if name and name[0] == 'index' and len(name) == 3:
                return IndexType(tag(name[1]), tag(name[2]))

            # list literal: ['list', elems]
            if name and name[0] == 'list' and len(name) > 1:
                elems = name[1]
                return ListType([tag(el) for el in elems])

            if len(name) == 3 and name[0] == 'member':
                return MemberAccess(tag(name[1]), name[2], line)

            # getwcore keyword (special form)
            if name and name[0] == 'getwcore' and len(name) == 2:
                arg = name[1]
                if isinstance(arg, list) and len(arg) == 2:
                    return KeywordCodeLine('getwcore', [tag(arg[0]), tag(arg[1])], line)

            if len(name) == 3 and name[0] == 'call' and isinstance(name[2], list):
                return wcf.FunctionCall(
                    tag(name[1]),
                    [tag(arg) for arg in name[2]],
                    line,
                )

            if len(name) == 3 and name[0] == 'kwarg':
                return ['kwarg', name[1], name[2]]

            # handle binary operators including arithmetic, comparison and bit ops
            if len(name) == 3 and isinstance(name[1], str) and name[1] in ['+', '-', '*', '/', '//', '^', '->', 'is', '==', '!=', '<', '>', '<=', '>=', '&', '|']:
                return BinaryOperator(name[1], resolve_binary_operand(tag(name[0])), resolve_binary_operand(tag(name[2])))

            # function call pattern: ['fname', [arg1, arg2]] (after keywords/ops)
            if len(name) == 2 and isinstance(name[0], str) and isinstance(name[1], list):
                args_list = [tag(a) for a in name[1]]
                return wcf.FunctionCall(name[0], args_list, line)

            if len(name) == 1:
                return tag(name[0])
            return tag(name[0])
        try:
            float(name)
            return NumberType(int(float(name)) if int(float(name)) == float(name) else float(name))
        except Exception:
            if isinstance(name, str):
                if name.startswith("$'") and name.endswith("'"):
                    content = name[2:-1]
                    parts = []
                    cursor = 0
                    while cursor < len(content):
                        start = content.find('{', cursor)
                        if start < 0:
                            parts.append(content[cursor:])
                            break
                        if start > cursor:
                            parts.append(content[cursor:start])
                        end = content.find('}', start + 1)
                        if end < 0:
                            raise SyntaxError('Unclosed interpolation expression.')
                        parts.append(tag(lex(content[start + 1:end])))
                        cursor = end + 1
                    return InterpolatedString(parts)
                if name.startswith("'") and name.endswith("'"):
                    return StringType(name[1:-1])
                lower_name = name.lower()
                if lower_name == 'true':
                    return NumberType(1)
                if lower_name == 'false':
                    return NumberType(0)
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

        # return directive: function return value
        if token and token[0] == 'return':
            arg = token[1] if len(token) > 1 else NumberType(0)
            cb.code_lines.append(KeywordCodeLine('return', [tag(arg)], line))
            return

        # nested block, e.g. ['rep', ['num', '+', '1'], ':'] with child body
        if token and isinstance(token[0], list):
            header = token[0]
            body = token[1] if len(token) > 1 else []
                # support rep and conditional blocks: if / eif / else / please
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

                if kw == 'please':
                    body_block = interpret(body, the_first_time_running=False)
                    cb.code_lines.append(KeywordCodeLine('please', [body_block], line))
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
                        prev_please = None
                        for prev in reversed(cb.code_lines):
                            if isinstance(prev, KeywordCodeLine) and prev.name == 'please':
                                prev_please = prev
                                break
                        if prev_please:
                            prev_please.arg.append(body_block)
                        else:
                            cb.code_lines.append(KeywordCodeLine('final', [body_block], line))
                    return
                # token 形如 ["ret", expr_ast]
                
                # function definition: func name(args):
                if kw == 'func':
                    name_part = header[1] if len(header) > 1 else None
                    func_name = None
                    func_args = []
                    print_debug(f"[FUNC_HEADER_RAW] header = {header}")
                    print_debug(f"[FUNC_HEADER_RAW] name_part = {name_part}")

                    def _extract_func_header(node):
                        is_stored = False
                        if isinstance(node, list):
                            if len(node) >= 2 and node[0] == 'stored':
                                is_stored = True
                                sub_stored, real_name, real_args = _extract_func_header(node[1])
                                return (True, real_name, real_args)

                            if len(node) >= 2 and isinstance(node[0], str) and isinstance(node[1], list):
                                func_name = node[0]
                                arg_part = node[1]
                                func_args = []
                                for item in arg_part:
                                    if isinstance(item, tuple) and len(item) == 2:
                                        raw_name, default_text = item
                                        func_args.append((raw_name, tag(lex(default_text))))
                                    elif isinstance(item, list) and len(item) == 2 and isinstance(item[0], str):
                                        raw_name, default_text = item
                                        func_args.append((raw_name, tag(lex(default_text))))
                                    elif isinstance(item, str):
                                        func_args.append(item)
                                    elif hasattr(item, 'name'):
                                        func_args.append(item.name)
                                    else:
                                        raise TypeError(f"Function parameters must be strings. Now is {type(item)}")
                                return (is_stored, func_name, func_args)

                            if len(node) >= 1 and isinstance(node[0], str):
                                func_name = node[0]
                                func_args = []
                                if len(node) > 1:
                                    arg_part = node[1]
                                    if isinstance(arg_part, list):
                                        for item in arg_part:
                                            if isinstance(item, tuple) and len(item) == 2:
                                                raw_name, default_text = item
                                                func_args.append((raw_name, tag(lex(default_text))))
                                            elif isinstance(item, list) and len(item) == 2 and isinstance(item[0], str):
                                                raw_name, default_text = item
                                                func_args.append((raw_name, tag(lex(default_text))))
                                            elif isinstance(item, str):
                                                func_args.append(item)
                                            elif hasattr(item, 'name'):
                                                func_args.append(item.name)
                                            else:
                                                raise TypeError(f"Function parameters must be strings. Now is {type(item)}")
                                    elif isinstance(arg_part, str):
                                        func_args = [arg_part]
                                    elif hasattr(arg_part, 'name'):
                                        func_args = [arg_part.name]
                                return (is_stored, func_name, func_args)

                        if isinstance(node, str):
                            return (is_stored, node, [])
                        if hasattr(node, 'name'):
                            return (is_stored, node.name, [])

                        return (is_stored, "", [])

                    is_stored_func, func_name, func_args = _extract_func_header(name_part)

                    body_block = interpret(body, the_first_time_running=False)
                    if func_name:
                        print_debug(f"[FUNC_DEF_STORE] func={func_name}, args={func_args}")
                        function_value = (is_stored_func, body_block, func_args)
                        if CURRENT_TYPE_DEFINITION is not None:
                            CURRENT_TYPE_DEFINITION.methods[func_name] = function_value
                        else:
                            var_list.append(VariableSpace(func_name, function_value))
                    return

                if kw == 'type':
                    type_name = header[1] if len(header) > 1 else ''
                    definition = TypeDefinition(type_name)
                    previous_type = globals().get('CURRENT_TYPE_DEFINITION')
                    globals()['CURRENT_TYPE_DEFINITION'] = definition
                    interpret(body, the_first_time_running=False)
                    globals()['CURRENT_TYPE_DEFINITION'] = previous_type
                    var_list[:] = [item for item in var_list if item.name != type_name]
                    var_list.append(VariableSpace(type_name, definition))
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
                            prev_please = None
                            for prev in reversed(cb.code_lines):
                                if isinstance(prev, KeywordCodeLine) and prev.name == 'please':
                                    prev_please = prev
                                    break
                            if prev_please:
                                prev_please.arg.append(body_block)
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

        if len(token) == 4 and token[0] == 'abstract' and token[2] == '=':
            var_def = VariableDefinitionCodeLine(token[1], [tag(token[3])], line)
            setattr(var_def, 'is_const', True)
            cb.code_lines.append(var_def)
            return

        if len(token) == 3 and token[1] in ('+=', '-=', '*=', '/='):
            op_map = {'+=': '+', '-=': '-', '*=': '*', '/=': '/'}
            op = op_map[token[1]]
            cb.code_lines.append(VariableDefinitionCodeLine(token[0], [BinaryOperator(op, Variable(token[0]), tag(token[2]))], line))
            return

        if len(token) == 3 and token[1] == '=':
            left = tag(token[0])
            if isinstance(left, MemberAccess):
                cb.code_lines.append(MemberAssignCodeLine(left, tag(token[2]), line))
                return
            cb.code_lines.append(VariableDefinitionCodeLine(token[0], [tag(token[2])], line))
            return
        elif token[0] == "index_assign":
            base = tag(token[1])
            idx_expr = tag(token[2])
            rhs = tag(token[3])
      
            line_obj = IndexAssignCodeLine(base, idx_expr, rhs)
            cb.code_lines.append(line_obj)
            return

        if token[0] == 'member_assign' and len(token) == 3:
            cb.code_lines.append(MemberAssignCodeLine(tag(token[1]), tag(token[2]), line))
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
                    alias = token[2] if len(token) > 2 else os.path.splitext(os.path.basename(path))[0]
                    before_ids = {id(item) for item in var_list}
                    with open(path, 'r', encoding='utf-8') as ext_file:
                        ext_lines = [l for l in ext_file.read().split('\n') if l.strip() != '' and not l.strip().startswith('#')]
                    # print(ext_lines, path)
                    ext_tokens = tokenize(ext_lines)
                    ext_cb = interpret(ext_tokens, the_first_time_running=False)
                    imported = [item for item in var_list if id(item) not in before_ids]
                    methods = {
                        item.name: item.value
                        for item in imported
                        if (isinstance(item.value, tuple) and len(item.value) == 3)
                        or isinstance(item.value, TypeDefinition)
                    }
                    if len(token) > 2 and alias == 'nothing':
                        # `nothing` means import members into the current scope.
                        return
                    var_list.append(VariableSpace(alias, TypeDefinition(alias, methods, is_library=True)))
                else:
                    Error('Ext Error', f"Included file '{arg}' not found.", line).emit()

            return

        if token[0] == 'call' and len(token) == 3:
            cb.code_lines.append(tag(token))
            return


        # simple function call: ['name', [arg1, arg2]]
        if isinstance(token, list) and token and isinstance(token[0], str):
            func_name = token[0]
            arg_tokens = token[1] if (len(token)>1 and isinstance(token[1],list)) else []
            # build AST args
            ast_args = []
            for item in arg_tokens:
                ast_args.append(tag(item))
            # 只生成FunctionCall AST节点，加入code_lines，仅此而已！
            cb.code_lines.append(wcf.FunctionCall(func_name, ast_args, line))
            return
                 

    for token in tokens:
        line += 1
        parse_token(token)

    if the_first_time_running:
        print_debug("====TOP CODEBLOCK====")
        for idx, line in enumerate(cb.code_lines):
            print_debug(idx, type(line).__name__, repr(line))
        print_debug("======================")
        cb.run(local_vars=[], global_vars=var_list)
        for instance in list(wcf._instances):
            destructor = instance.definition.methods.get('_die')
            if destructor is not None:
                BoundMethod(instance, '_die', destructor).call([], [], var_list)
    else:
        return cb
        




if __name__ == "__main__":
    command = sys.argv[1]
    BASE_DIR = os.path.dirname(os.path.abspath(command))
    with open(command, 'r', encoding='utf-8') as f:
        code_lines = [l for l in f.read().split('\n') if l.strip() != '' and not l.strip().startswith('#')]

    from wcf import CACHE_FILE
    import pickle
    from wcf import function_call_cache, function_call_disk_cache
    import time

    start_ms = time.perf_counter()

    # your interpreter work
    try:
        interpret(tokenize(code_lines), True)
    except wcf.WantedError as error:
        print('Error in Wanted File occured')
        print(f'Location: in file <default>[{error.line}]')
        print(f'{error.attr}: {error.des}')
        sys.exit(1)

    end_ms = time.perf_counter()
    elapsed_ms = (end_ms - start_ms) * 1000

    from wcf import TIME_REC_ACTIVATE
    if TIME_REC_ACTIVATE: print(f"Program running time: {elapsed_ms:.2f} ms")

    # 1. clear in‑memory caches FIRST
    function_call_cache.clear()
    function_call_disk_cache.clear()

    # 2. write empty to disk
    try:
        with open(CACHE_FILE, 'wb') as _cf:
            pickle.dump({}, _cf)
        # print("Disk cache cleared after interpret")
    except Exception as e:
        pass


