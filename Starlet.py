# Thodwrhs Dhmas 2682 - cse42682
# Leuterhs Panagiwths Kwstakhs 2741 - cse42741


#!/usr/bin/python

import sys
from collections import OrderedDict

# ----- Symbol Table Declarations -----

# Keep the variables of functions when we call this one
# With this way check for the correct order,mode and count of arguments
# A specific method later check this one for the semantic analysis
function_parameters = []

# The framelength of the main program and the halt label we calculate at the end of the program
# For debugging here and in other situations later like this we have assign a negative
# number for better debugging
program_framelength = halt_label = -1

# Save all the scopes of the program
# This list increase and decrease after the insert or the delete of a scope the correct time
# in program
scopes = list()

class Scope():
    def __init__(self, nested_level=0, enclosing_scope = None):
        self.entities, self.nested_level = list(), nested_level
        self.enclosing_scope = enclosing_scope
        self.tmp_offset = 12

    def addEntity(self, entity):
        self.entities.append(entity)

    def get_offset(self):
        retval = self.tmp_offset
        self.tmp_offset += 4
        return retval

    def __str__(self):
        return self.__repr__() + ': (' + str(self.nested_level) + ', ' + self.enclosing_scope.__repr__() + ')'

class Argument():
    def __init__(self, par_mode, next_arg=None):
        self.par_mode = par_mode
        self.next_arg = next_arg

    def set_next(self, next_arg):
        self.next_arg = next_arg

    def __str__(self):
        return self.__repr__() + ': (' + self.par_mode + ',\t' + self.next_arg.__repr__() + ')'

class Entity():
    def __init__(self, name, etype):
        self.name, self.etype, self.next = name, etype, None

    def __str__(self):
        return self.etype + ': ' + self.name

# Entities consist of the objects variable (temp or not),function and parameters
# We use inheritance to organize our information better
class Variable(Entity):
    def __init__(self, name, offset=-1):
        super().__init__(name, "VARIABLE")
        self.offset = offset

    def __str__(self):
        return super().__str__() + ', offset: ' + str(self.offset)

class Function(Entity):
    def __init__(self, name, ret_type, start_quad=-1):
        super().__init__(name, "FUNCTION")
        self.ret_type, self.start_quad = ret_type, start_quad
        self.args, self.framelength = list(), -1

    def add_arg(self, arg):
        self.args.append(arg)

    def set_framelen(self, framelength):
        self.framelength = framelength

    def set_start_quad(self, start_quad):
        self.start_quad = start_quad

    def __str__(self):
        return super().__str__() + ', retv: ' + self.ret_type \
            + ', squad: ' + str(self.start_quad) + ', framelen: ' + str(self.framelength)

class Parameter(Entity):
    def __init__(self, name, par_mode, offset=-1):
        super().__init__(name, "PARAMETER")
        self.par_mode, self.offset = par_mode, offset

    def __str__(self):
        return super().__str__() + ', mode: ' + self.par_mode \
            + ', offset: ' + str(self.offset)

class TmpVar(Entity):
    def __init__(self, name, offset=-1):
        super().__init__(name, "TMPVAR")
        self.offset = offset

    def __str__(self):
        return super().__str__() + ', offset: ' + str(self.offset)

# ----- Final Code Generation Declarations -----

# We use this help variables to implement pass by copy(CP) later
inandout_arguments = []
offsets = []


# ----- Intermediate Code Declarations -----

# In the function program() we need to save the name of the file for the begin block
# and for the entity of main program / with this way pass the information and in other functions
program_name = ""

# After we find the keyword return we save this information
# Later we check if it is placed correct and if every function has at least one return
# We use list instead of a temporary variable to cover the nested situations
have_return = []

# Same as above the following help us to
inside_loop = []
exit_loop = []
inside_function = []

# Use this to generate the c code later - for nested functions
have_subprog = False

# The file that we use to write intermediate code
int_file = open("Intermediate Code", 'w', encoding='utf-8')

# The file that we use to write the final code
outfile = open("Final Code", 'w+', encoding='utf-8')
outfile.write('     .data newline: .asciiz "\n".text')

# The label of the next quad
nextlabel = 0

# Here we save all the temporary variables
tmpvars = dict()

# Return the number for the next temporary variable
next_temp_variable = 1

# Here we save all the quads that we generate for intermediate code
quad_codes = list()

# Holds subprogram parameters as discovered while traversing intermediate code
actual_pars  = list()

# This class organize the quadruples and help us to save the information of them
class Quad():
    def __init__(self, label, op, op1, op2, op3):
        self.label, self.op, self.op1, self.op2 , self.op3 = label, op, op1, op2 , op3

    def __str__(self):
        return '(' + str(self.label) + ': ' + str(self.op)+ ', ' + \
            str(self.op1) + ', ' + str(self.op2) + ', ' + str(self.op3) + ')'

    def tofile(self):
        return str(self.label) + ': (' + str(self.op)+ ', ' + \
            str(self.op1) + ', ' + str(self.op2) + ', ' + str(self.op3) + ')'

# ----- Lexical Analyzer -----

# Give to every variable a number as id in range 0-53
# This number represents the position of every one in the list all_symbols
tk_Add, tk_Sub, tk_Mul, tk_Div, tk_Semicolon, tk_Comma, tk_leftParenthesis, tk_rightParenthesis, \
tk_leftBrace, tk_rightBrace, tk_colon, tk_Program, tk_Endprogram, tk_Declare, tk_If , tk_Then , \
tk_Else , tk_Endif, tk_Dowhile, tk_While, tk_Endwhile, tk_Loop, tk_Endloop, tk_Exit, tk_Forcase, \
tk_Endforcase, tk_Incase, tk_Endincase, tk_When, tk_Default, tk_Enddefault , tk_Function, \
tk_Endfunction, tk_Return, tk_In, tk_Inout, tk_Inandout, tk_And, tk_Or, tk_Not, tk_Input, tk_Print, tk_EOI, \
tk_Identifier, tk_Integer , tk_lessEqual, tk_greaterEqual, tk_assign, tk_define, tk_greater, tk_less, \
tk_different, tk_equal, tk_Enddowhile = range(54)


# Here we keep all the possible token-classes that can have
all_symbols = ["Op_add","Op_substract","Op_multiply","Op_divide","Semicolon","Comma","LeftParenthesis",
               "RightParenthesis","LeftBrace","RightBrace","Colon","Keyword_program","Keyword_endprogram",
               "Keyword_declare","Keyword_if","Keyword_then","Keyword_else","Keyword_endif",
               "Keyword_dowhile","Keyword_while","Keyword_endwhile","Keyword_loop","Keyword_endloop",
               "Keyword_exit","Keyword_forcase","Keyword_endforcase","Keyword_incase","Keyword_endincase",
               "Keyword_when","Keyword_default","Keyword_enddefault","Keyword_function","Keyword_endfunction",
               "Keyword_return","Keyword_in","Keyword_inout","Keyword_inandout","Keyword_and","Keyword_or",
               "Keyword_not","Keyword_input","Keyword_print","End_of_input","Identifier","Integer","LessEqual",
               "GreaterEqual","Assign","Define","Greater","Less","Op_different","Op_equal","Keyword_endDoWhile"]

