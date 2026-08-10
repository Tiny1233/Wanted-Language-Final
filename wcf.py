# -*- coding: UTF-8 -*-

###
# This file is about transfer built-in classes to final results.
# It can also be used for Wanted Compiled Classes (*.wcc) loadout
# Default, it is the medium for Wanted File (*.wcn)'s final interpreting
# 2026.07.06
###

import math
import sys
import lib.wcore.dec



INF = math.inf
TINY = 0.000000000000001



class Error:
    def __init__(self, attr: str, des: str, line: int = 0, content: str = '', filename: str = '<default>'):
        self.attr = attr
        self.des = des
        self.line = line
        self.content = content
        self.filename = filename

    def emit(self):
        print( 'Error in Wanted File occured')
        print(f'Location: in file {self.filename}[{self.line}]')
        print(f'{self.content}')
        print(f'{self.attr}: {self.des}')
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
        match self.name:
            case 'getwcore':
                if len(self.arg) != 2:
                    Error('GetWCore Error', f'2 sub arguments were expected, but {len(self.arg)} {'was' if len(self.arg) < 2 else 'were'} given.', self.line).emit()

                subcommand: Type = self.arg[0]
                subcontent: Type = self.arg[1]
                from lib.wcore.wsfilter import wsfilter
                match subcommand.get():
                    case 'stdout':
                        result = subcontent.get(local_vars=None, global_vars=None)
                        if isinstance(result, (StringType, NumberType)):
                            print(wsfilter(result.get(local_vars=None, global_vars=None)), end='')
                        elif isinstance(result, ListType):
                            print(', '.join([str(wsfilter(i.get(local_vars=None, global_vars=None))) for i in result.get(local_vars=None, global_vars=None)]), end='')
                        return result
                    
                    case 'stdin':
                        prompt = subcontent.get(local_vars=None, global_vars=None)
                        print(prompt)
                        
                        if isinstance(prompt, (StringType, NumberType)):
                            prompt = prompt.get(local_vars=None, global_vars=None)
                        return StringType(input(prompt))
            
            case 'rep':
                if len(self.arg) not in [2, 3]:
                    Error('SyntaxError', f'Repeat body and times were expected, but {len(self.arg)} {'was' if len(self.arg) < 2 else 'were'} given.', self.line).emit()
                final_block = self.arg[2] if len(self.arg) == 3 else None
                reptime = self.arg[0]
                while not isinstance(reptime, (StringType, NumberType)):
                    reptime = reptime.get(local_vars=None, global_vars=None)
                repbody = self.arg[1]

                if not isinstance(reptime, NumberType):
                    Error('SyntaxError', 'The condition was expected to be a real number.', self.line)
                if not isinstance(repbody, CodeBlock):
                    Error('InitialDebugError', 'WCB was expected.')
                # Runtime error
                if math.isinf(reptime.get(local_vars=None, global_vars=None)) or abs(int(reptime.get(local_vars=None, global_vars=None))) if math.isinf(reptime.get(local_vars=None, global_vars=None)) else 16777217 > 16777216:
                    Error('PerformanceError', 'Repeation times out of expectation, maximum 16777216.')
                broken = False
                for ct in range(abs(int(reptime.get(local_vars=None, global_vars=None)))):
                    try:
                        repbody.run()
                    except BreakLoop:
                        broken = True
                        break
                if final_block is not None and not broken:
                    final_block.run()
                
                return
            
            case 'if':
                if len(self.arg) < 2:
                    Error('SyntaxError', 'If statement expected condition and body.', self.line).emit()

                condition = self.arg[0]
                then_block = self.arg[1]
                

                if not isinstance(then_block, CodeBlock):
                    Error('TypeError', 'If branch must be a code block.', self.line).emit()

                while not isinstance(condition, (StringType, NumberType)):
                    condition = condition.get(local_vars=None, global_vars=None)

                if not isinstance(condition, (StringType, NumberType)):
                    Error('TypeError', 'Condition must evaluate to a number or string.', self.line).emit()

                def _is_true(value):
                    if isinstance(value, NumberType):
                        return value.get(local_vars=None, global_vars=None) != 0
                    if isinstance(value, StringType):
                        return value.get(local_vars=None, global_vars=None) != ''
                    return bool(value)
           
                if _is_true(condition):
                    then_block.run()
                    return

                for branch in self.arg[2:]:
                    if isinstance(branch, CodeBlock):
                        branch.run()
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
                            elif_condition = elif_condition.get(local_vars=None, global_vars=None)
                        if not isinstance(elif_condition, (StringType, NumberType)):
                            Error('TypeError', 'Eif condition must evaluate to a number or string.', self.line).emit()
                        if _is_true(elif_condition):
                            elif_block.run()
                            return
                        continue

                    if branch.name == 'else':
                        if len(branch.arg) != 1:
                            Error('SyntaxError', 'Else statement expected a single body.', self.line).emit()
                        else_block = branch.arg[0]
                        if not isinstance(else_block, CodeBlock):
                            Error('TypeError', 'Else branch must be a code block.', self.line).emit()
                        else_block.run()
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
                        return value.get(local_vars=None, global_vars=None) != 0
                    if isinstance(value, StringType):
                        return value.get(local_vars=None, global_vars=None) != ''
                    return bool(value)

                def _eval_condition():
                    cond = condition
                    while not isinstance(cond, (StringType, NumberType)):
                        cond = cond.get(local_vars=None, global_vars=None)
                    if not isinstance(cond, (StringType, NumberType)):
                        Error('TypeError', 'While condition must evaluate to a number or string.', self.line).emit()
                    return cond

                broken = False
                while _is_true(_eval_condition()):
                    try:
                        while_body.run()
                    except BreakLoop:
                        broken = True
                        break

                if else_body is not None and not broken:
                    else_body.run()
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
                    condition = condition.get(local_vars=None, global_vars=None)

                if not isinstance(condition, (StringType, NumberType)):
                    Error('TypeError', 'Assert condition must evaluate to a number or string.', self.line).emit()

                cond_true = False
                if isinstance(condition, NumberType):
                    cond_true = condition.get(local_vars=None, global_vars=None) != 0
                elif isinstance(condition, StringType):
                    cond_true = condition.get(local_vars=None, global_vars=None) != ''

                if not cond_true:
                    msg_text = ''
                    if message is not None:
                        while not isinstance(message, (StringType, NumberType)):
                            message = message.get(local_vars=None, global_vars=None)
                        msg_text = str(message.get(local_vars=None, global_vars=None)) if isinstance(message, (StringType, NumberType)) else repr(message)
                    Error('AssertionError', msg_text or 'Assertion failed.', self.line).emit()
                return

            case 'return':
                # return <value>
                if len(self.arg) == 0:
                    raise ReturnException(NumberType(0))
                if len(self.arg) != 1:
                    Error('SyntaxError', 'Return expected zero or one expression.', self.line).emit()
                val = self.arg[0]
                while not isinstance(val, (StringType, NumberType, ListType)):
                    val = val.get(local_vars=None, global_vars=None)
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
                    fname_str = fname.get(local_vars=None, global_vars=None)
                elif isinstance(fname, Variable):
                    fname_str = fname.name
                else:
                    Error('TypeError', 'Function name must be a string or variable.', self.line).emit()

                # params should be a ListType of StringType, raw strings, or variable-like nodes
                param_names = []
                def _normalize_param_item(p):
                    if isinstance(p, StringType):
                        return p.get(local_vars=None, global_vars=None)
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
                    raw_params = params.get(local_vars=None, global_vars=None)
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
                                v = v.get(local_vars=None, global_vars=None)
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

        print('[CodeBlock] Variable list of names: ')
        print('[CodeBlock] local vars: ', [(v.name, v.value) for v in local_vars])
        print('[CodeBlock] global vars: ', [(v.name, v.value) for v in global_vars])

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

    def __add__(self, other):
        if isinstance(other, str):
            other = StringType(other)
        while not isinstance(other, (StringType, NumberType, ListType)):
            other = other.get(local_vars=None, global_vars=None)

        if isinstance(other, NumberType):
            return StringType(self.get(local_vars=None, global_vars=None) + str(other.get(local_vars=None, global_vars=None)))

        return StringType(self.get(local_vars=None, global_vars=None) + other.get(local_vars=None, global_vars=None))

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
    
    def __add__(self, other):
        if isinstance(other, (int, float)):
            other = NumberType(other)
        while not isinstance(other, (StringType, NumberType, ListType)):
            other = other.get(local_vars=None, global_vars=None)
        from lib.wcore.numconv import number as n
        if isinstance(other, StringType): return NumberType(self.get(local_vars=None, global_vars=None) + n(other.get(local_vars=None, global_vars=None)))
        return NumberType(lib.wcore.dec.add(self.get(local_vars=None, global_vars=None) , other.get(local_vars=None, global_vars=None)))
    
    def __sub__(self, other):
        if isinstance(other, (int, float)):
            other = NumberType(other)
        while not isinstance(other, (StringType, NumberType, ListType)):
            other = other.get(local_vars=None, global_vars=None)
        return NumberType(lib.wcore.dec.sub(self.get(local_vars=None, global_vars=None) , other.get(local_vars=None, global_vars=None)))
    def __pow__(self, other):
        if isinstance(other, (int, float)):
            other = NumberType(other)
        while not isinstance(other, (StringType, NumberType)):
            other = other.get(local_vars=None, global_vars=None)
        return NumberType(lib.wcore.dec.pow(self.get(local_vars=None, global_vars=None) , other.get(local_vars=None, global_vars=None)))
    def __mul__(self, other):
        if isinstance(other, (int, float)):
            other = NumberType(other)
        while not isinstance(other, (StringType, NumberType, ListType)):
            other = other.get(local_vars=None, global_vars=None)
        if isinstance(other, NumberType):
            return NumberType(lib.wcore.dec.mul(self.get(local_vars=None, global_vars=None) , other.get(local_vars=None, global_vars=None)))
        if isinstance(other, StringType):
            return StringType(other.get(local_vars=None, global_vars=None)*self.get(local_vars=None, global_vars=None))
        
        Error('SyntaxError', 'Operator * expected to match type either NumberType or StringType.', self.line)

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            other = NumberType(other)
        while not isinstance(other, (StringType, NumberType, ListType)):
            other = other.get(local_vars=None, global_vars=None)
        return NumberType(lib.wcore.dec.div(self.get(local_vars=None, global_vars=None) , other.get(local_vars=None, global_vars=None))) if other.get(local_vars=None, global_vars=None) != 0 else NumberType(INF)


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
        if isinstance(other, ListType):
            for i in other.get():
                self.value.append(i)
        else:
            self.value.append(other)

    def __repr__(self):
        return '{' + ', '.join(repr(x) for x in self.value) + '}'
    
    def get_index(self, ind: NumberType):
        while not isinstance(ind, (StringType, NumberType)):
            ind = ind.get(local_vars=None, global_vars=None)

        return self.get(local_vars=None, global_vars=None)[ind.get(local_vars=None, global_vars=None)]
