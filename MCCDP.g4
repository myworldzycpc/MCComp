grammar MCCDP;

start_: statement* EOF;

expr
    : '(' expr ')'                                        # ParenExpr
    | selector                                            # SelectorExpr
    | atom                                                # AtomExpr
    | expr member                                         # MemberExpr
    | expr index                                          # IndexExpr
    | lval                                                # LvalExpr
    | expr '(' argList? ')'                               # CallExpr
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
argList: arg (',' arg)*;
arg: (ID ':')? expr;

atom: literal | '[' ('I' | 'B' | 'L') ';' exprList? ']' | '[' exprList? ']' | '{' pairList? '}';
pair: (ID | STRING) ':' expr;
pairList: pair (',' pair)*;
literal: int | real | range | STRING | char | BOOL | NULL;

lval: namespacedId (member | index)*;
member: '.' ID;
index: '[' expr ']';

DOT_DOT: '..';
sign: '+' | '-';
signedNumber: signedReal | signedInt;

range: signedNumber? DOT_DOT signedNumber?;

int: (INT_DEC | INT_HEX) typeProfix?;
typeProfix: ID;
signedInt: sign? int;
INT_DEC: [0-9]+;
INT_HEX: '0x' [0-9a-fA-F]+;

real: realValue typeProfix?;
signedReal: sign? real;
realValue: (INT_DEC* '.' INT_DEC+ | INT_DEC+ '.' INT_DEC*)(('E' | 'e') sign?INT_DEC)?;

STRING: '"' (~["\\] | '\\' .)* '"' | '\'' (~['\\] | '\\' .) '\'';
char: ('C' | 'c')STRING;
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

scalingFactor: '<' expr '>';
functionStatement: decorator? 'async'? 'function' namespacedId '(' params? ')' typeDecl? block;
classStatement: decorator? 'class' namespacedId ('extends' namespacedId)? ('implements' namespacedId (',' namespacedId)*)? ('{' (defineStatement | classStatement | functionStatement)* '}')?;
interfaceStatement: 'interface' namespacedId ('extends' namespacedId (',' namespacedId)*) '{' (defineStatement | functionStatement)* '}';

params: param (',' param)*;
param: ID (':' type) ('=' expr)?;
type: ID;

decorator: '@' namespacedIdSingleColon ('(' exprList? ')')?;
selector: ('@a' | '@e' | '@s' | '@r' | '@p') ('[' argList? ']')?;
case: 'case' expr ':' statement*;
default: 'default' ':' statement*;
typeDecl: ':' type;
namespacedId: (ID '::')? ID;
namespacedIdSingleColon: namespacedId | (ID ':')? ID;
ID: [a-zA-Z_][a-zA-Z0-9_]*;

WS: [ \t\n\r]+ -> skip;
COMMENT: ('/*' .*? '*/' | '//' ~[\r\n]*) -> skip;