# Single character only symbols will help as later to define if this is a certain single symbol
# and not followed by other one symbol
symbols = { '+': tk_Add, '-': tk_Sub, "*":tk_Mul,"/":tk_Div,";":tk_Semicolon,
            ',': tk_Comma,"(":tk_leftParenthesis,")":tk_rightParenthesis,"[":tk_leftBrace,
            "]":tk_rightBrace,"=":tk_equal}

# We will use this list to avoid choose an identifier as keyword
# One important rule that will follow our lexical analyzer is to check first if a text is a keyword and
# later if it is an identifier
key_words = {"program":tk_Program, "endprogram":tk_Endprogram, "declare":tk_Declare,
             "if":tk_If, "then":tk_Then, "else":tk_Else, "endif":tk_Endif, "dowhile":tk_Dowhile, "while":tk_While,
             "endwhile":tk_Endwhile,"loop":tk_Loop,"endloop":tk_Endloop,"exit":tk_Exit,
             "forcase":tk_Forcase,"endforcase":tk_Endforcase,"incase":tk_Incase,"endincase":tk_Endincase,
             "when":tk_When,"default":tk_Default,"enddefault":tk_Enddefault,
             "function":tk_Function,"endfunction":tk_Endfunction,"return":tk_Return,"in":tk_In,
             "inout":tk_Inout,"inandout":tk_Inandout,"and":tk_And,"or":tk_Or,"not":tk_Not,
             "input":tk_Input, "print":tk_Print, "enddowhile":tk_Enddowhile}

# Must have one or more space character
# The rule that will follow is that current character must always have a character
# Also we want to differentiate form the end_of_input that is a character with length 0
current_character = " "
line = 1

# Input from command line


filename = str(sys.argv[1])

try:
    input_file = open(filename, "r")
except Exception:
    print("Could not open file")

'''
# Input from the keyboard
filename = input("Give the full path of your file:")

try:
    input_file = open(filename, "r")
except Exception:
    print("Could not open file")
'''


# Get the next character from the input file and in every call move the pointer that
# points to the next character in the file. Also count the number of lines
def get_next_character():

    global current_character ,line
    current_character = input_file.read(1)

    if current_character == "\n":
        line += 1

    return current_character


# Print error and exit from the program
# Because there are various reasons for an error we decided to print the error that we find and a solution
# that could fix it. Later in syntax analysis it will be more clear.
def error(line,message):
    global token

    print("[Error line {}] -- {}".format(line, message))
    exit(1)

    if len(token) == 3:
        print("[Error line {}] -- I found {} '{}'\n\n{} \n".format(line,all_symbols[token[0]],token[2],message))
    elif len(token) == 2:
        print("[Error line {}] -- I found {}\n\n{} \n".format(line,all_symbols[token[0]],message))
    else:
        print("[Error line {}] -- {}".format(line,message))

    exit(1)


# Give as argument the next character and check if the expression is legal
# The main aim is to avoid the unget function. The structure of language allow us by looking the next
# character understand immediately the token class and lexeme. Later in the parser we use LL(1).
def follow(expect_next_symbol,current_character,tk_with_expect_next_symbol,tk_without_expect_next_symbol,error_line):
    if get_next_character() == expect_next_symbol:
        get_next_character()
        return tk_with_expect_next_symbol,error_line,current_character + expect_next_symbol

    if tk_without_expect_next_symbol == tk_EOI:
        error(error_line, "Unrecognized character: (%d) '%c'" % (ord(current_character), current_character))

    return tk_without_expect_next_symbol,error_line,current_character


# We use one variable to define the kind of comments
# Then check if we have double comments
# Finally skip all the characters that are in the comments
# To do the last one we go to the next character again and again until find the terminal characters
# for the comment or if changed the line if this is one line comment
def div_or_comment(error_line):

    is_one_line_comment = False
    get_next_character()

    if current_character != '/' and current_character != "*":
        return tk_Div,error_line,"/"

    # Comment found
    if current_character == '/':
        is_one_line_comment = True

    get_next_character()

    while True:
        if current_character == '*':
            if get_next_character() == '/':
                get_next_character()
                return get_token()
        elif current_character == "/":
            get_next_character()
            if current_character == "*" or current_character == "/":
                return error(error_line,"Double comments")
        elif current_character == '\n' and is_one_line_comment == True:
            get_next_character()
            return get_token()
        elif len(current_character) == 0 and is_one_line_comment == False:
            error(error_line,"EOF in comment")
        else:
            get_next_character()

# We use a boolean variable to understand if we have number or an identifier
# If it is a number check if it is valid
# If it is identifier return the first 30 characters of this string
def identifier_or_integer(error_line):
    is_number = True
    text = ""

    while current_character.isalnum():
        text += current_character
        if not current_character.isdigit():
            is_number = False
        get_next_character()

    if len(text) == 0:
        error(error_line, "Identifier or integer: unrecognized character: (%d) '%c'" % (ord(current_character),current_character))

    if text[0].isdigit():
        if not is_number:
            error(error_line, "invalid number: %s" % (text))
        number = int(text)
        if number < -32767 or number > 32767: # Check if number has a valid value
            error(error_line,"Number out of range")
        return tk_Integer, error_line , number

    if text in key_words:
        return key_words[text],error_line,text

    return tk_Identifier,error_line,text[:30] # max 30 character [:30]


# Check if the token is one of the following <,<=,<>
def lessEqual_or_different(error_line):
    get_next_character()

    if current_character == "=":
        get_next_character()
        return tk_lessEqual,error_line,"<="
    elif current_character == ">":
        get_next_character()
        return tk_different,error_line,"<>"
    else:
        return tk_less,error_line,"<"


# Return a tuple with every token and the line that we found
# Checks for lexical errors that include illegal identifiers or unrecognized symbols
# We choose instead of keep a variable that represent the state and all the states operate like one
# to separate every transition and extract a method for each one. The main reason for this choice is to
# understand more easy and quickly which the next state.
def get_token():
    while current_character.isspace():
        get_next_character()

    error_line = line

    if len(current_character) == 0 : return tk_EOI,error_line
    elif current_character == '/': return div_or_comment(error_line)
    elif current_character == "<": return lessEqual_or_different(error_line)
    elif current_character == ">": return follow("=",current_character,tk_greaterEqual,tk_greater,error_line)
    elif current_character == ":": return follow("=",current_character,tk_assign,tk_define,error_line)
    elif current_character in symbols:
        cc = current_character
        symbol = symbols[current_character]
        get_next_character()
        return symbol,error_line,cc
    else:
        return identifier_or_integer(error_line)


# ----- Syntax Analyzer -----

# Use this tuple as global to keep the information that give us the lexical analyzer
# More specific the token <token-class,lexeme> and the line that we find this one
token = ()

