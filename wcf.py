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
        self.emit()

    def emit(self):
        raise WantedError(self.attr, self.des, self.line)


class WantedError(Exception):
    def __init__(self, attr, des, line=0):
        self.attr = attr
        self.des = des
        self.line = line
        super().__init__(f'{attr}: {des}')


class BreakLoop(Exception):
    """Internal exception used to implement break keyword."""
    pass

class ReturnException(BaseException):
    def __init__(self, value):
        self.value = value
        super().__init__()


class TypeDefinition:
    def __init__(self, name, methods=None, is_library=False):
        self.name = name
        self.methods = methods or {}
        self.is_library = is_library

    def get(self, local_vars=None, global_vars=None):
        return self

    def instantiate(self, args, local_vars, global_vars):
        if self.is_library:
            Error('TypeError', f'Library {self.name} cannot be constructed.')
        instance = InstanceType(self)
        _instances.append(instance)
        setup = self.methods.get('_setup')
        if setup is not None:
            BoundMethod(instance, '_setup', setup).call(args, local_vars, global_vars)
        elif args:
            Error('TypeError', f'Type {self.name} does not accept constructor arguments.')
        return instance

    def get_member(self, name):
        method = self.methods.get(name)
        if isinstance(method, TypeDefinition):
            return method
        if method is not None:
            return BoundMethod(None, name, method)
        Error('AttributeError', f"Library {self.name} has no member '{name}'.")

    def __repr__(self):
        return f'<type: {self.name}>'


_instances = []

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
     
                
                # print(f"[GETWCORE DEBUG] cmd repr={repr(subcommand.get(local_vars, global_vars))}")
  
                match subcommand.get(local_vars, global_vars):
                    case 'stdout':
           
                        result = subcontent.get(local_vars, global_vars)
                        if isinstance(result, (StringType, NumberType)):
                            print('nothignnyudsa')
                            print(wsfilter(result.get(local_vars, global_vars)) if result.get(local_vars, global_vars) is not None else 'Nothing', end='')
                        elif isinstance(result, ListType):
                        
                            print(', '.join([str(wsfilter(i.get(local_vars, global_vars))) for i in result.get(local_vars, global_vars)]), end='')
                        return None
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


                    case 'lengthOf':
                        # 反复求值直到不再有 .get()
                        val = subcontent
                        while hasattr(val, "get"):
                            val = val.get(local_vars, global_vars)

                        # duck‑type，规避isinstance跨模块类身份问题
                        if isinstance(val, list):
                            length = len(val)
                        elif isinstance(val, str):
                            length = len(val)
                        else:
                            import math
                            num = float(val)
                            if num == 0:
                                length = 1
                            else:
                                length = math.ceil(math.log10(abs(num)))
                        return NumberType(length)

                    case 'rand':
                        import random
                        return NumberType(random.random())

                    
                    case 'stdin':
                        prompt = subcontent.get(local_vars, global_vars)
                        #print(prompt)
                        
                        if isinstance(prompt, (StringType, NumberType)):
                            prompt = prompt.get(local_vars, global_vars)
                        return StringType(input(prompt))
            
            case 'rep':
                if len(self.arg) not in [2, 3]:
                    Error('SyntaxError', f'Repeat body and times were expected, but {len(self.arg)} {'was' if len(self.arg) < 2 else 'were'} given.', self.line).emit()
                final_block = self.arg[2] if len(self.arg) == 3 else None
                reptime = self.arg[0]
                while not isinstance(reptime, (NumberType, StringType, ListType)):
                    reptime = reptime.get(local_vars, global_vars)
                    if isinstance(reptime, int):
                        reptime = NumberType(reptime)
                repbody = self.arg[1]

                if not isinstance(reptime, NumberType):
                    Error('SyntaxError', 'The reptime was expected to be a real number. Not ' + str(type(reptime)), self.line)
                if not isinstance(repbody, CodeBlock):
                    Error('InitialDebugError', 'WCB was expected.')
                # Runtime error
                import math
                # if math.isinf(reptime.get(local_vars, global_vars)) or abs(int(reptime.get(local_vars, global_vars))) if math.isinf(reptime.get(local_vars, global_vars)) else 16777217 > 16777216:
                #     Error('PerformanceError', 'Repeation times out of expectation, maximum 16777216.')
                broken = False
                if not math.isinf(reptime.get(local_vars, global_vars)):
                    for ct in range(abs(int(reptime.get(local_vars, global_vars)))):
                        try:
                            repbody.run(local_vars=local_vars, global_vars=global_vars)
                        except BreakLoop:
                            broken = True
                            break
                else:
                    while 1:
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

            case 'please':
                if len(self.arg) < 1 or len(self.arg) > 3:
                    Error('SyntaxError', 'Please block expected body, optional else and final blocks.', self.line).emit()
                body = self.arg[0]
                else_body = self.arg[1] if len(self.arg) > 1 else None
                final_body = self.arg[2] if len(self.arg) > 2 else None
                if not isinstance(body, CodeBlock):
                    Error('TypeError', 'Please body must be a code block.', self.line).emit()
                try:
                    body.run(local_vars=local_vars, global_vars=global_vars)
                except WantedError:
                    if else_body is not None:
                        else_body.run(local_vars=local_vars, global_vars=global_vars)
                finally:
                    if final_body is not None:
                        final_body.run(local_vars=local_vars, global_vars=global_vars)
                return

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
                while not isinstance(val, (LiteralType)):
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
                            while not isinstance(v, (LiteralType)):
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
    
