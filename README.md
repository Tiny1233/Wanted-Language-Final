# Wanted

Wanted is an interpreted programming language. Its primary interpreter is implemented in C++; this repository also includes a Python implementation and supporting tools. It contains the runtime, bundled libraries, example programs, and language tests.

## Features

- Variables, aliases, and numeric and string values
- Lists and nested list access
- Functions with default and named arguments
- Conditional branches and repeat/while loops
- Arithmetic, comparison, and compound assignment operators
- Built-in and external Wanted libraries

## Requirements

- A C++11-compatible compiler, such as `g++`, to build the primary interpreter
- Python 3.12 or later for the Python implementation and optional tools
- Nuitka is only needed to build a standalone executable with the Python packaging helper `wper.py`

There is no package installation step. Build the C++ interpreter from the repository root:

```console
g++ -std=c++11 wanted.cpp lib/bin/wanted_runtime.cpp -o wanted.exe
```

Run a Wanted source file with the C++ interpreter:

```console
.\wanted.exe test.wcn
```

Create a file named `hello.wcn`:

```text
getwcore 'stdout' 'Hello, Wanted!'
```

Then run it:

```console
.\wanted.exe hello.wcn
```

## Language example

```text
ext @builtin.wcn

func add(a, b = 1):
    return a + b

result = add(4)
outln(result)

rep 3:
    outln('Wanted')
```

## Project layout

| Path | Description |
| --- | --- |
| `wanted.cpp` | Entry point for the primary C++ interpreter |
| `lib/bin/wanted_runtime.cpp`, `lib/bin/wanted_runtime.hpp` | C++ interpreter implementation |
| `wcf.h` | Runtime value definitions used by the C++ interpreter |
| `wanted.py`, `wcf.py` | Python interpreter implementation and runtime support |
| `wper.py` | Optional helper for packaging a Python-interpreted program as an executable |
| `lib/` | Bundled libraries and Python runtime support |
| `test/` | Wanted language test programs |
| `tutorial.ipynb` | Interactive tutorial |

## Tests

The tests are Wanted source files rather than a single configured test suite. Build the C++ interpreter, then run an individual test from the repository root, for example:

```console
.\wanted.exe test\assert\test_arithmetic_precedence_multiplication.wcn
```

## Build a standalone executable

The repository also contains a Python packaging helper for creating an executable from a Wanted source file. Install Nuitka in the Python environment, then run:

```console
python -m pip install nuitka
python wper.py test.wcn
```

The generated executable is written alongside the input source file.

## Contributing

Contributions and bug reports are welcome. When submitting a change, include a minimal reproduction or a test program where applicable.

## License

MIT License

Copyright (c) 2026 Tiny1233

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.