# Check if the first word of program is the keyword 'program'
# Then check if exist the name of program
# Finally check if the last word of program is the keyword 'endprogram'
def program():
    global token , program_name, halt_label
    token = get_token()

    if token[0] == tk_Program:
        token = get_token()

        if token[0] == tk_Identifier:
            program_name = token[2]
            token = get_token()

            scopes.append(Scope())

            block(program_name)

            if token[0] == tk_Endprogram:
                halt_label = nextquad()
                genquad("halt")
                genquad("end_block",program_name)

                print("Complete Succesfully")
            else:
                return error(token[1],"Check if you forget or add not allowed ';'\n"
                                      "Check the correct order of declarations,subprograms,statements \n"
                                      "Check that last word of program is the keyword 'endprogram'\n"
                                      "Check other unexpected reasons for this error")
        else:
            return error(token[1],"Forget the name of program.")

    else:
        return error(token[1],"First word of program is not the keyword 'program'.")

# Call 3 functions that check all the syntax structure of the program
# Every one of this check a specific part of the program
def block(block_name):
    #print_scopes()
    declarations()
    subprograms()
    block_start_quad = update_func_entity_quad(block_name)
    genquad("begin_block", block_name)
    statements()
    update_func_entity_framelen(block_name, scopes[-1].tmp_offset)

    for quad in quad_codes[block_start_quad:]:
        gen_mips_asm(quad, block_name)
    scopes.pop()
    #print_scopes()

def declarations():
    global token

    while token[0] == tk_Declare:
        token = get_token()
        varlist()

        if token[0] == tk_Semicolon:
            token = get_token()
        else:
            return error(token[1],"I lose a ';' or illegal expression before")

def varlist():
    global token

    if token[0] == tk_Identifier:

        add_var_entity(token[2])
        token = get_token()

        while token[0] == tk_Comma:
            token = get_token()

            if token[0] == tk_Identifier:
                add_var_entity(token[2])
                token = get_token()
            else:
                return error(token[1],"I waited for identifier")

def subprograms():
    subprogram()

def subprogram():
    global token , have_return , inside_function

    while token[0] == tk_Function:
        token = get_token()
        have_return.append(False)
        inside_function.append(True)
        add_new_scope()

        if token[0] == tk_Identifier:
            function_name = token[2]
            token = get_token()
            add_func_entity(function_name)
            funcbody(function_name)

            if token[0] == tk_Endfunction:
                if have_return.pop() == False:
                    error(line,"Every function must have a 'return' statement")

                token = get_token()
                inside_function.pop()
                genquad("end_block", function_name)
                # print_scopes()
            else:
                return error(token[1],"Check if you forget or add ';' that not allowed \n"
                                      "Check the correct order of declarations,subprograms,statements\n"
                                      "Check if you forget the keyword 'endfunction'\n"
                                      "Check other unexpected reasons for this error\n")
        else:
            return error(token[1],"I did not find name's function")

def funcbody(function_name):
    formalpars(function_name)
    block(function_name)

def formalpars(function_name):
    global token

    if token[0] == tk_leftParenthesis:
        token = get_token()

        formalparlist(function_name)

        if token[0] == tk_rightParenthesis:
            token = get_token()
        else:
            return error(token[1],"Forget the ')' or illegal expression after the '('.")
    else:
        return error(token[1],"Forget the  '(' after the name of function.")

# Here we need to lookahead the next token to decide the next step
# This happen because we need to check the '()' situation
def formalparlist(function_name):
    global token

    # lookahead the next character
    if token[0] == tk_rightParenthesis:
        return

    formalparitem(function_name)
    while token[0] == tk_Comma:
        token = get_token()
        formalparitem(function_name)

def formalparitem(function_name):
    global token

    if token[0] == tk_In or token[0] == tk_Inout or token[0] == tk_Inandout:

        par_mode = token[2]
        token = get_token()

        if token[0] == tk_Identifier:
            par_name = token[2]
            add_func_arg(function_name,par_mode)
            add_param_entity(par_name,par_mode)
            token = get_token()
        else:
            return error(token[1],"I didn't find the name of one argument in function")
    else:
        return error(token[1],"Every argument in one function must have the keyword 'in' or 'inout' or 'inandout' ")

def statements():
    global token

    statement()

    while token[0] == tk_Semicolon:
        token = get_token()
        statement()

# This is an important part of our program because find the correct statement
# and continue to read the next tokens. Also a statement could be empty.
def statement():
    global token ,inside_function , have_return

    if token[0] == tk_Identifier:
        operator3 = token[2]
        check_id_declaration(operator3) # Check that all identifiers have declared before
        operator1 = assigment_stat()
        genquad(":=",operator1,"_",operator3)
    elif token[0] == tk_If: return if_stat()
    elif token[0] == tk_While: return while_stat()
    elif token[0] == tk_Dowhile: return do_while_stat()
    elif token[0] == tk_Loop: return loop_stat()
    elif token[0] == tk_Exit:return exit_stat()
    elif token[0] == tk_Forcase: return forcase_stat()
    elif token[0] == tk_Incase: return incase_stat()
    elif token[0] == tk_Return:
        if(inside_function == list()):
            error(line,"You have a 'return' statement outside of a function")
        else:
            have_return.append(True)
        return return_stat()
    elif token[0] == tk_Input: return input_stat()
    elif token[0] == tk_Print: return print_stat()

# Help method that check if a variable has declared before
# Created for the semantic analysis stage
def check_id_declaration(name):
    try:
        tmp_entity, elevel = search_entity_by_name(name)
    except:
        error(line,"Undeclared variable {}".format(name))
    if tmp_entity.etype == 'FUNCTION':
        error(line,"Illegal use of function {}".format(name))

# If we see at the beginning of a line an identifier then we need to have the symbol ':='
def assigment_stat():
    global token

    if token[0] == tk_Identifier:
        token = get_token()

        if token[0] == tk_assign:
            token = get_token()
            return expression()
        else:
            error(token[1],"Lose the operator of assign after the identifier")

def if_stat():
    global token

    if token[0] == tk_If:
        token = get_token()

        if token[0] == tk_leftParenthesis:
            token = get_token()

            (condition_true,condition_false) = condition()

            if token[0] == tk_rightParenthesis:
                token = get_token()

                if token[0] == tk_Then:
                    token = get_token()

                    backpatch(condition_true,nextquad())

                    statements()

                    iflist = makelist(nextquad())
                    genquad("jump")
                    backpatch(condition_false,nextquad())

                    elsepart()

                    backpatch(iflist,nextquad())

                    if token[0] == tk_Endif:
                        token = get_token()
                    else:
                        return error(token[1],"Check if you forget ';' or add more than one.\n"
                                              "Check the correct order of declarations,subprograms,statements.\n"
                                              "Check if you forget the keyword 'endif'."
                                              "Check for other unexpected reasons.\n")

                else:
                    return error(token[1],"Forget the keyword 'then'.")
            else:
                return error(token[1],"Forget the ')' or illegal expression after the '('.")
        else:
            return error(token[1],"Forget the '(' ")

def elsepart():
    global token

    if token[0] == tk_Else:
        token = get_token()
        statements()

