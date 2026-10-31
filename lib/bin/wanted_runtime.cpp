// gcc compile: g++ -std=c++11 wanted.cpp lib/bin/wanted_runtime.cpp -o wanted.exe

#include "wanted_runtime.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace wanted {
namespace {
struct SourceLine;
// basic utilities for the interpreter
// tokens
typedef std::vector<std::string> Tokens;
// precision of division
const int DIVISION_PRECISION = 100;

// judge if equal, LHS and RHS are both Value
bool valuesEqual(const Value& left, const Value& right,
                 std::vector<std::pair<const InstanceValue*, const InstanceValue*> >& comparedInstances) {
    // if the type is different, return false directly
    if (left.kind != right.kind) return false;
    // otherwise, judge their values
    if (left.kind == Value::Number) return left.number == right.number;
    if (left.kind == Value::String) return left.string == right.string;
    if (left.kind == Value::Instance) {
        if (left.instance == right.instance) return true;
        if (left.instance->type != right.instance->type ||
            left.instance->members.size() != right.instance->members.size()) return false;

        for (std::size_t i = 0; i < comparedInstances.size(); ++i) {
            if ((comparedInstances[i].first == left.instance.get() &&
                 comparedInstances[i].second == right.instance.get()) ||
                (comparedInstances[i].first == right.instance.get() &&
                 comparedInstances[i].second == left.instance.get())) return true;
        }
        comparedInstances.push_back(std::make_pair(left.instance.get(), right.instance.get()));

        for (std::map<std::string, Value>::const_iterator member = left.instance->members.begin();
             member != left.instance->members.end(); ++member) {
            std::map<std::string, Value>::const_iterator other = right.instance->members.find(member->first);
            if (other == right.instance->members.end() ||
                !valuesEqual(member->second, other->second, comparedInstances)) return false;
        }
        return true;
    }
    // list comparison
    if (left.kind == Value::List) {
        // if length is different, return false directly
        if (left.list.size() != right.list.size()) return false;
        // compare each element
        for (std::size_t i = 0; i < left.list.size(); ++i)
            if (!valuesEqual(left.list[i], right.list[i], comparedInstances)) return false;
        return true;
    }
    // function comparison, compare their string representation
    return left.toString() == right.toString();
}

bool valuesEqual(const Value& left, const Value& right) {
    std::vector<std::pair<const InstanceValue*, const InstanceValue*> > comparedInstances;
    return valuesEqual(left, right, comparedInstances);
}

bool isNumericValue(const Value& value) {
    return value.kind == Value::Number || value.kind == Value::PositiveInfinity || value.kind == Value::NegativeInfinity;
}

int compareNumericValues(const Value& left, const Value& right) {
    if (left.kind == Value::PositiveInfinity) return right.kind == Value::PositiveInfinity ? 0 : 1;
    if (left.kind == Value::NegativeInfinity) return right.kind == Value::NegativeInfinity ? 0 : -1;
    if (right.kind == Value::PositiveInfinity) return -1;
    if (right.kind == Value::NegativeInfinity) return 1;
    if (left.number < right.number) return -1;
    if (left.number > right.number) return 1;
    return 0;
}

// utilities for parsing and evaluating the source code
std::string trim(const std::string& value) {
    // trim leading and trailing whitespace characters
    std::string::size_type first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    std::string::size_type last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string unquote(const std::string& value) {
    if (value.size() >= 2 && (value[0] == '\'' || value[0] == '"') && value[value.size() - 1] == value[0])
        return value.substr(1, value.size() - 2);
    return value;
}

// utilities for handling file paths, such as getting the directory of a path, joining paths, and checking if a file can be opened
std::size_t utf8Next(const std::string& value, std::size_t offset) {
    // determine the next character position in a UTF-8 encoded string
    // if the offset is beyond the string size, return the string size
    if (offset >= value.size()) return value.size();
    unsigned char lead = static_cast<unsigned char>(value[offset]);
    // determine the width of the UTF-8 character based on the lead byte
    std::size_t width = lead < 0x80 ? 1 : (lead & 0xE0) == 0xC0 ? 2 : (lead & 0xF0) == 0xE0 ? 3 : (lead & 0xF8) == 0xF0 ? 4 : 1;
    return std::min(value.size(), offset + width);
}

// utilities for handling file paths
std::string pathDirectory(const std::string& path) {
    std::string::size_type separator = path.find_last_of("/\\");
    if (separator == std::string::npos) return ".";
    if (separator == 0) return path.substr(0, 1);
    if (separator == 2 && path.size() > 1 && path[1] == ':') return path.substr(0, 3);
    return path.substr(0, separator);
}

// get the parent directory of a given path
std::string parentPath(const std::string& path) {
    std::string parent = pathDirectory(path);
    if (parent == path || parent == ".") return "";
    return parent;
}

// join path, literally
std::string joinPath(const std::string& directory, const std::string& path) {
    if (directory.empty() || directory == ".") return path;
    if (directory[directory.size() - 1] == '/' || directory[directory.size() - 1] == '\\') return directory + path;
    return directory + "/" + path;
}

// returns whether the file can be opened
bool canOpenFile(const std::string& path) {
    std::ifstream file(path.c_str(), std::ios::in | std::ios::binary);
    return file.good();
}

// strip comments from a line of code, considering quotes and escape characters
std::string stripComment(const std::string& line) {
    char quote = 0;
    bool escape = false;
    for (std::string::size_type i = 0; i < line.size(); ++i) {
        char ch = line[i];
        if (quote) {
            if (escape) escape = false;
            // akimbo quotes, 2x for each one
            else if (ch == '\\') escape = true;
            else if (ch == quote) quote = 0;
        } else if (ch == '\'' || ch == '"') quote = ch;
        else if (ch == '#') return line.substr(0, i);
    }
    return line;
}

std::size_t findTopLevelColon(const std::string& text) {
    int depth = 0;
    char quote = 0;
    bool escape = false;
    for (std::size_t i = 0; i < text.size(); ++i) {
        char ch = text[i];
        if (quote) {
            if (escape) escape = false;
            else if (ch == '\\') escape = true;
            else if (ch == quote) quote = 0;
            continue;
        }
        if (ch == '\'' || ch == '"') { quote = ch; continue; }
        if (ch == '(' || ch == '[' || ch == '{') ++depth;
        else if (ch == ')' || ch == ']' || ch == '}') --depth;
        else if (depth == 0 && ch == ':') return i;
    }
    return std::string::npos;
}

bool isBlockHeader(const std::string& text) {
    std::string trimmed = trim(text);
    if (trimmed.empty()) return false;
    if (trimmed == "else:" || trimmed == "please:" || trimmed == "final:") return true;
    return trimmed.compare(0, 4, "if ") == 0 || trimmed.compare(0, 5, "eif ") == 0 ||
           trimmed.compare(0, 4, "rep ") == 0 || trimmed.compare(0, 6, "while ") == 0 ||
           trimmed.compare(0, 6, "func ") == 0 || trimmed.compare(0, 5, "type ") == 0;
}

std::vector<std::string> splitInlineBlockLine(const std::string& line) {
    std::string text = trim(line);
    if (text.empty()) return {};
    char quote = 0;
    bool escape = false;
    for (std::size_t i = 0; i + 1 < text.size(); ++i) {
        char ch = text[i];
        if (quote) {
            if (escape) escape = false;
            else if (ch == '\\') escape = true;
            else if (ch == quote) quote = 0;
            continue;
        }
        if (ch == '\'' || ch == '"') { quote = ch; continue; }
        if (ch == '#' && text[i + 1] == ':') {
            std::string before = trim(text.substr(0, i));
            std::string after = trim(text.substr(i + 2));
            if (before.empty()) return { trim(stripComment(line)) };
            std::string header = before;
            std::size_t colon = findTopLevelColon(before);
            if (colon == std::string::npos) return { trim(stripComment(line)) };
            std::string beforeColon = trim(before.substr(0, colon + 1));
            if (!isBlockHeader(beforeColon)) return { trim(stripComment(line)) };
            std::string body = trim(before.substr(colon + 1));
            if (!after.empty()) body = body.empty() ? after : body + " " + after;
            if (body.empty()) return { beforeColon };
            return { beforeColon, body };
        }
    }
    std::string cleaned = trim(stripComment(line));
    if (cleaned.empty()) return {};
    return { cleaned };
}

// count indent
int indentation(const std::string& line) {
    int count = 0;
    while (count < static_cast<int>(line.size()) && line[count] == ' ') ++count;
    return count;
}

// tokenize the code
Tokens tokenize(const std::string& input) {
    Tokens result;
    for (std::string::size_type i = 0; i < input.size();) {
        unsigned char ch = static_cast<unsigned char>(input[i]);
        // ignore whitespace
        if (std::isspace(ch)) { ++i; continue; }
        // handle string literals and interpolated strings
        bool interpolated = input[i] == '$' && i + 1 < input.size() && (input[i + 1] == '\'' || input[i + 1] == '"');
        // ############## String Tokenizer ###############
        if (input[i] == '\'' || input[i] == '"' || interpolated) {
            if (interpolated) ++i;
            char quote = input[i++];
            std::string text;
            // generate the string
            while (i < input.size() && input[i] != quote) {
                if (input[i] == '\\' && i + 1 < input.size()) {
                    // handle escape characteres
                    ++i;
                    char escaped = input[i++];
                    if (escaped == 'n') text += '\n';
                    else if (escaped == 't') text += '\t';
                    else text += escaped;
                } else text += input[i++];
            }
            if (i < input.size()) ++i;
            result.push_back(std::string(1, interpolated ? '\x02' : '\x01') + text);
            continue;
        }
        // ############## Number Tokenizer ###############
        if (std::isdigit(ch) || (input[i] == '.' && i + 1 < input.size() && std::isdigit(static_cast<unsigned char>(input[i + 1])))) {
            std::string number;
            bool dot = false;
            while (i < input.size()) {
                char digit = input[i];
                if (std::isdigit(static_cast<unsigned char>(digit))) { number += digit; ++i; }
                else if (digit == '.' && !dot) { dot = true; number += digit; ++i; }
                else break;
            }
            result.push_back(number);
            continue;
        }
        // ############## Identifier Tokenizer ###############
        if (std::isalpha(ch) || input[i] == '_' || input[i] == '@') {
            std::string name;
            while (i < input.size()) {
                unsigned char c = static_cast<unsigned char>(input[i]);
                if (!std::isalnum(c) && input[i] != '_' && input[i] != '@') break;
                name += input[i++];
            }
            result.push_back(name);
            continue;
        }
        // ############## Operator Tokenizer ###############
        if (i + 1 < input.size()) {
            // handle operator that has 2 or 3 characters, such as //=, ->, ==, !=, >=, <=, +=, -=, *=, /=, ^=
            
            if (i + 2 < input.size() && input.substr(i, 3) == "//=") {
                // 2 chars
                result.push_back("//="); i += 3; continue;
            }

            // 2 chars
            std::string pair = input.substr(i, 2);
            if (pair == "//" || pair == "->" || pair == "==" || pair == "!=" || pair == ">=" || pair == "<=" ||
                pair == "+=" || pair == "-=" || pair == "*=" || pair == "/=" || pair == "^=") {
                result.push_back(pair); i += 2; continue;
            }
        }
        // 1 character
        result.push_back(input.substr(i, 1));
        ++i;
    }
    return result;
}

// parse expr
struct ExpressionParser {
    Tokens tokens;
    std::size_t position;
    // parse the expression and return the ASTNode
    explicit ExpressionParser(const Tokens& source) : tokens(source), position(0) {}
    // return the next token without consuming it
    std::string peek() const { return position < tokens.size() ? tokens[position] : ""; }
    // consume the next token and return it
    std::string take() { return (position < tokens.size()) ? tokens[position++] : ""; }
    
    // accept the next token if it matches the given token, and return true; otherwise, return false
    bool accept(const std::string& token) { if (peek() != token) return false; ++position; return true; }

    ASTNode parse() { return parseCompare(); }

    // parse comparison operators, such as ==, !=, <, >, <=, >=, is
    ASTNode parseCompare() {
        ASTNode left = parseAdd();
        while (peek() == "==" || peek() == "!=" || peek() == "<" || peek() == ">" ||
               peek() == "<=" || peek() == ">=" || peek() == "is") {
            std::string op = take();
            ASTNode node(ASTNode::Binary, op);
            node.children.push_back(left);
            node.children.push_back(parseAdd());
            left = node;
        }
        if (accept("->")) {
            ASTNode node(ASTNode::Binary, "->");
            node.children.push_back(left);
            node.children.push_back(parseCompare());
            left = node;
        }
        return left;
    }

    ASTNode parseAdd() {
        ASTNode left = parseProduct();
        while (peek() == "+" || peek() == "-") {
            std::string op = take(); ASTNode node(ASTNode::Binary, op);
            node.children.push_back(left); node.children.push_back(parseProduct()); left = node;
        }
        return left;
    }

    ASTNode parseProduct() {
        ASTNode left = parsePower();
        while (peek() == "*" || peek() == "/" || peek() == "//" || peek() == "%") {
            std::string op = take(); ASTNode node(ASTNode::Binary, op);
            node.children.push_back(left); node.children.push_back(parsePower()); left = node;
        }
        return left;
    }

    ASTNode parsePower() {
        ASTNode left = parseUnary();
        if (accept("^")) {
            ASTNode node(ASTNode::Binary, "^");
            node.children.push_back(left); node.children.push_back(parsePower()); return node;
        }
        return left;
    }

    ASTNode parseUnary() {
        if (peek() == "-" || peek() == "+" || peek() == "!") {
            ASTNode node(ASTNode::Unary, take()); node.children.push_back(parseUnary()); return node;
        }
        return parsePrimary();
    }

    ASTNode parsePrimary() {
        std::string token = take();
        ASTNode node;
        if (token.empty()) return ASTNode();
        if (token[0] == '\x01') node = ASTNode(ASTNode::String, token.substr(1));
        else if (token[0] == '\x02') node = ASTNode(ASTNode::InterpolatedString, token.substr(1));
        else if (std::isdigit(static_cast<unsigned char>(token[0])) || token[0] == '.') node = ASTNode(ASTNode::Number, token);
        else if (token == "getwcore") {
            ASTNode call(ASTNode::Call);
            call.children.push_back(ASTNode(ASTNode::Identifier, "getwcore"));
            std::string command = take();
            call.children.push_back(ASTNode(ASTNode::String, command.size() && command[0] == '\x01' ? command.substr(1) : command));
            call.children.push_back(parseCompare());
            return call;
        }
        else if (token == "(") {
            node = parseCompare(); accept(")");
        } else if (token == "{" || token == "[") {
            node = ASTNode(ASTNode::List);
            std::string close = token == "{" ? "}" : "]";
            while (!peek().empty() && peek() != close) {
                node.children.push_back(parseCompare());
                if (!accept(",")) break;
            }
            accept(close);
        } else node = ASTNode(ASTNode::Identifier, token);

        while (true) {
            if (accept(".")) {
                ASTNode member(ASTNode::Member, take());
                member.children.push_back(node);
                node = member;
                continue;
            }
            if (accept("[")) {
                ASTNode index(ASTNode::Index);
                index.children.push_back(node);
                index.children.push_back(parseCompare());
                accept("]");
                node = index;
                continue;
            }
            if (accept("(")) {
                ASTNode call(ASTNode::Call);
                call.children.push_back(node);
                while (!peek().empty() && peek() != ")") {
                    if (position + 1 < tokens.size() && tokens[position + 1] == "=") {
                        call.argumentNames.push_back(take()); take();
                    } else call.argumentNames.push_back("");
                    call.children.push_back(parseCompare());
                    if (!accept(",")) break;
                }
                accept(")"); node = call;
                continue;
            }
            break;
        }
        return node;
    }
};

struct SourceLine { int indent; std::string text; int number; };

namespace {
std::size_t nextAnonymousFunctionId() {
    static std::size_t id = 0;
    return id++;
}

bool isIdentifierBodyChar(char ch) {
    return std::isalnum(static_cast<unsigned char>(ch)) || ch == '_' || ch == '@' || ch == '.';
}

std::size_t findMatchingDelimiter(const std::string& text, std::size_t openIndex) {
    if (openIndex >= text.size()) return std::string::npos;
    char open = text[openIndex];
    char close = open == '(' ? ')' : open == '[' ? ']' : '}';
    int depth = 0;
    char quote = 0;
    bool escape = false;
    for (std::size_t i = openIndex; i < text.size(); ++i) {
        char ch = text[i];
        if (quote) {
            if (escape) escape = false;
            else if (ch == '\\') escape = true;
            else if (ch == quote) quote = 0;
            continue;
        }
        if (ch == '\'' || ch == '"') { quote = ch; continue; }
        if (ch == open) ++depth;
        else if (ch == close) {
            --depth;
            if (depth == 0) return i;
        }
    }
    return std::string::npos;
}

std::vector<SourceLine> expandAnonymousFunctions(const SourceLine& line) {
    std::string text = line.text;
    std::size_t candidate = 0;
    while (candidate < text.size()) {
        candidate = text.find("func", candidate);
        if (candidate == std::string::npos) break;
        if ((candidate > 0 && isIdentifierBodyChar(text[candidate - 1])) ||
            (candidate + 4 < text.size() && isIdentifierBodyChar(text[candidate + 4]))) {
            ++candidate;
            continue;
        }

        std::size_t pos = candidate + 4;
        while (pos < text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) ++pos;
        if (pos + 6 <= text.size() && text.compare(pos, 6, "stored") == 0) {
            pos += 6;
            while (pos < text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) ++pos;
        }
        if (pos >= text.size() || text[pos] != '(') {
            ++candidate;
            continue;
        }

        std::size_t firstOpen = pos;
        std::size_t firstClose = findMatchingDelimiter(text, firstOpen);
        if (firstClose == std::string::npos || firstClose + 1 >= text.size()) {
            ++candidate;
            continue;
        }

        std::size_t bodyCursor = firstClose + 1;
        while (bodyCursor < text.size() && std::isspace(static_cast<unsigned char>(text[bodyCursor]))) ++bodyCursor;
        if (bodyCursor >= text.size() || text[bodyCursor] != '(') {
            ++candidate;
            continue;
        }

        std::size_t secondOpen = bodyCursor;
        std::size_t secondClose = findMatchingDelimiter(text, secondOpen);
        if (secondClose == std::string::npos) {
            ++candidate;
            continue;
        }

        std::string params = text.substr(firstOpen + 1, firstClose - firstOpen - 1);
        std::string body = text.substr(secondOpen + 1, secondClose - secondOpen - 1);
        std::string prefix = text.substr(0, candidate);
        std::string suffix = text.substr(secondClose + 1);
        std::string name = "__anonymous_" + std::to_string(nextAnonymousFunctionId());

        std::vector<SourceLine> result;
        result.push_back(SourceLine{ line.indent, "func " + std::string((text.compare(pos, 6, "stored") == 0 || (pos + 6 <= text.size() && text.compare(pos, 6, "stored") == 0)) ? "stored " : "") + name + "(" + params + "):", line.number });

        std::istringstream bodyStream(body);
        std::string bodyLine;
        while (std::getline(bodyStream, bodyLine)) {
            std::string cleaned = trim(bodyLine);
            if (!cleaned.empty()) result.push_back(SourceLine{ line.indent + 4, cleaned, line.number });
        }

        std::string trimmedPrefix = trim(prefix);
        std::string trimmedSuffix = trim(suffix);
        if (!trimmedPrefix.empty() && trimmedPrefix.find('=') != std::string::npos && trimmedSuffix.empty()) {
            std::size_t eq = trimmedPrefix.find('=');
            std::string lhs = trim(trimmedPrefix.substr(0, eq));
            if (!lhs.empty()) result.push_back(SourceLine{ line.indent, lhs + " = " + name, line.number });
            return result;
        }

        if (trimmedPrefix.empty() && trimmedSuffix.empty()) {
            result.push_back(SourceLine{ line.indent, name, line.number });
            return result;
        }

        result.push_back(SourceLine{ line.indent, prefix + name + suffix, line.number });
        return result;
    }
    return std::vector<SourceLine>{ line };
}
} // namespace

class ProgramParser {
public:
    std::vector<SourceLine> lines;
    std::size_t index;
    explicit ProgramParser(const std::string& source) : index(0) {
        std::istringstream input(source); std::string line; int number = 0;
        std::string logical; int logicalIndent = 0, logicalLine = 0, nesting = 0;
        char quote = 0; bool escape = false;
        while (std::getline(input, line)) {
            ++number;
            std::vector<std::string> chunks = splitInlineBlockLine(line);
            if (chunks.size() > 1) {
                lines.push_back(SourceLine{ indentation(line), chunks[0], number });
                lines.push_back(SourceLine{ indentation(line) + 4, chunks[1], number });
                continue;
            }
            for (std::size_t c = 0; c < chunks.size(); ++c) {
                std::string current = chunks[c];
                if (trim(current).empty()) continue;
                if (logical.empty()) { logicalIndent = indentation(line); logicalLine = number; }
                else logical += " ";
                logical += trim(current);
                for (std::size_t i = 0; i < current.size(); ++i) {
                    char ch = current[i];
                    if (quote) {
                        if (escape) escape = false;
                        else if (ch == '\\') escape = true;
                        else if (ch == quote) quote = 0;
                    } else if (ch == '\'' || ch == '"') quote = ch;
                    else if (ch == '(' || ch == '[' || ch == '{') ++nesting;
                    else if (ch == ')' || ch == ']' || ch == '}') --nesting;
                }
                if (nesting <= 0 && !quote) {
                    SourceLine item = { logicalIndent, logical, logicalLine };
                    lines.push_back(item);
                    logical.clear(); nesting = 0;
                }
            }
        }
        if (!logical.empty()) {
            SourceLine item = { logicalIndent, logical, logicalLine };
            lines.push_back(item);
        }

        std::vector<SourceLine> expanded;
        for (std::size_t i = 0; i < lines.size(); ++i) {
            std::vector<SourceLine> transformed = expandAnonymousFunctions(lines[i]);
            expanded.insert(expanded.end(), transformed.begin(), transformed.end());
        }
        lines.swap(expanded);
    }

    ASTNode expression(const std::string& text) {
        ExpressionParser parser(tokenize(text));
        return parser.parse();
    }

    std::vector<ASTNode> block(int indent) {
        std::vector<ASTNode> result;
        while (index < lines.size() && lines[index].indent >= indent) {
            if (lines[index].indent > indent) throw std::runtime_error("Unexpected indentation at line " + std::to_string(lines[index].number));
            SourceLine sourceLine = lines[index++];
            std::string text = sourceLine.text;
            if (text.compare(0, 4, "func") == 0 && text.size() > 4 && std::isspace(static_cast<unsigned char>(text[4]))) {
                ASTNode fn(ASTNode::FunctionDefinition);
                fn.line = sourceLine.number; fn.sourceText = sourceLine.text;
                std::string signature = trim(text.substr(4));
                if (signature.compare(0, 7, "stored ") == 0) { fn.stored = true; signature = trim(signature.substr(7)); }
                std::size_t open = signature.find('('), close = signature.rfind(')');
                if (open == std::string::npos || close == std::string::npos || close < open) throw std::runtime_error("Invalid function definition: " + text);
                fn.text = trim(signature.substr(0, open));
                Tokens params = tokenize(signature.substr(open + 1, close - open - 1));
                std::size_t p = 0;
                while (p < params.size()) {
                    std::string name = params[p++];
                    if (p < params.size() && params[p] == ":") { p += 2; }
                    std::shared_ptr<ASTNode> defaultValue;
                    if (p < params.size() && params[p] == "=") {
                        ++p; Tokens expressionTokens;
                        while (p < params.size() && params[p] != ",") expressionTokens.push_back(params[p++]);
                        ExpressionParser parser(expressionTokens); defaultValue.reset(new ASTNode(parser.parse()));
                    }
                    fn.parameters.push_back(std::make_pair(name, defaultValue));
                    if (p < params.size() && params[p] == ",") ++p;
                }
                if (index < lines.size() && lines[index].indent > indent) fn.body = block(lines[index].indent);
                result.push_back(fn); continue;
            }
            if (text.compare(0, 5, "type ") == 0 && !text.empty() && text[text.size() - 1] == ':') {
                ASTNode type(ASTNode::TypeDefinition, trim(text.substr(5, text.size() - 6)));
                type.line = sourceLine.number; type.sourceText = sourceLine.text;
                if (index < lines.size() && lines[index].indent > indent) type.body = block(lines[index].indent);
                result.push_back(type); continue;
            }
            if (text == "please:") {
                ASTNode blockNode(ASTNode::Please);
                blockNode.line = sourceLine.number; blockNode.sourceText = sourceLine.text;
                if (index < lines.size() && lines[index].indent > indent) blockNode.body = block(lines[index].indent);
                result.push_back(blockNode); continue;
            }
            if (text == "final:") {
                std::vector<ASTNode> finalBody;
                if (index < lines.size() && lines[index].indent > indent) finalBody = block(lines[index].indent);
                if (result.empty() || (result.back().kind != ASTNode::Repeat &&
                                       result.back().kind != ASTNode::While &&
                                       result.back().kind != ASTNode::Please))
                    throw std::runtime_error("final block must follow a loop or please block");
                result.back().finalBody = finalBody;
                continue;
            }
            if (text.compare(0, 3, "if ") == 0) {
                ASTNode branch(ASTNode::If);
                branch.line = sourceLine.number; branch.sourceText = sourceLine.text;
                std::string condition = trim(text.substr(3));
                if (!condition.empty() && condition[condition.size() - 1] == ':') condition.erase(condition.size() - 1);
                ASTNode test = expression(condition);
                std::vector<ASTNode> body;
                if (index < lines.size() && lines[index].indent > indent) body = block(lines[index].indent);
                branch.branches.push_back(std::make_pair(test, body));
                while (index < lines.size() && lines[index].indent == indent &&
                       (lines[index].text.compare(0, 4, "eif ") == 0 || lines[index].text == "else:")) {
                    std::string next = lines[index++].text;
                    bool isElse = next == "else:";
                    std::string nextCondition;
                    if (!isElse) { nextCondition = trim(next.substr(4)); if (!nextCondition.empty() && nextCondition.back() == ':') nextCondition.pop_back(); }
                    std::vector<ASTNode> nextBody;
                    if (index < lines.size() && lines[index].indent > indent) nextBody = block(lines[index].indent);
                    branch.branches.push_back(std::make_pair(isElse ? ASTNode(ASTNode::Number, "1") : expression(nextCondition), nextBody));
                    if (isElse) break;
                }
                result.push_back(branch); continue;
            }
            if (text.compare(0, 4, "rep ") == 0 || text.compare(0, 6, "while ") == 0) {
                bool repeat = text.compare(0, 4, "rep ") == 0;
                std::string condition = trim(text.substr(repeat ? 4 : 6));
                if (!condition.empty() && condition.back() == ':') condition.pop_back();
                ASTNode loop(repeat ? ASTNode::Repeat : ASTNode::While);
                loop.line = sourceLine.number; loop.sourceText = sourceLine.text;
                loop.children.push_back(expression(condition));
                if (index < lines.size() && lines[index].indent > indent) loop.body = block(lines[index].indent);
                result.push_back(loop); continue;
            }
            ASTNode node = statement(text);
            node.line = sourceLine.number; node.sourceText = sourceLine.text;
            result.push_back(node);
        }
        return result;
    }

    ASTNode statement(const std::string& text) {
        if (text.compare(0, 4, "ext ") == 0) {
            ASTNode node(ASTNode::Import, trim(text.substr(4)));
            std::size_t alias = node.text.find('=');
            if (alias != std::string::npos) {
                std::string aliasName = trim(node.text.substr(alias + 1));
                node.text = trim(node.text.substr(0, alias));
                if (!aliasName.empty()) node.children.push_back(ASTNode(ASTNode::Identifier, aliasName));
            }
            if (!node.text.empty() && node.text[0] == '\x01') node.text = node.text.substr(1);
            if (node.text.size() > 1 && node.text[0] == '\x01') node.text = node.text.substr(1);
            return node;
        }
        if (text.compare(0, 7, "return ") == 0) {
            ASTNode node(ASTNode::Return); node.children.push_back(expression(trim(text.substr(7)))); return node;
        }
        if (text == "return") return ASTNode(ASTNode::Return);
        if (text == "break") return ASTNode(ASTNode::Break);
        if (text == "continue") return ASTNode(ASTNode::Continue);
        if (text.compare(0, 7, "assert ") == 0) {
            ASTNode node(ASTNode::Assert);
            node.children.push_back(expression(trim(text.substr(7))));
            return node;
        }
        if (text == "pass") return ASTNode(ASTNode::Noop);
        Tokens tokens = tokenize(text);
        int depth = 0;
        for (std::size_t i = 0; i < tokens.size(); ++i) {
            if (tokens[i] == "(" || tokens[i] == "[" || tokens[i] == "{") ++depth;
            else if (tokens[i] == ")" || tokens[i] == "]" || tokens[i] == "}") --depth;
            else if (depth == 0 && (tokens[i] == "=" || tokens[i] == "+=" || tokens[i] == "-=" || tokens[i] == "*=" || tokens[i] == "/=" || tokens[i] == "^=" || tokens[i] == "//=")) {
                Tokens lhsTokens(tokens.begin(), tokens.begin() + i);
                Tokens rhs(tokens.begin() + i + 1, tokens.end());
                ExpressionParser lhsParser(lhsTokens);
                ExpressionParser parser(rhs);
                ASTNode lhs = lhsParser.parse();
                std::string name = lhs.kind == ASTNode::Identifier ? lhs.text : "";
                ASTNode node(tokens[i] == "=" ? ASTNode::Assignment : ASTNode::CompoundAssignment, name);
                if (tokens[i] != "=") node.argumentNames.push_back(tokens[i] == "//=" ? "//" : tokens[i].substr(0, 1));
                if (lhs.kind == ASTNode::Member && tokens[i] == "=") node.children.push_back(lhs);
                node.children.push_back(parser.parse()); return node;
            }
        }
        ASTNode node(ASTNode::Expression); node.children.push_back(expression(text)); return node;
    }
};

std::string stripLeading(const std::string& value) {
    std::string::size_type first = value.find_first_not_of('0');
    return first == std::string::npos ? "0" : value.substr(first);
}

int compareUnsigned(const std::string& left, const std::string& right) {
    std::string a = stripLeading(left), b = stripLeading(right);
    if (a.size() != b.size()) return a.size() < b.size() ? -1 : 1;
    if (a == b) return 0;
    return a < b ? -1 : 1;
}
std::string addUnsigned(const std::string& left, const std::string& right) {
    std::string result; int carry = 0;
    int i = static_cast<int>(left.size()) - 1, j = static_cast<int>(right.size()) - 1;
    while (i >= 0 || j >= 0 || carry) {
        int sum = carry + (i >= 0 ? left[i--] - '0' : 0) + (j >= 0 ? right[j--] - '0' : 0);
        result += static_cast<char>('0' + sum % 10); carry = sum / 10;
    }
    std::reverse(result.begin(), result.end()); return result;
}

std::string subtractUnsigned(const std::string& left, const std::string& right) {
    std::string result; int borrow = 0;
    int i = static_cast<int>(left.size()) - 1, j = static_cast<int>(right.size()) - 1;
    while (i >= 0) {
        int digit = left[i--] - '0' - borrow - (j >= 0 ? right[j--] - '0' : 0);
        borrow = digit < 0 ? 1 : 0; if (digit < 0) digit += 10;
        result += static_cast<char>('0' + digit);
    }
    while (result.size() > 1 && result.back() == '0') result.pop_back();
    std::reverse(result.begin(), result.end()); return stripLeading(result);
}

std::string multiplyUnsigned(const std::string& left, const std::string& right) {
    if (left == "0" || right == "0") return "0";
    std::vector<int> digits(left.size() + right.size(), 0);
    for (int i = static_cast<int>(left.size()) - 1; i >= 0; --i)
        for (int j = static_cast<int>(right.size()) - 1; j >= 0; --j)
            digits[i + j + 1] += (left[i] - '0') * (right[j] - '0');
    for (int i = static_cast<int>(digits.size()) - 1; i > 0; --i) { digits[i - 1] += digits[i] / 10; digits[i] %= 10; }
    std::string result; for (std::size_t i = 0; i < digits.size(); ++i) result += static_cast<char>('0' + digits[i]);
    return stripLeading(result);
}

std::pair<std::string, std::string> divideUnsigned(const std::string& numerator, const std::string& denominator) {
    if (denominator == "0") throw std::runtime_error("Division by zero");
    std::string quotient, remainder = "0";
    for (std::size_t i = 0; i < numerator.size(); ++i) {
        remainder = stripLeading(remainder == "0" ? std::string(1, numerator[i]) : remainder + numerator[i]);
        int digit = 0;
        while (compareUnsigned(remainder, denominator) >= 0) { remainder = subtractUnsigned(remainder, denominator); ++digit; }
        quotient += static_cast<char>('0' + digit);
    }
    return std::make_pair(stripLeading(quotient), stripLeading(remainder));
}

} // namespace

BigNumber::BigNumber() : digits_("0"), scale_(0), negative_(false) {}
BigNumber::BigNumber(long long value) : scale_(0), negative_(value < 0) {
    unsigned long long magnitude = value < 0 ? static_cast<unsigned long long>(-(value + 1)) + 1 : static_cast<unsigned long long>(value);
    std::ostringstream out; out << magnitude; digits_ = out.str(); normalize();
}
BigNumber::BigNumber(const std::string& value) : scale_(0), negative_(false) {
    std::string text = trim(value);
    if (text.empty()) throw std::runtime_error("Invalid number");
    if (text[0] == '-' || text[0] == '+') { negative_ = text[0] == '-'; text.erase(0, 1); }
    bool decimal = false;
    for (std::size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '.' && !decimal) decimal = true;
        else if (std::isdigit(static_cast<unsigned char>(text[i]))) { digits_ += text[i]; if (decimal) ++scale_; }
        else throw std::runtime_error("Invalid number: " + value);
    }
    if (digits_.empty()) throw std::runtime_error("Invalid number: " + value);
    normalize();
}

