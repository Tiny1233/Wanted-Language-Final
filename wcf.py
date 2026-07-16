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

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value
        super().__init__()

class CodeLine:
    def __init__(self, name: str, line: int = 0):
        self.name = name
        self.line = line

    def get(self):
        return NotImplemented

    def __repr__(self):
        value = self.get()
        return repr(value) if value is not None else ''

class KeywordCodeLine(CodeLine):
    def __init__(self, name: str, arg: list, line: int = 0):
        super().__init__(name)
        self.arg = arg
        self.line = line
     

    def get(self):
        match self.name:
            case 'getwcore':
                if len(self.arg) != 2:
                    Error('GetWCore Error', f'2 sub arguments were expected, but {len(self.arg)} {'was' if len(self.arg) < 2 else 'were'} given.', self.line).emit()

                subcommand: Type = self.arg[0]
                subcontent: Type = self.arg[1]
                from lib.wcore.wsfilter import wsfilter
                match subcommand.get():
                    case 'stdout':
                        result = subcontent.get()
                        if isinstance(result, (StringType, NumberType)):
                            print(wsfilter(result.get()), end='')
                        elif isinstance(result, ListType):
                            print(', '.join([str(wsfilter(i.get())) for i in result.get()]), end='')
                        return result
                    
                    case 'stdin':
                        prompt = subcontent.get()
                        print(prompt)
                        
                        if isinstance(prompt, (StringType, NumberType)):
                            prompt = prompt.get()
                        return StringType(input(prompt))
            
            case 'rep':
                if len(self.arg) not in [2, 3]:
                    Error('SyntaxError', f'Repeat body and times were expected, but {len(self.arg)} {'was' if len(self.arg) < 2 else 'were'} given.', self.line).emit()
                final_block = self.arg[2] if len(self.arg) == 3 else None
                reptime = self.arg[0]
                while not isinstance(reptime, (StringType, NumberType)):
                    reptime = reptime.get()
                repbody = self.arg[1]

                if not isinstance(reptime, NumberType):
                    Error('SyntaxError', 'The condition was expected to be a real number.', self.line)
                if not isinstance(repbody, CodeBlock):
                    Error('InitialDebugError', 'WCB was expected.')
                # Runtime error
                if math.isinf(reptime.get()) or abs(int(reptime.get())) if math.isinf(reptime.get()) else 16777217 > 16777216:
                    Error('PerformanceError', 'Repeation times out of expectation, maximum 16777216.')
                broken = False
                for ct in range(abs(int(reptime.get()))):
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
                    condition = condition.get()

                if not isinstance(condition, (StringType, NumberType)):
                    Error('TypeError', 'Condition must evaluate to a number or string.', self.line).emit()

                def _is_true(value):
                    if isinstance(value, NumberType):
                        return value.get() != 0
                    if isinstance(value, StringType):
                        return value.get() != ''
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
                            elif_condition = elif_condition.get()
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
                        return value.get() != 0
                    if isinstance(value, StringType):
                        return value.get() != ''
                    return bool(value)

                def _eval_condition():
                    cond = condition
                    while not isinstance(cond, (StringType, NumberType)):
                        cond = cond.get()
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
                    condition = condition.get()

                if not isinstance(condition, (StringType, NumberType)):
                    Error('TypeError', 'Assert condition must evaluate to a number or string.', self.line).emit()

                cond_true = False
                if isinstance(condition, NumberType):
                    cond_true = condition.get() != 0
                elif isinstance(condition, StringType):
                    cond_true = condition.get() != ''

                if not cond_true:
                    msg_text = ''
                    if message is not None:
                        while not isinstance(message, (StringType, NumberType)):
                            message = message.get()
                        msg_text = str(message.get()) if isinstance(message, (StringType, NumberType)) else repr(message)
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
                    val = val.get()
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
                    fname_str = fname.get()
                elif isinstance(fname, Variable):
                    fname_str = fname.name
                else:
                    Error('TypeError', 'Function name must be a string or variable.', self.line).emit()

                # params should be a ListType of StringType, raw strings, or variable-like nodes
                param_names = []
                def _normalize_param_item(p):
                    if isinstance(p, StringType):
                        return p.get()
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
                    raw_params = params.get()
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
                                v = v.get()
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
        value = self.get()
        return repr(value) if value is not None else ''

class CodeBlock:
    def __init__(self, code_lines: list[CodeLine], line: int = 0):
        self.code_lines = code_lines
        self.line = line

    def run(self):
        for i in range(len(self.code_lines)):
            self.code_lines[i].get()

class Type:
    def __init__(self, value: any, name: str = '', line: int = 0):
        self.name = name
        self.value = value
        self.line = line

    def get(self):
        return NotImplemented

    def __repr__(self):
        value = self.get()
        return repr(value) if value is not None else ''

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if isinstance(other, Type):
            return self.get() == other.get()
        return self.get() == other

    def __ne__(self, other):
        return not self.__eq__(other)
    