class LiteralType(Type):
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


class InstanceType(Type):
    def __init__(self, definition):
        super().__init__({}, definition.name)
        self.definition = definition

    def get(self, local_vars=None, global_vars=None):
        return self

    def get_member(self, name):
        if name in self.value:
            return self.value[name]
        method = self.definition.methods.get(name)
        if method is not None:
            return BoundMethod(self, name, method)
        Error('AttributeError', f"Type {self.definition.name} has no member '{name}'.")

    def set_member(self, name, value):
        self.value[name] = value

    def __repr__(self):
        return f'<{self.definition.name} instance>'


class BoundMethod:
    def __init__(self, instance, name, function):
        self.instance = instance
        self.name = name
        self.function = function

    def get(self, local_vars=None, global_vars=None):
        return self

    def call(self, args, local_vars, global_vars):
        _, body_block, arg_names = self.function
        params = []
        defaults = {}
        for param in arg_names:
            if isinstance(param, tuple):
                pname, default = param
                defaults[pname] = default
            else:
                pname = param
            if isinstance(pname, str):
                pname = pname.strip()
            if pname and pname != ')':
                params.append(pname)
        if len(args) > len(params):
            Error('TypeError', f'Method {self.name} expected {len(params)} arguments, got {len(args)}.')
        bound_args = list(args)
        for pname in params[len(bound_args):]:
            if pname not in defaults:
                Error('TypeError', f'Method {self.name} missing required argument {pname}.')
            default = defaults[pname]
            while hasattr(default, 'get') and not isinstance(default, (LiteralType, InstanceType, TypeDefinition)):
                default = default.get(local_vars, global_vars)
            bound_args.append(default)
        method_local = [] if self.instance is None else [VariableSpace('my', self.instance)]
        method_local.extend(VariableSpace(name, value) for name, value in zip(params, bound_args))
        try:
            body_block.run(method_local, global_vars)
        except ReturnException as result:
            return result.value
        return NumberType(0)


def is_instance_of(value, target):
    if isinstance(target, Variable):
        target = target.name
    if isinstance(target, TypeDefinition):
        return isinstance(value, InstanceType) and value.definition is target
    builtin_types = {
        'NumberType': NumberType,
        'StringType': StringType,
        'ListType': ListType,
        'NothingType': NothingType,
        'Type': Type,
    }
    target_type = builtin_types.get(target) if isinstance(target, str) else target
    return isinstance(value, target_type) if isinstance(target_type, type) else False


def invoke_magic(value, method_name, args, local_vars, global_vars):
    if not isinstance(value, InstanceType):
        return None
    method = value.definition.methods.get(method_name)
    if method is None:
        return None
    return BoundMethod(value, method_name, method).call(args, local_vars, global_vars)

class NothingType(Type):
    def __init__(self, name: str = '', line: int = 0):
        self.name = name
        self.value = None
        self.line = line
    
    def get(self, local_vars:list, global_vars:list):
        return None

class StringType(LiteralType):
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
    
