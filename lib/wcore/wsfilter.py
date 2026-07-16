def wsfilter(a):
    if isinstance(a, (int, float)):
        return a
    filteritem = [
        ('\\n', '\n'),
        ('\\\\', '\\'),
        ('\\c', '#'),
        ('\\t', '\t')
        
    ]
    st = a
    for item in filteritem:
        st = st.replace(item[0], item[1])
    return st

if __name__ == '__main__':
    print(wsfilter('\\n'))