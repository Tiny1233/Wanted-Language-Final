# -*- coding: UTF-8 -*-

###
# This file is about transfer built-in classes to final results.
# It can also be used for Wanted Compiled Classes (*.wcc) loadout
# Default, it is the medium for Wanted File (*.wcn)'s final interpreting
# 2026.07.06
###

import math
import sys
import os
import json
import pickle
import atexit
import lib.wcore.dec
from lib.dbg import print_debug as print_debug, set_debug_mode as set_debug_mode

false = False
true = True

INF = math.inf
TINY = 0.000000000000001
TIME_REC_ACTIVATE = False



class Error:
    def __init__(self, attr: str, des: str, line: int = 0, content: str = '', filename: str = '<default>'):
        self.attr = attr
        self.des = des
        self.line = line
        self.content = content
        self.filename = filename

    def emit(self):
        RED = '\033[31m'
        BLUE = '\033[34m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
        print(RED + 'Error in Wanted File occured' + RESET)
        print(RED + f'Location: in file {self.filename}[{self.line}]' + RESET)
        print(BLUE   + f'{self.content}' + RESET)
        print(RED + BOLD + f'{self.attr}: ' + RESET + RED + f'{self.des}' + RESET)
        sys.exit(1)


class BreakLoop(Exception):
    """Internal exception used to implement break keyword."""
    pass

class ReturnException(BaseException):
    def __init__(self, value):
        self.value = value
        super().__init__()

class CodeLine:
    def __init__(self, name: str, line: int = 0):
        self.name = name
        self.line = line

    def get(self, local_vars:list, global_vars:list):
        return NotImplemented

    def __repr__(self):
        return '<CodeLine {}>'.format(self.name)