class IndexAssignCodeLine(CodeLine):
    def __init__(self, base_node, idx_node, val_node, line=0):
        super().__init__("index_assign", line)
        self.base_node = base_node
        self.idx_node = idx_node
        self.val_node = val_node

    def get(self, local_vars, global_vars):
        base_obj = self.base_node
        while not isinstance(base_obj, LiteralType):
            base_obj = self.base_node.get(local_vars, global_vars)
        idx_raw = self.idx_node.get(local_vars, global_vars)
        new_val = self.val_node.get(local_vars, global_vars)

        # 下标转整数
        if hasattr(idx_raw, "get"):
            idx = int(idx_raw.get(local_vars, global_vars))
        else:
            idx = int(idx_raw)
        if isinstance(base_obj, list):
            base_obj = ListType(base_obj)
        # 禁止字符串赋值
        if isinstance(base_obj, StringType):
            raise RuntimeError("String does not support item assignment")
        if not isinstance(base_obj, ListType):
            raise RuntimeError("Only list support index-assign, current is " + str(type(base_obj)))

        items = base_obj.value
        if idx < 0 or idx >= len(items):
            raise IndexError(f"list index {idx} out of range")

        # 原地修改列表，@引用参数外部直接生效
        items[idx] = new_val
        return None

    

class NumberType(LiteralType):
    def __init__(self, value: float | int, name: str = '', line: int = 0):
        if not isinstance(value, (float, int)):
            Error('WCFError', 'Interpreter detected type ' + str(type(value)) + ' while loading NumberType. If you cannot seek the reason, please report on github.') 
        self.value = value
        super().__init__(value, name, line)
        

    def get(self, local_vars=None, global_vars=None):
        return self.value
    
    def __repr__(self):
        return str(self.value)
    
    # Numeric/string/list operator implementations moved to BinaryOperator


class ListType(LiteralType):
    def __init__(self, value: list, name: str = '', line: int = 0, local_vars=None, global_vars=None):
        super().__init__(value, name, line)
    
        self.name = name
        self.value = value
        self.local_vars = local_vars
        self.global_vars = global_vars

    def refresh(self):
        #print('REFRESH')
        normalized = []
        for v in (self.value):
            if isinstance(v, (LiteralType)):
                normalized.append(v)
            elif isinstance(v, list):
                normalized.append(ListType(v))
            elif isinstance(v, (int, float)):
                normalized.append(NumberType(v))
            elif isinstance(v, str):
                normalized.append(StringType(v))
            else:
                while hasattr(v, 'get'):
                    # if (v.get(self.local_vars, self.global_vars)) is None:
                    #     raise RuntimeError('Nonetype detected from value ' + v.name + f' ({str(type(v))})')
                    #print(self.name, ' has varlists: ', self.local_vars, self.global_vars)
                    v = v.get(self.local_vars, self.global_vars)
                normalized.append(v)
        
        self.value = normalized
        #print('value is', self.value)


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
    def __init__(self, var_name: str, value: Type, is_const: bool = False, reference: str = ''):
        self.name = var_name
        self.value = value
        self.is_const = is_const
        self.reference = reference

    def get(self, local_vars=None, global_vars=None):
        return self.value

    def __repr__(self):
        return f'<VS {self.name}{' (Const)' if self.is_const else ''}{f' -> {self.reference}' if self.reference else ''}>'