def while_stat():
    global token

    if token[0] == tk_While:
        token = get_token()
        firstquad = nextquad()

        if token[0] == tk_leftParenthesis:
            token = get_token()

            (condition_true, condition_false) = condition()

            if token[0] == tk_rightParenthesis:
                token = get_token()

                backpatch(condition_true,nextquad())

                statements()

                genquad("jump","_","_",firstquad)
                backpatch(condition_false,nextquad())

                if token[0] == tk_Endwhile:
                    token = get_token()
                else:
                    return error(token[1],"Forget the keyword 'endwhile'.")
            else:
                return error(token[1],"Forget the ')' or illegal expression after the '('.")
        else:
            return error(token[1],"Forget the '('.")

def do_while_stat():
    global token

    if token[0] == tk_Dowhile:
        token = get_token()
        firstquad = nextquad()

        statements()

        if token[0] == tk_Enddowhile:
            token = get_token()

            if token[0] == tk_leftParenthesis:
                token = get_token()

                (condition_true, condition_false) = condition()


                if token[0] == tk_rightParenthesis:
                    token = get_token()

                    backpatch(condition_true,firstquad)
                    backpatch(condition_false,nextquad())
                else:
                    error(token[1],"Forget the ')' or illegal expression after the '('.")
            else:
                error(token[1],"Forget the '('.")
        else:
            error(token[1],"Forget the keyword 'enddowhile'.")

def loop_stat():
    global token ,exit_loop , inside_loop
    first_quad = nextquad()

    if token[0] == tk_Loop:
        token = get_token()
        inside_loop.append(True)
        first_quad = nextquad()
        statements()
        genquad("jump", "_", "_", first_quad)

        if exit_loop != list():
            backpatch(exit_loop.pop(), nextquad())


        if token[0] == tk_Endloop:
            token = get_token()
            inside_loop.pop() # Every time has at least one True from the beginning before the pop()
        else:
            return error(token[1],"Forget the keyword 'endloop' or illegal expression before.")

def exit_stat():
    global token ,exit_loop,inside_loop

    if token[0] == tk_Exit:

        # Check if someone placed an 'exit' somewhere illegal
        if (inside_loop == list()):
            error(token[0],"You have an 'exit' outside of a loop-endloop statement")

        exit_list = makelist(nextquad())
        genquad("jump")
        exit_loop.append(exit_list)
        token = get_token()

def forcase_stat():
    global token

    if token[0] == tk_Forcase:
        token = get_token()
        exitlsit = emptylist()
        firstquad = nextquad()

        while token[0] == tk_When:
            token = get_token()

            if token[0] == tk_leftParenthesis:
                token = get_token()
                (condition_true,condition_false) = condition()

                if token[0] == tk_rightParenthesis:
                    token = get_token()

                    if token[0] == tk_define:
                        token = get_token()

                        backpatch(condition_true,nextquad())
                        statements()

                        outlist = makelist(nextquad())
                        genquad("jump")
                        backpatch(condition_false,nextquad())
                        exitlsit = merge(exitlsit,outlist)

                    else:
                        error(token[1], "Forget the symbol ':' or illegal expression before.")
                else:
                    error(token[1],"Forget the ')' or illegal expression after the '('.")
            else:
                error(token[1],"Forget the '('.")

        if token[0] == tk_Default:
            token = get_token()

            if token[0] == tk_define:
                token = get_token()
                statements()

                genquad("jump","_","_",firstquad)

                if token[0] == tk_Enddefault:
                    token = get_token()

                    if token[0] == tk_Endforcase:
                        token = get_token()

                        backpatch(exitlsit,nextquad())
                    else:
                        error(token[1], "Forget the keyword 'endforcase' or illegal expression before.")
                else:
                    error(token[1],"Forget the keyword 'enddefault'or illegal expression before.")
            else:
                error(token[1],"Forget the symbol ':' or illegal expression before.")
        else:
            error(token[1],"Forget the keyword 'default' or illegal expression before.")

def incase_stat():
    global token

    if token[0] == tk_Incase:
        token = get_token()
        tmpvar = newTemp()
        firstquad = nextquad()
        genquad(":=","0","_",tmpvar) # Suppose that is false

        while token[0] == tk_When:
            token = get_token()

            if token[0] == tk_leftParenthesis:
                token = get_token()

                (condition_true,condition_false) = condition()

                if token[0] == tk_rightParenthesis:
                    token = get_token()

                    if token[0] == tk_define:
                        token = get_token()

                        backpatch(condition_true,nextquad())
                        genquad(":=","1","_",tmpvar) # It becomes true
                        statements()
                        backpatch(condition_false,nextquad())

                    else:
                        error(token[1],"Forget the symbol ':' or illegal expression before.")
                else:
                    error(token[1],"Forget the ')' or illegal expression after the '('.")
            else:
                error(token[1],"Forget the '('.")

        if token[0] == tk_Endincase:
            token = get_token()
            genquad("=", "1", tmpvar, firstquad)
        else:
            error(token[1], "Forget the keyword 'endincase' or found something illegal before.")

def return_stat():
    global token

    if token[0] == tk_Return:
        token = get_token()
        operator1 = expression()
        genquad("retv",operator1)

def print_stat():
    global token

    if token[0] == tk_Print:
        token = get_token()
        operator1 = expression()
        genquad("out",operator1)

def input_stat():
    global token

    if token[0] == tk_Input:
        token = get_token()

        if token[0] == tk_Identifier:
            operator1 = token[2]
            check_id_declaration(operator1)
            token = get_token()
            genquad("inp",operator1)
        else:
            error(token[1],"Forget the identifier after the keyword 'input'.")

# Lookahead the next character to choose the next functions that we need to call
# The most important thing in this function is that if we decide that we don't need check for the parameters
# then we need to get the next token to follow. If we forget this part then we can fail in sentences like x:=fun()
def actualpars():
    global token

    if token[0] == tk_leftParenthesis:
        token = get_token()

        if token[0] == tk_rightParenthesis:
            token = get_token()
            return True

        actualparlist()
        if token[0] == tk_rightParenthesis:
            token = get_token()
        else:
            error(token[1],"Forget the ')' or illegal expression after the '('.")

        return True

def actualparlist():
    global token

    actualparitem()

    while token[0] == tk_Comma:
        token = get_token()
        actualparitem()

def actualparitem():
    global token, function_parameters

    if token[0] == tk_In:
        function_parameters.append("CV")
        token = get_token()
        par_name = expression()
        genquad("par",par_name,"CV")
    elif token[0] == tk_Inout:
        function_parameters.append("REF")
        token = get_token()
        par_name = token[2]
        if token[0] == tk_Identifier:
            token = get_token()
            genquad("par",par_name,"REF")
        else:
            return error(token[1],"Forget the name of identifier after the keyword inout.")

    elif token[0] == tk_Inandout:
        function_parameters.append("CP")
        token = get_token()
        par_name = token[2]

        if(token[0] == tk_Identifier):
            token = get_token()
            genquad("par",par_name,"CP")
        else:
            return error(token[1],"Forget the name of identifier after the keyword inandout.")
    else:
        return error(token[1],"Forget the keyword 'in' or 'inout' or 'inandout' or '('.")