class KeywordCodeLine(CodeLine):
    def __init__(self, name: str, arg: list, line: int = 0):
        super().__init__(name)
        self.arg = arg
        self.line = line
     

    def get(self, local_vars: list | None = None, global_vars: list | None = None):
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list
        # print('[KW NAME]' + self.name)
        match self.name:
            case 'getwcore':
                if len(self.arg) != 2:
                    Error('GetWCore Error', f'2 sub arguments were expected, but {len(self.arg)} {'was' if len(self.arg) < 2 else 'were'} given.', self.line).emit()

                subcommand: Type = self.arg[0]
                subcontent: Type = self.arg[1]
                from lib.wcore.wsfilter import wsfilter
                match subcommand.get():
                    case 'stdout':
                        result = subcontent.get(local_vars, global_vars)
                        if isinstance(result, (StringType, NumberType)):
                            print(wsfilter(result.get(local_vars, global_vars)), end='')
                        elif isinstance(result, ListType):
                            print(', '.join([str(wsfilter(i.get(local_vars, global_vars))) for i in result.get(local_vars, global_vars)]), end='')
                        return result
                    case 'wdbg':
                        # activate debugmode?
                        val = subcontent.get(local_vars, global_vars)
                        
                        if val:
                            set_debug_mode(True)
                        else:
                            set_debug_mode(False)
                        return NumberType(1) if val else NumberType(1)


                    case 'rt':
                        global TIME_REC_ACTIVATE 
                        val = subcontent.get(local_vars, global_vars)

                        if val:
                            TIME_REC_ACTIVATE = True
                        else:
                            TIME_REC_ACTIVATE = False


                        return NumberType(TIME_REC_ACTIVATE)



                    
                    case 'stdin':
                        prompt = subcontent.get(local_vars, global_vars)
                        print(prompt)
                        
                        if isinstance(prompt, (StringType, NumberType)):
                            prompt = prompt.get(local_vars, global_vars)
                        return StringType(input(prompt))
            
            case 'rep':
                if len(self.arg) not in [2, 3]:
                    Error('SyntaxError', f'Repeat body and times were expected, but {len(self.arg)} {'was' if len(self.arg) < 2 else 'were'} given.', self.line).emit()
                final_block = self.arg[2] if len(self.arg) == 3 else None
                reptime = self.arg[0]
                while not isinstance(reptime, (StringType, NumberType)):
                    reptime = reptime.get(local_vars, global_vars)
                repbody = self.arg[1]

                if not isinstance(reptime, NumberType):
                    Error('SyntaxError', 'The condition was expected to be a real number.', self.line)
                if not isinstance(repbody, CodeBlock):
                    Error('InitialDebugError', 'WCB was expected.')
                # Runtime error
                if math.isinf(reptime.get(local_vars, global_vars)) or abs(int(reptime.get(local_vars, global_vars))) if math.isinf(reptime.get(local_vars, global_vars)) else 16777217 > 16777216:
                    Error('PerformanceError', 'Repeation times out of expectation, maximum 16777216.')
                broken = False
                for ct in range(abs(int(reptime.get(local_vars, global_vars)))):
                    try:
                        repbody.run(local_vars=local_vars, global_vars=global_vars)
                    except BreakLoop:
                        broken = True
                        break
                if final_block is not None and not broken:
                    final_block.run(local_vars=local_vars, global_vars=global_vars)
                
                return
            
            case 'if':
                print_debug(f'[IFCL] local_vars: {[(v.name, v.value) for v in local_vars]}')
                if len(self.arg) < 2:
                    Error('SyntaxError', 'If statement expected condition and body.', self.line).emit()

                condition = self.arg[0]
                then_block = self.arg[1]
                

                if not isinstance(then_block, CodeBlock):
                    Error('TypeError', 'If branch must be a code block.', self.line).emit()

                while not isinstance(condition, (StringType, NumberType)):
                    condition = condition.get(local_vars, global_vars)

                if not isinstance(condition, (StringType, NumberType)):
                    Error('TypeError', 'Condition must evaluate to a number or string.', self.line).emit()

                def _is_true(value):
                    if isinstance(value, NumberType):
                        return value.get(local_vars, global_vars) != 0
                    if isinstance(value, StringType):
                        return value.get(local_vars, global_vars) != ''
                    return bool(value)
           
                if _is_true(condition):
                    then_block.run(local_vars=local_vars, global_vars=global_vars)
                    return

                for branch in self.arg[2:]:
                    if isinstance(branch, CodeBlock):
                        branch.run(local_vars=local_vars, global_vars=global_vars)
                        return
                    if not isinstance(branch, KeywordCodeLine):
                        Error('SyntaxError', 'Invalid branch in if statement.', self.line).emit()
             
                    if branch.name == 'eif':
                        if len(branch.arg) != 2:
                            Error('SyntaxError', 'Eif statement expected condition and body.', self.line).emit()
                        elif_condition = branch.arg[0]
                        elif_block = branch.arg[1]
                        if not isinstance(elif_block, CodeBlock):
                            Error('TypeError', 'Eif branch must be a code block.', self.line).emit()
                        while not isinstance(elif_condition, (StringType, NumberType)):
                            elif_condition = elif_condition.get(local_vars, global_vars)
                        if not isinstance(elif_condition, (StringType, NumberType)):
                            Error('TypeError', 'Eif condition must evaluate to a number or string.', self.line).emit()
                        if _is_true(elif_condition):
                            elif_block.run(local_vars=local_vars, global_vars=global_vars)
                            return
                        continue

                    if branch.name == 'else':
                        if len(branch.arg) != 1:
                            Error('SyntaxError', 'Else statement expected a single body.', self.line).emit()
                        else_block = branch.arg[0]
                        if not isinstance(else_block, CodeBlock):
                            Error('TypeError', 'Else branch must be a code block.', self.line).emit()
                        else_block.run(local_vars=local_vars, global_vars=global_vars)
                        return

                    Error('SyntaxError', 'Invalid branch in if statement.', self.line).emit()

            case 'while':
                if len(self.arg) < 2 or len(self.arg) > 3:
                    Error('SyntaxError', 'While statement expected condition and body, optional else body.', self.line).emit()

                condition = self.arg[0]
                while_body = self.arg[1]
                else_body = self.arg[2] if len(self.arg) == 3 else None

                if not isinstance(while_body, CodeBlock):
                    Error('TypeError', 'While body must be a code block.', self.line).emit()
                if else_body is not None and not isinstance(else_body, CodeBlock):
                    Error('TypeError', 'While else branch must be a code block.', self.line).emit()

                def _is_true(value):
                    if isinstance(value, NumberType):
                        return value.get(local_vars, global_vars) != 0
                    if isinstance(value, StringType):
                        return value.get(local_vars, global_vars) != ''
                    return bool(value)

                def _eval_condition():
                    cond = condition
                    while not isinstance(cond, (StringType, NumberType)):
                        cond = cond.get(local_vars, global_vars)
                    if not isinstance(cond, (StringType, NumberType)):
                        Error('TypeError', 'While condition must evaluate to a number or string.', self.line).emit()
                    return cond

                broken = False
                while _is_true(_eval_condition()):
                    try:
                        while_body.run(local_vars=local_vars, global_vars=global_vars)
                    except BreakLoop:
                        broken = True
                        break
                if else_body is not None and not broken:
                    else_body.run(local_vars=local_vars, global_vars=global_vars)
                return

            case 'ext':
                if len(self.arg) != 1:
                    Error('SyntaxError', 'A filename was expected.', self.line).emit()

                fn = self.arg[0]
                if not isinstance(fn, str):
                    Error('TypeError', 'Filename must be a string.', self.line).emit()

                if fn.startswith('@'):
                    import os
                    fn = fn.lstrip('@')
                    base_dir = os.path.join(os.path.dirname(__file__), 'lib', 'interior')
                    path = os.path.join(base_dir, fn)
                else:
                    path = fn

                try:
                    if path.endswith('.wcn'):
                        import os, runpy, sys
                        wanted_script = os.path.join(os.path.dirname(__file__), 'wanted.py')
                        old_argv = sys.argv
                        sys.argv = [wanted_script, path]
                        runpy.run_path(wanted_script, run_name='__main__')
                        sys.argv = old_argv
                    else:
                        import runpy
                        runpy.run_path(path, run_name='__main__')
                except FileNotFoundError:
                    Error('FileNotFoundError', f'Included file {fn} not found.', self.line).emit()
                    return
                return

            case 'assert':
      
                # assert <condition> [<message>]
                if len(self.arg) < 1 or len(self.arg) > 2:
                    Error('SyntaxError', 'Assert expected one condition and optional message.', self.line).emit()

                condition = self.arg[0]
                message = None
                if len(self.arg) == 2:
                    message = self.arg[1]

                while not isinstance(condition, (StringType, NumberType)):
                    condition = condition.get(local_vars, global_vars)

                if not isinstance(condition, (StringType, NumberType)):
                    Error('TypeError', 'Assert condition must evaluate to a number or string.', self.line).emit()

                cond_true = False
                if isinstance(condition, NumberType):
                    cond_true = condition.get(local_vars, global_vars) != 0
                elif isinstance(condition, StringType):
                    cond_true = condition.get(local_vars, global_vars) != ''

                if not cond_true:
                    msg_text = ''
                    if message is not None:
                        while not isinstance(message, (StringType, NumberType)):
                            message = message.get(local_vars, global_vars)
                        msg_text = str(message.get(local_vars, global_vars)) if isinstance(message, (StringType, NumberType)) else repr(message)
                    Error('AssertionError', msg_text or 'Assertion failed.', self.line).emit()
                return

            case 'return':
                # green output return called
                # print('[RETURN] return called with args:', self.arg)
                # return <value>
                if len(self.arg) == 0:
                    raise ReturnException(NumberType(0))
                if len(self.arg) != 1:
                    Error('SyntaxError', 'Return expected zero or one expression.', self.line).emit()
                val = self.arg[0]
                while not isinstance(val, (StringType, NumberType, ListType)):
                    val = val.get(local_vars, global_vars)
                raise ReturnException(val)

            case 'func':
                # func <name>(params): <body>
                if len(self.arg) != 3:
                    Error('SyntaxError', 'Function definition expected name, params and body.', self.line).emit()
                fname = self.arg[0]
                params = self.arg[1]
                body = self.arg[2]

                # resolve function name
                if isinstance(fname, StringType):
                    fname_str = fname.get(local_vars, global_vars)
                elif isinstance(fname, Variable):
                    fname_str = fname.name
                else:
                    Error('TypeError', 'Function name must be a string or variable.', self.line).emit()

                # params should be a ListType of StringType, raw strings, or variable-like nodes
                param_names = []
                def _normalize_param_item(p):
                    if isinstance(p, StringType):
                        return p.get(local_vars, global_vars)
                    if isinstance(p, str):
                        return p
                    if isinstance(p, Variable):
                        return p.name
                    if isinstance(p, VariableDefinitionCodeLine):
                        return p.name
                    if isinstance(p, KeywordCodeLine):
                        return p.name
                    Error('TypeError', 'Function parameters must be strings.', self.line).emit()

                if isinstance(params, ListType):
                    raw_params = params.get(local_vars, global_vars)
                elif isinstance(params, (list, tuple)):
                    raw_params = params
                elif isinstance(params, (StringType, str, Variable, VariableDefinitionCodeLine, KeywordCodeLine)):
                    raw_params = [params]
                else:
                    Error('TypeError', 'Function parameters must be a list.', self.line).emit()

                for p in raw_params:
                    param_names.append(_normalize_param_item(p))

                if not isinstance(body, CodeBlock):
                    Error('TypeError', 'Function body must be a code block.', self.line).emit()

                # define function type
                class FunctionType(Type):
                    def __init__(self, name, params, body):
                        super().__init__(None, name)
                        self.params = params
                        self.body = body

                    def get(self, args:list):
                        # bind params as local variables
                        if len(args) != len(self.params):
                            Error('TypeError', f'Function {self.name} expected {len(self.params)} arguments, got {len(args)}.').emit()
                        # push params to var_list
                        added = []
                        for pname, aval in zip(self.params, args):
                            # ensure aval is a Type
                            v = aval
                            while not isinstance(v, (StringType, NumberType, ListType)):
                                v = v.get(local_vars, global_vars)
                            var = VariableSpace(pname, v)
                            var_list.append(var)
                            added.append(var)
                        # run body and capture return
                        try:
                            self.body.run()
                            ret = NumberType(0)
                        except ReturnException as re:
                            ret = re.value
                        # remove added params
                        for a in added:
                            try:
                                var_list.remove(a)
                            except ValueError:
                                pass
                        return ret

                # store function in variable list
                func_obj = FunctionType(fname_str, param_names, body)
                # remove existing var if exists
                for vs in var_list:
                    if vs.name == fname_str:
                        vs.value = func_obj
                        break
                else:
                    var_list.append(VariableSpace(fname_str, func_obj))
                return

    def __repr__(self):
        return '<KeywordCodeLine {}>'.format(self.name)