class VariableDefinitionCodeLine(CodeLine):
    def __init__(self, var_name: str, arg: list[Type], line: int = 0, is_const: bool = False):
        print_debug(f'[VAR_DEF] {var_name} = {arg}')
        self.name = var_name
        self.arg = arg
        self.line = line
        self.is_const = is_const

    def get(self, local_vars: list | None = None, global_vars: list | None = None, force_global = False):
        #print(self.name+'\'s definition base list: ', local_vars, global_vars)
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list

        flag = True
        t = self.arg[0]
        target_list = local_vars if local_vars else global_vars
        # 这里！不要 t.get()，要把上下文传下去

        while not isinstance(t, LiteralType):
            #printtype(t))
          
            if isinstance(t, Variable) and self.name.startswith('@'):
                cname = self.name[1:]
                ref = t.name
                # print(cname, ref)
                try:
                    #printt)
                    t.local_vars = local_vars
                    t.global_vars = global_vars
                    t.refresh()
                  
                    target_list.append(VariableSpace(cname, t.get(local_vars, global_vars), self.is_const))
     
            
                except Exception as e:
              
            
                    target_list.append(VariableSpace(cname, t.get(local_vars, global_vars), self.is_const))

                return 0

            # print_debug(F'[TYPE OF T:{self.var_name}] ', type(t))
            
            t = t.get(local_vars, global_vars)
    

        # 顶层脚本赋值写 global_vars；函数内部赋值写 local_vars
        target_list = (local_vars if local_vars else global_vars) if not force_global else global_vars

        for var in target_list:
            if var.name == self.name:
                if var.is_const:
                    Error('TypeError', f'Cannot reassign to readonly variable {self.name}.', self.line).emit()
                # 传入变量表给需要内部解析的类型
                try:
                    t.global_vars = global_vars
                    t.local_vars = local_vars
                    t.refresh()
                except:pass
                var.value = t
                if var.reference:
                    for a in global_vars + local_vars:
                      
                        if a.name == var.reference:
                            if isinstance(a, VariableSpace): VariableDefinitionCodeLine(a.name, [t], self.line, is_const=var.is_const).get(local_vars, global_vars, force_global = True)
                flag = False
                break
        if flag:
            try:
                #print(t)
                t.local_vars = local_vars
                t.global_vars = global_vars
                t.refresh()
                target_list.append(VariableSpace(self.name, t, self.is_const))
                #print(f'The first time defined: {self.name}', type(t))
        
     
            except Exception as e:
     
            
                target_list.append(VariableSpace(self.name, t.get(local_vars, global_vars), self.is_const))
        return t

    def __repr__(self):
        return f"<VariableDefinitionCodeLine name={self.name!r}>"
    
class Variable(Type):
    def __init__(self, name, line:int=0):
        super().__init__('var', name)
        self.name = name
        self.line = line


    def get(self, local_vars: list | None = None, global_vars: list | None = None):
        if local_vars is None:
            local_vars = []
        if global_vars is None:
            global_vars = var_list
        #print(self.name+'\'s list: ', local_vars, global_vars)
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
            
        Error('NameError', f"Undefined identifier '{self.name}'")
        raise RuntimeError('Nonetype may be produced when processing the value of variable ' + self.name)


class MemberAccess(Type):
    def __init__(self, base, member, line=0):
        super().__init__(None, member, line)
        self.base = base
        self.member = member

    def get(self, local_vars=None, global_vars=None):
        value = self.base
        while hasattr(value, 'get') and not isinstance(value, (InstanceType, TypeDefinition, LiteralType)):
            value = value.get(local_vars, global_vars)
        if not isinstance(value, (InstanceType, TypeDefinition)):
            Error('AttributeError', f"Value has no member '{self.member}'.", self.line)
        return value.get_member(self.member)


