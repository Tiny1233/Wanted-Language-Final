import wcf

wcf.var_list[:] = [
    wcf.VariableSpace('true', wcf.NumberType(1)),
    wcf.VariableSpace('false', wcf.NumberType(0)),
    wcf.VariableSpace('inf', wcf.NumberType(wcf.INF)),
    wcf.VariableSpace('nega_inf', wcf.NumberType(-wcf.INF)),
]

body = wcf.CodeBlock([
    wcf.KeywordCodeLine('if', [
        wcf.BinaryOperator('==', wcf.Variable('n'), wcf.NumberType(1)),
        wcf.CodeBlock([wcf.KeywordCodeLine('return', [wcf.NumberType(1)])]),
        wcf.KeywordCodeLine('eif', [
            wcf.BinaryOperator('==', wcf.Variable('n'), wcf.NumberType(2)),
            wcf.CodeBlock([wcf.KeywordCodeLine('return', [wcf.NumberType(1)])]),
        ]),
        wcf.KeywordCodeLine('else', [
            wcf.CodeBlock([
                wcf.KeywordCodeLine('return', [
                    wcf.BinaryOperator(
                        '+',
                        wcf.FunctionCall('fibo', [wcf.BinaryOperator('-', wcf.Variable('n'), wcf.NumberType(1))]),
                        wcf.FunctionCall('fibo', [wcf.BinaryOperator('-', wcf.Variable('n'), wcf.NumberType(2))]),
                    )
                ])
            ])
        ])
    ])
])

wcf.var_list.append(wcf.VariableSpace('fibo', (body, ['n'])))
print('before', wcf.function_call_cache)
res = wcf.FunctionCall('fibo', [wcf.NumberType(4)]).get([], wcf.var_list)
print('result', res)
print('after', wcf.function_call_cache)
print('after_disk', wcf.function_call_disk_cache)
