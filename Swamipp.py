import random,time,requests,os, datetime
from colorama import Fore,Style, init
from bs4 import BeautifulSoup
init()
#Tokens
TT_INT="TT_INT"
TT_FLOAT="FLOAT"
TT_PLUS="PLUS"
TT_MINUS="MINUS"
TT_MUL="MUL"
TT_DIV="DIV"
TT_LPAREN="LPAREN"
TT_MOD="MOD"
TT_RPAREN="RPAREN"
TT_EOF="EOF"
TT_KEYWORD="KEYWORD"
TT_IDENTIFIER="IDENTIFIER"
TT_EQ="EQ"
KEYWORDS=["let","and","or","not", "if","then","elif","else", "while","for","to","step", "func","end","continue","return","break","each","do","class"]
TT_POW="POW"
TT_EE = "EE"
TT_NE="NE"
TT_LT="LT"
TT_GT="GT"
TT_LTE="LTE"
TT_GTE="GTE"
TT_COMMA="COMMA"
TT_ARROW="ARROW"
TT_STRING="STRING"
TT_LSQUARE="LSQUARE"
TT_RSQUARE="RSQUARE"
TT_NEWLINE="NEWLINE"
TT_DOT="DOT"
#Constants
DIGITS="0123456789"
LETTERS="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
LETTERS_DIGITS=LETTERS+DIGITS
#Errors
def string_with_arrows(text, pos_start, pos_end):
	result = ''

	# Calculate indices
	idx_start = max(text.rfind('\n', 0, pos_start.index), 0)
	idx_end = text.find('\n', idx_start + 1)
	if idx_end < 0: idx_end = len(text)

	# Generate each line
	line_count = pos_end.ln - pos_start.ln + 1
	for i in range(line_count):
		# Calculate line columns
		line = text[idx_start:idx_end]
		col_start = pos_start.cn if i == 0 else 0
		col_end = pos_end.cn if i == line_count - 1 else len(line) - 1

		# Append to result
		result += line + '\n'
		result += ' ' * col_start + '^' * (col_end - col_start)

		# Re-calculate indices
		idx_start = idx_end
		idx_end = text.find('\n', idx_start + 1)
		if idx_end < 0: idx_end = len(text)

	return result.replace('\t', '')
class Error:
	def __init__(self,pos_start, pos_end,error_name,details):
		self.pos_start=pos_start
		self.pos_end=pos_end
		self.error_name=error_name
		self.details=details
	def toString(self):
		out= f"{self.error_name}: {self.details}"
		out+= f"\n\tFile: {self.pos_start.fn}"
		out+=f"\n\tLine, Col: {self.pos_start.ln+1}, {self.pos_start.cn+1}-{self.pos_end.cn}"
		out+="\n\n"+string_with_arrows(self.pos_start.ftxt,self.pos_start,self.pos_end)

		#out+=f"\n\t{self.pos_start.ftxt[self.pos_start.index:self.pos_end.index]}"
		return out
class CharacterError(Error):
	def __init__(self,pos_start,pos_end,details):
		super().__init__(pos_start,pos_end,"Unrecognized Character",details)
class InvalidSyntaxError(Error):
	def __init__(self,pos_start,pos_end,details):
		super().__init__(pos_start,pos_end,"Invalid Syntax",details)
class ExpectedCharError(Error):
	def __init__(self,pos_start,pos_end,details):
		super().__init__(pos_start,pos_end,"Expected Character",details)
class RTError(Error):
	def __init__(self,pos_start,pos_end,details,context):
		super().__init__(pos_start,pos_end,"Run Time Error",details)
		self.context=context
	def toString(self):
		out=self.generate_traceback()
		out+= f"\n{self.error_name}: {self.details}"

		out+=f"\n\tLine, Col: {self.pos_start.ln+1}, {self.pos_start.cn+1}-{self.pos_end.cn}"
		#out+=f"\n\t{self.pos_start.ftxt[self.pos_start.index:self.pos_end.index]}"
		return out
	def generate_traceback(self):
		result=""
		pos=self.pos_start
		context=self.context
		while context:
			result=f"\n\tFile: {pos.fn}, Line {pos.ln+1} in {context.display_name}"+result
			pos=context.parent_entry_pos
			context=context.parent
		return "Error Traceback: "+result
class Position:
	def __init__(self,index,ln,cn,fn,ftxt):
		self.index=index
		self.ln=ln
		self.cn=cn
		self.fn=fn
		self.ftxt=ftxt
	def advance(self,current_char=None):
		self.index+=1
		self.cn+=1
		if current_char=="\n":
			self.ln+=1
			self.cn=0
		return self
	def copy(self):
		return Position(self.index,self.ln,self.cn,self.fn,self.ftxt)
class Token:
	def __init__(self,type_,value=None,pos_start=None,pos_end=None):
		self.type=type_
		self.value=value
		if pos_start:
			self.pos_start=pos_start.copy()
			self.pos_end=pos_start.copy().advance()
		if pos_end:
			self.pos_end=pos_end
	def matches(self,type_,value):
		return self.type==type_ and self.value==value
	def __repr__(self):
		if self.value != None: return f"{self.type}:{self.value}"
		return f"{self.type}"
class Lexer:
	token_lookup = {
		"\n": TT_NEWLINE,
		";": TT_NEWLINE,
		"+": TT_PLUS,
		"-": TT_MINUS,
		".": TT_DOT,
		"*": TT_MUL,
		"/": TT_DIV,
		"%": TT_MOD,
		"^": TT_POW,
		"(": TT_LPAREN,
		")": TT_RPAREN,
		"[": TT_LSQUARE,
		"]": TT_RSQUARE,
		",": TT_COMMA,
		":": TT_ARROW
	}
	def __init__(self,fn,text):
		self.text=text
		self.fn =fn
		self.pos=Position(-1,0,-1,fn,text)
		self.current_char=None
		self.advance()
	def advance(self):
		self.pos.advance(self.current_char)
		self.current_char=self.text[self.pos.index] if self.pos.index<len(self.text) else None
	def make_tokens(self):
		tokens=[]
		while self.current_char!=None:
			if self.current_char in "\t ":
				self.advance()
			elif self.current_char in DIGITS:
				tokens.append(self.make_number())
			elif self.current_char in LETTERS:
				tokens.append(self.make_identifier())
			elif self.current_char=='"':
				tokens.append(self.make_string())
				self.advance()
			elif self.current_char in self.token_lookup:
				tokens.append(Token(self.token_lookup[self.current_char], pos_start=self.pos))
				self.advance()
			elif self.current_char=="#":
				self.skip_comment()
			elif self.current_char=="!":
				tok,error=self.make_not_equals()
				if error:
					return [],error
				tokens.append(tok)
				#self.advance()
			elif self.current_char=="=":
				tokens.append(self.make_equals())
			elif self.current_char=="<":
				tokens.append(self.make_less_than())
			elif self.current_char==">":
				tokens.append(self.make_greater_than())
			else:
				pos_start=self.pos.copy()

				char = self.current_char
				self.advance()
				return [],CharacterError(pos_start,self.pos,'"'+char+'"')
		tokens.append(Token(TT_EOF,pos_start=self.pos))
		#print(tokens)
		return tokens,None
	def make_number(self):
		num=""
		dot_count=0
		pos_start=self.pos.copy()
		while self.current_char!=None and self.current_char in DIGITS+".":
			if self.current_char==".":
				if dot_count==1: break
				dot_count+=1
				num+="."
			else:
				num+=self.current_char
			self.advance()
		#print(num)
		if dot_count==0:
			return Token(TT_INT,int(num),pos_start,self.pos)
		else:
			return Token(TT_FLOAT,float(num),pos_start,self.pos)
	def make_identifier(self):
		id_str=""
		pos_start=self.pos.copy()
		while self.current_char != None and self.current_char in LETTERS_DIGITS:
			id_str+=self.current_char
			self.advance()
		tok_type=TT_KEYWORD if id_str in KEYWORDS else TT_IDENTIFIER
		return Token(tok_type,id_str,pos_start,self.pos)
	def make_not_equals(self):
		pos_start=self.pos.copy()
		self.advance()
		if self.current_char=="=":
			self.advance()
			return Token(TT_NE,pos_start,self.pos), None
		self.advance()
		return None, ExpectedCharError(pos_start,pos_end,"Expected '='")
	def make_equals(self):
		tok_type=TT_EQ
		pos_start=self.pos.copy()
		self.advance()
		if self.current_char=="=":
			self.advance()
			tok_type=TT_EE
		return Token(tok_type,pos_start,self.pos)
	def make_less_than(self):
		tok_type=TT_LT
		pos_start=self.pos.copy()
		self.advance()
		if self.current_char=="=":
			self.advance()
			tok_type=TT_LTE
		return Token(tok_type,pos_start,self.pos)
	def make_greater_than(self):
		tok_type=TT_GT
		pos_start=self.pos.copy()
		self.advance()
		if self.current_char=="=":
			self.advance()
			tok_type=TT_GTE
		return Token(tok_type,pos_start,self.pos)
	def make_string(self):
		string=""
		pos_start=self.pos.copy()
		escape_char=False
		self.advance()
		escape_chars={"n":"\n","t":"\t"}
		while self.current_char!=None and (self.current_char != '"' or escape_char):
			if escape_char:
				escape_char=False
				string+=escape_chars.get(self.current_char,self.current_char)
			else:
				if self.current_char=="\\":
					escape_char=True
				else:
					string+=self.current_char
			self.advance()
			#if self.current_char==None:
				#return None, ExpectedCharError(pos_start,self.pos,"Expected '\"'")
		#self.advance()

		return Token(TT_STRING,string,pos_start,self.pos)
	def skip_comment(self):
		self.advance()
		while self.current_char!="\n":
			self.advance()
		self.advance()