class CodeBlock:
    def __init__(self, code_lines:list):
        self.code_lines = code_lines

    # def run(self, local_vars: list, global_vars: list):
    def run(self, local_vars: list | None = None, global_vars: list | None = None):
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list

        print_debug('[CodeBlock] Variable list of names: ')
        print_debug('[CodeBlock] local vars: ', [(v.name, v.value) for v in local_vars])
        print_debug('[CodeBlock] global vars: ', [(v.name, v.value) for v in global_vars])

        for i in range(len(self.code_lines)):
            self.code_lines[i].get(local_vars, global_vars)

class Type:
    def __init__(self, value: any, name: str = '', line: int = 0):
        self.name = name
        self.value = value
        self.line = line

    def get(self, local_vars:list, global_vars:list):
        return NotImplemented

    def __repr__(self):
        return '<Type {}>'.format(self.name)

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if isinstance(other, Type):
            return self.get(local_vars=None, global_vars=None) == other.get(local_vars=None, global_vars=None)
        return self.get(local_vars=None, global_vars=None) == other

    def __ne__(self, other):
        return not self.__eq__(other)
    

class StringType(Type):
    def __init__(self, value: str, name: str = '', line: int = 0):
        """
        @brief Represents a string type in the Wanted language.

        @param value: The string value.
        @param name: Optional name for the string type.
        @param line: Optional line number for error reporting.
        @return: None
        """
        super().__init__(value, name, line)

    def get(self, local_vars=None, global_vars=None):
        return self.value
    
    def __repr__(self):
        return f"'{self.value}'"
    def get_index(self, ind: NumberType):
        while not isinstance(ind, (StringType, NumberType)):
            ind = ind.get(local_vars=None, global_vars=None)
        return StringType(self.get(local_vars=None, global_vars=None)[ind.get(local_vars=None, global_vars=None)])
    
    