def condition():
    global token

    (b_true,b_false) = (q1_true,q1_false) = boolterm()

    while token[0] == tk_Or:
        backpatch(b_false,nextquad())
        token = get_token()
        (q2_true,q2_false) = boolterm()
        b_true = merge(b_true,q2_true)
        b_false = q2_false

    return (b_true,b_false)

def boolterm():
    global token

    (q_true,q_false) = (r1_true,r1_false) = boolfactor()

    while token[0] == tk_And:
        backpatch(q_true,nextquad())
        token = get_token()
        (r2_true,r2_false) = boolfactor()
        q_false = merge(q_false,r2_false)
        q_true = r2_true

    return (q_true,q_false)

def boolfactor():
    global token

    if token[0] == tk_Not:
        token = get_token()

        if token[0] == tk_leftBrace:
            token = get_token()
            return_value = condition()
            return_value = return_value[::-1] # reverse list for the jump

            if token[0] == tk_rightBrace:
                token = get_token()
            else:
                error(token[2],"You forget the ']' or illegal expression before")
        else:
            error(token[2],"You forget the '[' or illegal expression before")

    elif token[0] == tk_leftBrace:
        token = get_token()

        return_value = condition()

        if token[0] == tk_rightBrace:
            token = get_token()
        else:
            error(token[2],"You forget the ']' or illegal expression before")

    else:
        operator1 = expression()
        operator = relational_oper()
        operator2 = expression()

        relation_true_list = makelist(nextquad())
        genquad(operator,operator1,operator2)
        relation_false_list = makelist(nextquad())
        genquad("jump")
        return_value = (relation_true_list,relation_false_list)

    return return_value

def expression():
    global token

    sign = optional_sign()
    operator1 = term()

    # Check if a number has sign and if it has create a temp variable
    # that keeps the result of the number +-0
    if sign != None:
        tmp_sign = newTemp()
        genquad(sign,0,operator1,tmp_sign)
        operator1 = tmp_sign

    while token[0] == tk_Add or token[0] == tk_Sub:
        operator = token[2]
        token = get_token()
        operator2 = term()
        tmpvar = newTemp()
        genquad(operator,operator1,operator2,tmpvar)
        operator1 = tmpvar

    return operator1

def term():
    global token

    operator1 = factor()

    while token[0] == tk_Mul or token[0] == tk_Div:
        operator = token[2]
        token = get_token()
        operator2 = factor()
        tmpvar = newTemp()
        genquad(operator,operator1,operator2,tmpvar)
        operator1 = tmpvar

    return operator1

# For semantic analysis we check situations if we find a function (used with wrong way)
# or a variable undeclared
def factor():
    global token, function_parameters

    if token[0] == tk_Integer:
        return_value = token[2]
        token = get_token()

    elif token[0] == tk_leftParenthesis:
        token = get_token()
        return_value = expression()

        if token[0] == tk_rightParenthesis:
            token = get_token()
        else:
            return error(token[1],"Forget the ')' or illegal expression after the '('.")

    elif token[0] == tk_Identifier:
        return_value = token[2]
        token = get_token()
        tail = idtail()

        if tail != None:
            function_return_value = newTemp()
            genquad("par",function_return_value,"RET")

            try:
                funce, funcl = search_entity(return_value,"FUNCTION")
            except:
                error(line,"Undefined function {}".format(return_value))

            check_function_arguments(funce, function_parameters,return_value)
            function_parameters.clear()

            genquad("call",return_value)
            return_value = function_return_value

        else:
            try:
                tmp_entity, elevel = search_entity_by_name(return_value)
            except:
                error(line,"Undeclared Variable {} ".format(return_value))

            if tmp_entity.etype == "FUNCTION":
                error(line,"'{}' is function and used as variable".format(return_value))

    else:
        return error(token[1],"Forget a constant or identifier or an expression with parentheses.")

    return return_value

# Help method that used for semantic analysis
# Check if the arguments of a function that we call are like this one in the declaration
# of the function
def check_function_arguments(func_entity, function_parameters, function_name):
    if len(function_parameters) == 0:
        if (len(func_entity.args) != 0):
            error(line,"The function {} must not have parameters".format(function_name))
    else:
        if (len(function_parameters) != len(func_entity.args)):
            error(line,"The count of parameters for function {} is not like the declare of this.".format(function_name))

        function_parameters = function_parameters[::-1] # reverse list to check the arguments with the correct order
        for arg in func_entity.args:
            function_parameter = function_parameters.pop()
            if arg.par_mode != function_parameter:
                error(line,"I expected {} but i found {} in the function {}".format(arg.par_mode,function_parameter,function_name))

# Here ia another tricky situation that we must check the next token before we call the correct function
def idtail():
    global token

    if token[0] != tk_leftParenthesis:
        return

    return actualpars()

def relational_oper():
    global token

    oper = token[2]

    if token[0] == tk_equal or token[0] == tk_lessEqual or token[0] == tk_greaterEqual or token[0] == tk_greater or token[0] == tk_less or token[0] == tk_different:
        token = get_token()
    else:
        return error(token[1],"Must have one from the following symbols =,<=,>=,>,<,<> or illegal expression before")

    return oper

def add_oper():
    global token

    oper = token[2]

    if token[0] == tk_Add or token[0] == tk_Sub:
        token = get_token()
    else:
        return error(token[1],"Must have one from the following symbols +,- or illegal expression before")

    return oper

def mul_oper():
    global token

    oper = token[2]

    if token[0] == tk_Mul or token[0] == tk_Div:
        token = get_token()
    else:
        return error(token[1],"Must have one from the following symbols *,/ or illegal expression before")

    return oper

def optional_sign():
    global token

    opt_signal = token[2]

    if token[0] == tk_Add or token[0] == tk_Sub:
        token = get_token()
        return opt_signal

# ----- Intermediate Code -----

# Return the label for the next quad
def nextquad():
    return nextlabel

# Fill the fields of a quad
def genquad(op = None, op1 = '_', op2 = '_', op3 = '_'):
    global nextlabel
    label = nextlabel
    nextlabel += 1
    newquad = Quad(label, op, op1, op2, op3)
    quad_codes.append(newquad)

# Return the next temp variable
def newTemp():
    global temp_variables, next_temp_variable
    key = 'T_' + str(next_temp_variable)
    tmpvars[key] = None

    offset = scopes[-1].get_offset()
    scopes[-1].addEntity(TmpVar(key,offset))

    next_temp_variable += 1
    return key

def emptylist():
    return list()

def makelist(label):
    newlist = list()
    newlist.append(label)
    return newlist

def merge(list1, list2):
    return list1 + list2

def backpatch(list, label):
    global quad_codes
    for quad in quad_codes:
        if quad.label in list:
            quad.op3 = label

# Generate a file containing the intermediate code of the user program
def generate_int_code_file():
    for quad in quad_codes:
        int_file.write(quad.tofile() + '\n')
    int_file.close()