class VariableSpace: # Won't be declared in Wanted Codes
    def __init__(self, var_name: str, value: Type):
        self.name = var_name
        self.value = value

    def get(self, local_vars=None, global_vars=None):
        return self.value

class VariableDefinitionCodeLine(CodeLine):
    def __init__(self, var_name: str, arg: list[Type], line: int = 0):
        print(f'[VAR_DEF] {var_name} = {arg}')
        self.name = var_name
        self.arg = arg
        self.line = line

    def get(self, local_vars: list | None = None, global_vars: list | None = None):
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list

        flag = True
        t = self.arg[0]
        # 这里！不要 t.get()，要把上下文传下去
        while not isinstance(t, (NumberType, StringType)):
            print(F'[TYPE OF T:{self.var_name}] ', type(t))
            t = t.get(local_vars, global_vars)

        # 顶层脚本赋值写 global_vars；函数内部赋值写 local_vars
        target_list = local_vars if local_vars else global_vars

        for var in target_list:
            if var.name == self.name:
                var.value = t
                flag = False
                break
        if flag:
            target_list.append(VariableSpace(self.name, t))
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
        print('[VAR CALL]Variable get() called for variable name:', self.name)
        lv = [(v.name, v.value) for v in local_vars]
        print(f'[VAR CALL {self.name}] local_vars name&value: {lv}')
        gv = [(v.name, v.value) for v in global_vars]
        print(f'[VAR CALL {self.name}] global_vars name&value: {gv}')

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
        print(f'Callable {fname} feedback!')

    def get(self, local_vars: list | None = None, global_vars: list | None = None):
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list

        print("[FC_DEBUG] FunctionCall get enter, global_vars ids=%d, real var_list id=%d" % (id(global_vars), id(var_list)))

        # 查找函数名
        target_var = None
        for v in global_vars:
            if v.name == self.fname:
                target_var = v
                break
        if target_var is None:
            raise RuntimeError(f"Undefined function '{self.fname}'")

        print(f"[FC_DUMP] raw value = {target_var.value}")
        print(f"[FC_DUMP] value type = {type(target_var.value)}")

        val = target_var.value
        if not isinstance(val, tuple):
            raise RuntimeError(f"Function store expects tuple, got {type(val)}")
        body_block, arg_names = val

        print(f"[FC_GET] arg_names={arg_names}, types={[type(x) for x in arg_names]}")
        for p in arg_names:
            if not isinstance(p, str):
                raise TypeError(f"Function formal parameters must be strings. Now is {type(p)}")

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
            return value

        # 解析实参
        eval_args = []
        for a in (self.args or []):
            v = _resolve_type(a, local_vars, global_vars)
            eval_args.append(v)
        print(f"resolved args values: {eval_args}")

        # 参数数量校验
        if len(eval_args) != len(arg_names):
            Error('TypeError', f'Function {self.fname} expected {len(arg_names)} arguments, got {len(eval_args)}.', self.line).emit()

        # 构造函数局部变量表
        func_local = []
        for param_name, real_val in zip(arg_names, eval_args):
            func_local.append(VariableSpace(param_name, real_val))

        # 执行函数体：局部表 + 全局表
        ret = NumberType(0)
        try:
            body_block.run(func_local, global_vars)
        except ReturnException as re:
            ret = re.value
        return _resolve_type(ret, local_vars, global_vars)