void BigNumber::normalize() {
    digits_ = stripLeading(digits_);
    while (scale_ > 0 && digits_.size() > 1 && digits_[digits_.size() - 1] == '0') { digits_.erase(digits_.size() - 1); --scale_; }
    if (digits_ == "0") { scale_ = 0; negative_ = false; }
}

std::string BigNumber::str() const {
    std::string out = digits_;
    if (scale_ > 0) {
        if (out.size() <= static_cast<std::size_t>(scale_)) out = std::string(static_cast<std::size_t>(scale_) + 1 - out.size(), '0') + out;
        out.insert(out.size() - scale_, ".");
    }
    return negative_ && out != "0" ? "-" + out : out;
}
bool BigNumber::isZero() const { return digits_ == "0"; }
bool BigNumber::isInteger() const { return scale_ == 0; }
BigNumber BigNumber::truncated() const {
    BigNumber result(*this);
    if (result.scale_ >= static_cast<int>(result.digits_.size())) result.digits_ = "0";
    else if (result.scale_ > 0) result.digits_.erase(result.digits_.size() - result.scale_);
    result.scale_ = 0;
    result.normalize();
    return result;
}
long long BigNumber::toLongLong() const {
    std::string text = str(); if (text.find('.') != std::string::npos) text.erase(text.find('.'));
    std::istringstream in(text); long long result = 0; in >> result; return result;
}
long double BigNumber::toLongDouble() const { return std::strtold(str().c_str(), NULL); }
BigNumber BigNumber::operator-() const { BigNumber result(*this); if (!result.isZero()) result.negative_ = !result.negative_; return result; }