class MemberAssignCodeLine(CodeLine):
    def __init__(self, target, value, line=0):
        super().__init__('member_assign', line)
        self.target = target
        self.value = value

    def get(self, local_vars=None, global_vars=None):
        owner = self.target.base
        while hasattr(owner, 'get') and not isinstance(owner, InstanceType):
            owner = owner.get(local_vars, global_vars)
        if not isinstance(owner, InstanceType):
            Error('AttributeError', f"Value has no member '{self.target.member}'.", self.line)
        value = self.value
        while hasattr(value, 'get') and not isinstance(value, LiteralType):
            value = value.get(local_vars, global_vars)
        if isinstance(value, (int, float)):
            value = NumberType(value)
        elif isinstance(value, str):
            value = StringType(value)
        owner.set_member(self.target.member, value)
        return value


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

        # Resolve either a named function or a callable value returned by an expression.
        target_var = None
        callable_value = None
        lookup_name = self.fname.name if hasattr(self.fname, 'name') else self.fname
        if hasattr(self.fname, 'get') and not isinstance(self.fname, Variable):
            callable_value = self.fname.get(local_vars, global_vars)
        else:
            for scope in (local_vars, global_vars):
                for v in reversed(scope):
                    if v.name == lookup_name:
                        target_var = v
                        break
                if target_var is not None:
                    break
            if target_var is not None:
                callable_value = target_var.value
        if target_var is None and callable_value is None:
            Error('NameError', f"Undefined function '{lookup_name}'")

        if isinstance(callable_value, TypeDefinition):
            resolved_args = []
            for arg in self.args or []:
                value = arg
                while hasattr(value, 'get') and not isinstance(value, (LiteralType, InstanceType, TypeDefinition)):
                    value = value.get(local_vars, global_vars)
                resolved_args.append(value)
            return callable_value.instantiate(resolved_args, local_vars, global_vars)

        if isinstance(callable_value, BoundMethod):
            resolved_args = []
            for arg in self.args or []:
                value = arg
                while hasattr(value, 'get') and not isinstance(value, (LiteralType, InstanceType, TypeDefinition)):
                    value = value.get(local_vars, global_vars)
                resolved_args.append(value)
            return callable_value.call(resolved_args, local_vars, global_vars)

        print_debug(f"[FC_DUMP] raw value = {callable_value}")
        print_debug(f"[FC_DUMP] value type = {type(callable_value)}")

        val = callable_value
        if not isinstance(val, tuple):
            raise RuntimeError(f"Function store expects tuple, got {type(val)}")
        is_stored, body_block, arg_names = val

        print_debug(f"[FC_GET] arg_names={arg_names}, types={[type(x) for x in arg_names]}")
        # normalize parameter names: accept strings or Type/Variable with .name
        normalized_arg_names = []
        references = []
        param_defaults = {}
        for p in arg_names:
            if isinstance(p, tuple):
                pname, default_value = p
                if isinstance(pname, str):
                    pn = pname[1:] if pname.startswith('@') else pname
                    normalized_arg_names.append(pn)
                    references.append(pn if pname.startswith('@') else False)
                    param_defaults[pn] = default_value
                    continue
            if isinstance(p, str):
                if p.startswith('@'):
                    pn = p[1:]
                    normalized_arg_names.append(pn)
                    references.append(pn)
                    continue
                references.append(False)
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

        def _resolve_type(value, local, global_, idx = 0):
            while not isinstance(value, (LiteralType, InstanceType, TypeDefinition)):
                if hasattr(value, 'get'):
                    if isinstance(value, Variable):
                        # 处理指针
                        if references[idx]:
                            references[idx] = (references[idx], value.name)
                

                        return value.get(local, global_)
                    
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

        # 解析实参：支持位置参数和命名参数，并应用默认值
        positional_args = []
        named_args = {}
        for a in (self.args or []):
            if isinstance(a, list) and len(a) == 3 and a[0] == 'kwarg':
                kw_name = a[1].name if hasattr(a[1], 'name') else a[1]
                named_args[kw_name] = a[2]
            else:
                positional_args.append(a)

        eval_args = []
        for a in positional_args:
            eval_args.append(_resolve_type(a, local_vars, global_vars, len(eval_args)))

        resolved_map = {}
        used_positional = 0
        for idx, pname in enumerate(arg_names):
            if idx < len(positional_args):
                resolved_map[pname] = _resolve_type(positional_args[idx], local_vars, global_vars, idx)
                used_positional += 1
            else:
                resolved_map[pname] = None

        for kw_name, kw_value in named_args.items():
            if kw_name not in arg_names:
                Error('TypeError', f"Function {self.fname} got unexpected keyword argument '{kw_name}'.", self.line).emit()
            if kw_name in resolved_map and resolved_map[kw_name] is not None:
                Error('TypeError', f"Function {self.fname} got multiple values for argument '{kw_name}'.", self.line).emit()
            resolved_map[kw_name] = _resolve_type(kw_value, local_vars, global_vars, 0)

        final_eval_args = []
        for pname in arg_names:
            if resolved_map.get(pname) is None:
                if pname in param_defaults:
                    resolved_map[pname] = _resolve_type(param_defaults[pname], local_vars, global_vars, 0)
                else:
                    Error('TypeError', f"Function {self.fname} missing required argument '{pname}'.", self.line).emit()
            final_eval_args.append(resolved_map[pname])

        eval_args = final_eval_args
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
        for param_name, real_val, ref in zip(arg_names, eval_args, references):
            pname = param_name if isinstance(param_name, str) else str(param_name)
            func_local.append(VariableSpace(pname, real_val, reference = (ref[1] if ref else '')))
         

      
        print_debug(f"[FC_BIND] func={self.fname}, params={[(v.name, type(v.value)) for v in func_local]}")
    

        ret = NumberType(0)
        print_debug(f'[FUNCTION RESOLVE {self.fname}]')
        try:
            body_block.run(func_local, global_vars)

        except ReturnException as re:

            ret = re.value
            ##print('[FUNCTION RETURN VAL]', ret)

        print_debug(f'[FC {self.fname}]Run ended.')
        result = _resolve_type(ret, local_vars, global_vars)
        ##print(f'[FC_CACHE {self.fname}] READY TO STORE')
        try:
            if not is_user_defined_func:
                return result
            prim = _to_primitive(result)
            function_call_cache.setdefault(func_name, {})[args_key] = prim
            function_call_disk_cache.setdefault(func_name, {})[args_key] = prim
            print_debug(f"[FC_CACHE_STORE] func={func_name}, args={args_key}, value={prim}")
        except Exception as e:
            print_debug(f"[FC_CACHE_STORE_ERROR]" + str(e))

        ##print('[Function return value]', result)
        
        return result