var_list: list[VariableSpace] = [VariableSpace('true', NumberType(1)), VariableSpace('false', NumberType(0)), VariableSpace('inf', NumberType(INF)), VariableSpace('nega_inf', NumberType(-INF))]    
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
        # unwrap wrapper objects until we get a primitive (String/Number/List)
        while not isinstance(a, (StringType, NumberType, ListType)) and hasattr(a, 'get'):
            a = a.get(local_vars, global_vars)
            # print('a', type(a))
      
        
        while not isinstance(b, (StringType, NumberType, ListType)) and hasattr(b, 'get'):
            # print('b', type(self.b))
            b = b.get(local_vars, global_vars)
        
        # arithmetic
        match self.operator:
            case '+':
                return (a + b)
            case '-':
                return (a - b)
            case '*':
                return (a * b)
            case '^':
                return (a ** b)
            case '/':
                return (a / b) if b.get(local_vars=None, global_vars=None) != 0 else (NumberType(INF) if a.get(local_vars=None, global_vars=None) > 0 else NumberType(-INF))

        # comparisons (return NumberType(1) for true, NumberType(0) for false)
        try:
            aval = a.get(local_vars=None, global_vars=None) if isinstance(a, (NumberType, StringType, ListType)) else a
            bval = b.get(local_vars=None, global_vars=None) if isinstance(b, (NumberType, StringType, ListType)) else b
        except Exception:
            aval = a
            bval = b

        match self.operator:
            case '>':
                return NumberType(1) if float(aval) > float(bval) else NumberType(0)
            case '<':
                return NumberType(1) if float(aval) < float(bval) else NumberType(0)
            case '==':
                return NumberType(1) if aval == bval else NumberType(0)
            case '<=':
                return NumberType(1) if float(aval) <= float(bval) else NumberType(0)
            case '>=':
                return NumberType(1) if float(aval) >= float(bval) else NumberType(0)
            case '!=':
                return NumberType(1) if aval != bval else NumberType(0)
            case '&':
                return NumberType(1) if (float(aval) != 0 and float(bval) != 0) else NumberType(0)
            case '|':
                return NumberType(1) if (float(aval) != 0 or float(bval) != 0) else NumberType(0)

            case _:
                return 0
    
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
