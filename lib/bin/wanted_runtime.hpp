#ifndef WANTED_RUNTIME_HPP
#define WANTED_RUNTIME_HPP

#include "../../wcf.h"
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace wanted {

struct ExecutionTraceFrame {
    std::string functionName;
    std::string definitionFilename;
    std::string callFilename;
    std::string definitionSource;
    std::string callSource;
    int definitionLine;
    int callLine;

    ExecutionTraceFrame(const std::string& name, const std::string& definitionFile,
        const std::string& callFile, const std::string& definition, int definitionNumber,
        const std::string& call, int callNumber)
        : functionName(name), definitionFilename(definitionFile), callFilename(callFile),
          definitionSource(definition), callSource(call),
          definitionLine(definitionNumber), callLine(callNumber) {}
};

class ExecutionError : public std::runtime_error {
public:
    std::string errorType;
    std::string filename;
    std::string sourceText;
    int line;
    std::vector<ExecutionTraceFrame> traceFrames;

    ExecutionError(const std::string& type, const std::string& message, const std::string& file,
        int sourceLine, const std::string& source)
        : std::runtime_error(message), errorType(type), filename(file), sourceText(source), line(sourceLine) {}
};

class Interpreter {
public:
    Interpreter();
    void runFile(const std::string& path);
    void runSource(const std::string& source, const std::string& filename = "<input>");

private:
    struct VariableLocation {
        int scope;
        std::string name;
        VariableLocation(int scopeIndex = -2, const std::string& variableName = "")
            : scope(scopeIndex), name(variableName) {}
    };

    std::map<std::string, Value> globals_;
    std::map<std::string, VariableLocation> globalReferences_;
    std::set<std::string> readOnlyGlobals_;
    std::vector<std::map<std::string, Value> > scopes_;
    std::vector<std::map<std::string, VariableLocation> > references_;
    std::vector<std::set<std::string> > readOnlyScopes_;
    std::set<std::string> loadedModules_;
    std::set<std::string> loadedTypes_;
    std::map<std::string, std::shared_ptr<TypeValue> > moduleNamespaces_;
    std::string filename_;
    int currentSourceLine_;
    std::string currentSourceText_;
    Value evaluate(const ASTNode& node);
    std::string stringify(const Value& value);
    void execute(const ASTNode& node);
    void executeBlock(const std::vector<ASTNode>& nodes);
    Value call(const Value& callable, const ASTNode& node);
    Value invoke(const std::shared_ptr<FunctionValue>& function, const std::vector<Value>& args,
                 const std::map<std::string, Value>& named,
                 const std::vector<VariableLocation>& positionalReferences,
                 const std::map<std::string, VariableLocation>& namedReferences,
                 const ASTNode& callNode,
                 const std::shared_ptr<InstanceValue>& owner = std::shared_ptr<InstanceValue>());
    Value callBuiltin(const std::string& name, const std::vector<Value>& args);
    bool matchesErrorHandler(const std::string& type, const std::string& errorType) const;
    Value lookup(const std::string& name) const;
    void assign(const std::string& name, const Value& value);
    std::size_t referenceDepthLimit() const;
    VariableLocation resolveLocation(const std::string& name) const;
    Value readLocation(const VariableLocation& location) const;
    void writeLocation(const VariableLocation& location, const Value& value);
};

std::vector<ASTNode> parseProgram(const std::string& source);

} // namespace wanted

#endif