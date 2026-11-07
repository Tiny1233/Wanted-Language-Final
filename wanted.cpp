#include "lib/bin/wanted_runtime.hpp"

#include <exception>
#include <iostream>
#include <algorithm>
#include <string>

namespace {
void printSourceLine(int line, const std::string& source, std::size_t width, std::size_t indent) {
	std::cerr << std::string(indent + (line > 0 ? width - std::to_string(line).size() : width), ' ');
	if (line > 0) std::cerr << line;
	std::cerr << " | " << source << '\n';
}
}

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
		std::cerr << "   Occured in file \"" << error.filename << "\":\n";
		int callerLine = error.line;
		std::string callerSource = error.sourceText;
		std::string callerFilename = error.filename;
		if (!error.traceFrames.empty()) {
			const wanted::ExecutionTraceFrame& caller = error.traceFrames.back();
			if (caller.callLine > 0) {
				callerLine = caller.callLine;
				callerSource = caller.callSource;
				callerFilename = caller.callFilename;
			}
		}
		std::size_t lineWidth = std::to_string(std::max(1, callerLine)).size();
		lineWidth = std::max(lineWidth, std::to_string(std::max(1, error.line)).size());
		for (std::size_t i = 0; i < error.traceFrames.size(); ++i) {
			lineWidth = std::max(lineWidth, std::to_string(std::max(1, error.traceFrames[i].definitionLine)).size());
			lineWidth = std::max(lineWidth, std::to_string(std::max(1, error.traceFrames[i].callLine)).size());
		}
		std::cerr << "      line " << callerLine << ", in \"" << callerFilename << "\":\n";
		if (!callerSource.empty()) printSourceLine(callerLine, callerSource, lineWidth, 10);
		for (std::size_t i = error.traceFrames.size(); i > 0; --i) {
			const wanted::ExecutionTraceFrame& frame = error.traceFrames[i - 1];
			const int targetLine = i > 1 ? error.traceFrames[i - 2].callLine : error.line;
			const std::string& targetSource = i > 1 ? error.traceFrames[i - 2].callSource : error.sourceText;
			std::cerr << "      -> line " << frame.definitionLine << ", in " << frame.functionName
				<< " (\"" << frame.definitionFilename << "\"):\n";
			printSourceLine(frame.definitionLine, frame.definitionSource, lineWidth, 10);
			if (targetLine > frame.definitionLine + 1)
				printSourceLine(0, "...", lineWidth, 10);
			if (targetLine > 0 && targetLine != frame.definitionLine && !targetSource.empty()) {
				const std::string& targetFilename = i > 1
					? error.traceFrames[i - 2].callFilename : error.filename;
				std::cerr << "          in \"" << targetFilename << "\":\n";
				printSourceLine(targetLine, targetSource, lineWidth, 10);
			}
		}
		std::cerr << error.errorType << ": " << error.what() << '\n';
		return 1;
	} catch (const std::exception& error) {
		std::cerr << "Error:\n";
		std::cerr << "Occured in line 0 of file \"" << (argc > 1 ? argv[1] : "<input>") << "\"\n";
		std::cerr << "RuntimeError: " << error.what() << '\n';
		return 1;
	}
}