var_list: list[VariableSpace] = [VariableSpace('true', NumberType(1)), VariableSpace('false', NumberType(0)), VariableSpace('inf', NumberType(INF)), VariableSpace('nega_inf', NumberType(-INF)), VariableSpace('nothing', NothingType())]    
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
                # #print('function ', func_name, ' is actually cachable!!!')
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
            while not isinstance(value, (LiteralType, NothingType, InstanceType, TypeDefinition)) and hasattr(value, 'get'):
                value = value.get(local_vars, global_vars)
            return value

        a = _resolve(a)
        if self.operator == 'is':
            if isinstance(b, Variable):
                try:
                    b = b.get(local_vars, global_vars)
                except (WantedError, RuntimeError):
                    pass
            return NumberType(1 if is_instance_of(a, b) else 0)
        if isinstance(a, (int, float)): a = NumberType(a)
        if isinstance(a, str): a = StringType(a)
        b = _resolve(b)
        if isinstance(b, (int, float)): b = NumberType(b)
        if isinstance(b, str): b = StringType(b)

        a_val = a.get(local_vars, global_vars) if isinstance(a, (LiteralType)) else a
        b_val = b.get(local_vars, global_vars) if isinstance(b, (LiteralType)) else b

        magic_names = {
            '+': '_add', '-': '_sub', '*': '_mul', '/': '_div',
            '//': '_floordiv', '^': '_pow', '==': '_eq', '!=': '_ne',
            '<': '_lt', '<=': '_le', '>': '_gt', '>=': '_ge',
            '->': '_convert',
        }
        magic_name = magic_names.get(self.operator)
        if self.operator == '->' and isinstance(b, TypeDefinition):
            convert_method = b.methods.get('_convert')
            if convert_method is not None:
                target_instance = b.instantiate([a], local_vars, global_vars)
                return BoundMethod(target_instance, '_convert', convert_method).call([a], local_vars, global_vars)
            Error('TypeError', f"Type {b.name} does not define '_convert'.")
        if magic_name and isinstance(a, InstanceType):
            magic_result = invoke_magic(a, magic_name, [b], local_vars, global_vars)
            if magic_result is not None:
                return magic_result
        from lib.wcore.dec import add, sub, mul, div
        # arithmetic
        if isinstance(a, NothingType) or isinstance(b, NothingType):
            Error('TypeError', 'NothingType does not support binary operators.')
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
                if isinstance(a, StringType) and isinstance(b, (NumberType, ListType)):
                    return StringType(a_val + str(b_val))
                if isinstance(a, ListType) and isinstance(b, ListType):
                    return ListType(a_val + b_val)
                if isinstance(a, ListType):
                    return ListType(a_val + ([b_val] if not isinstance(b_val, list) else b_val))
                if isinstance(b, ListType):
                    return ListType(([a_val] if not isinstance(a_val, list) else a_val) + b_val)
                if isinstance(a, StringType) or isinstance(b, StringType):
                    return StringType(str(a_val) + str(b_val))
                #print('Never errors: ', a_val, b_val)
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
                    Error('ZeroDivisionError', 'Cannot divide by zero.')
                return NumberType(div(a_val, b_val))
            case '//':
                if isinstance(b_val, (int, float)) and float(b_val) == 0:
                    Error('ZeroDivisionError', 'Cannot divide by zero.')
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
      
base_type = (ListType, NumberType, StringType)
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