class StringType(Type):
    def __init__(self, value: str, name: str = '', line: int = 0):
        super().__init__(value, name, line)

    def get(self):
        return self.value
    
    def __repr__(self):
        return str(self.get())

    def __add__(self, other):
        while not isinstance(other, (StringType, NumberType, 'ListType')):
            other = other.get()

        if isinstance(other, NumberType):
            return StringType(self.get() + str(other.get()))

        return StringType(self.get() + other.get())

    def get_index(self, ind: NumberType):
        while not isinstance(ind, (StringType, NumberType)):
            ind = ind.get()
        return StringType(self.get()[ind.get()])
    
    

class NumberType(Type):
    def __init__(self, value: float | int, name: str = '', line: int = 0):
        super().__init__(value, name, line)

    def get(self):
        return self.value
    
    def __repr__(self):
        return str(self.get())
    
    def __add__(self, other):
        while not isinstance(other, (StringType, NumberType, 'ListType')):
            other = other.get()
        from lib.wcore.numconv import number as n
        if isinstance(other, StringType): return NumberType(self.get() + n(other.get()))
        return NumberType(lib.wcore.dec.add(self.get() , other.get()))
    
    def __sub__(self, other):
        while not isinstance(other, (StringType, NumberType, 'ListType')):
            other = other.get()
        return NumberType(lib.wcore.dec.sub(self.get() , other.get()))
    
    def __mul__(self, other):
        while not isinstance(other, (StringType, NumberType, 'ListType')):
            other = other.get()
        if isinstance(other, NumberType):
            return NumberType(lib.wcore.dec.mul(self.get() , other.get()))
        if isinstance(other, StringType):
            return StringType(other.get()*self.get())
        
        Error('SyntaxError', 'Operator * expected to match type either NumberType or StringType.', self.line)

    def __truediv__(self, other):
        while not isinstance(other, (StringType, NumberType, 'ListType')):
            other = other.get()
        return NumberType(lib.wcore.dec.div(self.get() , other.get())) if other.get() != 0 else NumberType(INF)


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

    def get(self):
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
            ind = ind.get()

        return self.get()[ind.get()]
class VariableSpace: # Won't be declared in Wanted Codes
    def __init__(self, var_name: str, value: Type):
        self.name = var_name
        self.value = value

    def get(self):
        return self.value

class VariableDefinitionCodeLine(CodeLine):
    def __init__(self, var_name: str, arg: list[Type], line: int = 0):
        self.name = var_name
        self.arg = arg
        self.line = line

    def get(self):
        flag = True
        for var in var_list:
            if var.name == self.name:
                t = self.arg[0]
                while not isinstance(t, (NumberType, StringType)):
                    t = t.get()
                var.value = t
                flag = False
                # print(f'<Variable {var.name}> has been modified!')
                break
        if flag:      
            var_list.append(VariableSpace(self.name, self.arg[0]))
            # print(f'<Variable {self.name}> has been added to variable list!')
        return self.arg[0].get()
    
    def __repr__(self):
        value = self.get()
        return repr(value) if value is not None else ''