class NumberType(Type):
    def __init__(self, value: float | int, name: str = '', line: int = 0):
        super().__init__(value, name, line)

    def get(self, local_vars=None, global_vars=None):
        return self.value
    
    def __repr__(self):
        return str(self.value)
    
    # Numeric/string/list operator implementations moved to BinaryOperator


class ListType(Type):
    def __init__(self, value: list, name: str = '', line: int = 0):
        super().__init__(value, name, line)
        # normalize elements to Type instances
        normalized = []
        for v in (value or []):
            if isinstance(v, (StringType, NumberType, ListType)):
                normalized.append(v)
            elif isinstance(v, list):
                normalized.append(ListType(v))
            elif isinstance(v, (int, float)):
                normalized.append(NumberType(v))
            elif isinstance(v, str):
                normalized.append(StringType(v))
            else:
                normalized.append(v)
        self.value = normalized

    def get(self, local_vars=None, global_vars=None):
        return self.value

    def __add__(self, other):
        # kept minimal: behavior moved to BinaryOperator
        if isinstance(other, ListType):
            return ListType(self.get(local_vars=None, global_vars=None) + other.get(local_vars=None, global_vars=None))
        return ListType(self.get(local_vars=None, global_vars=None) + [other])

    def __repr__(self):
        return '{' + ', '.join(repr(x) for x in self.value) + '}'
    
    def get_index(self, ind: NumberType):
        while not isinstance(ind, (StringType, NumberType)):
            ind = ind.get(local_vars=None, global_vars=None)

        return self.get(local_vars=None, global_vars=None)[ind.get(local_vars=None, global_vars=None)]
