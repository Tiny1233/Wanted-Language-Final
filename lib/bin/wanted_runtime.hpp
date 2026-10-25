#ifndef WANTED_RUNTIME_HPP
#define WANTED_RUNTIME_HPP

#include "../../wcf.h"
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace wanted {

class ExecutionError : public std::runtime_error {
public:
    std::string errorType;
    std::string filename;
    std::string sourceText;
    int line;

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
    std::vector<std::map<std::string, Value> > scopes_;
    std::vector<std::map<std::string, VariableLocation> > references_;
    std::set<std::string> loadedModules_;
    std::set<std::string> loadedTypes_;
    std::map<std::string, std::shared_ptr<TypeValue> > moduleNamespaces_;
    std::string filename_;
    Value evaluate(const ASTNode& node);
    void execute(const ASTNode& node);
    void executeBlock(const std::vector<ASTNode>& nodes);
    Value call(const Value& callable, const ASTNode& node);
    Value invoke(const std::shared_ptr<FunctionValue>& function, const std::vector<Value>& args,
                 const std::map<std::string, Value>& named,
                 const std::vector<VariableLocation>& positionalReferences,
                 const std::map<std::string, VariableLocation>& namedReferences,
                 const std::shared_ptr<InstanceValue>& owner = std::shared_ptr<InstanceValue>());
    Value callBuiltin(const std::string& name, const std::vector<Value>& args);
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