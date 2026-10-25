#ifndef WANTED_WCF_H
#define WANTED_WCF_H

#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace wanted {

class BigNumber {
public:
	BigNumber();
	explicit BigNumber(long long value);
	explicit BigNumber(const std::string& value);

	std::string str() const;
	bool isZero() const;
	bool isInteger() const;
	BigNumber truncated() const;
	long long toLongLong() const;
	long double toLongDouble() const;

	BigNumber operator-() const;
	friend BigNumber operator+(const BigNumber&, const BigNumber&);
	friend BigNumber operator-(const BigNumber&, const BigNumber&);
	friend BigNumber operator*(const BigNumber&, const BigNumber&);
	friend BigNumber operator/(const BigNumber&, const BigNumber&);
	friend BigNumber operator%(const BigNumber&, const BigNumber&);
	friend bool operator==(const BigNumber&, const BigNumber&);
	friend bool operator!=(const BigNumber&, const BigNumber&);
	friend bool operator<(const BigNumber&, const BigNumber&);
	friend bool operator<=(const BigNumber&, const BigNumber&);
	friend bool operator>(const BigNumber&, const BigNumber&);
	friend bool operator>=(const BigNumber&, const BigNumber&);

	static BigNumber power(const BigNumber&, const BigNumber&);

private:
	std::string digits_;
	int scale_;
	bool negative_;
	void normalize();
};

struct ASTNode {
	enum Kind {
		Number, String, InterpolatedString, Identifier, List, Unary, Binary, Call,
		Member, Index, Assignment, CompoundAssignment, Expression, Return,
		FunctionDefinition, TypeDefinition, Import, If, Repeat, While,
		Break, Continue, Assert, Please, Noop
	};

	Kind kind;
	std::string text;
	std::string sourceText;
	int line;
	std::vector<ASTNode> children;
	std::vector<ASTNode> body;
	std::vector<ASTNode> finalBody;
	std::vector<std::pair<ASTNode, std::vector<ASTNode> > > branches;
	std::vector<std::pair<std::string, std::shared_ptr<ASTNode> > > parameters;
	std::vector<std::string> argumentNames;
	bool stored;

	explicit ASTNode(Kind nodeKind = Noop, const std::string& nodeText = "", int sourceLine = 0,
		const std::string& source = "")
		: kind(nodeKind), text(nodeText), sourceText(source), line(sourceLine), stored(false) {}
};

struct FunctionValue;
struct TypeValue;
struct InstanceValue;

struct Value {
	enum Kind { Nothing, Number, PositiveInfinity, NegativeInfinity, String, List, Function, Type, Instance, BoundMethod };
	Kind kind;
	BigNumber number;
	std::string string;
	std::vector<Value> list;
	std::shared_ptr<FunctionValue> function;
	std::shared_ptr<TypeValue> typeValue;
	std::shared_ptr<InstanceValue> instance;

	Value();
	explicit Value(Kind valueKind);
	explicit Value(const BigNumber& value);
	explicit Value(const std::string& value);
	explicit Value(const char* value);
	explicit Value(const std::vector<Value>& value);
	explicit Value(const std::shared_ptr<FunctionValue>& value);
	explicit Value(const std::shared_ptr<TypeValue>& value);
	explicit Value(const std::shared_ptr<InstanceValue>& value);
	Value(const std::shared_ptr<FunctionValue>& method, const std::shared_ptr<InstanceValue>& owner);

	std::string toString() const;
	bool truthy() const;
};

struct FunctionValue {
	std::string name;
	std::vector<std::pair<std::string, std::shared_ptr<ASTNode> > > parameters;
	std::vector<ASTNode> body;
	bool stored;
	std::map<std::string, Value> cache;

	FunctionValue() : stored(false) {}
};

struct TypeValue {
	std::string name;
	std::map< std::string, std::shared_ptr<FunctionValue> > methods;
	std::map<std::string, Value> members;
	bool isLibrary;
	TypeValue() : isLibrary(false) {}
};

struct InstanceValue {
	std::shared_ptr<TypeValue> type;
	std::map<std::string, Value> members;
};

} // namespace wanted

#endif