class VariableSpace: # Won't be declared in Wanted Codes
    def __init__(self, var_name: str, value: Type, is_const: bool = False):
        self.name = var_name
        self.value = value
        self.is_const = is_const

    def get(self, local_vars=None, global_vars=None):
        return self.value

class VariableDefinitionCodeLine(CodeLine):
    def __init__(self, var_name: str, arg: list[Type], line: int = 0, is_const: bool = False):
        print_debug(f'[VAR_DEF] {var_name} = {arg}')
        self.name = var_name
        self.arg = arg
        self.line = line
        self.is_const = is_const

    def get(self, local_vars: list | None = None, global_vars: list | None = None):
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list

        flag = True
        t = self.arg[0]
        # 这里！不要 t.get()，要把上下文传下去
        while not isinstance(t, (NumberType, StringType)):
            print_debug(F'[TYPE OF T:{self.var_name}] ', type(t))
            t = t.get(local_vars, global_vars)

        # 顶层脚本赋值写 global_vars；函数内部赋值写 local_vars
        target_list = local_vars if local_vars else global_vars

        for var in target_list:
            if var.name == self.name:
                if var.is_const:
                    Error('TypeError', f'Cannot reassign to readonly variable {self.name}.', self.line).emit()
                var.value = t
                flag = False
                break
        if flag:
            target_list.append(VariableSpace(self.name, t, self.is_const))
        return t

    # 修复：__repr__禁止调用get()，只打印静态信息，不执行业务逻辑
    def __repr__(self):
        return f"<VariableDefinitionCodeLine name={self.name!r}>"
    
class Variable(Type):
    def __init__(self, name, line:int=0):
        super().__init__(None, name)
        self.name = name
        self.line = line

    # 不要 def get(self, local_vars:list, global_vars:list):
# 改成带兜底，防止外部误传None（但是业务执行链路一定传真实list）
    def get(self, local_vars: list | None = None, global_vars: list | None = None):
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list
        print_debug('[VAR CALL]Variable get() called for variable name:', self.name)
        lv = [(v.name, v.value) for v in local_vars]
        print_debug(f'[VAR CALL {self.name}] local_vars name&value: {lv}')
        gv = [(v.name, v.value) for v in global_vars]
        print_debug(f'[VAR CALL {self.name}] global_vars name&value: {gv}')

        for vs in reversed(local_vars):
            if vs.name == self.name:
                return vs.value
        for vs in reversed(global_vars):
            if vs.name == self.name:
                return vs.value
            
        raise RuntimeError(f"Undefined variable '{self.name}'")