BigNumber operator+(const BigNumber& a, const BigNumber& b) {
    int scale = std::max(a.scale_, b.scale_);
    std::string left = a.digits_ + std::string(scale - a.scale_, '0');
    std::string right = b.digits_ + std::string(scale - b.scale_, '0');
    BigNumber result; result.scale_ = scale;
    if (a.negative_ == b.negative_) { result.digits_ = addUnsigned(left, right); result.negative_ = a.negative_; }
    else {
        int comparison = compareUnsigned(left, right);
        if (comparison >= 0) { result.digits_ = subtractUnsigned(left, right); result.negative_ = a.negative_; }
        else { result.digits_ = subtractUnsigned(right, left); result.negative_ = b.negative_; }
    }
    result.normalize(); return result;
}
BigNumber operator-(const BigNumber& a, const BigNumber& b) { return a + (-b); }
BigNumber operator*(const BigNumber& a, const BigNumber& b) {
    BigNumber result; result.digits_ = multiplyUnsigned(a.digits_, b.digits_); result.scale_ = a.scale_ + b.scale_;
    result.negative_ = a.negative_ != b.negative_; result.normalize(); return result;
}
BigNumber operator/(const BigNumber& a, const BigNumber& b) {
    if (b.isZero()) throw std::runtime_error("Division by zero");
    std::string numerator = a.digits_ + std::string(DIVISION_PRECISION + b.scale_, '0');
    std::string denominator = b.digits_ + std::string(a.scale_, '0');
    BigNumber result; result.digits_ = divideUnsigned(numerator, denominator).first;
    result.scale_ = DIVISION_PRECISION; result.negative_ = a.negative_ != b.negative_; result.normalize(); return result;
}
BigNumber operator%(const BigNumber& a, const BigNumber& b) {
    if (b.isZero()) throw std::runtime_error("Modulo by zero");
    int scale = std::max(a.scale_, b.scale_);
    std::string left = a.digits_ + std::string(scale - a.scale_, '0');
    std::string right = b.digits_ + std::string(scale - b.scale_, '0');
    BigNumber result;
    result.digits_ = divideUnsigned(left, right).second;
    result.scale_ = scale;
    result.negative_ = a.negative_;
    result.normalize();
    return result;
}
bool operator==(const BigNumber& a, const BigNumber& b) { return !(a < b) && !(a > b); }
bool operator!=(const BigNumber& a, const BigNumber& b) { return !(a == b); }
bool operator<(const BigNumber& a, const BigNumber& b) {
    if (a.negative_ != b.negative_) return a.negative_;
    int scale = std::max(a.scale_, b.scale_);
    int comparison = compareUnsigned(a.digits_ + std::string(scale - a.scale_, '0'), b.digits_ + std::string(scale - b.scale_, '0'));
    return a.negative_ ? comparison > 0 : comparison < 0;
}
bool operator<=(const BigNumber& a, const BigNumber& b) { return a < b || a == b; }
bool operator>(const BigNumber& a, const BigNumber& b) { return b < a; }
bool operator>=(const BigNumber& a, const BigNumber& b) { return b <= a; }
BigNumber BigNumber::power(const BigNumber& base, const BigNumber& exponent) {
    if (exponent.isInteger()) {
        long long count = exponent.toLongLong();
        if (count > 100000 || count < -100000) throw std::runtime_error("Exponent is too large");
        bool inverse = count < 0; if (inverse) count = -count;
        BigNumber result(1), factor(base);
        while (count) { if (count & 1) result = result * factor; factor = factor * factor; count >>= 1; }
        return inverse ? BigNumber(1) / result : result;
    }
    std::ostringstream out; out.precision(30); out << std::pow(base.toLongDouble(), exponent.toLongDouble());
    return BigNumber(out.str());
}

