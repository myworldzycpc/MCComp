grammar MCCDP;

start_: statement* EOF;

expr
    : '(' expr ')'                                        # ParenExpr
    | selector                                            # SelectorExpr
    | atom                                                # AtomExpr
    | expr '.' ID                                         # MemberExpr
    | expr '[' expr ']'                                   # IndexExpr
    | lval                                                # LvalExpr
    | expr '(' exprList? ')'                              # CallExpr
    | 'await' expr '(' exprList? ')'                      # AwaitExpr
    | lval ('++' | '--')                                  # PostIncDecExpr
    | ('++' | '--') lval                                  # PreIncDecExpr
    | ('+' | '-' | '!' | '~') expr                        # UnaryExpr
    | expr ('*' | '/' | '%') expr                         # MultiplicativeExpr
    | expr ('+' | '-') expr                               # AdditiveExpr
    | expr 'instanceof' type                              # InstanceofExpr
    | expr ('==' | '!=' | '<' | '>' | '<=' | '>=') expr   # CompareExpr
    | expr ('||' | '&&') expr                             # LogicalExpr
    | expr '?' expr ':' expr                              # TernaryExpr
    | lval ('=' | '+=' | '-=' | '*=' | '/=' | '%=') expr  # AssignExpr
    ;

exprList: expr (',' expr)*;

atom: literal | '[' exprList? ']' | '{' pairList? '}';
pair: (ID | STRING) ':' expr;
pairList: pair (',' pair)*;
literal: int | real | range | STRING | CHAR | BOOL | NULL;

lval
    : namespacedId ('[' expr ']' | '.' ID)*
    ;

// 词法规则
real: REAL_VALUE REAL_TYPE?;
REAL_VALUE: [+-]?([0-9]* '.' [0-9]+ | [0-9]+ '.' [0-9]*)([eE] [+-]?[0-9]+)?;
REAL_TYPE: [FfDd];
int: (INT_DEC | INT_HEX) INT_TYPE?;
INT_DEC: [+-]?[0-9]+;
INT_TYPE: [BbSsIiLlFfDd];
INT_HEX: '0x' [0-9a-fA-F]+;
range: (int | real)? '..' (int | real)?;
STRING: '"' (~["\\] | '\\' .)* '"' | '\'' (~['\\] | '\\' .) '\'';
CHAR: [Cc]STRING;
BOOL: 'true' | 'false';
NULL: 'null';

block: '{' statement* '}';

statement
    : ';'                                                      # EmptyStmt
    | expr ';'                                                 # ExprStmt
    | block                                                    # BlockStmt
    | 'if' '(' expr ')' statement ('else' statement)?          # IfStmt
    | 'switch' '(' expr ')' '{' (case | default)* '}'          # SwitchStmt
    | 'for' '(' (expr | defineStatement)? ';' expr? ';' expr? ')' statement      # ForStmt
    | 'while' '(' expr ')' statement                           # WhileStmt
    | 'repeat' ID range statement                              # RepeatStmt
    | 'with' '(' expr ')' statement                            # WithStmt
    | 'break' ';'                                              # BreakStmt
    | 'continue' ';'                                           # ContinueStmt
    | 'return' expr? ';'                                       # ReturnStmt
    | defineStatement ';'                                     # DefineStmt
    | functionStatement                                       # FunctionStmt
    | classStatement                                          # ClassStmt
    | interfaceStatement                                      # InterfaceStmt
    ;

defineStatement
    : 'let' namespacedId typeDecl? ('=' expr)?               # LetStmt
    | 'const' namespacedId typeDecl? ('=' expr)?             # ConstStmt
    | 'data' namespacedId typeDecl? ('=' expr)?              # DataStmt
    | 'score' scalingFactor? namespacedId ('=' expr)?       # ScoreStmt
    ;

scalingFactor: '<' (int | real) '>';
functionStatement: decorator? 'async'? 'function' namespacedId '(' params? ')' typeDecl? statement?;
classStatement: decorator? 'class' namespacedId ('extends' namespacedId)? ('implements' namespacedId (',' namespacedId)*)? ('{' (defineStatement | classStatement | functionStatement)* '}')?;
interfaceStatement: 'interface' namespacedId ('extends' namespacedId (',' namespacedId)*) '{' (defineStatement | functionStatement)* '}';

params: param (',' param)*;
param: ID (':' type) ('=' expr)?;
type: ID;

decorator: '@' namespacedIdSingleColon ('(' exprList? ')')?;
selector: ('@a' | '@e' | '@s' | '@r' | '@p') ('[' (ID '=' expr)* ']')?;
case: 'case' expr ':' statement*;
default: 'default' ':' statement*;
typeDecl: ':' type;
namespacedId: (ID '::')? ID;
namespacedIdSingleColon: namespacedId | (ID ':')? ID;
ID: [a-zA-Z_][a-zA-Z0-9_]*;

WS: [ \t\n\r]+ -> skip;
COMMENT: ('/*' .*? '*/' | '//' ~[\r\n]*) -> skip;