class Variable(Type):
    def __init__(self, var_name: str):
        self.name = var_name
        self.value = self.get()

    def get(self):
        # print([vs.name for vs in var_list])
        for vs in var_list:
            if self.name == vs.name:
                return vs.get()
        return None
    
    def __repr__(self):
        value = self.get()
        return repr(value) if value is not None else 'None'
    
    def __add__(self, other):
        while not isinstance(other, (StringType, NumberType)):
            other = other.get()
        return (self.get() + other)
    
    def __sub__(self, other):
        while not isinstance(other, (StringType, NumberType)):
            other = other.get()
        return (self.get() - other)
    
    def __mul__(self, other):
        while not isinstance(other, (StringType, NumberType)):
            other = other.get()
        return (self.get() * other)
    
    def __truediv__(self, other):
        while not isinstance(other, (StringType, NumberType)):
            other = other.get()
        return (self.get() / other)


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

    def get(self):
        # resolve function name
        if isinstance(self.fname, StringType):
            name = self.fname.get()
        elif isinstance(self.fname, Variable):
            name = self.fname.name
        elif isinstance(self.fname, str):
            name = self.fname
        else:
            # try to evaluate to a string
            fn = self.fname
            while not isinstance(fn, (StringType, NumberType, ListType)):
                fn = fn.get()
            name = fn.get() if isinstance(fn, StringType) else None

        if name is None:
            Error('TypeError', 'Function name must be a string or variable.', self.line).emit()

        # find function object in var_list
        func_obj = None
        for vs in var_list:
            if vs.name == name:
                func_obj = vs.get()
                break

        if func_obj is None:
            Error('NameError', f"Function '{name}' not found.", self.line).emit()

        if isinstance(func_obj, tuple):
            if len(func_obj) == 3 and isinstance(func_obj[0], (str, StringType)):
                fname_val = func_obj[0].get() if isinstance(func_obj[0], StringType) else func_obj[0]
                params = func_obj[1]
                body = func_obj[2]
            elif len(func_obj) == 2:
                fname_val = name
                params = func_obj[0]
                body = func_obj[1]
            else:
                Error('TypeError', 'Invalid function object representation.', self.line).emit()

            def _normalize_params(params_value):
                if isinstance(params_value, ListType):
                    params_value = params_value.get()
                elif isinstance(params_value, CodeBlock):
                    params_value = params_value.code_lines
                elif isinstance(params_value, tuple):
                    params_value = list(params_value)
                elif not isinstance(params_value, list):
                    params_value = [params_value]

                normalized = []
                for item in params_value:
                    if isinstance(item, StringType):
                        normalized.append(item.get())
                    elif isinstance(item, Variable):
                        normalized.append(item.name)
                    elif isinstance(item, str):
                        normalized.append(item)
                    elif isinstance(item, VariableDefinitionCodeLine):
                        normalized.append(item.name)
                    else:
                        Error('TypeError', f'Function parameters must be strings. Now is {str(type(item))}', self.line).emit()
                return normalized

            params = _normalize_params(params)

            class FunctionType(Type):
                def __init__(self, name, params, body):
                    super().__init__(None, name)
                    self.params = params
                    self.body = body

                def get(self, args):
                    if not isinstance(args, (list, tuple)):
                        args = [args]
                    if len(args) != len(self.params):
                        Error('TypeError', f'Function {self.name} expected {len(self.params)} arguments, got {len(args)}.').emit()
                    added = []
                    for pname, aval in zip(self.params, args):
                        v = aval
                        while not isinstance(v, (StringType, NumberType, ListType)):
                            if hasattr(v, 'get'):
                                v = v.get()
                            else:
                                break
                        param_name = pname.get() if isinstance(pname, StringType) else pname
                        var = VariableSpace(param_name, v)
                        var_list.append(var)
                        added.append(var)
                    try:
                        self.body.run()
                        ret = NumberType(0)
                    except ReturnException as re:
                        ret = re.value
                    for a in added:
                        try:
                            var_list.remove(a)
                        except ValueError:
                            pass
                    return ret

            func_obj = FunctionType(fname_val, params, body)
            vs.value = func_obj

        def _resolve_type(value):
            while not isinstance(value, (StringType, NumberType, ListType)):
                if hasattr(value, 'get'):
                    value = value.get()
                else:
                    break
            return value

        # prepare evaluated args (keep as Type instances expected by FunctionType.get)
        eval_args = []
        for a in (self.args or []):
            v = a
            if isinstance(v, str):
                v = StringType(v)
            elif isinstance(v, (float, int)):
                v = NumberType(v)
            v = _resolve_type(v)
            eval_args.append(v)

        result = None
        if hasattr(func_obj, 'params') and hasattr(func_obj, 'body'):
            result = func_obj.get(eval_args)
        elif callable(func_obj):
            result = func_obj(*[x.get() if isinstance(x, (StringType, NumberType, ListType)) else x for x in eval_args])
        elif hasattr(func_obj, 'get'):
            try:
                result = func_obj.get(eval_args)
            except TypeError:
                if len(eval_args) == 0:
                    result = func_obj.get()
                else:
                    raise
        else:
            Error('TypeError', f"Object '{name}' is not callable.", self.line).emit()

        return _resolve_type(result)

var_list: list[VariableSpace] = [VariableSpace('true', NumberType(1)), VariableSpace('false', NumberType(0)), VariableSpace('inf', NumberType(INF)), VariableSpace('nega_inf', NumberType(-INF))]    
class Operator:
    def __init__(self, operator: str):
        self.operator = operator
        self.a = None

    def get(self):
        return NotImplemented
    
    def __repr__(self):
        return self.get()
    
class BinaryOperator:
    def __init__(self, operator: str, a: Type, b: Type):
        self.operator = operator
        self.a = a
        self.b = b
        


        

    def get(self):
        a = self.a
        b = self.b
        while not isinstance(a, (StringType, NumberType, ListType)):
            
            a = a.get()
            # print('a', type(a))
      
        
        while not isinstance(b, (StringType, NumberType, ListType)):
            # print('b', type(self.b))
            b = b.get()
        
        # arithmetic
        match self.operator:
            case '+':
                return (a + b)
            case '-':
                return (a - b)
            case '*':
                return (a * b)
            case '/':
                return (a / b) if b.get() != 0 else (NumberType(INF) if a.get() > 0 else NumberType(-INF))

        # comparisons (return NumberType(1) for true, NumberType(0) for false)
        try:
            aval = a.get() if isinstance(a, (NumberType, StringType, ListType)) else a
            bval = b.get() if isinstance(b, (NumberType, StringType, ListType)) else b
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
        return repr(self.get())
      

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