Value::Value() : kind(Nothing), number(0) {}
Value::Value(Kind valueKind) : kind(valueKind), number(0) {}
Value::Value(const BigNumber& value) : kind(Number), number(value) {}
Value::Value(const std::string& value) : kind(String), number(0), string(value) {}
Value::Value(const char* value) : kind(String), number(0), string(value) {}
Value::Value(const std::vector<Value>& value) : kind(List), number(0), list(value) {}
Value::Value(const std::shared_ptr<FunctionValue>& value) : kind(Function), number(0), function(value) {}
Value::Value(const std::shared_ptr<TypeValue>& value) : kind(Type), number(0), typeValue(value) {}
Value::Value(const std::shared_ptr<InstanceValue>& value) : kind(Instance), number(0), instance(value) {}
Value::Value(const std::shared_ptr<FunctionValue>& method, const std::shared_ptr<InstanceValue>& owner)
    : kind(BoundMethod), number(0), function(method), instance(owner) {}
std::string Value::toString() const {
    if (kind == Nothing) return "nothing";
    if (kind == Number) return number.str();
    if (kind == PositiveInfinity) return "inf";
    if (kind == NegativeInfinity) return "-inf";
    if (kind == String) return string;
    if (kind == Function || kind == BoundMethod) return "<func " + function->name + ">";
    if (kind == Type) return "<type: " + typeValue->name + ">";
    if (kind == Instance) return "<type: " + instance->type->name + ">";
    std::string out = "{";
    for (std::size_t i = 0; i < list.size(); ++i) { if (i) out += ", "; out += list[i].toString(); }
    return out + "}";
}
bool Value::truthy() const {
    if (kind == Nothing) return false;
    if (kind == Number) return !number.isZero();
    if (kind == PositiveInfinity || kind == NegativeInfinity) return true;
    if (kind == String) return !string.empty();
    if (kind == List) return !list.empty();
    return true;
}