class FunctionCall(CodeLine):
    """Call a function defined by 'func' keyword.
    fname can be a Variable, StringType or raw string. args is a list of expressions.
    """
    def __init__(self, fname, args: list, line: int = 0):
        super().__init__('call', line)
        self.fname = fname
        self.args = args
        self.line = line
        print_debug(f'Callable {fname} feedback!')

    def get(self, local_vars: list | None = None, global_vars: list | None = None):
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list

        print_debug("[FC_DEBUG] FunctionCall get enter, global_vars ids=%d, real var_list id=%d" % (id(global_vars), id(var_list)))

        # 查找函数名
        target_var = None
        for v in global_vars:
            if v.name == self.fname:
                target_var = v
                break
        if target_var is None:
            raise RuntimeError(f"Undefined function '{self.fname}'")

        print_debug(f"[FC_DUMP] raw value = {target_var.value}")
        print_debug(f"[FC_DUMP] value type = {type(target_var.value)}")

        val = target_var.value
        if not isinstance(val, tuple):
            raise RuntimeError(f"Function store expects tuple, got {type(val)}")
        is_stored, body_block, arg_names = val

        print_debug(f"[FC_GET] arg_names={arg_names}, types={[type(x) for x in arg_names]}")
        # normalize parameter names: accept strings or Type/Variable with .name
        normalized_arg_names = []
        for p in arg_names:
            if isinstance(p, str):
                normalized_arg_names.append(p)
            elif hasattr(p, 'name'):
                normalized_arg_names.append(p.name)
            else:
                raise TypeError(f"Function formal parameters must be strings. Now is {type(p)}")
        arg_names = normalized_arg_names

        # --------------------------
        # 上面到此为止，不要再解析 self.fname、不要再 vs.get()！
        # 下面直接解析实参、构造局部变量表、运行body_block
        # --------------------------

        def _resolve_type(value, local, global_):
            while not isinstance(value, (StringType, NumberType, ListType)):
                if hasattr(value, 'get'):
                    value = value.get(local, global_)
                else:
                    break
            # wrap raw python primitives into Type instances so function
            # local variable table always stores Type objects
            if isinstance(value, (int, float)):
                return NumberType(value)
            if isinstance(value, str):
                return StringType(value)
            if isinstance(value, list):
                return ListType(value)
            return value

        # 解析实参
        eval_args = []
        for a in (self.args or []):
            v = _resolve_type(a, local_vars, global_vars)
            eval_args.append(v)
        print_debug(f"resolved args values: {eval_args}")

        func_name = _normalize_function_name(self.fname, local_vars, global_vars)
        is_user_defined_func = _is_user_defined_function_name(func_name, local_vars, global_vars)
        args_key = _normalize_cache_args(eval_args)

        # only memoize actual func-defined user functions; ignore builtins/side-effect calls
        print_debug('[CACHE INFO]function_call_cache='+str(function_call_cache))
        print_debug('[CACHE INFO]function_call_disk_cache='+str(function_call_disk_cache))
        try:
            if is_user_defined_func:
                if func_name in function_call_cache and args_key in function_call_cache[func_name]:
                    cached_value = function_call_cache[func_name][args_key]
                    print_debug(f"[FC_CACHE_HIT-MEM] func={func_name}, args={args_key}, value={cached_value}")
                    return _from_primitive(cached_value)
                
                if func_name in function_call_disk_cache and args_key in function_call_disk_cache[func_name]:
                    cached_value = function_call_disk_cache[func_name][args_key]
                    function_call_cache.setdefault(func_name, {})[args_key] = cached_value
                    print_debug(f"[FC_CACHE_HIT-DISK] func={func_name}, args={args_key}, value={cached_value}")
                    return _from_primitive(cached_value)
        except Exception as e:
            print_debug('[CACHE_ERROR]', e)

        # 参数数量校验
        if len(eval_args) != len(arg_names):
            Error('TypeError', f'Function {self.fname} expected {len(arg_names)} arguments, got {len(eval_args)}.', self.line).emit()

        # 构造函数局部变量表
        func_local = []
        for param_name, real_val in zip(arg_names, eval_args):
            pname = param_name if isinstance(param_name, str) else str(param_name)
            func_local.append(VariableSpace(pname, real_val))

      
        print_debug(f"[FC_BIND] func={self.fname}, params={[(v.name, type(v.value)) for v in func_local]}")
    

        ret = NumberType(0)
        print_debug(f'[FUNCTION RESOLVE {self.fname}]')
        try:
            body_block.run(func_local, global_vars)

        except ReturnException as re:

            ret = re.value
            #print('[FUNCTION RETURN VAL]', ret)

        print_debug(f'[FC {self.fname}]Run ended.')
        result = _resolve_type(ret, local_vars, global_vars)
        #print(f'[FC_CACHE {self.fname}] READY TO STORE')
        try:
            if not is_user_defined_func:
                return result
            prim = _to_primitive(result)
            function_call_cache.setdefault(func_name, {})[args_key] = prim
            function_call_disk_cache.setdefault(func_name, {})[args_key] = prim
            print_debug(f"[FC_CACHE_STORE] func={func_name}, args={args_key}, value={prim}")
        except Exception as e:
            print_debug(f"[FC_CACHE_STORE_ERROR]" + str(e))

        #print('[Function return value]', result)
        return result

var_list: list[VariableSpace] = [VariableSpace('true', NumberType(1)), VariableSpace('false', NumberType(0)), VariableSpace('inf', NumberType(INF)), VariableSpace('nega_inf', NumberType(-INF))]    
# functions that must not be cached because they have side-effects
NON_CACHEABLE_FUNCS = set(['out', 'outln', '_wcore_stdout', '_wcore_wdbg', 'input', 'getwcore', 'set_wdbg', 'outs'])
# persistent cache for function calls stored on disk.
# Cache format: { function_name: { (arg1,arg2,...): return_value_primitive, ... } }
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'function_cache.pkl')
LEGACY_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'function_cache.json')


def _normalize_function_name(fname, local_vars=None, global_vars=None):
    value = fname
    if hasattr(value, 'get'):
        try:
            value = value.get(local_vars, global_vars)
        except Exception:
            pass
    if hasattr(value, 'name') and not isinstance(value, str):
        value = value.name
    if isinstance(value, (StringType, NumberType)):
        try:
            value = value.get(local_vars, global_vars)
        except Exception:
            pass
    return str(value)


