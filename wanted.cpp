#include "lib/bin/wanted_runtime.hpp"

#include <exception>
#include <iostream>
#include <string>

#ifdef _WIN32
#include <windows.h>
#endif

int main(int argc, char** argv) {
#ifdef _WIN32
	SetConsoleOutputCP(CP_UTF8);
	SetConsoleCP(CP_UTF8);
#endif
	try {
		wanted::Interpreter interpreter;
		if (argc < 2) {
			std::cerr << "Usage: wanted <source.wcn>\n";
			return 2;
		}
		interpreter.runFile(argv[1]);
		return 0;
	} catch (const wanted::ExecutionError& error) {
		std::cerr << "Error:\n";
		std::cerr << "Occured in line " << error.line << " of file \"" << error.filename << "\"\n";
		if (!error.sourceText.empty()) std::cerr << "\t" << error.sourceText << '\n';
		std::cerr << error.errorType << ": " << error.what() << '\n';
		return 1;
	} catch (const std::exception& error) {
		std::cerr << "Error:\n";
		std::cerr << "Occured in line 0 of file \"" << (argc > 1 ? argv[1] : "<input>") << "\"\n";
		std::cerr << "RuntimeError: " << error.what() << '\n';
		return 1;
	}
}