std::vector<ASTNode> parseProgram(const std::string& source) {
    ProgramParser parser(source);
    return parser.lines.empty() ? std::vector<ASTNode>() : parser.block(parser.lines[0].indent);
}

class ReturnSignal { public: Value value; explicit ReturnSignal(const Value& v) : value(v) {} };
class BreakSignal {};
class ContinueSignal {};

Interpreter::Interpreter() {
    globals_["nothing"] = Value(); globals_["true"] = Value(BigNumber(1)); globals_["false"] = Value(BigNumber(0));
    globals_["inf"] = Value(Value::PositiveInfinity);
    globals_["nega_inf"] = Value(Value::NegativeInfinity);
    globals_["PI"] = Value(BigNumber("3.14159265358979323846264338327950288419716939937510"));
    globals_["E"] = Value(BigNumber("2.71828182845904523536028747135266249775724709369996"));
}

static bool endsWith(const std::string& value, const std::string& suffix) {
    if (suffix.size() > value.size()) return false;
    return value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

void Interpreter::runFile(const std::string& path) {
    // check file extension
    std::vector<std::string> validFileExtensions = {".wcn", ".wn"};
    bool isWanted = false;
    for (auto extension: validFileExtensions) {
        if (endsWith(path, extension)) { isWanted = true; break; }
    }
    if (!isWanted) throw std::runtime_error("Invalid file extension: " + path);
    std::ifstream file(path.c_str(), std::ios::in | std::ios::binary);    if (!file) throw std::runtime_error("Cannot open source file: " + path);
    std::ostringstream contents; contents << file.rdbuf(); runSource(contents.str(), path);
}
void Interpreter::runSource(const std::string& source, const std::string& filename) {
    filename_ = filename;
    executeBlock(parseProgram(source));
}
Value Interpreter::lookup(const std::string& name) const {
    return readLocation(resolveLocation(name));
}
void Interpreter::assign(const std::string& name, const Value& value) {
    if (!scopes_.empty()) {
        std::map<std::string, VariableLocation>::const_iterator reference = references_.back().find(name);
        if (reference != references_.back().end()) {
            writeLocation(reference->second, value);
            return;
        }
        scopes_.back()[name] = value;
    } else {
        std::map<std::string, VariableLocation>::const_iterator reference = globalReferences_.find(name);
        if (reference != globalReferences_.end()) {
            writeLocation(reference->second, value);
            return;
        }
        globals_[name] = value;
    }
}

std::size_t Interpreter::referenceDepthLimit() const {
    std::size_t limit = globalReferences_.size() + 1;
    for (std::size_t scope = 0; scope < references_.size(); ++scope)
        limit += references_[scope].size();
    return limit;
}

Interpreter::VariableLocation Interpreter::resolveLocation(const std::string& name) const {
    VariableLocation location;
    for (int scope = static_cast<int>(scopes_.size()) - 1; scope >= 0; --scope) {
        if (scopes_[scope].find(name) != scopes_[scope].end()) {
            location = VariableLocation(scope, name);
            break;
        }
    }
    if (location.scope == -2 && globals_.find(name) != globals_.end()) location = VariableLocation(-1, name);
    if (location.scope == -2) throw std::runtime_error("Undefined name '" + name + "'");

    for (std::size_t depth = 0; depth < referenceDepthLimit(); ++depth) {
        if (location.scope < 0) {
            std::map<std::string, VariableLocation>::const_iterator reference = globalReferences_.find(location.name);
            if (reference == globalReferences_.end()) return location;
            location = reference->second;
            continue;
        }
        if (static_cast<std::size_t>(location.scope) >= references_.size()) return location;
        std::map<std::string, VariableLocation>::const_iterator reference = references_[location.scope].find(location.name);
        if (reference == references_[location.scope].end()) return location;
        location = reference->second;
    }
    throw std::runtime_error("Circular variable reference involving '" + name + "'");
}

Value Interpreter::readLocation(const VariableLocation& original) const {
    VariableLocation location = original;
    for (std::size_t depth = 0; depth < referenceDepthLimit(); ++depth) {
        const std::map<std::string, Value>* values = location.scope < 0 ? &globals_ : &scopes_[location.scope];
        std::map<std::string, Value>::const_iterator value = values->find(location.name);
        if (value == values->end()) throw std::runtime_error("Undefined referenced name '" + location.name + "'");
        if (location.scope < 0) {
            std::map<std::string, VariableLocation>::const_iterator reference = globalReferences_.find(location.name);
            if (reference != globalReferences_.end()) { location = reference->second; continue; }
        } else if (static_cast<std::size_t>(location.scope) < references_.size()) {
            std::map<std::string, VariableLocation>::const_iterator reference = references_[location.scope].find(location.name);
            if (reference != references_[location.scope].end()) { location = reference->second; continue; }
        }
        return value->second;
    }
    throw std::runtime_error("Circular variable reference involving '" + original.name + "'");
}

void Interpreter::writeLocation(const VariableLocation& original, const Value& value) {
    VariableLocation location = original;
    for (std::size_t depth = 0; depth < referenceDepthLimit(); ++depth) {
        if (location.scope < 0) {
            std::map<std::string, VariableLocation>::const_iterator reference = globalReferences_.find(location.name);
            if (reference != globalReferences_.end()) { location = reference->second; continue; }
        } else if (static_cast<std::size_t>(location.scope) < references_.size()) {
            std::map<std::string, VariableLocation>::const_iterator reference = references_[location.scope].find(location.name);
            if (reference != references_[location.scope].end()) { location = reference->second; continue; }
        }
        if (location.scope < 0) globals_[location.name] = value;
        else scopes_[location.scope][location.name] = value;
        return;
    }
    throw std::runtime_error("Circular variable reference involving '" + original.name + "'");
}

Value Interpreter::evaluate(const ASTNode& node) {
    if (node.kind == ASTNode::Number) return Value(BigNumber(node.text));
    if (node.kind == ASTNode::String) return Value(node.text);
    if (node.kind == ASTNode::InterpolatedString) {
        std::string result;
        std::size_t cursor = 0;
        while (cursor < node.text.size()) {
            std::size_t open = node.text.find('{', cursor);
            if (open == std::string::npos) { result += node.text.substr(cursor); break; }
            result += node.text.substr(cursor, open - cursor);
            std::size_t close = node.text.find('}', open + 1);
            if (close == std::string::npos) throw std::runtime_error("Unclosed interpolation expression");
            ExpressionParser parser(tokenize(node.text.substr(open + 1, close - open - 1)));
            result += evaluate(parser.parse()).toString();
            cursor = close + 1;
        }
        return Value(result);
    }
    if (node.kind == ASTNode::Identifier) return lookup(node.text);
    if (node.kind == ASTNode::Member) {
        Value owner = evaluate(node.children[0]);
        if (owner.kind == Value::Type) {
            std::map<std::string, std::shared_ptr<FunctionValue> >::const_iterator method = owner.typeValue->methods.find(node.text);
            if (method != owner.typeValue->methods.end()) return Value(method->second);
            std::map<std::string, Value>::const_iterator member = owner.typeValue->members.find(node.text);
            if (member != owner.typeValue->members.end()) return member->second;
            throw std::runtime_error("Library " + owner.typeValue->name + " has no member '" + node.text + "'");
        }
        if (owner.kind != Value::Instance) throw std::runtime_error("Member access requires an instance");
        std::map<std::string, Value>::const_iterator member = owner.instance->members.find(node.text);
        if (member != owner.instance->members.end()) return member->second;
        std::map<std::string, std::shared_ptr<FunctionValue> >::const_iterator method = owner.instance->type->methods.find(node.text);
        if (method != owner.instance->type->methods.end()) return Value(method->second, owner.instance);
        throw std::runtime_error("Type " + owner.instance->type->name + " has no member '" + node.text + "'");
    }
    if (node.kind == ASTNode::Index) {
        Value collection = evaluate(node.children[0]);
        long long index = evaluate(node.children[1]).number.toLongLong();
        if (collection.kind == Value::List) {
            if (index < 0) index += static_cast<long long>(collection.list.size());
            if (index < 0 || static_cast<std::size_t>(index) >= collection.list.size()) throw std::runtime_error("List index out of range");
            return collection.list[static_cast<std::size_t>(index)];
        }
        if (collection.kind == Value::String) {
            std::vector<std::size_t> offsets;
            for (std::size_t offset = 0; offset < collection.string.size(); offset = utf8Next(collection.string, offset)) offsets.push_back(offset);
            if (index < 0) index += static_cast<long long>(offsets.size());
            if (index < 0 || static_cast<std::size_t>(index) >= offsets.size()) throw std::runtime_error("String index out of range");
            std::size_t begin = offsets[static_cast<std::size_t>(index)];
            return Value(collection.string.substr(begin, utf8Next(collection.string, begin) - begin));
        }
        throw std::runtime_error("Indexing requires a list or string");
    }
    if (node.kind == ASTNode::List) {
        std::vector<Value> values; for (std::size_t i = 0; i < node.children.size(); ++i) values.push_back(evaluate(node.children[i])); return Value(values);
    }
    if (node.kind == ASTNode::Unary) {
        Value value = evaluate(node.children[0]);
        if (node.text == "-") return Value(-value.number);
        if (node.text == "+") return value;
        return Value(BigNumber(value.truthy() ? 0 : 1));
    }
    if (node.kind == ASTNode::Call) {
        if (!node.children.empty() && node.children[0].kind == ASTNode::Identifier) {
            const std::string& name = node.children[0].text;
            if (name == "getwcore") {
                if (node.children.size() < 3) throw std::runtime_error("getwcore expects a command and content");
                Value command = evaluate(node.children[1]);
                Value content = evaluate(node.children[2]);
                if (command.string == "stdout") { std::cout << content.toString(); return content; }
                if (command.string == "stdin") { std::cout << content.toString(); std::string line; std::getline(std::cin, line); return Value(line); }
                if (command.string == "typename") {
                    if (content.kind == Value::Type) return Value("<type: " + content.typeValue->name + ">");
                    if (content.kind == Value::Instance) return Value("<type: " + content.instance->type->name + ">");
                    if (content.kind == Value::Number) return Value("<type: NumberType>");
                    if (content.kind == Value::String) return Value("<type: StringType>");
                    if (content.kind == Value::List) return Value("<type: ListType>");
                    return Value("<type: NothingType>");
                }
                if (command.string == "typeBase") {
                    if (content.kind == Value::Instance) return Value(content.instance->type);
                    if (content.kind == Value::Type) return content;
                    throw std::runtime_error("typeBase expects an instance or type");
                }
                if (command.string == "lengthOf") {
                    if (content.kind == Value::List)
                        return Value(BigNumber(static_cast<long long>(content.list.size())));
                    if (content.kind == Value::String) {
                        long long length = 0;
                        for (std::size_t offset = 0; offset < content.string.size(); offset = utf8Next(content.string, offset))
                            ++length;
                        return Value(BigNumber(length));
                    }
                    if (content.kind == Value::Number) {
                        long double number = content.number.toLongDouble();
                        if (!std::isfinite(number)) throw std::runtime_error("lengthOf numeric argument is out of range");
                        long long length = number == 0 ? 1 : static_cast<long long>(std::ceil(std::log10(std::fabs(number))));
                        return Value(BigNumber(length));
                    }
                    throw std::runtime_error("lengthOf expects a number, string, or list");
                }
                if (command.string == "rt" || command.string == "wdbg") return Value(BigNumber(0));
                throw std::runtime_error("Unknown getwcore command '" + command.string + "'");
            }
            if (name == "out" || name == "outln" || name == "outs" || name == "len" || name == "str" ||
                name == "num" || name == "int" || name == "abs" || name == "floor" || name == "ceil" ||
                name == "round" || name == "input" || name == "fac" || name == "factorial") {
                std::vector<Value> args;
                for (std::size_t i = 1; i < node.children.size(); ++i) args.push_back(evaluate(node.children[i]));
                return callBuiltin(name, args);
            }
        }
        return call(evaluate(node.children[0]), node);
    }
    if (node.kind != ASTNode::Binary) return Value();
    Value left = evaluate(node.children[0]);
    if (node.text == "->") {
        const ASTNode& target = node.children[1];
        if (target.kind != ASTNode::Identifier) throw std::runtime_error("Conversion target must be a type name");
        if (loadedTypes_.count(target.text)) {
            Value targetType = lookup(target.text);
            if (targetType.kind != Value::Type) throw std::runtime_error("Conversion target is not a type: '" + target.text + "'");
            std::map<std::string, std::shared_ptr<FunctionValue> >::const_iterator converter = targetType.typeValue->methods.find("_convert");
            if (converter == targetType.typeValue->methods.end())
                throw std::runtime_error("Type " + target.text + " does not define '_convert'");

            std::shared_ptr<InstanceValue> targetInstance(new InstanceValue());
            targetInstance->type = targetType.typeValue;
            std::vector<Value> args(1, left);
            std::map<std::string, Value> named;
            std::vector<VariableLocation> positionalReferences;
            std::map<std::string, VariableLocation> namedReferences;
            std::map<std::string, std::shared_ptr<FunctionValue> >::const_iterator setup = targetType.typeValue->methods.find("_setup");
            if (setup != targetType.typeValue->methods.end())
                invoke(setup->second, args, named, positionalReferences, namedReferences, targetInstance);
            else if (!args.empty()) throw std::runtime_error("Type " + target.text + " takes no arguments");
            return invoke(converter->second, args, named, positionalReferences, namedReferences, targetInstance);
        }
        if (target.text == "NumberType") {
            if (left.kind == Value::Number) return left;
            try { return Value(BigNumber(left.toString())); }
            catch (...) { throw std::runtime_error("Cannot convert value to NumberType"); }
        }
        if (target.text == "StringType") return Value(left.toString());
        if (target.text == "ListType") {
            if (left.kind == Value::List) return left;
            std::vector<Value> values; values.push_back(left); return Value(values);
        }
        if (target.text == "NothingType") return Value();
        throw std::runtime_error("Undefined conversion type '" + target.text + "'");
    }
    if (node.text == "is" && node.children[1].kind == ASTNode::Identifier) {
        const std::string& type = node.children[1].text;
        bool matches = (type == "NothingType" && left.kind == Value::Nothing) ||
                       (type == "NumberType" && isNumericValue(left)) ||
                       (type == "StringType" && left.kind == Value::String) ||
                       (type == "ListType" && left.kind == Value::List);
        if (!matches && loadedTypes_.count(type) && left.kind == Value::Instance) {
            Value typeValue = lookup(type);
            matches = typeValue.kind == Value::Type && left.instance->type == typeValue.typeValue;
        }
        return Value(BigNumber(matches ? 1 : 0));
    }
    Value right = evaluate(node.children[1]);
    if (node.text == "+") {
        if (left.kind == Value::String) return Value(left.toString() + right.toString());
        if (left.kind == Value::Number && right.kind == Value::String) {
            try { return Value(left.number + BigNumber(right.string)); }
            catch (const std::exception&) { return Value(left.toString() + right.toString()); }
        }
        if (left.kind == Value::List) { std::vector<Value> values = left.list; if (right.kind == Value::List) values.insert(values.end(), right.list.begin(), right.list.end()); else values.push_back(right); return Value(values); }
        return Value(left.number + right.number);
    }
    if (node.text == "-") return Value(left.number - right.number);
    if (node.text == "*") {
        if (left.kind == Value::String && right.kind == Value::Number) {
            std::string repeated; long long count = right.number.toLongLong();
            if (count > 0 && count <= 1000000) for (long long i = 0; i < count; ++i) repeated += left.string;
            return Value(repeated);
        }
        if (right.kind == Value::String && left.kind == Value::Number) {
            std::string repeated; long long count = left.number.toLongLong();
            if (count > 0 && count <= 1000000) for (long long i = 0; i < count; ++i) repeated += right.string;
            return Value(repeated);
        }
        return Value(left.number * right.number);
    }
    if (node.text == "/") return Value(left.number / right.number);
    if (node.text == "//") return Value((left.number / right.number).truncated());
    if (node.text == "%") return Value(left.number % right.number);
    if (node.text == "^") return Value(BigNumber::power(left.number, right.number));
    bool result = false;
    if (node.text == "is") result = left.kind == right.kind;
    else if (node.text == "==") result = valuesEqual(left, right);
    else if (node.text == "!=") result = !valuesEqual(left, right);
    else if (isNumericValue(left) && isNumericValue(right)) {
        int comparison = compareNumericValues(left, right);
        if (node.text == "<") result = comparison < 0;
        if (node.text == ">") result = comparison > 0;
        if (node.text == "<=") result = comparison <= 0;
        if (node.text == ">=") result = comparison >= 0;
    }
    return Value(BigNumber(result ? 1 : 0));
}

Value Interpreter::call(const Value& callable, const ASTNode& node) {
    std::vector<Value> args; std::map<std::string, Value> named;
    std::vector<VariableLocation> positionalReferences;
    std::map<std::string, VariableLocation> namedReferences;
    for (std::size_t i = 1; i < node.children.size(); ++i) {
        Value value = evaluate(node.children[i]);
        VariableLocation reference;
        if (node.children[i].kind == ASTNode::Identifier) reference = resolveLocation(node.children[i].text);
        if (i - 1 < node.argumentNames.size() && !node.argumentNames[i - 1].empty()) {
            const std::string& name = node.argumentNames[i - 1];
            named[name] = value;
            if (reference.scope != -2) namedReferences[name] = reference;
        } else {
            args.push_back(value);
            positionalReferences.push_back(reference);
        }
    }
    if (callable.kind == Value::Type) {
        if (callable.typeValue->isLibrary) throw std::runtime_error("Library " + callable.typeValue->name + " cannot be constructed");
        std::shared_ptr<InstanceValue> instance(new InstanceValue());
        instance->type = callable.typeValue;
        std::map<std::string, std::shared_ptr<FunctionValue> >::const_iterator setup = callable.typeValue->methods.find("_setup");
        if (setup != callable.typeValue->methods.end()) invoke(setup->second, args, named, positionalReferences, namedReferences, instance);
        else if (!args.empty()) throw std::runtime_error("Type " + callable.typeValue->name + " takes no arguments");
        return Value(instance);
    }
    if (callable.kind == Value::BoundMethod) return invoke(callable.function, args, named, positionalReferences, namedReferences, callable.instance);
    if (callable.kind != Value::Function) throw std::runtime_error("Value is not callable: " + callable.toString());
    return invoke(callable.function, args, named, positionalReferences, namedReferences);
}

Value Interpreter::invoke(const std::shared_ptr<FunctionValue>& function, const std::vector<Value>& args,
                          const std::map<std::string, Value>& named,
                          const std::vector<VariableLocation>& positionalReferences,
                          const std::map<std::string, VariableLocation>& namedReferences,
                          const std::shared_ptr<InstanceValue>& owner) {
    std::map<std::string, Value> bindings;
    std::map<std::string, VariableLocation> bindingReferences;
    std::size_t argIndex = 0;
    for (std::size_t i = 0; i < function->parameters.size(); ++i) {
        const std::string& parameterName = function->parameters[i].first;
        const bool byReference = !parameterName.empty() && parameterName[0] == '@';
        const std::string name = byReference ? parameterName.substr(1) : parameterName;
        std::map<std::string, Value>::const_iterator namedValue = named.find(name);
        if (namedValue != named.end() && argIndex < args.size()) throw std::runtime_error("Multiple values for argument '" + name + "'");
        VariableLocation reference;
        if (namedValue != named.end()) {
            bindings[name] = namedValue->second;
            std::map<std::string, VariableLocation>::const_iterator target = namedReferences.find(name);
            if (target != namedReferences.end()) reference = target->second;
        }
        else if (argIndex < args.size()) {
            bindings[name] = args[argIndex];
            if (argIndex < positionalReferences.size()) reference = positionalReferences[argIndex];
            ++argIndex;
        }
        else if (function->parameters[i].second) bindings[name] = evaluate(*function->parameters[i].second);
        else throw std::runtime_error("Function " + function->name + " missing argument '" + name + "'");
        if (byReference) {
            if (reference.scope == -2) throw std::runtime_error("Reference parameter '" + name + "' requires a variable argument");
            bindingReferences[name] = reference;
        }
    }
    if (argIndex < args.size()) throw std::runtime_error("Too many arguments for function " + function->name);
    for (std::map<std::string, Value>::const_iterator it = named.begin(); it != named.end(); ++it) {
        bool found = false;
        for (std::size_t i = 0; i < function->parameters.size(); ++i) if (function->parameters[i].first == it->first) found = true;
        if (!found) throw std::runtime_error("Unexpected named argument '" + it->first + "'");
    }
    std::string key;
    for (std::size_t i = 0; i < function->parameters.size(); ++i) {
        const std::string& name = function->parameters[i].first;
        const std::string value = bindings[name].toString();
        key += std::to_string(name.size()) + ":" + name + std::to_string(value.size()) + ":" + value;
    }
    const bool cacheable = function->stored && bindingReferences.empty();
    if (cacheable) { std::map<std::string, Value>::const_iterator cached = function->cache.find(key); if (cached != function->cache.end()) return cached->second; }
    if (owner) bindings["my"] = Value(owner);
    scopes_.push_back(bindings);
    references_.push_back(bindingReferences);
    Value result(BigNumber(0));
    try { executeBlock(function->body); }
    catch (const ReturnSignal& returned) { result = returned.value; }
    catch (...) { references_.pop_back(); scopes_.pop_back(); throw; }
    references_.pop_back();
    scopes_.pop_back();
    if (cacheable) function->cache[key] = result;
    return result;
}

Value Interpreter::callBuiltin(const std::string& name, const std::vector<Value>& args) {
    if (name == "out" || name == "outln" || name == "outs") {
        if (!args.empty()) std::cout << args[0].toString();
        if (name == "outln") std::cout << '\n';
        if (name == "outs") std::cout << (args.size() > 1 ? args[1].toString() : "\n");
        return Value();
    }
    if (name == "len") {
        if (args.empty()) throw std::runtime_error("len expects one argument");
        return Value(BigNumber(args[0].kind == Value::List ? static_cast<long long>(args[0].list.size()) : static_cast<long long>(args[0].string.size())));
    }
    if (name == "str") return Value(args.empty() ? "" : args[0].toString());
    if (name == "num" || name == "int") return args.empty() ? Value(BigNumber(0)) : Value(name == "int" ? args[0].number.truncated() : args[0].number);
    if (name == "abs") return args.empty() ? Value(BigNumber(0)) : Value(args[0].number < BigNumber(0) ? -args[0].number : args[0].number);
    if (name == "floor" || name == "ceil" || name == "round") {
        if (args.empty()) return Value(BigNumber(0));
        long double n = args[0].number.toLongDouble();
        return Value(BigNumber(static_cast<long long>(name == "floor" ? std::floor(n) : name == "ceil" ? std::ceil(n) : std::floor(n + 0.5L))));
    }
    if (name == "input") { std::string prompt = args.empty() ? "" : args[0].toString(); std::cout << prompt; std::string line; std::getline(std::cin, line); return Value(line); }
    if (name == "fac" || name == "factorial") {
        long long n = args.empty() ? 0 : args[0].number.toLongLong(); BigNumber product(1);
        for (long long i = 2; i <= n; ++i) product = product * BigNumber(i);
        return Value(product);
    }
    throw std::runtime_error("Unknown function '" + name + "'");
}

void Interpreter::execute(const ASTNode& node) {
    if (node.kind == ASTNode::Noop) return;
    if (node.kind == ASTNode::Import) {
        std::string path = unquote(trim(node.text));
        bool builtinAlias = !path.empty() && path[0] == '@' && path.compare(0, 6, "@file:") != 0;
        if (path.compare(0, 6, "@file:") == 0) path = trim(path.substr(6));
        if (builtinAlias) {
            std::string modulePath = "lib/interior/" + path.substr(1);
            std::string directory = pathDirectory(filename_);
            while (!directory.empty()) {
                std::string candidate = joinPath(directory, modulePath);
                if (canOpenFile(candidate)) { path = candidate; break; }
                directory = parentPath(directory);
            }
            if (builtinAlias && !canOpenFile(path)) path = modulePath;
        } else if (!path.empty() && path[0] != '/' && !(path.size() > 1 && path[1] == ':')) {
            std::string sourceRelative = joinPath(pathDirectory(filename_), path);
            if (canOpenFile(sourceRelative)) path = sourceRelative;
        }
        std::string alias;
        if (!node.children.empty()) alias = node.children[0].text;
        else {
            std::string filename = path.substr(path.find_last_of("/\\") == std::string::npos ? 0 : path.find_last_of("/\\") + 1);
            std::string::size_type extension = filename.find_last_of('.');
            alias = extension == std::string::npos ? filename : filename.substr(0, extension);
        }
        std::shared_ptr<TypeValue> module;
        std::map<std::string, std::shared_ptr<TypeValue> >::iterator cachedModule = moduleNamespaces_.find(path);
        if (cachedModule != moduleNamespaces_.end()) module = cachedModule->second;
        else {
            std::ifstream imported(path.c_str(), std::ios::in | std::ios::binary);
            if (!imported) throw std::runtime_error("Cannot import module '" + path + "'");
            std::ostringstream source; source << imported.rdbuf();
            std::set<std::string> previousNames;
            for (std::map<std::string, Value>::const_iterator it = globals_.begin(); it != globals_.end(); ++it) previousNames.insert(it->first);
            loadedModules_.insert(path);
            std::string previousFile = filename_;
            filename_ = path;
            try { executeBlock(parseProgram(source.str())); }
            catch (...) { filename_ = previousFile; throw; }
            filename_ = previousFile;
            module.reset(new TypeValue());
            module->name = alias;
            module->isLibrary = true;
            for (std::map<std::string, Value>::const_iterator it = globals_.begin(); it != globals_.end(); ++it) {
                if (previousNames.find(it->first) != previousNames.end()) continue;
                if (it->second.kind == Value::Function) module->methods[it->first] = it->second.function;
                else module->members[it->first] = it->second;
            }
            moduleNamespaces_[path] = module;
        }
        if (alias != "nothing") {
            module->name = alias;
            assign(alias, Value(module));
        }
        return;
    }
    if (node.kind == ASTNode::FunctionDefinition) {
        std::shared_ptr<FunctionValue> fn(new FunctionValue()); fn->name = node.text; fn->parameters = node.parameters; fn->body = node.body; fn->stored = node.stored;
        assign(node.text, Value(fn)); return;
    }
    if (node.kind == ASTNode::TypeDefinition) {
        std::shared_ptr<TypeValue> type(new TypeValue());
        type->name = node.text;
        for (std::size_t i = 0; i < node.body.size(); ++i) {
            if (node.body[i].kind != ASTNode::FunctionDefinition) continue;
            std::shared_ptr<FunctionValue> method(new FunctionValue());
            method->name = node.text + "." + node.body[i].text;
            method->parameters = node.body[i].parameters;
            method->body = node.body[i].body;
            method->stored = node.body[i].stored;
            type->methods[node.body[i].text] = method;
        }
        loadedTypes_.insert(node.text);
        assign(node.text, Value(type));
        return;
    }
    if (node.kind == ASTNode::Assignment) {
        if (!node.children.empty() && node.children[0].kind == ASTNode::Member) {
            if (node.children.size() < 2) throw std::runtime_error("Invalid member assignment");
            Value owner = evaluate(node.children[0].children[0]);
            if (owner.kind != Value::Instance) throw std::runtime_error("Member assignment requires an instance");
            owner.instance->members[node.children[0].text] = evaluate(node.children[1]);
            return;
        }
        if (!node.text.empty() && node.text[0] == '@') {
            const std::string targetName = node.text.substr(1);
            const ASTNode& aliasNode = node.children[0];
            if (aliasNode.kind != ASTNode::Identifier || aliasNode.text.empty() || aliasNode.text[0] == '@')
                throw std::runtime_error("Variable alias requires an identifier on the right side");
            const std::string& aliasName = aliasNode.text;
            VariableLocation target = resolveLocation(targetName);
            if (scopes_.empty()) {
                if (target.scope == -1 && target.name == aliasName)
                    throw std::runtime_error("Circular variable reference involving '" + aliasName + "'");
                globals_[aliasName] = readLocation(target);
                globalReferences_[aliasName] = target;
            } else {
                const int currentScope = static_cast<int>(scopes_.size()) - 1;
                if (target.scope == currentScope && target.name == aliasName)
                    throw std::runtime_error("Circular variable reference involving '" + aliasName + "'");
                scopes_.back()[aliasName] = readLocation(target);
                references_.back()[aliasName] = target;
            }
            return;
        }
        assign(node.text, evaluate(node.children[0])); return;
    }
    if (node.kind == ASTNode::CompoundAssignment) {
        std::string targetName = node.text;
        if (!targetName.empty() && targetName[0] == '@') {
            targetName.erase(0, 1);
            bool hasAlias = !references_.empty() && references_.back().find(targetName) != references_.back().end();
            if (!hasAlias) {
                try { resolveLocation(targetName); }
                catch (const std::runtime_error&) {
                    if (!scopes_.empty() && node.children[0].kind == ASTNode::Identifier) {
                        VariableLocation target = resolveLocation(node.children[0].text);
                        scopes_.back()[targetName] = readLocation(target);
                        references_.back()[targetName] = target;
                        return;
                    }
                    throw;
                }
                if (!scopes_.empty()) {
                    VariableLocation target = resolveLocation(targetName);
                    scopes_.back()[targetName] = readLocation(target);
                    references_.back()[targetName] = target;
                }
            }
        }
        Value old = lookup(targetName); Value rhs = evaluate(node.children[0]);
        const std::string& op = node.argumentNames[0];
        if (op == "+") {
            if (old.kind == Value::String) assign(targetName, Value(old.toString() + rhs.toString()));
            else if (old.kind == Value::Number && rhs.kind == Value::String) {
                try { assign(targetName, Value(old.number + BigNumber(rhs.string))); }
                catch (const std::exception&) { assign(targetName, Value(old.toString() + rhs.toString())); }
            } else if (old.kind == Value::List) {
                std::vector<Value> values = old.list;
                if (rhs.kind == Value::List) values.insert(values.end(), rhs.list.begin(), rhs.list.end());
                else values.push_back(rhs);
                assign(targetName, Value(values));
            } else assign(targetName, Value(old.number + rhs.number));
        }
        else if (op == "-") assign(targetName, Value(old.number - rhs.number));
        else if (op == "*") {
            if (old.kind == Value::String && rhs.kind == Value::Number) {
                std::string repeated; long long count = rhs.number.toLongLong();
                if (count > 0 && count <= 1000000) for (long long i = 0; i < count; ++i) repeated += old.string;
                assign(targetName, Value(repeated));
            } else if (old.kind == Value::Number && rhs.kind == Value::String) {
                std::string repeated; long long count = old.number.toLongLong();
                if (count > 0 && count <= 1000000) for (long long i = 0; i < count; ++i) repeated += rhs.string;
                assign(targetName, Value(repeated));
            } else assign(targetName, Value(old.number * rhs.number));
        }
        else if (op == "/") assign(targetName, Value(old.number / rhs.number));
        else if (op == "^") assign(targetName, Value(BigNumber::power(old.number, rhs.number)));
        else if (op == "//") assign(targetName, Value((old.number / rhs.number).truncated()));
        return;
    }
    if (node.kind == ASTNode::Expression) {
        const ASTNode& expr = node.children[0];
        if (expr.kind == ASTNode::Call && expr.children.size() && expr.children[0].kind == ASTNode::Identifier) {
            std::string name = expr.children[0].text;
            if (name == "out" || name == "outln" || name == "outs" || name == "len" || name == "str" || name == "num" || name == "int" || name == "abs" || name == "floor" || name == "ceil" || name == "round" || name == "input" || name == "fac" || name == "factorial") {
                std::vector<Value> args; for (std::size_t i = 1; i < expr.children.size(); ++i) args.push_back(evaluate(expr.children[i])); callBuiltin(name, args); return;
            }
        }
        evaluate(expr); return;
    }
    if (node.kind == ASTNode::Return) throw ReturnSignal(node.children.empty() ? Value(BigNumber(0)) : evaluate(node.children[0]));
    if (node.kind == ASTNode::Assert) {
        if (!evaluate(node.children[0]).truthy()) throw std::runtime_error("Assertion failed");
        return;
    }
    if (node.kind == ASTNode::If) {
        for (std::size_t i = 0; i < node.branches.size(); ++i) if (evaluate(node.branches[i].first).truthy()) { executeBlock(node.branches[i].second); break; }
        return;
    }
    if (node.kind == ASTNode::Repeat) {
        long long count = evaluate(node.children[0]).number.toLongLong();
        bool broken = false;
        for (long long i = 0; i < count; ++i) {
            try { executeBlock(node.body); }
            catch (const ContinueSignal&) { continue; }
            catch (const BreakSignal&) { broken = true; break; }
        }
        if (!broken) executeBlock(node.finalBody);
        return;
    }
    if (node.kind == ASTNode::While) {
        long long guard = 0;
        bool broken = false;
        while (evaluate(node.children[0]).truthy()) {
            if (++guard > 1000000) throw std::runtime_error("Loop iteration limit exceeded");
            try { executeBlock(node.body); }
            catch (const ContinueSignal&) { continue; }
            catch (const BreakSignal&) { broken = true; break; }
        }
        if (!broken) executeBlock(node.finalBody);
        return;
    }
    if (node.kind == ASTNode::Please) {
        try { executeBlock(node.body); }
        catch (...) {
            executeBlock(node.finalBody);
            throw;
        }
        executeBlock(node.finalBody);
        return;
    }
    if (node.kind == ASTNode::Break) throw BreakSignal();
    if (node.kind == ASTNode::Continue) throw ContinueSignal();
}
void Interpreter::executeBlock(const std::vector<ASTNode>& nodes) {
    for (std::size_t i = 0; i < nodes.size(); ++i) {
        try { execute(nodes[i]); }
        catch (const ExecutionError&) { throw; }
        catch (const std::exception& error) {
            const std::string type = nodes[i].kind == ASTNode::Assert ? "AssertionError" : "RuntimeError";
            throw ExecutionError(type, error.what(), filename_, nodes[i].line, nodes[i].sourceText);
        }
    }
}

} // namespace wanted