class NumberNode:
	def __init__(self,tok):
		self.tok=tok
		self.pos_start=tok.pos_start
		self.pos_end=tok.pos_end
	def __repr__(self):
		return f"{self.tok}"
class StringNode:
	def __init__(self,tok):
		self.tok=tok
		self.pos_start=tok.pos_start
		self.pos_end=tok.pos_end
	def __repr__(self):
		return f"{self.tok}"
class BiOpNode:
	def __init__(self,left,op,right):
		self.left,self.op,self.right=left,op,right
		self.pos_start=left.pos_start
		self.pos_end=right.pos_end
	def __repr__(self):
		return f"({self.left}, {self.op.type}, {self.right})"
class UnOpNode:
	def __init__(self,op,node):
		self.op=op
		self.node=node
		self.pos_start=op.pos_start
		self.pos_end=node.pos_end
	def __repr__(self):
		return f"({self.op}, {self.node})"
class VarAccessNode:
	def __init__(self,tok):
		self.var_name_tok=tok
		self.pos_start=tok.pos_start
		self.pos_end=tok.pos_end
	def __repr__(self):
		return f"<Access {self.var_name_tok.value}>"
class VarAssignNode:
	def __init__(self,tok,node):
		self.var_name_tok=tok
		self.value_node=node
		self.pos_start=tok.pos_start
		self.pos_end=tok.pos_end
	def __repr__(self):
		return f"<Assign {self.var_name_tok.value}={self.value_node}>"
class ClassAssignNode:
	def __init__(self,tok,child,node):
		self.var=tok
		self.child=child
		self.value_node=node
		self.pos_start=tok.pos_start
		self.pos_end=tok.pos_end
	def __repr__(self):
		return f"<Class {self.var.value}>"
class IfNode:
	def __init__(self,cases,_else):
		self.cases=cases
		self._else=_else

		self.pos_end=(self._else or self.cases[len(self.cases)-1])[0].pos_end

		self.pos_start=cases[0][0].pos_start
	def __repr__(self):
		return f"if <{self.cases} else {self._else}>"
class ForNode:
	def __init__(self,var_name_tok,start_value_node,end_value_node,step_value_node,body_node,should_return_null):
		self.var_name_tok=var_name_tok
		self.start_value_node=start_value_node
		self.end_value_node=end_value_node
		self.step_value_node=step_value_node
		self.body_node=body_node
		self.pos_start=var_name_tok.pos_start
		self.pos_end=body_node.pos_end
		self.should_return_null=should_return_null
	def __repr__(self):
		return f"<For node {self.body_node}>"
class WhileNode:
	def __init__(self,condition_node,body_node,should_return_null):
		self.condition_node=condition_node
		self.body_node=body_node
		self.pos_start=condition_node.pos_start
		self.pos_end=body_node.pos_end
		self.should_return_null=should_return_null
	def __repr__(self):
		return f"<While node {self.body_node}>"
class ForEachNode:
	def __init__(self,var_name_tok,iterator_node,body_node,should_return_null):
		self.var_name_tok=var_name_tok
		self.iterator_node=iterator_node
		self.body_node=body_node
		self.pos_start=var_name_tok.pos_start
		self.pos_end=body_node.pos_end
		self.should_return_null=should_return_null
	def __repr__(self):
		return f"<For Each node {self.body_node}>"
class DoNode:
	def __init__(self,condition_node,body_node,should_return_null):
		self.condition_node=condition_node
		self.body_node=body_node
		self.pos_start=condition_node.pos_start
		self.pos_end=body_node.pos_end
		self.should_return_null=should_return_null
	def __repr__(self):
		return f"<Do node {self.body_node}>"
class FuncDefNode:
	def __init__(self,var_name_tok,arg_name_toks, body_node,should_auto_return):
		self.var_name_tok=var_name_tok
		self.arg_name_toks=arg_name_toks
		self.body_node=body_node
		self.should_auto_return=should_auto_return
		if var_name_tok:
			self.pos_start=var_name_tok.pos_start
		elif len(arg_name_toks)>0:
			self.pos_start=arg_name_toks[0].pos_start
		else:
			self.pos_start=body_node.pos_start
		self.pos_end=body_node.pos_end
	def __repr__(self):
		return f"<Function node {self.body_node}>"
class ClassDefNode:
	def __init__(self,var_name_tok,arg_name_toks,body_node):
		self.var_name_tok=var_name_tok
		self.arg_name_toks=arg_name_toks
		self.body_node=body_node
		self.pos_start=var_name_tok.pos_start
		self.pos_end=body_node.pos_end
	def __repr__(self):
		return f"<Class node {self.body_node}>"
class ReturnNode:
	def __init__(self,node_to_return,pos_start,pos_end):
		self.node_to_return=node_to_return
		self.pos_start=pos_start
		self.pos_end=pos_end
	def __repr__(self):
		return f"<Return {self.node_to_return}>"
class ContinueNode:
	def __init__(self,pos_start,pos_end):
		self.pos_start=pos_end
		self.pos_end=pos_end
	def __repr__(self):
		return f"<Continue>"
class BreakNode:
	def __init__(self,pos_start,pos_end):
		self.pos_start=pos_end
		self.pos_end=pos_end
	def __repr__(self):
		return f"<Break"
class CallNode:
	def __init__(self,node_to_call,arg_nodes):
		self.node_to_call=node_to_call
		self.arg_nodes=arg_nodes
		self.pos_start=node_to_call.pos_start
		if len(arg_nodes)>0:
			self.pos_end=arg_nodes[0].pos_end
		else:
			self.pos_end=node_to_call.pos_end
	def __repr__(self):
		return f"<Call {self.node_to_call}>"
class ListNode:
	def __init__(self,element,pos_start,pos_end):
		self.element_nodes=element
		self.pos_start=pos_start
		self.pos_end=pos_end
	def __repr__(self):
		return f"<List {self.element_nodes}>"
class ParseResult:
	def __init__(self):
		self.error=None
		self.node=None
		self.advance_count=0
		self.to_reverse_count=0
	def register(self,res):
		self.advance_count+=res.advance_count
		if res.error:
			self.error = res.error
		return res.node
	def try_register(self,res):
		if res.error:
			self.to_reverse_count=res.advance_count
			return None
		return self.register(res)
	def register_advance(self):
		self.advance_count+=1
	def success(self,node):
		self.node=node
		return self
	def failure(self,error):
		if not self.error: # or self.advance_count==0:
			self.error=error
		return self