# ----- Equivalent C -----

# Find which variables should be declared.
def find_var_decl(quad):
    vars = dict()
    index = quad_codes.index(quad) + 1
    while True:
        q = quad_codes[index]
        if q.op == 'end_block':
            break
        if q.op2 not in ('CV', 'REF', 'CP' ,'RET') and q.op != 'call':
            if isinstance(q.op1, str):
                vars[q.op1] = 'int'
            if isinstance(q.op2, str):
                vars[q.op2] = 'int'
            if isinstance(q.op3, str):
                vars[q.op3] = 'int'
        index += 1
    if '_' in vars:
        del vars['_']
    return OrderedDict(sorted(vars.items()))


# Transform variable declarations to C equivalent.
def transform_decls(vars):
    flag = False
    retval = '\n\tint '
    for var in vars:
        flag = True
        retval += var + ', '
    if flag == True:
        return retval[:-2] + ';'
    else:
        return ''


# Transform a quad to C code.
def transform_to_c(quad):
    addlabel = True
    if quad.op == 'jump':
        retval = 'goto L_' + str(quad.op3) + ';'
    elif quad.op in ('=', '<>', '<', '<=', '>', '>='):
        op = quad.op
        if op == '=':
            op = '=='
        elif op == '<>':
            op = '!='
        retval = 'if (' + str(quad.op1) + ' ' + op + ' ' + \
            str(quad.op2) + ') goto L_' + str(quad.op3) + ';'
    elif quad.op == ':=':
        retval = quad.op3 + ' = ' + str(quad.op1) + ';'
    elif quad.op in ('+', '-', '*', '/'):
        retval = quad.op3 + ' = ' + str(quad.op1) + ' ' + \
            str(quad.op) + ' ' + str(quad.op2) + ';'
    elif quad.op == 'out':
        retval = 'printf("%d\\n", ' + str(quad.op1) + ');'
    elif quad.op == 'retv':
        retval = 'return (' + str(quad.op1) + ');'
    elif quad.op == 'begin_block':
        addlabel = False
        if quad.op1 == program_name:
            retval = 'int main(void)\n{'
        else:
            retval = 'int ' + quad.op1 + '()\n{'
        vars = find_var_decl(quad)
        retval += transform_decls(vars)
        retval += '\n\tL_' + str(quad.label) + ':'
    elif quad.op == 'call':
        retval = quad.op1 + '();'
    elif quad.op == 'end_block':
        addlabel = False
        retval = '\tL_' + str(quad.label) + ': {}\n'
        retval += '}\n'
    elif quad.op == 'halt':
        retval = 'return 0;'
    else:
        return None
    if addlabel == True:
        retval = '\tL_' + str(quad.label) + ': ' + retval
    return retval


ceq_file = open("C_Equivalent", 'w', encoding='utf-8')

# Generate a file containing the C equivalent code of intermediate code.
def generate_c_code_file():
    ceq_file.write('#include <stdio.h>\n\n')
    for quad in quad_codes:
        tmp = transform_to_c(quad)
        if tmp != None:
            ceq_file.write(tmp + '\n')
    ceq_file.close()


# ----- Symbol Table ------

def add_new_scope():
    enclosing_scope = scopes[-1]
    curr_scope = Scope(enclosing_scope.nested_level + 1, enclosing_scope)
    scopes.append(curr_scope)

def delete_scope():
    scopes.pop()

# Help method used to check if all were good -- Mainly for debugging
def print_scopes():
    print('* main scope\n|')
    for scope in scopes:
        level = scope.nested_level + 1
        print('    ' * level + str(scope))
        for entity in scope.entities:
            print('|    ' * level + str(entity))
            if isinstance(entity, Function):
                for arg in entity.args:
                    print('|    ' * level + '|    ' + str(arg))
    print('\n')

# Add a new function entity.
def add_func_entity(name):
    # Function declarations are on the enclosing scope of the current scope.
    nested_level = scopes[-1].enclosing_scope.nested_level

    if not unique_entity(name, "FUNCTION", nested_level):
        error(line,"Redefinition of {}".format(name))

    try:
        tmp_entity, elevel = search_entity_by_name(name)
    except:
        scopes[-2].addEntity(Function(name, "int"))
        return

    if elevel == nested_level-1 and tmp_entity.etype == "FUNCTION":
        error(line,"You have declared the variable {} again".format(name))
    elif elevel == nested_level and tmp_entity.etype == "VARIABLE":
        error(line, "You have declared the variable {} again".format(name))

    scopes[-2].addEntity(Function(name, "int"))

# Update the start quad label of a function entity.
def update_func_entity_quad(name):
    start_quad = nextquad()
    if name == program_name:
        return start_quad
    func_entity = search_entity(name, "FUNCTION")[0]
    func_entity.set_start_quad(start_quad)
    return start_quad

# Update the framelength of a function entity.
def update_func_entity_framelen(name, framelength):
    global program_framelength
    if name == program_name:
        program_framelength = framelength
        return
    func_entity = search_entity(name, "FUNCTION")[0]
    func_entity.set_framelen(framelength)

# Add a new parameter entity.
def add_param_entity(name, par_mode):
    nested_level = scopes[-1].nested_level
    par_offset   = scopes[-1].get_offset()
    if not unique_entity(name, "PARAMETER", nested_level):
        error(line,"Redefinition of {}".format(name))
    scopes[-1].addEntity(Parameter(name, par_mode, par_offset))

# Add a new variable entity.
def add_var_entity(name):
    nested_level = scopes[-1].nested_level
    var_offset   = scopes[-1].get_offset()
    if not unique_entity(name, "VARIABLE", nested_level):
        error(line,"Redifinition of {}".format(name))
    if var_is_param(name, nested_level):
        error(line,"Redeclared again different {}".format(name))

    try:
        tmp_entity, elevel = search_entity_by_name(name)
    except:
        scopes[-1].addEntity(Variable(name, var_offset))
        return

    if elevel == nested_level-1 and tmp_entity.etype == "FUNCTION":
        error(line, "You have declared the variable {} again".format(name))
    elif elevel == nested_level and tmp_entity.etype == "VARIABLE":
        error(line,"You have declared the variable {} again".format(name))

    scopes[-1].addEntity(Variable(name, var_offset))

# Add a new function argument to a given function.
def add_func_arg(func_name, par_mode):
    if (par_mode == 'in'):
        new_arg = Argument('CV')
    elif(par_mode == 'inout'):
        new_arg = Argument('REF')
    else:
        new_arg = Argument('CP')

    func_entity = search_entity(func_name, "FUNCTION")[0]
    if func_entity == None:
        error(line,"No definition was found for {}".format(func_entity))
    if func_entity.args != list():
        func_entity.args[-1].set_next(new_arg)
    func_entity.add_arg(new_arg)

# Search for an entity given the name and type of this
def search_entity(name, etype):
    if scopes == list():
        return
    tmp_scope = scopes[-1]
    while tmp_scope != None:
        for entity in tmp_scope.entities:
            if entity.name == name and entity.etype == etype:
                return entity, tmp_scope.nested_level
        tmp_scope = tmp_scope.enclosing_scope