def _normalize_cache_value(value):
    if isinstance(value, (NumberType, StringType, ListType)):
        return value.get(local_vars=None, global_vars=None)
    if isinstance(value, tuple):
        return tuple(_normalize_cache_value(v) for v in value)
    if isinstance(value, list):
        return tuple(_normalize_cache_value(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((str(k), _normalize_cache_value(v)) for k, v in value.items()))
    return value


def _normalize_cache_args(args):
    return tuple(_normalize_cache_value(arg) for arg in args)


def _is_user_defined_function_name(func_name, local_vars=None, global_vars=None):
    if not func_name:
        return False
    search_scope = []
    if local_vars is not None:
        search_scope.extend(local_vars)
    if global_vars is not None:
        search_scope.extend(global_vars)
    for variable in search_scope:
        if getattr(variable, 'name', None) != func_name:
            continue
        value = getattr(variable, 'value', None)
        if (
            isinstance(value, tuple)
            and len(value) == 3
            and isinstance(value[0], bool)
            and isinstance(value[1], CodeBlock)
            and isinstance(value[2], (list, tuple))
        ):
            is_stored_func = value[0]
            if is_stored_func:
                print('function ', func_name, ' is actually cachable!!!')
                return True
            else:
                return False
    return False


def _prune_non_cacheable_cache_entries(cache):
    if not isinstance(cache, dict):
        return
    # for name in list(cache.keys()):
    #     if name in NON_CACHEABLE_FUNCS:
    #         del cache[name]
    #     elif not _is_user_defined_function_name(name):
    #         del cache[name]


def _load_disk_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as _cf:
                cache = pickle.load(_cf)
                if isinstance(cache, dict):
                    _prune_non_cacheable_cache_entries(cache)
                    return cache
        except Exception:
            pass
    cache = {}
    if os.path.exists(LEGACY_CACHE_FILE):
        try:
            with open(LEGACY_CACHE_FILE, 'r', encoding='utf-8') as _cf:
                legacy = json.load(_cf)
            if isinstance(legacy, dict):
                for key, value in legacy.items():
                    if isinstance(key, str) and '||' in key:
                        name, _, _ = key.partition('||')
                        # if name not in NON_CACHEABLE_FUNCS:
                        cache.setdefault(name, {})[()] = value
        except Exception:
            pass
    _prune_non_cacheable_cache_entries(cache)
    _save_disk_cache(cache)
    print_debug('[CACHE_LOAD] ' + str(cache))
    return cache


def _save_disk_cache(cache):
    if cache is None:
        cache = {}
    try:
        tmp_file = CACHE_FILE + '.tmp'
        with open(tmp_file, 'wb') as _cf:
            pickle.dump(cache, _cf, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp_file, CACHE_FILE)
    except Exception as e:
        print_debug('[FC_CACHE_WRITE_ERROR]', str(e))


def _flush_cache_on_exit():
    try:
        if function_call_disk_cache:
            _save_disk_cache(function_call_disk_cache)
    except Exception:
        pass


function_call_disk_cache = _load_disk_cache()

# in-memory cache for Type objects keyed by function name -> arg tuple -> primitive result
function_call_cache: dict = {}
atexit.register(_flush_cache_on_exit)

def _to_primitive(t):
    # convert Type instance to JSON-serializable primitive
    try:
        if isinstance(t, NumberType):
            return t.get(local_vars=None, global_vars=None)
        if isinstance(t, StringType):
            return t.get(local_vars=None, global_vars=None)
        if isinstance(t, ListType):
            return [_to_primitive(x) for x in t.get(local_vars=None, global_vars=None)]
    except Exception:
        pass
    # fallback: stringify
    try:
        return str(t)
    except Exception:
        return None

def _from_primitive(p):
    if isinstance(p, list):
        return ListType([_from_primitive(x) for x in p])
    if isinstance(p, (int, float)):
        return NumberType(p)
    if isinstance(p, str):
        return StringType(p)
    # fallback
    return StringType(str(p))
class Operator:
    def __init__(self, operator: str):
        self.operator = operator
        self.a = None

    def get(self, local_vars=None, global_vars=None):
        return NotImplemented
    
    def __repr__(self):
        return self.get(local_vars=None, global_vars=None)
    
class BinaryOperator:
    def __init__(self, operator: str, a: Type, b: Type):
        self.operator = operator
        self.a = a
        self.b = b
        


        

    def get(self, local_vars=None, global_vars=None):
        a = self.a
        b = self.b

        def _resolve(value):
            while not isinstance(value, (StringType, NumberType, ListType)) and hasattr(value, 'get'):
                value = value.get(local_vars, global_vars)
            return value

        a = _resolve(a)
        b = _resolve(b)

        a_val = a.get(local_vars, global_vars) if isinstance(a, (StringType, NumberType, ListType)) else a
        b_val = b.get(local_vars, global_vars) if isinstance(b, (StringType, NumberType, ListType)) else b
        from lib.wcore.dec import add, sub, mul, div
        # arithmetic
        match self.operator:
            case '+':
                if isinstance(a, NumberType) and isinstance(b, StringType):
                    # accept signed numeric strings like '-5' or '+3.2'
                    b_is_num = False
                    try:
                        # allow leading +/- and one decimal point
                        b_is_num = b_val.replace('.', '', 1).lstrip('+-').isdigit()
                    except Exception:
                        b_is_num = False
                    return NumberType(add(a_val, float(b_val))) if b_is_num else StringType(str(a_val) + str(b_val))
                if isinstance(a, StringType) and isinstance(b, NumberType):
                    return StringType(a_val + str(b_val))
                if isinstance(a, ListType) and isinstance(b, ListType):
                    return ListType(a_val + b_val)
                if isinstance(a, ListType):
                    return ListType(a_val + ([b_val] if not isinstance(b_val, list) else b_val))
                if isinstance(b, ListType):
                    return ListType(([a_val] if not isinstance(a_val, list) else a_val) + b_val)
                if isinstance(a, StringType) or isinstance(b, StringType):
                    return StringType(str(a_val) + str(b_val))
                return NumberType(add(a_val, b_val))
            case '-':
                return NumberType(sub(a_val,  b_val))
            case '*':
                if isinstance(a, StringType) and isinstance(b, NumberType):
                    return StringType(a_val * int(b_val))
                if isinstance(b, StringType) and isinstance(a, NumberType):
                    return StringType(b_val * int(a_val))
                if isinstance(a, ListType) and isinstance(b, NumberType):
                    return ListType(a_val * int(b_val))
                if isinstance(b, ListType) and isinstance(a, NumberType):
                    return ListType(b_val * int(a_val))
                return NumberType(mul(a_val, b_val))
            case '^':
                return NumberType(a_val ** b_val)
            case '/':
                if isinstance(b_val, (int, float)) and float(b_val) == 0:
                    return NumberType(INF) if float(a_val) > 0 else NumberType(-INF)
                return NumberType(div(a_val, b_val))
            case '//':
                if isinstance(b_val, (int, float)) and float(b_val) == 0:
                    return NumberType(INF) if float(a_val) > 0 else NumberType(-INF)
                return NumberType(int(a_val / b_val))

        def _is_truthy(value):
            if isinstance(value, list):
                return len(value) != 0
            return bool(value)

        aval = a_val
        bval = b_val

        match self.operator:
            case '>':
                return NumberType(1) if aval > bval else NumberType(0)
            case '<':
                return NumberType(1) if aval < bval else NumberType(0)
            case '==':
                return NumberType(1) if aval == bval else NumberType(0)
            case '<=':
                return NumberType(1) if aval <= bval else NumberType(0)
            case '>=':
                return NumberType(1) if aval >= bval else NumberType(0)
            case '!=':
                return NumberType(1) if aval != bval else NumberType(0)
            case '&':
                return NumberType(1) if (_is_truthy(aval) and _is_truthy(bval)) else NumberType(0)
            case '|':
                return NumberType(1) if (_is_truthy(aval) or _is_truthy(bval)) else NumberType(0)

            case _:
                return NumberType(0)
    
    def __repr__(self):
        return '<BinaryOperator {}>'.format(self.operator)
      

if __name__ == '__main__':
    # codeblock = CodeBlock(
    #     [
    #         VariableDefinitionCodeLine(
    #             'a',
    #             [NumberType(5)]
    #         ),
    #         KeywordCodeLine(
    #             'rep',
    #             [
    #                 Variable('a'),
    #                 CodeBlock([
    #                     VariableDefinitionCodeLine(
    #                         'a',
    #                         [BinaryOperator(
    #                             '*',
    #                             Variable('a'),
    #                             NumberType(1.2)
    #                         )]
    #                     ),
    #                     KeywordCodeLine(
    #                         'getwcore',
    #                         [
    #                             StringType('stdout'),
    #                             Variable('a')
    #                         ]
    #                     )
    #                 ])
    #             ]
    #         )
    #     ]
    # )
    # codeblock = CodeBlock([
    #     KeywordCodeLine(
    #         'getwcore',
    #         [
    #             StringType('stdout'),
    #             BinaryOperator(
    #                 '+',
    #                 NumberType(0.1),
    #                 NumberType(0.2)
    #             )
    #         ]
    #     )
    # ])
    # codeblock.run()
    pass