class Parser:
	def __init__(self,tokens):
		#(tokens)
		self.tokens=tokens
		self.index=-1
		self.advance()
	def advance(self):
		self.index+=1
		if self.index < len(self.tokens):
			self.current_tok=self.tokens[self.index]
		return self.current_tok
	def reverse(self,amount=1):
		self.index -=amount
		if self.index>=0 and self.index < len(self.tokens):
			self.current_tok=self.tokens[self.index]
		return self.current_tok
	def parse(self):
		res=self.statements()
		if not res.error and self.current_tok.type != TT_EOF:
			#print(self.current_tok)
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,
			self.current_tok.pos_end,"Unexpected token"))
		return res
	def statements(self):
		res= ParseResult()
		statements=[]
		pos_start=self.current_tok.pos_start.copy()
		while self.current_tok.type==TT_NEWLINE:
			res.register_advance()
			self.advance()
		statement=res.register(self.statement())
		if res.error:
			return res
		statements.append(statement)
		more_statements=True
		while True:
			newline_count=0
			while self.current_tok.type==TT_NEWLINE:
				res.register_advance()
				self.advance()
				newline_count+=1
			if newline_count==0:
				more_statements=False
			if not more_statements:
				break
			statement=res.try_register(self.statement())
			if not statement:
				#print(res.error)
				#self.reverse(res.to_reverse_count)
				more_statements=False
				continue
			statements.append(statement)
		return res.success(ListNode(statements,pos_start,self.current_tok.pos_end))
	def statement(self):
		res=ParseResult()
		pos_start=self.current_tok.pos_start.copy()
		if self.current_tok.matches(TT_KEYWORD,"return"):
			self.advance()
			res.register_advance()
			r=res.register(self.expr())
			if res.error:
				return res
			return res.success(ReturnNode(r,pos_start,self.current_tok.pos_end))
		if self.current_tok.matches(TT_KEYWORD,"continue"):
			res.register_advance()
			self.advance()
			return res.success(ContinueNode(pos_start,self.current_tok.pos_end))
		if self.current_tok.matches(TT_KEYWORD,"break"):
			res.register_advance()
			self.advance()
			return res.success(BreakNode(pos_start,self.current_tok.pos_end))
		expr=res.register(self.expr())
		if res.error:
			return res #res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,"Expected ')',let, if, for, while, func, int, float, identifier,  [, return, continue, break"))
		return res.success(expr)
	def call(self):
		res=ParseResult()
		atom = res.register(self.atom())
		if res.error:
			return res
		if self.current_tok.type==TT_LPAREN:
			res.register_advance()
			self.advance()
			arg_nodes=[]
			if self.current_tok.type==TT_RPAREN:
				res.register_advance()
				self.advance()
			else:
				arg_nodes.append(res.register(self.expr()))
				if res.error:
					return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
					"Expected ')',let, if, for, while, func, int, float, identifier,  ["))
				while self.current_tok.type==TT_COMMA:
					self.advance()
					res.register_advance()
					arg_nodes.append(res.register(self.expr()))
					if res.error:
						return res
					#self.advance()
					#res.register_advance()
				if self.current_tok.type!=TT_RPAREN:
					#print(self.current_tok)
					return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
					"Expected ')'"))
				res.register_advance()
				self.advance()
			return res.success(CallNode(atom,arg_nodes))
		return res.success(atom)

	def atom(self):
		res=ParseResult()
		tok=self.current_tok
		if tok.type in (TT_INT,TT_FLOAT):
			res.register_advance()
			self.advance()
			return res.success(NumberNode(tok))
		elif tok.type==TT_IDENTIFIER:
			res.register_advance()
			self.advance()
			return res.success(VarAccessNode(tok))
		elif tok.type ==TT_STRING:
			res.register_advance()
			self.advance()
			return res.success(StringNode(tok))
		elif self.current_tok.matches(TT_KEYWORD,"if"):
			ifexpr=res.register(self.if_expr())
			if res.error:
				#print(res.error.toString())
				return res
			#print(res.node)
			return res.success(ifexpr)
		elif self.current_tok.matches(TT_KEYWORD,"for"):
			forexpr=res.register(self.for_expr())
			if res.error:
				return res
			return res.success(forexpr)
		elif self.current_tok.matches(TT_KEYWORD,"while"):
			forexpr=res.register(self.while_expr())
			if res.error:
				#print(res.error.toString())
				return res
			return res.success(forexpr)
		elif self.current_tok.matches(TT_KEYWORD,"do"):
			forexpr=res.register(self.do_expr())
			if res.error:
				#print("res.error.toString()")
				return res
			return res.success(forexpr)
		elif self.current_tok.matches(TT_KEYWORD,"func"):
			func = res.register(self.func_def())
			if res.error:
				#print(res.error.toString())
				return res
			return res.success(func)

		elif self.current_tok.matches(TT_KEYWORD,"class"):
					class_ = res.register(self.class_def())
					if res.error:
						return res
					return res.success(class_)
		elif self.current_tok.type==TT_LSQUARE:
			#print("list")
			list_expr=res.register(self.list_expr())
			if res.error:
				return res
			return res.success(list_expr)
		elif tok.type ==TT_LPAREN:
			res.register_advance()
			self.advance()
			factor=res.register(self.expr())
			if res.error:return res
			if self.current_tok.type==TT_RPAREN:
				res.register_advance()
				self.advance()
				return res.success(factor)
			else:
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,
				self.current_tok.pos_end,"Expected ')'"))

		return res.failure(InvalidSyntaxError(tok.pos_start,tok.pos_end,"Expected Int or float, Operator, identifier, while, for, if, [, ("))
	def power(self):
		return self.binOp(self.call,(TT_POW),self.factor)
	def factor(self):
		res = ParseResult()
		tok = self.current_tok
		if tok.type in (TT_PLUS,TT_MINUS):
			res.register_advance()
			self.advance()
			factor=res.register(self.factor())
			if res.error:return res
			return res.success(UnOpNode(tok,factor))
		return self.child()
	def term(self):
		return self.binOp(self.factor,(TT_MUL,TT_DIV,TT_MOD))
	def arith_expr(self):
		return self.binOp(self.term,(TT_PLUS,TT_MINUS))
	def child(self):
		return self.binOp(self.power,(TT_DOT))
	def comp_expr(self):
		res = ParseResult()
		if self.current_tok.matches(TT_KEYWORD,"not"):
			op_tok = self.current_tok
			res.register_advance()
			self.advance()
			node = res.register(self.comp_expr())
			if res.error:
				return res
			return res.success(UnOpNode(op_tok,node))
		node=res.register(self.binOp(self.arith_expr,(TT_EE,TT_NE,TT_GT,TT_LT,TT_LTE,TT_GTE)))
		if res.error:
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,"Expected Int or float, not, operator or identifier, (, ["))
		return res.success(node)

	def expr(self):
		res = ParseResult()
		if self.current_tok.matches(TT_KEYWORD,"let"):
			res.register_advance()
			self.advance()
			if self.current_tok.type != TT_IDENTIFIER:
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,
				self.current_tok.pos_end,"Expected Identifier"))
			var_name=self.current_tok
			res.register_advance()
			self.advance()
			if self.current_tok.type==TT_DOT:
				res.register_advance()
				self.advance()
				if self.current_tok.type!=TT_IDENTIFIER:
					return res.failure(InvalidSyntaxError(self.current_tok.pos_start,
					self.current_tok.pos_end,"Expected Identifier"))
				child=VarAccessNode(self.current_tok)
				if res.error:
					return res
				self.advance()
				res.register_advance()
				if self.current_tok.type != TT_EQ:
					return res.failure(InvalidSyntaxError(self.current_tok.pos_start,
					self.current_tok.pos_end,"Expected '='"))
				res.register_advance()
				self.advance()
				expr = res.register(self.expr())
				if res.error:
					return res
				#print(type(child),"lex")
				return res.success(ClassAssignNode(var_name,child,expr))
			if self.current_tok.type != TT_EQ:
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,
				self.current_tok.pos_end,"Expected '='"))
			res.register_advance()
			self.advance()
			expr = res.register(self.expr())
			if res.error:
				return res
			return res.success(VarAssignNode(var_name,expr))




		node=res.register(self.binOp(self.comp_expr,((TT_KEYWORD,"and"),(TT_KEYWORD,"or"))))
		if res.error:
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected Int or float, Operator, let, or identifier, while, for, if, (, ["))
		return res.success(node)
	def binOp(self,func,ops,func_b=None):
		res = ParseResult()
		left=res.register(func())
		if func_b==None:
			func_b=func
		if res.error:return res
		#print(ops)
		inops=False
		try:
			inops=(self.current_tok.type,self.current_tok.value) in ops
		except:
			pass
		while self.current_tok.type in ops or inops:
			op_tok=self.current_tok
			res.register_advance()
			self.advance()
			right=res.register(func_b())
			#print(func)
			#print(left,right)
			#print(type(left))
			if right==None:
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected Operator"))			
			left=BiOpNode(left,op_tok,right)
			try:
				inops=(self.current_tok.type,self.current_tok.value) in ops
			except:
				pass
		return res.success(left)
	def list_expr(self):
		#print("Called")
		res=ParseResult()
		elemement_nodes=[]
		pos_start=self.current_tok.pos_start.copy()
		#print(self.current_tok.type)
		if self.current_tok.type != TT_LSQUARE:

			return res.failure(res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected '['")))
		res.register_advance()
		self.advance()
		#print("hyaj")
		if self.current_tok.type==TT_RSQUARE:
			self.advance()
			res.register_advance()
		else:
			elemement_nodes.append(res.register(self.expr()))
			if res.error:
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected ']',let, if, for, while, func, int, float, identifier"))
			while self.current_tok.type==TT_COMMA:
				self.advance()
				res.register_advance()
				elemement_nodes.append(res.register(self.expr()))
				if res.error:
					return res
				#self.advance()
				#res.register_advance()
			if self.current_tok.type!=TT_RSQUARE:
				#print(self.current_tok)
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected ']' or ','"))
			res.register_advance()
			self.advance()
		return res.success(ListNode(elemement_nodes,pos_start,self.current_tok.pos_end.copy()))
	def if_expr(self):
		res = ParseResult()
		all_cases=res.register(self.if_expr_cases("if"))
		if res.error:
			return res
		cases,else_case=all_cases
		return res.success(IfNode(cases, else_case))
	def if_expr_b(self):
		return self.if_expr_cases("elif")
	def if_expr_c(self):
		res=ParseResult()
		else_case=None
		if self.current_tok.matches(TT_KEYWORD,"else"):
			res.register_advance()
			self.advance()
			if self.current_tok.type==TT_NEWLINE:
				res.register_advance()
				self.advance()
				statements=res.register(self.statements())
				if res.error:
					return res
				else_case=(statements,True)
				if self.current_tok.matches(TT_KEYWORD,"end"):
					res.register_advance()
					self.advance()
				else:
					return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,"Expected 'end'"))
			else:
				expr=res.register(self.statement())
				if res.error:
					return res
				else_case=(expr,False)
		return res.success(else_case)
	def if_expr_b_or_c(self):
		res=ParseResult()
		cases,else_case=[],None
		if self.current_tok.matches(TT_KEYWORD,"elif"):
			all_cases=res.register(self.if_expr_b())
			if res.error:
				return res
			cases,else_case=all_cases
		else:
			else_case=res.register(self.if_expr_c())
			if res.error:
				return res
		return res.success((cases,else_case))
	def if_expr_cases(self,case_keyword):
		res = ParseResult()
		cases=[]
		else_case=None
		if not self.current_tok.matches(TT_KEYWORD,case_keyword):
			return res.failure(res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'if'")))
		res.register_advance()
		self.advance()
		condition= res.register(self.comp_expr())
		#print(condition_node)
		#print(condition_node)
		if res.error:
			return res
		#print(self.current_tok)
		if not self.current_tok.matches(TT_KEYWORD,"then"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'then'"))
		res.register_advance()
		self.advance()
		if self.current_tok.type==TT_NEWLINE:
			res.register_advance()
			self.advance()
			statements=res.register(self.statements())
			if res.error:
				return res
			cases.append((condition,statements,True))
			if self.current_tok.matches(TT_KEYWORD,"end"):
				res.register_advance()
				self.advance()
			else:
				all_cases=res.register(self.if_expr_b_or_c())
				if res.error:
					return res
				new_cases,else_case=all_cases
				cases.extend(new_cases)

		else:
			expr=res.register(self.statement())
			if res.error:
				return res
			cases.append((condition,expr,False))
			all_cases=res.register(self.if_expr_b_or_c())
			new_cases,else_case=all_cases
			#print(new_cases)
			cases.extend(new_cases)
		#print(cases,else_case)
		return res.success((cases,else_case))
	def for_expr(self):
		res=ParseResult()
		if not self.current_tok.matches(TT_KEYWORD,"for"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'for'"))

		res.register_advance()
		self.advance()


		if not self.current_tok.type==TT_IDENTIFIER:
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected Identifier"))
		var_name=self.current_tok
		res.register_advance()
		self.advance()
		if self.current_tok.matches(TT_KEYWORD,"each"):
			self.advance()
			res.register_advance()
			iterator=res.register(self.expr())
			if not self.current_tok.matches(TT_KEYWORD,"then"):
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected 'then'"))
			self.advance()
			res.register_advance()
			if self.current_tok.type==TT_NEWLINE:
				res.register_advance()
				self.advance()
				body=res.register(self.statements())
				if res.error:
					return res
				if not self.current_tok.matches(TT_KEYWORD,"end"):
					return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
					"Expected 'end'"))
				res.register_advance()
				self.advance()
				return res.success(ForEachNode(var_name,iterator,body,True))
			body=res.register(self.statement())
			if res.error:
				return res
			return res.success(ForEachNode(var_name,iterator,body,False))
		if not self.current_tok.type==TT_EQ:
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected '='"))
		res.register_advance()
		self.advance()
		var_value=res.register(self.expr())
		if res.error:
			return res
		#self.advance()
		#res.register_advance()
		if not self.current_tok.matches(TT_KEYWORD,"to"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'to'"))
		self.advance()
		res.register_advance()
		var_to=res.register(self.expr())
		if res.error:
			return res
		step_value=None
		if self.current_tok.matches(TT_KEYWORD,"step"):
			res.register_advance()
			self.advance()
			step_value=res.register(self.expr())
			if res.error:
				return res
		if not self.current_tok.matches(TT_KEYWORD,"then"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'then'"))
		res.register_advance()
		self.advance()

		if self.current_tok.type==TT_NEWLINE:
			res.register_advance()
			self.advance()
			body=res.register(self.statements())
			if res.error:
				return res
			if not self.current_tok.matches(TT_KEYWORD,"end"):
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected 'end'"))
			res.register_advance()
			self.advance()
			return res.success(ForNode(var_name,var_value,var_to,step_value,body,True))
		body=res.register(self.statement())
		if res.error:
			return res
		return res.success(ForNode(var_name,var_value,var_to,step_value,body,False))
	def while_expr(self):
		res = ParseResult()
		if not self.current_tok.matches(TT_KEYWORD,"while"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'while'"))
		res.register_advance()
		self.advance()
		condition=res.register(self.statement())
		if res.error:
			return res
		if not self.current_tok.matches(TT_KEYWORD,"then"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'then'"))
		res.register_advance()
		self.advance()

		if self.current_tok.type==TT_NEWLINE:
			res.register_advance()
			self.advance()
			body=res.register(self.statements())
			if res.error:
				return res
			if not self.current_tok.matches(TT_KEYWORD,"end"):
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected 'end'"))
			res.register_advance()
			self.advance()
			return res.success(WhileNode(condition,body,True))
		body=res.register(self.statement())
		if res.error:
			return res
		return res.success(WhileNode(condition,body,False))
	def do_expr(self):
		res = ParseResult()
		if not self.current_tok.matches(TT_KEYWORD,"do"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'do'"))
		res.register_advance()
		self.advance()
		condition=res.register(self.statement())
		if res.error:
			return res
		if not self.current_tok.matches(TT_KEYWORD,"then"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'then'"))
		res.register_advance()
		self.advance()

		if self.current_tok.type==TT_NEWLINE:
			res.register_advance()
			self.advance()
			body=res.register(self.statements())
			if res.error:
				return res
			if not self.current_tok.matches(TT_KEYWORD,"end"):
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected 'end'"))
			res.register_advance()
			self.advance()
			return res.success(WhileNode(condition,body,True))
		body=res.register(self.statement())
		if res.error:
			return res
		return res.success(DoNode(condition,body,False))
	def func_def(self):
		res=ParseResult()
		if not self.current_tok.matches(TT_KEYWORD,"func"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'func'"))
		res.register_advance()
		self.advance()
		if self.current_tok.type==TT_IDENTIFIER:
			var_name_tok=self.current_tok
			res.register_advance()
			self.advance()
			if self.current_tok.type != TT_LPAREN:
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected ')'"))
		else:
			var_name_tok=None
			if self.current_tok.type != TT_LPAREN:
				return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected 'Identifier' or '('"))
		res.register_advance()
		self.advance()
		arg_name_toks=[]
		if self.current_tok.type==TT_IDENTIFIER:
			arg_name_toks.append(self.current_tok)
			res.register_advance()
			self.advance()
			while self.current_tok.type==TT_COMMA:
				self.advance()
				res.register_advance()
				if self.current_tok.type==TT_IDENTIFIER:
					arg_name_toks.append(self.current_tok)
					self.advance()
					res.register_advance()
				else:
					return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
					"Expected 'Identifier'"))
		if not self.current_tok.type==TT_RPAREN:
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected ')' or ','"))
		res.register_advance()
		self.advance()
		if self.current_tok.type ==TT_ARROW:

			res.register_advance()
			self.advance()
			node_to_return=res.register(self.expr())
			if res.error:
				#print(res.error)
				return res
			return res.success(FuncDefNode(var_name_tok,arg_name_toks,node_to_return,True))
		if self.current_tok.type!=TT_NEWLINE:
			#print("error")
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected ':' or new line"))
		res.register_advance()
		self.advance()
		body=res.register(self.statements())
		if res.error:
			#print(res.error.toString())
			return res
		if not self.current_tok.matches(TT_KEYWORD,"end"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'end'"))
		res.register_advance()
		self.advance()
		return res.success(FuncDefNode(var_name_tok,arg_name_toks,body,False))
	def class_def(self):
		res = ParseResult()
		if not self.current_tok.matches(TT_KEYWORD,"class"):
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'class'"))
		res.register_advance()
		self.advance()
		if not self.current_tok.type==TT_IDENTIFIER:
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected Identifier"))
		var_name_tok=self.current_tok
		self.advance()
		res.register_advance()
		if not self.current_tok.type==TT_LPAREN:
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected ')'"))

		self.advance()
		res.register_advance()
		arg_name_toks=[]
		if self.current_tok.type==TT_IDENTIFIER:
			arg_name_toks.append(self.current_tok)
			res.register_advance()
			self.advance()
			while self.current_tok.type==TT_COMMA:
				self.advance()
				res.register_advance()
				if self.current_tok.type==TT_IDENTIFIER:
					arg_name_toks.append(self.current_tok)
					self.advance()
					res.register_advance()
				else:
					return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
				"Expected 'Identifier'"))
		if not self.current_tok.type==TT_RPAREN:
			#print(self.current_tok.type)
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
		"Expected ')' or ','"))
		res.register_advance()
		self.advance()

		if not self.current_tok.type == TT_NEWLINE:
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Expected 'NewLine'"))
		body=res.register(self.statements())
		if res.error:
			return res
		if not self.current_tok.matches(TT_KEYWORD,"end"):
			#print(self.current_tok)
			return res.failure(InvalidSyntaxError(self.current_tok.pos_start,self.current_tok.pos_end,
			"Class Expected 'end'"))
		self.advance()
		res.register_advance()
		return res.success(ClassDefNode(var_name_tok,arg_name_toks,body))
class RTResult:
	def __init__(self):
		self.reset()
	def reset(self):
		self.value=None
		self.error=None
		self.func_return_value=None
		self.loop_should_continue=False
		self.loop_should_break=False
	def register(self,res):
		self.error=res.error
		self.func_return_value=res.func_return_value
		self.loop_should_continue=res.loop_should_continue
		self.loop_should_break=res.loop_should_break
		return res.value
	def success(self,value):
		self.reset()
		self.value=value
		return self
	def success_return(self,value):
		self.reset()
		self.func_return_value=value
		return self
	def success_continue(self):
		self.reset()
		self.loop_should_continue=True
		return self
	def success_break(self):
		self.reset()
		#print("break")
		self.loop_should_break=True
		return self
	def failure(self,error):
		self.reset()
		self.error=error
		return self
	def should_return(self):
		#  print(self.loop_should_break)
		return (self.error or self.func_return_value
		or self.loop_should_continue or self.loop_should_break)
class Value:
	def __init__(self):
		self.set_pos()
		self.set_context()
	def set_pos(self,pos_start=None,pos_end=None):
		self.pos_start=pos_start
		self.pos_end=pos_end
		return self
	def set_context(self,context=None):
		self.context=context
		return self
	def added_to(self,other):
		return None,self.illegal_operation(other)
	def dotted_to(self,other):
		return None,self.illegal_operation(other)
	def sub_to(self,other):
		return None,self.illegal_operation(other)
	def mul_to(self,other):
		return None,self.illegal_operation(other)
	def pow_to(self,other):
		return None,self.illegal_operation(other)
	def div_to(self,other):
		return None,self.illegal_operation(other)
	def mod_to(self,other):
		return None,self.illegal_operation(other)
	def get_comparison_eq(self,other):
		return None,self.illegal_operation(other)
	def get_comparison_ne(self,other):
		return None,self.illegal_operation(other)
	def get_comparison_lt(self,other):
		return None,self.illegal_operation(other)
	def get_comparison_lte(self,other):
		return None,self.illegal_operation(other)
	def get_comparison_gt(self,other):
		return None,self.illegal_operation(other)
	def get_comparison_gte(self,other):
		return None,self.illegal_operation(other)
	def anded_by(self,other):
		return None,self.illegal_operation(other)
	def ored_by(self,other):
		return None,self.illegal_operation(other)
	def dotted_to(self,other):
		return None, self.illegal_operation(other)
	def notted(self):
		return None,self.illegal_operation()
	def copy(self):
		raise Exception("Copy Method Not Specified")
	def is_true(self):
		return None,self.illegal_operation()
	def illegal_operation(self,other=None):
		if not other:other=self
		return RTError(self.pos_start,other.pos_end,"Illegal Operation",self.context)
	def execute(self):
		return None,self.illegal_operation(None)
	def __repr__(self):
		return str("Value")
class Number(Value):
	def __init__(self,value):
		self.value=value
		super().__init__()
	def type_(self):
		return "Number"
	def set_pos(self,pos_start=None,pos_end=None):
		self.pos_start=pos_start
		self.pos_end=pos_end
		return self
	def set_context(self,context=None):
		self.context=context
		return self
	def added_to(self,other):
		if isinstance(other,Number):
			#print(type(other),other.value,type(self))
			return Number(self.value+other.value).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def sub_to(self,other):
		if isinstance(other,Number):
			return Number(self.value-other.value).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def mul_to(self,other):
		if isinstance(other,Number):
			return Number(self.value*other.value).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def pow_to(self,other):
		if isinstance(other,Number):
			return Number(self.value**other.value).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def div_to(self,other):
		if isinstance(other,Number):
			if other.value==0:
				return None, RTError(other.pos_start,other.pos_end,"Cannot Divide By 0",self.context)
			return Number(self.value/other.value).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def mod_to(self,other):
		if isinstance(other,Number):
			if other.value==0:
				return None, RTError(other.pos_start,other.pos_end,"Cannot Divide By 0",self.context)
			return Number(self.value%other.value).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_eq(self,other):
		if isinstance(other,Number):
			return Number(int(self.value==other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_ne(self,other):
		if isinstance(other,Number):
			return Number(int(self.value!=other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_lt(self,other):
		if isinstance(other,Number):
			return Number(int(self.value<other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_lte(self,other):
		if isinstance(other,Number):
			#print(self.value,other.value)
			return Number(int(self.value<=other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_gt(self,other):
		if isinstance(other,Number):
			return Number(int(self.value>other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_gte(self,other):
		if isinstance(other,Number):
			return Number(int(self.value>=other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def anded_by(self,other):
		if isinstance(other,Number):
			return Number(int(self.value and other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def ored_by(self,other):
		if isinstance(other,Number):
			return Number(int(self.value or other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def notted(self):
		return Number(int(not  self.value)).set_context(self.context),None
	def copy(self):
		copy = Number(self.value)
		copy.set_pos(self.pos_start,self.pos_end)
		copy.set_context(self.context)
		return copy
	def is_true(self):
		return self.value !=0
	def __repr__(self):
		return str(self.value)
Number.null=Number(0)
Number.false=Number(0)
Number.true=Number(1)
class BaseFunction(Value):
	def __init__(self,name):
		super().__init__()
		self.name=name or "<anonymous>"
	def generate_new_context(self):
		#print(self.name,self.context,self.pos_start)
		new_context=Context(self.name,parent=self.context,parent_entry_pos=self.pos_start)
		new_context.symbol_table=SymbolTable(new_context.parent.symbol_table)
		return new_context
	def type_(self):
		return "Function"
	def check_args(self,arg_names,args):
		res = RTResult()
		if len(args) != len(arg_names):
			return res.failure(RTError(self.pos_start,self.pos_end,
			f"Expected {len(arg_names)} args, got {len(args)}",self.context))
		return res.success(None)
	def populate_args(self,arg_names,args,exec_ctx):
		for i in range(len(args)):
			arg_name=arg_names[i]
			arg_value=args[i]
			#print("set: ",type(arg_value),type(arg_name))
			arg_value.set_context(exec_ctx)
			exec_ctx.symbol_table.set(arg_name,arg_value)
	def check_and_populate_args(self,arg_names,args,exec_ctx):
		res=RTResult()
		res.register(self.check_args(arg_names,args))
		if res.should_return():
			return res
		self.populate_args(arg_names,args,exec_ctx)
		return res.success(None)

class Function(BaseFunction):
	def __init__(self,name,body_node,arg_names,should_auto_return):
		super().__init__(name)
		self.body_node=body_node
		self.arg_names=arg_names
		self.should_auto_return=should_auto_return
	def execute(self,args):
		res=RTResult()
		interpreter=Interpreter()
		exec_ctx=self.generate_new_context()
		res.register(self.check_and_populate_args(self.arg_names,args,exec_ctx))
		if res.should_return():
			return res
		value=res.register(interpreter.visit(self.body_node,exec_ctx))
		if res.should_return() and res.func_return_value==None:

			return res
		ret_value=(value if self.should_auto_return else None) or res.func_return_value or Number.null

		return res.success(ret_value)
	def copy(self):
		copy=Function(self.name,self.body_node,self.arg_names,self.should_auto_return)
		copy.set_context(self.context)
		copy.set_pos(self.pos_start,self.pos_end)
		return copy
	def __repr__(self):
		return f"<Function {self.name}>"



class Class(BaseFunction):
	def __init__(self,name,body_node,arg_names):
		super().__init__(name)
		self.body_node=body_node
		self.arg_names = arg_names
		#self.context=parent
		#self.exec_ctx=None
	def type_(self):
		return "Class"
	def execute(self,args):
		res=RTResult()
		interpreter=Interpreter()
		self.exec_ctx=self.generate_new_context()
		self.exec_ctx.symbol_table.set("this",self)
		res.register(self.check_and_populate_args(self.arg_names,args,self.exec_ctx))
		if res.should_return():
			return res
		res.register(interpreter.visit(self.body_node,self.exec_ctx))
		if res.should_return():
			return res

		return res.success(self)
	def dotted_to(self,other):
		#print("called")
		res = RTResult()
		#print(type(other))
		if not isinstance(other,VarAccessNode):
			return None,self.illegal_operation(other)
		try:
			self.exec_ctx
		except:
			return None,RTError(self.pos_start,self.pos_end,
			f"Class has not been initialized yet",self.context)
		if other.var_name_tok.type != TT_IDENTIFIER:
			return None,RTError(self.pos_start,self.pos_end,
			f"Expected Identifier",self.context)
		ret=self.exec_ctx.symbol_table.get(other.var_name_tok.value,True)
		if ret==None:
			return None,RTError(self.pos_start,self.pos_end,
			f"Could not find {other.var_name_tok.value}",self.context)

		return ret,None
	def set(self,other,value):
		res = RTResult()
		#print(type(other))
		if not isinstance(other,VarAccessNode):
			return None,self.illegal_operation(other)
		try:
			self.exec_ctx
		except:
			return None,RTError(self.pos_start,self.pos_end,
			f"Class has not been initialized yet",self.context)
		if other.var_name_tok.type != TT_IDENTIFIER:
			return None,RTError(self.pos_start,self.pos_end,
			f"Expected Identifier",self.context)
		self.exec_ctx.symbol_table.set(other.var_name_tok.value,value)
		return value, None
	def copy(self):
		copy=Class(self.name,self.body_node,self.arg_names)
		copy.set_pos(self.pos_start,self.pos_end)
		copy.set_context(self.context)
		#copy.gen_ctx()
		try:
			copy.exec_ctx=self.exec_ctx
		except:
			pass
		return copy
	def __repr__(self):
		return f"<Class {self.name}>"

class BuiltInFunction(BaseFunction):
	def __init__(self,name):
		super().__init__(name)
	def execute(self,args):
		res=RTResult()
		exec_ctx=self.generate_new_context()
		method_name=f'execute_{self.name}'
		method = getattr(self,method_name,self.no_visit_method)
		res.register(self.check_and_populate_args(method.arg_names, args, exec_ctx))
		if res.should_return():
			return res
		r=res.register(method(exec_ctx))
		if res.should_return():
			return res
		return res.success(r)
	def no_visit_method(self,node,context):
		raise Exception(f"execute_{self.name} is undefined...")
	def execute_print(self,exec_ctx):
		#print(type(exec_ctx))
		print(str(exec_ctx.symbol_table.get("value")),end="")
		#print(Number.null)
		return RTResult().success(Number.null)
	execute_print.arg_names=["value"]
	def execute_println(self,exec_ctx):
		#print(type(exec_ctx))
		print(str(exec_ctx.symbol_table.get("value")))
		#print(Number.null)
		return RTResult().success(Number.null)
	execute_println.arg_names=["value"]
	def execute_print_ret(self,exec_ctx):
		r=str(exec_ctx.symbol_table.get("value"))
		return RTResult().success(String(r))
	execute_print_ret.arg_names=["value"]
	def execute_input(self,exec_ctx):
		r=input()
		return RTResult().success(String(r))
	execute_input.arg_names=[]
	def execute_int(self,exec_ctx):
		try:
			r=int(exec_ctx.symbol_table.get("value").value)
		except:
			return RTResult().failure(RTError(self.pos_start,self.pos_end
			,"Cannot convert to int",exec_ctx))
		return RTResult().success(Number(r))
	execute_int.arg_names=["value"]
	def execute_float(self,exec_ctx):
		try:
			r=float(exec_ctx.symbol_table.get("value").value)
		except:
			return RTResult().failure(RTError(self.pos_start,self.pos_end
			,"Cannot convert to float",exec_ctx))
		return RTResult().success(Number(r))
	execute_float.arg_names=["value"]
	def execute_string(self,exec_ctx):
		try:
			r=str(exec_ctx.symbol_table.get("value").value)
		except:
			return RTResult().failure(RTError(self.pos_start,self.pos_end
			,"Cannot convert to String",exec_ctx))
		return RTResult().success(String(r))
	execute_string.arg_names=["value"]
	def execute_list(self,exec_ctx):
		try:
			r=str(exec_ctx.symbol_table.get("value").value)
		except:
			return RTResult().failure(RTError(self.pos_start,self.pos_end
			,"Cannot convert to list",exec_ctx))
		re=[]
		for i in r:
			re.append(String(i))
		return RTResult().success(List(list(re)))
	execute_list.arg_names=["value"]
	def execute_is_number(self,exec_ctx):
		r=isinstance(exec_ctx.symbol_table.get("value"),Number)
		return RTResult().success(Number(int(r)))
	execute_is_number.arg_names=["value"]
	def execute_is_string(self,exec_ctx):
		r=isinstance(exec_ctx.symbol_table.get("value"),String)
		return RTResult().success(Number(int(r)))
	execute_is_string.arg_names=["value"]
	def execute_is_func(self,exec_ctx):
		r=isinstance(exec_ctx.symbol_table.get("value"),BaseFunction)
		return RTResult().success(Number(int(r)))
	execute_is_func.arg_names=["value"]
	def execute_is_list(self,exec_ctx):
		r=isinstance(exec_ctx.symbol_table.get("value"),List)
		return RTResult().success(Number(int(r)))
	execute_is_list.arg_names=["value"]
	def execute_type(self,exec_ctx):
		r=exec_ctx.symbol_table.get("value")
		ret=""
		if isinstance(r,Class):
			ret=r.name
		else:
			ret=r.type_()
		return RTResult().success(String(ret))
	execute_type.arg_names=["value"]
	execute_is_list.arg_names=["value"]
	def execute_append(self,exec_ctx):
		list_=exec_ctx.symbol_table.get("l")
		value=exec_ctx.symbol_table.get("value")
		if not isinstance(list_,List):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected List as first argument",exec_ctx))
		list_.elements.append(value)
		return RTResult().success(Number.null)
	execute_append.arg_names=["l","value"]
	def execute_extend(self,exec_ctx):
		list_=exec_ctx.symbol_table.get("la")
		value=exec_ctx.symbol_table.get("lb")
		if not isinstance(list_,List):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected List as first argument",exec_ctx))
		if not isinstance(value,List):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected List as second argument",exec_ctx))

		list_.elements.extend(value.elements)
		return RTResult().success(Number.null)
	execute_extend.arg_names=["la","lb"]
	def execute_pop(self,exec_ctx):
		list_=exec_ctx.symbol_table.get("l")
		value=exec_ctx.symbol_table.get("index")
		if not isinstance(list_,List):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected List as first argument",exec_ctx))
		if not isinstance(value,Number):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected Number as second argument",exec_ctx))

		try:
			element=list_.elements.pop(value.value)
		except:
			return RTResult().failure(RTError(self.pos_start,self.pos_end,
			"index out of range",exec_ctx))
		return RTResult().success(element)
	execute_pop.arg_names=["l","index"]
	def execute_copy(self,exec_ctx):
		value=exec_ctx.symbol_table.get("value")
		if not isinstance(value,List):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected Number as second argument",exec_ctx))
		return RTResult().success(List(value.elements*1))
	execute_copy.arg_names=["value"]
	def execute_import(self,exec_ctx):
		file = exec_ctx.symbol_table.get("file")
		if not isinstance(file,String):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected String as first argument",exec_ctx))
		file=file.value
		try:
			code=open(file,"r").read()
		except Exception as e:
			#print(e)
			#import os
			#for i in os.walk('C:/Users/Clay/Clay/Python/Swami++'):
				#print(i)
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Could not read file",exec_ctx))
		temp,error=run(file,code)
		if error:
			return RTResult().failure(RTError(self.pos_start,self.pos_end,f"Import Failed for {file}\n{error.toString()}",exec_ctx))
		return RTResult().success(Number.null)
	execute_import.arg_names=["file"]
	def execute_len(self,exec_ctx):
		value = exec_ctx.symbol_table.get("value")
		if isinstance(value,String):
			return RTResult().success(Number(len(value.value)))
		elif isinstance(value,List):
			return RTResult().success(Number(len(value.elements)))
		else:
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"expected String or List",exec_ctx))
	execute_len.arg_names=["value"]
	def execute_random(self,exec_ctx):
		lower=exec_ctx.symbol_table.get("lower")
		upper=exec_ctx.symbol_table.get("upper")
		if not isinstance(lower,Number):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected Number as first argument",exec_ctx))
		if not isinstance(upper,Number):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected Number as second argument",exec_ctx))
		try:
			return RTResult().success(Number(random.randint(lower.value,upper.value)))
		except:
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"ValueError",exec_ctx))
	def execute_sleep(self,exec_ctx):
		value = exec_ctx.symbol_table.get("value")
		if not isinstance(value,Number):
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"expected Number",exec_ctx))
		time.sleep(value.value)
		return RTResult().success(Number.null)
	execute_sleep.arg_names=["value"]
	execute_random.arg_names=["lower","upper"]
	def execute_request(self,exec_ctx):
		website=exec_ctx.symbol_table.get("web")
		if not (isinstance(website,String)):
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"expected String",exec_ctx))
		try:
			page=requests.get(website.value)
		except Exception as e:
			#print(e)
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Unable to load website",exec_ctx))
		try:
			soup=BeautifulSoup(page.content,"html.parser")
		except:
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Unable to parse page",exec_ctx))
		return RTResult().success(String(soup.text))
	execute_request.arg_names=["web"]
	def execute_requestGet(self,exec_ctx):
		website=exec_ctx.symbol_table.get("web")
		type_=exec_ctx.symbol_table.get("t")
		iden=exec_ctx.symbol_table.get("i")
		name=exec_ctx.symbol_table.get("name")
		if not (isinstance(website,String) and isinstance(type_,String) and isinstance(name,String)):
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"expected String",exec_ctx))
		try:
			page=requests.get(website)
		except Exception as e:
			#print(e)
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Unable to load website",exec_ctx))
		try:
			soup=BeautifulSoup(page.content,"html.parser")
			r=soup.find(type_.value,{iden.value:name.value})

		except:
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Unable to parse page",exec_ctx))
		try:
			return RTResult().success(String(r.text))
		except:
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Unable to find element",exec_ctx))
	def execute_requestAll(self,exec_ctx):
		website=exec_ctx.symbol_table.get("web")
		type_=exec_ctx.symbol_table.get("t")
		
		if not (isinstance(website,String) and isinstance(type_,String)):
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"expected String",exec_ctx))
		try:
			page=requests.get(website)
		except Exception as e:
			#print(e)
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Unable to load website",exec_ctx))
		try:
			soup=BeautifulSoup(page.content,"html.parser")
			r=soup.find_all(type_.value)

		except:
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Unable to parse page",exec_ctx))
		try:
			return RTResult().success(List([String(i.text) for i in r]))
		except:
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Unable to find element",exec_ctx))
	execute_requestGet.arg_names=["web","t","i","name"]
	execute_requestAll.arg_names=["web","t"]
	def execute_variables(self,exec_ctx):
		ctx=exec_ctx
		out=[]
		while 1:
			out.extend(ctx.symbol_table.symbols.keys())
			if  ctx.parent:
				ctx=ctx.parent
			else:
				break
		out = [String(i) for i in out]
		return RTResult().success(List(out))
	execute_variables.arg_names=[]
	def execute_args(self,exec_ctx):
		value = exec_ctx.symbol_table.get("value")
		if isinstance(value,BuiltInFunction):
			method_name=f'execute_{value.name}'
			method = getattr(self,method_name,self.no_visit_method)
			args=method.arg_names
			args = [String(i) for i in args]
			return RTResult().success(List(args))
		if  isinstance(value,BaseFunction):
			args = [String(i) for i in value.arg_names]
			return RTResult().success(List(args))
		return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected Function or Class",exec_ctx))
	execute_args.arg_names=["value"]
	def execute_os(self,exec_ctx):
		command = exec_ctx.symbol_table.get("command")
		if not isinstance(command,String):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected String",exec_ctx))
		try:
			os.system(command.value)
		except Exception as e:
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"OS error",exec_ctx))
		return RTResult().success(Number.null)
	execute_os.arg_names = ["command"]
	def execute_read(self,exec_ctx):
		f=exec_ctx.symbol_table.get("file")
		if not isinstance(f,String):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected String",exec_ctx))
		try:
			r = open(f.value,"r").read()
			return RTResult().success(String(r))
		except:
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Could not load file",exec_ctx))
	execute_read.arg_names=["file"]
	def execute_write(self,exec_ctx):
		f=exec_ctx.symbol_table.get("file")
		text = exec_ctx.symbol_table.get("text")
		if not isinstance(f,String):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected String for first arg",exec_ctx))
		if not isinstance(text,String):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expexted String for second arg",exec_ctx))
		try:
			open(f.value,"w").write(text.value)
			return RTResult().success(Number.null)
		except:
			return  RTResult().failure(RTError(self.pos_start,self.pos_end,"Could write to file",exec_ctx))
	execute_write.arg_names=["file","text"]
	def execute_time(self,exec_ctx):
		now = datetime.datetime.now()
		#print(now.strftime("%Y/%m/%d/%h/%M/%S"))
		return RTResult().success(List([Number(int(i)) for i in now.strftime("%Y/%m/%d/%H/%M/%S").split("/")]))
	execute_time.arg_names=[]
	def execute_error(self,exec_ctx):
		msg = exec_ctx.symbol_table.get("msg")
		if not isinstance(msg,String):
			return RTResult().failure(RTError(self.pos_start,self.pos_end,"Expected String",exec_ctx))
		return RTResult().failure(RTError(self.pos_start,self.pos_end,msg.value,exec_ctx))
	execute_error.arg_names=["msg"]
	def copy(self):
		copy=BuiltInFunction(self.name)
		copy.set_context(self.context)
		copy.set_pos(self.pos_start,self.pos_end)
		return copy
	def __repr__(self):
		return f"<BuiltInFunction {self.name}>"
BuiltInFunction.print=BuiltInFunction("print")
BuiltInFunction.println=BuiltInFunction("println")
BuiltInFunction.print_ret=BuiltInFunction("print_ret")
BuiltInFunction.input=BuiltInFunction("input")
BuiltInFunction.int=BuiltInFunction("int")
BuiltInFunction.float=BuiltInFunction("float")
BuiltInFunction.string=BuiltInFunction("string")
BuiltInFunction.list=BuiltInFunction("list")
BuiltInFunction.is_number=BuiltInFunction("is_number")
BuiltInFunction.is_string=BuiltInFunction("is_string")
BuiltInFunction.is_list=BuiltInFunction("is_list")
BuiltInFunction.is_function=BuiltInFunction("is_function")
BuiltInFunction.append=BuiltInFunction("append")
BuiltInFunction.extend=BuiltInFunction("extend")
BuiltInFunction.pop=BuiltInFunction("pop")
BuiltInFunction.import_=BuiltInFunction("import")
BuiltInFunction.len=BuiltInFunction("len")
BuiltInFunction.random=BuiltInFunction("random")
BuiltInFunction.sleep=BuiltInFunction("sleep")
BuiltInFunction.copy_=BuiltInFunction("copy")
BuiltInFunction.type=BuiltInFunction("type")
BuiltInFunction.request=BuiltInFunction("request")
BuiltInFunction.requestGet=BuiltInFunction("requestGet")
BuiltInFunction.requestAll=BuiltInFunction("requestAll")
BuiltInFunction.variables=BuiltInFunction("variables")
BuiltInFunction.args=BuiltInFunction("args")
BuiltInFunction.os=BuiltInFunction("os")
BuiltInFunction.read=BuiltInFunction("read")
BuiltInFunction.write=BuiltInFunction("write")
BuiltInFunction.time=BuiltInFunction("time")
BuiltInFunction.error=BuiltInFunction("error")
class String(Value):
	def __init__(self,value):
		self.value=value
		super().__init__()
	def set_pos(self,pos_start=None,pos_end=None):
		self.pos_start=pos_start
		self.pos_end=pos_end
		return self
	def set_context(self,context=None):
		self.context=context
		return self
	def type_(self):
		return "String"
	def added_to(self,other):
		if isinstance(other,String):
			return String(self.value+other.value).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def mul_to(self,other):
		if isinstance(other,Number):
			return String(self.value*other.value).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_eq(self,other):
		if isinstance(other,String):
			return Number(int(self.value==other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_ne(self,other):
		if isinstance(other,String):
			return Number(int(self.value!=other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_lt(self,other):
		if isinstance(other,String):
			return Number(int(self.value<other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def get_comparison_lte(self,other):
		if isinstance(other,String):
			return Number(int(self.value<=other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)

			return None, self.illegal_operation(other)
	def get_comparison_gte(self,other):
		if isinstance(other,String):
			return Number(int(self.value>=other.value)).set_context(self.context),None
		else:
			return None, self.illegal_operation(other)
	def copy(self):
		copy = String(self.value)
		copy.set_pos(self.pos_start,self.pos_end)
		copy.set_context(self.context)
		return copy
	def is_true(self):
		return int(bool(self.value))
	def __str__(self):
		return f'{str(self.value)}'
	def __repr__(self):
		return f'"{str(self.value)}"'
class List(Value):
	def __init__(self,elements):
		super().__init__()
		self.elements=elements
	def type_(self):
		return "List"
	def mul_to(self,other):
		new_list=self.copy()
		new_list.elements.append(other)
		return new_list, None
	def sub_to(self,other):
		if isinstance(other,Number):
			try:
				new_list=self.copy()
				new_list.elements.pop(other.value)
				return new_list, None
			except:
				return None, RTError(self.pos_start,self.pos_end,"List Index out of range",self.context)
		else:
			return None, self.illegal_operation(other)
	def added_to(self,other):
		if isinstance(other,List):
			new_list=self.copy()
			new_list.elements.extend(other.elements)
			return new_list,None
		else:
			return None, self.illegal_operation(other)
	def div_to(self,other):
		if isinstance(other,Number):
			try:
				#print(other.value)
				return self.elements[other.value], None
			except:
				return None, RTError(self.pos_start,self.pos_end,"List Index out of range",self.context)
		else:
			return None, self.illegal_operation(other)
	def copy(self):
		return List(self.elements).set_pos(self.pos_start,self.pos_end).set_context(self.context)
	def __repr__(self):
		return f"{self.elements}"


class Context:
	def __init__(self,display_name,parent=None,parent_entry_pos=None):
		self.display_name=display_name
		self.parent=parent
		self.parent_entry_pos=parent_entry_pos
		self.symbol_table=None


class SymbolTable:
	def __init__(self,parent=None):
		self.symbols={}
		self.parent=parent
	def get(self,name,immediate=False):
		value=self.symbols.get(name,None)
		if value==None and self.parent != None and not immediate:
			return self.parent.get(name)
		return value
	def set(self,name,value):
		self.symbols[name]=value
	def remove(self,name):
		del self.symbols[name]
class Interpreter:
	def visit(self,node,context):
		method_name=f'visit_{type(node).__name__}'
		method=getattr(self,method_name,self.no_visit_method)
		return method(node,context)
	def no_visit_method(self,node,context):
		raise Exception(f"No visit method defined for node: {type(node).__name__} ")
	def visit_VarAccessNode(self,node,context):
		res = RTResult()
		var_name = node.var_name_tok.value
		value=context.symbol_table.get(var_name)
		#print(value,type(value))
		if value==None:
			return res.failure(RTError(node.pos_start,node.pos_end,f"Variable name '{var_name}' is not defined",context))
		#print(value,type(value))
		value=value.copy().set_pos(node.pos_start,node.pos_end).set_context(context)
		#print(value,type(value))
		return res.success(value)
	def visit_IfNode(self,node,context):
		res=RTResult()
		for condition,expr,should_return_null in node.cases:
			c = res.register(self.visit(condition,context))
			if res.should_return():
				return res
			if c.is_true():
				e = res.register(self.visit(expr,context))
				#print(res.loop_should_break)
				if res.should_return():
					return res
				return res.success(Number.null if should_return_null else e)
		if node._else:
			expr,should_return_null=node._else
			e = res.register(self.visit(expr,context))
			if res.should_return():
				return res
			return res.success(Number.null if should_return_null else e)
		#print(node._else)
		return res.success(Number.null)
		#alue=None
		#if condition.value:
			#value = res.register(self.visit(node.execution,context))
		#if res.should_return():
			#return res
		#return res.success(value)
	def visit_ForNode(self,node,context):
		res=RTResult()
		elements=[]
		start_value=res.register(self.visit(node.start_value_node,context))
		if res.should_return():
			return res
		end_value=res.register(self.visit(node.end_value_node,context))
		if res.should_return():
			return res
		if node.step_value_node:
			step_value=res.register(self.visit(node.step_value_node,context))
			if res.should_return():
				return res
		else:
			step_value=Number(1)
		i = start_value.value
		if step_value.value>=0:
			condition=lambda:i<end_value.value
		else:
			condition=lambda:i>end_value.value
		while condition():
			#print("Ran")
			context.symbol_table.set(node.var_name_tok.value,Number(i))
			i+=step_value.value
			#print(i)
			#print(body_node)
			value=res.register(self.visit(node.body_node,context))
			#print(res.loop_should_break)
			if res.should_return() and res.loop_should_continue==False and res.loop_should_break==False:
				return res
			if res.loop_should_continue:
				continue
			if res.loop_should_break:
				break
			elements.append(value)
		return res.success(Number.null if node.should_return_null else List(elements).set_context(context).set_pos(node.pos_start,node.pos_end))
	def visit_ForEachNode(self,node,context):
		res=RTResult()
		iterator=res.register(self.visit(node.iterator_node,context))
		ret=[]
		if res.should_return():
			return res
		if not isinstance(iterator,List):
			return res.failure(RTError(node.pos_start,node.pos_end,f"Expected List type",context))
		for i in iterator.elements:
			context.symbol_table.set(node.var_name_tok.value,i)
			value=res.register(self.visit(node.body_node,context))

			if res.should_return() and res.loop_should_continue==False and res.loop_should_break==False:
				return res
			if res.loop_should_continue:
				continue
			if res.loop_should_break:
				break
			ret.append(value)
		return res.success(Number.null if node.should_return_null else List(ret).set_context(context).set_pos(node.pos_start,node.pos_end))

	def visit_WhileNode(self,node,context):
		res=RTResult()
		elements=[]
		while 1:
			condition=res.register(self.visit(node.condition_node,context))
			if res.should_return():
				return res
			if not condition.is_true():
				break
			value=res.register(self.visit(node.body_node,context))
			if res.should_return() and res.loop_should_continue==False and res.loop_should_break==False:
				return res
			if res.loop_should_continue:
				continue
			if res.loop_should_break:
				break
				#print(res.loop_should_break)
			elements.append(value)
		return res.success(Number.null if node.should_return_null else List(elements).set_context(context).set_pos(node.pos_start,node.pos_end))
	def visit_DoNode(self,node,context):
		res=RTResult()
		elements=[]
		while 1:
			condition=res.register(self.visit(node.condition_node,context))
			if res.should_return():
				return res
			value=res.register(self.visit(node.body_node,context))
			if res.should_return() and res.loop_should_continue==False and res.loop_should_break==False:
				return res
			if res.loop_should_continue:
				continue
			if res.loop_should_break:
				break
			if not condition.is_true():
				break
				#print(res.loop_should_break)
			elements.append(value)
		return res.success(Number.null if node.should_return_null else List(elements).set_context(context).set_pos(node.pos_start,node.pos_end))

	def visit_VarAssignNode(self,node,context):
		res = RTResult()
		var_name=node.var_name_tok.value
		value=  res.register(self.visit(node.value_node,context))
		#print(value,type(value))
		if res.should_return():
			return res
		context.symbol_table.set(var_name,value)
		return res.success(value)
	def visit_ClassAssignNode(self,node,context):
		res=RTResult()
		class_=context.symbol_table.get(node.var.value)
		#if res.should_return():
			#return res
		if not isinstance(class_,Class):
			return res.failure(RTError(node.pos_start,node.pos_end,f"Expected Class",context))
		child = node.child
		#if res.should_return():
			#return res
		#print(child)

		if res.should_return():
			return res
		value = res.register(self.visit(node.value_node,context))
		if res.should_return():
			return res
		class_.set(child,value)
		return res.success(value)
	def visit_NumberNode(self,node,context):
		#print("Number",node.tok.value)
		result= Number(node.tok.value).set_context(context).set_pos(node.pos_start,node.pos_end)
		#print(result)
		return RTResult().success(result)
	def visit_StringNode(self,node,context):
		result=String(node.tok.value).set_context(context).set_pos(node.pos_start,node.pos_end)
		return RTResult().success(result)
	def visit_ListNode(self,node,context):
		res=RTResult()
		elements=[]
		for elemement_node in node.element_nodes:
			elements.append(res.register(self.visit(elemement_node,context)))
			if res.should_return():
				return res
		return res.success(List(elements).set_context(context).set_pos(node.pos_start,node.pos_end))

	def visit_BiOpNode(self,node,context):
		#print("BiOpNode")
		res=RTResult()
		left=res.register(self.visit(node.left,context))
		if res.should_return():
			return res
		if node.op.type != TT_DOT:
			right=res.register(self.visit(node.right,context))
			if res.should_return():
				 return res
		else:
			right=node.right
		#print(type(left.value),right,node.op)
		if node.op.type==TT_PLUS:
			#print("here",type(left),type(node.left))
			result,error= left.added_to(right)
		elif node.op.type==TT_MINUS:
			result,error=left.sub_to(right)
		elif node.op.type==TT_MUL:
			result,error=left.mul_to(right)
		elif node.op.type==TT_DIV:
			result,error=left.div_to(right)
		elif node.op.type==TT_MOD:
			result,error=left.mod_to(right)
		elif node.op.type==TT_POW:
			result,error=left.pow_to(right)
		elif node.op.type==TT_EE:
			result,error=left.get_comparison_eq(right)
		elif node.op.type==TT_NE:
			result,error=left.get_comparison_ne(right)
		elif node.op.type==TT_LT:
			result,error=left.get_comparison_lt(right)
		elif node.op.type==TT_LTE:
			result,error=left.get_comparison_lte(right)
		elif node.op.type==TT_GT:
			result,error=left.get_comparison_gt(right)
		elif node.op.type==TT_GTE:
			result,error=left.get_comparison_gte(right)
		elif node.op.matches(TT_KEYWORD,"and"):
			result,error=left.anded_by(right)
		elif node.op.matches(TT_KEYWORD,"or"):
			result,error=left.ored_by(right)
		elif node.op.type==TT_DOT:
			#if not isinstance(node.left,Class):
				#print(type(node.left))
				#result,error = None,RTError(node.pos_start,node.pos_end,f"Expected Class",context)
			#elif not isinstance(node.right,VarAccessNode):
			#	result,error = None,RTError(node.pos_start,node.pos_end,f"Expected Identifier",context)
			#else:
			result,error=left.dotted_to(right)
		if error:
			return res.failure(error)
		#print(result)
		return res.success(result.set_pos(node.pos_start,node.pos_end))
	def visit_UnOpNode(self,node,context):
		res=RTResult()
		number=res.register(self.visit(node.node,context))
		#print(number,node.op==TT_MINUS)
		if res.should_return():
			return res
		error=None
		if node.op.type==TT_MINUS:
			#print("minissd")
			result,error=number.mul_to(Number(-1))
			#print(result)
		elif node.op.matches(TT_KEYWORD,"not"):
			result,error=number.notted()
		#print(node.op)
		if error:
			return res.failure(error)
		return res.success(result.set_pos(node.pos_start,node.pos_end))
	def visit_FuncDefNode(self,node,context):
		res=RTResult()
		func_name=node.var_name_tok.value if node.var_name_tok else None
		body_node = node.body_node
		arg_names = [arg_name.value for arg_name in node.arg_name_toks]
		func_value=Function(func_name,body_node,arg_names,node.should_auto_return).set_context(context).set_pos(node.pos_start,node.pos_end)
		if node.var_name_tok:
			context.symbol_table.set(func_name,func_value)
		return res.success(func_value)
	def visit_ClassDefNode(self,node,context):
		res=RTResult()
		func_name=node.var_name_tok.value
		body_node=node.body_node
		arg_names = [a.value for a in node.arg_name_toks]
		class_value = Class(func_name,body_node,arg_names).set_pos(node.pos_start,node.pos_end).set_context(context)
		context.symbol_table.set(func_name,class_value)
		return res.success(class_value)
	def visit_CallNode(self,node,context):
		res = RTResult()
		args=[]
		value_to_call=res.register(self.visit(node.node_to_call,context))
		if res.should_return():
			return res
		value_to_call=value_to_call.copy().set_pos(node.pos_start,node.pos_end)
		for arg_node in node.arg_nodes:
			args.append(res.register(self.visit(arg_node,context)))
			if res.should_return():
				return res
		#print(args)
		try:
			return_value=res.register(value_to_call.execute(args))
		except Exception as e:
			print(e)
			return res.failure(RTError(node.pos_start,node.pos_end,f"Wrap function in parentheses",context))
		if res.should_return():
			return res
		return_value=return_value.copy().set_pos(node.pos_start,node.pos_end).set_context(context)
		return res.success(return_value)
	def visit_ReturnNode(self,node,context):
		res=RTResult()
		value=res.register(self.visit(node.node_to_return,context))
		if res.should_return():
			return res
		return res.success_return(value)
	def visit_ContinueNode(self,node,context):
		res=RTResult()
		return res.success_continue()
	def visit_BreakNode(self,node,context):
		res=RTResult()
		#print("breaking")
		return res.success_break()
global_symbol_table=SymbolTable()
global_symbol_table.set("null",Number.null)
global_symbol_table.set("false",Number.false)
global_symbol_table.set("true",Number.true)
global_symbol_table.set("print",BuiltInFunction.print)
global_symbol_table.set("print_ret",BuiltInFunction.print_ret)
global_symbol_table.set("input",BuiltInFunction.input)
global_symbol_table.set("int",BuiltInFunction.int)
global_symbol_table.set("float",BuiltInFunction.float)
global_symbol_table.set("list",BuiltInFunction.list)
global_symbol_table.set("string",BuiltInFunction.string)
global_symbol_table.set("is_number",BuiltInFunction.is_number)
global_symbol_table.set("is_string",BuiltInFunction.is_string)
global_symbol_table.set("is_list",BuiltInFunction.is_list)
global_symbol_table.set("is_function",BuiltInFunction.is_function)
global_symbol_table.set("append",BuiltInFunction.append)
global_symbol_table.set("pop",BuiltInFunction.pop)
global_symbol_table.set("extend",BuiltInFunction.extend)
global_symbol_table.set("pi",Number(3.14159265358979323846))
global_symbol_table.set("println",BuiltInFunction.println)
global_symbol_table.set("import",BuiltInFunction.import_)
global_symbol_table.set("len",BuiltInFunction.len)
global_symbol_table.set("randint",BuiltInFunction.random)
global_symbol_table.set("sleep",BuiltInFunction.sleep)
global_symbol_table.set("copy",BuiltInFunction.copy_)
global_symbol_table.set("type",BuiltInFunction.type)
global_symbol_table.set("request",BuiltInFunction.request)
global_symbol_table.set("requestGet",BuiltInFunction.requestGet)
global_symbol_table.set("requestAll",BuiltInFunction.requestAll)
global_symbol_table.set("variables",BuiltInFunction.variables)
global_symbol_table.set("args",BuiltInFunction.args)
global_symbol_table.set("os",BuiltInFunction.os)
global_symbol_table.set("read",BuiltInFunction.read)
global_symbol_table.set("write",BuiltInFunction.write)
global_symbol_table.set("time",BuiltInFunction.time)
global_symbol_table.set("error",BuiltInFunction.error)
global_symbol_table.set("RED",String(Fore.RED))
global_symbol_table.set("BLUE",String(Fore.BLUE))
global_symbol_table.set("GREEN",String(Fore.GREEN))
global_symbol_table.set("RESET",String(Style.RESET_ALL))
global_symbol_table.set("YELLOW",String(Fore.YELLOW))
global_symbol_table.set("MAGENTA",String(Fore.MAGENTA))
global_symbol_table.set("CYAN",String(Fore.CYAN))
global_symbol_table.set("WHITE",String(Fore.WHITE))
global_symbol_table.set("BLACK",String(Fore.BLACK))
def run(fn, text):
	lexer=Lexer(fn, text)
	tokens,error=lexer.make_tokens()
	if error:
		return None,error
	#print(tokens[:])
	parser=Parser(tokens)
	ast=parser.parse()
	if ast.error:
		return None,ast.error
	#print(ast)
	interpreter=Interpreter()
	context=Context("<program>")
	context.symbol_table=global_symbol_table
	result=interpreter.visit(ast.node,context)

	return result.value,result.error
def build(fn, text):
	lexer=Lexer(fn, text)
	tokens,error=lexer.make_tokens()
	if error:
		return None,error
	#print(tokens[:])
	parser=Parser(tokens)
	ast=parser.parse()
	if ast.error:
		return None,ast.error
	#print(ast)
	return ast,None

	#return result.value,result.error