# Search for an entity given the name only
def search_entity_by_name(name):
    if scopes == list():
        return
    tmp_scope = scopes[-1]
    while tmp_scope != None:
        for entity in tmp_scope.entities:
            if entity.name == name:
                return entity, tmp_scope.nested_level
        tmp_scope = tmp_scope.enclosing_scope

# Check if entity named 'name' of type 'etype' at nested level 'nested_level' is redefined.
def unique_entity(name, etype, nested_level):

    if scopes[-1].nested_level < nested_level:
        return
    scope = scopes[nested_level]
    list_len = len(scope.entities)
    for i in range(list_len):
        for j in range(list_len):
            e1 = scope.entities[i]
            e2 = scope.entities[j]
            if e1.name == e2.name and e1.etype == e2.etype \
                    and e1.name == name and e1.etype == etype:
                return False
    return True

# Check if a variable entity already exits as parameter
def var_is_param(name, nested_level):
    if scopes[-1].nested_level < nested_level:
        return
    scope = scopes[nested_level]
    list_len = len(scope.entities)
    for i in range(list_len):
        e = scope.entities[i]
        if e.etype == "PARAMETER" and e.name == name:
            return True
    return False


# ----- Final Code ------


# Load in register $t0 the address of the non-local variable 'v'.
def gnvlcode(v):
    try:
        tmp_entity, elevel  = search_entity_by_name(v)
    except:
        print("Underclared variable: {}",v)
        exit(1)
    if tmp_entity.etype == 'FUNCTION':
        print("Undeclared variable: {}",v)
        exit(1)
    curr_nested_level   = scopes[-1].nested_level
    outfile.write('    lw      $t0, -4($sp)\n')
    n = curr_nested_level - elevel - 1
    while  n > 0:
        outfile.write('    lw      $t0, -4($t0)\n')
        n -= 1
    outfile.write('    addi    $t0, $t0, -%d\n' % tmp_entity.offset)

# Load immediate or data 'v' from memory to register $t{r}.
def loadvr(v, r):
    if str(v).isdigit():
        outfile.write('    li      $t%s, %d\n' % (r, v))
    else:
        try:
            tmp_entity, elevel = search_entity_by_name(v)
        except:
            print("Undeclared variable: {}",v)
            exit(1)
        curr_nested_level  = scopes[-1].nested_level
        if tmp_entity.etype == 'VARIABLE' and elevel == 0:
            outfile.write('    lw      $t%s, -%d($s0)\n' % (r, tmp_entity.offset))
        elif (tmp_entity.etype == 'VARIABLE' and elevel == curr_nested_level) \
                or (tmp_entity.etype == 'PARAMETER' and (tmp_entity.par_mode == 'in'or tmp_entity.par_mode == 'inandout') and elevel == curr_nested_level) \
                or (tmp_entity.etype == 'TMPVAR'):
            outfile.write('    lw      $t%s, -%d($sp)\n' % (r, tmp_entity.offset))
        elif tmp_entity.etype == 'PARAMETER' and tmp_entity.par_mode == 'inout' \
                and elevel == curr_nested_level:
            outfile.write('    lw      $t0, -%d($sp)\n' % tmp_entity.offset)
            outfile.write('    lw      $t%s, 0($t0)\n' % r)
        elif (tmp_entity.etype == 'VARIABLE' and elevel < curr_nested_level) \
                or (tmp_entity.etype == 'PARAMETER'
                and (tmp_entity.par_mode == 'in' or tmp_entity.par_mode == 'inandout') \
                and elevel < curr_nested_level):
            gnvlcode(v)
            outfile.write('    lw      $t%s, 0($t0)\n' % r)
        elif tmp_entity.etype == 'PARAMETER' and tmp_entity.par_mode == 'inout' \
                and elevel < curr_nested_level:
            gnvlcode(v)
            outfile.write('    lw      $t0, 0($t0)\n')
            outfile.write('    lw      $t%s, 0($t0)\n' % r)
        else:
            print("loadvr loads an immediate or data from memory to a register")
            exit(1)


# Store the contents of register $t{r} to the memory allocated for variable 'v'.
def storerv(r, v):
    try:
        tmp_entity, elevel = search_entity_by_name(v)
    except:
        print("Undeclared variable: {}",v)
    curr_nested_level  = scopes[-1].nested_level
    if tmp_entity.etype == 'VARIABLE' and elevel == 0:
        outfile.write('    sw      $t%s, -%d($s0)\n' % (r, tmp_entity.offset))
    elif (tmp_entity.etype == 'VARIABLE' and elevel == curr_nested_level) \
            or (tmp_entity.etype == 'PARAMETER' and (tmp_entity.par_mode == 'in' or tmp_entity.par_mode == 'inandout') and elevel == curr_nested_level) \
            or (tmp_entity.etype == 'TMPVAR'):
        outfile.write('    sw      $t%s, -%d($sp)\n' % (r, tmp_entity.offset))
    elif tmp_entity.etype == 'PARAMETER' and tmp_entity.par_mode == 'inout' \
            and elevel == curr_nested_level:
        outfile.write('    lw      $t0, -%d($sp)\n' % tmp_entity.offset)
        outfile.write('    sw      $t%s, 0($t0)\n' % r)
    elif (tmp_entity.etype == 'VARIABLE' and \
            elevel < curr_nested_level) or \
            (tmp_entity.etype == 'PARAMETER' and (tmp_entity.par_mode == 'in' or tmp_entity.par_mode == 'inandout') \
            and elevel < curr_nested_level):
        gnvlcode(v)
        outfile.write('    sw      $t%s, 0($t0)\n' % r)
    elif tmp_entity.etype == 'PARAMETER' and tmp_entity.par_mode == 'inout' \
            and elevel < curr_nested_level:
        gnvlcode(v)
        outfile.write('    lw      $t0, 0($t0)\n')
        outfile.write('    sw      $t%s, 0($t0)\n' % r)
    else:
        print("storerv stores the contents of a register to memory")
        exit(1)

# Generate the assembly code for quad 'quad'. 'block_name' is the name
# of the block that is currently translated into final code.
def gen_mips_asm(quad, block_name):
    global actual_pars,inandout_arguments,offsets

    if str(quad.label) == '0':
        outfile.write(' ' * 70) # Will be later overwritten
    outfile.write('\nL_' + str(quad.label) + ':   #' + quad.tofile() + '\n')
    starlet_relop = ('=', '<>', '<', '<=', '>', '>=')
    asm_relop = ('beq', 'bne', 'blt', 'ble', 'bgt', 'bge')
    starlet_op    = ('+', '-', '*', '/')
    asm_op    = ('add', 'sub', 'mul', 'div')
    if quad.op == 'jump':
        outfile.write('    j       L_%d\n' % quad.op3)
    elif quad.op in starlet_relop:
        relop = asm_relop[starlet_relop.index(quad.op)]
        loadvr(quad.op1, '1')
        loadvr(quad.op2, '2')
        outfile.write('    %s     $t1, $t2, L_%d\n' % (relop, quad.op3))
    elif quad.op == ':=':
        loadvr(quad.op1, '1')
        storerv('1', quad.op3)
    elif quad.op in starlet_op:
        op = asm_op[starlet_op.index(quad.op)]
        loadvr(quad.op1, '1')
        loadvr(quad.op2, '2')
        outfile.write('    %s     $t1, $t1, $t2\n' % op)
        storerv('1', quad.op3)
    elif quad.op == 'out':
        loadvr(quad.op1, '9')
        outfile.write('    li      $v0, 1\n')
        outfile.write('    add     $a0, $zero, $t9\n')
        outfile.write('    syscall   # service code 1: print integer\n')
        outfile.write('    la      $a0, newline\n')
        outfile.write('    li      $v0, 4\n')
        outfile.write('    syscall   # service code 4: print (a null terminated) string\n')
    elif quad.op == 'retv':
        loadvr(quad.op1, '1')
        outfile.write('    lw      $t0, -8($sp)\n')
        outfile.write('    sw      $t1, 0($t0)\n')
        # Actually return to caller; just like end_block case.
        outfile.write('    lw      $ra, 0($sp)\n')
        outfile.write('    jr      $ra\n')
    elif quad.op == 'halt':
        outfile.write('    li      $v0, 10   # service code 10: exit\n')
        outfile.write('    syscall\n')
    elif quad.op == 'par':
        if block_name == program_name:
            caller_level = 0
            framelength = program_framelength
        else:
            caller_entity, caller_level = search_entity(block_name, 'FUNCTION')
            framelength = caller_entity.framelength
        if actual_pars == []:
            outfile.write('    addi    $fp, $sp, -%d\n' % framelength)
        actual_pars.append(quad)
        param_offset = 12 + 4 * actual_pars.index(quad)
        if (quad.op2 == 'CV') :
            loadvr(quad.op1, '0')
            outfile.write('    sw      $t0, -%d($fp)\n' % param_offset)
        elif (quad.op2 == 'CP'):
            loadvr(quad.op1, '0')
            outfile.write('    sw      $t0, -%d($fp)\n' % param_offset)
            inandout_arguments.append(quad.op1)
            offsets.append(param_offset)
        elif quad.op2 == 'REF':
            try:
                var_entity, var_level = search_entity_by_name(quad.op1)
            except:
                print("Undeclared variable: {}",quad.op1)
                exit(1)
            if caller_level == var_level:
                if var_entity.etype == 'VARIABLE' or \
                        (var_entity.etype == 'PARAMETER' and \
                        (var_entity.par_mode == 'in' or var_entity.par_mode == "inandout" )):
                    outfile.write('    addi    $t0, $sp, -%s\n' % var_entity.offset)
                    outfile.write('    sw      $t0, -%d($fp)\n' % param_offset)
                elif var_entity.etype == 'PARAMETER' and \
                        var_entity.par_mode == 'inout':
                    outfile.write('    lw      $t0, -%d($sp)\n' % var_entity.offset)
                    outfile.write('    sw      $t0, -%d($fp)\n' % param_offset)
            else:
                if var_entity.etype == 'VARIABLE' or \
                        (var_entity.etype == 'PARAMETER' and \
                        (var_entity.par_mode == 'in' or var_entity.par_mode == "inandout")):
                    gnvlcode(quad.op1)
                    outfile.write('    sw      $t0, -%d($fp)\n' % param_offset)
                elif var_entity.etype == 'PARAMETER' and \
                        var_entity.par_mode == 'inout':
                    gnvlcode(quad.op1)
                    outfile.write('    lw      $t0, 0($t0)\n')
                    outfile.write('    sw      $t0, -%d($fp)\n' % param_offset)
        elif quad.op2 == 'RET':
            try:
                var_entity, var_level = search_entity_by_name(quad.op1)
            except:
                print("Undeclared variable: {}", quad.op1)
                exit(1)
            outfile.write('    addi    $t0, $sp, -%d\n' % var_entity.offset)
            outfile.write('    sw      $t0, -8($fp)\n')
    elif quad.op == 'call':
        if block_name == program_name:
            caller_level = 0
            framelength = program_framelength
        else:
            caller_entity, caller_level = search_entity(block_name, 'FUNCTION')
            framelength = caller_entity.framelength
        try:
            callee_entity, callee_level = search_entity(quad.op1, 'FUNCTION')
        except:
            print("Undefined function: {}", quad.op1)
            exit(1)
        check_subprog_args(callee_entity.name)
        if caller_level == callee_level:
            outfile.write('    lw      $t0, -4($sp)\n')
            outfile.write('    sw      $t0, -4($fp)\n')
        else:
            outfile.write('    sw      $sp, -4($fp)\n')
        outfile.write('    addi    $sp, $sp, -%d\n' % framelength)
        outfile.write('    jal     L_%s\n' % str(callee_entity.start_quad))

        inandout_arguments = inandout_arguments[::-1]

        for arg in inandout_arguments:
            outfile.write('    lw    $t1, -%d($fp)\n' % offsets.pop())
            storerv('1',arg)

        inandout_arguments.clear()

        outfile.write('    addi    $sp, $sp, %d\n' % framelength)

    elif quad.op == 'begin_block':
        outfile.write('    sw      $ra, 0($sp)\n')
        if block_name == program_name:
            outfile.seek(0,0)   # Go to the beginning of the output file
            outfile.write('    .data\n     newline: .asciiz "\\n"\n')  # For printing newline character

            outfile.write('    .globl L_%d\n' % quad.label)
            outfile.write('    .text\n\n')
            outfile.write('    j       L_%d   # main program\n' % quad.label)
            outfile.seek(0,2)   # Go to the end of the output file
            outfile.write('    move    $s0, $sp\n')
    elif quad.op == 'end_block':
        if block_name == program_name:
            outfile.write('    j       L_%d\n' % halt_label)
            # For printing newline character
            outfile.write('\n###########################\n\n')
            outfile.write('    .data\n\n')
            outfile.write('newline:  .asciiz    "\\n"\n\n')
        else:
            outfile.write('    lw      $ra, 0($sp)\n')
            outfile.write('    jr      $ra\n')


# Check if actual parameters of subprogram 'name' are of the same type as typical parameters.
def check_subprog_args(name):
    global actual_pars
    entity, level = search_entity_by_name(name)
    if entity.ret_type == 'int':
        actual_pars.pop() # pop parameter of type 'RET'
    if len(entity.args) != len(actual_pars):
        print("Missmatching subprogram argument number")
        exit(1)
    for arg in entity.args:
        quad = actual_pars.pop(0)
        if not (arg.par_mode == quad.op2):
            if arg.par_mode == 'CV':
                ptype = 'int'
            else:
                ptype = 'int *'
            print("Expected parameter {} to be of type {}",quad.op1,ptype)
            exit(1)

# ----- Main Program -----


program()
generate_int_code_file()
generate_c_code_file()

