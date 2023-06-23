"""
File contains functions that test whether two ast trees are equivalently the same line of code
"""

import ast

class UnsupportedSyntaxError(Exception):
    """
    Raised when a class has not been handled in our AST solver class
    """
    pass

def same_ast_tree(expected, actual): 
    """
    Function determines whether two lines of code are equivalent
    Returns a boolean stating whether the two lines of code passed in are equivalent
    """
    if expected == actual:
        return True
        
    try:
        expected_tree = ast.parse(expected.strip())
        actual_tree = ast.parse(actual.strip())
    except SyntaxError:
        return False

    if len(expected_tree.body) != 1:
        return False
    elif type(expected_tree.body[0]) != type(actual_tree.body[0]): 
        # ensuring the type of each class we are checking is the same
        if (isinstance(actual_tree.body[0], ast.AugAssign) or isinstance(actual_tree.body[0], ast.Assign)) and (isinstance(expected_tree.body[0], ast.AugAssign) or isinstance(expected_tree.body[0], ast.Assign)):
            # an exception to the classes needing to be the same is AugAssign and Assign
            return check_augassign_or_assign_equal(expected_tree.body[0], actual_tree.body[0])
        return False 
    elif isinstance(actual_tree.body[0], ast.Expr):
        # checking whether both classes are expressions, then checks whether the expressions are equivalent
        return check_type(expected_tree.body[0].value, actual_tree.body[0].value)
    elif isinstance(actual_tree.body[0], ast.Assign):
        # checking whether both classes are assign statements, then checks whether the targets and values are the same
        if len(actual_tree.body[0].targets) != len(expected_tree.body[0].targets):
            return False
        for i in range(len(actual_tree.body[0].targets)):
            if not check_type(actual_tree.body[0].targets[i], expected_tree.body[0].targets[i]):
                return False
        return check_type(expected_tree.body[0].value, actual_tree.body[0].value)
    elif isinstance(actual_tree.body[0], ast.AugAssign):
        # checking whether both classes are AugAssign statements, then checks whether the targets and values are the same
        if actual_tree.body[0].target.id == expected_tree.body[0].target.id: # check if being assigned to the same variable
            if type(actual_tree.body[0].op) == type(expected_tree.body[0].op): # check if same operation is being used
                return check_type(expected_tree.body[0].value, actual_tree.body[0].value) # check if the values have the same type
    elif isinstance(actual_tree.body[0], ast.Return):
        # checking whether both classes are return statements, then checks whether the values are the same
        return check_type(expected_tree.body[0].value, actual_tree.body[0].value)
    elif isinstance(actual_tree.body[0], ast.Delete):
        # checking whether both classes are delete statements, then checks whether the targets are the same
        if len(actual_tree.body[0].targets) != len(expected_tree.body[0].targets):
            return False
        for i in range(len(actual_tree.body[0].targets)):
            if not check_type(actual_tree.body[0].targets[i], expected_tree.body[0].targets[i]):
                return False
        return True
    elif isinstance(actual_tree.body[0], ast.If):
        # checking whether both classes are if statements, then checks whether the body,orelse and test are the same
        return check_type(expected_tree.body[0].body[0], actual_tree.body[0].body[0]) and check_type(expected_tree.body[0].orelse, actual_tree.body[0].orelse) and check_type(expected_tree.body[0].test, actual_tree.body[0].test) 
    elif isinstance(actual_tree.body[0], ast.For):
        # checking whether both classes are if statements, then checks whether the body,orelse,iter, and target are the same
        return check_type(expected_tree.body[0].body, actual_tree.body[0].body) and check_type(expected_tree.body[0].orelse, actual_tree.body[0].orelse) and check_type(expected_tree.body[0].iter, actual_tree.body[0].iter) and check_type(expected_tree.body[0].target, actual_tree.body[0].target) 
    elif isinstance(actual_tree.body[0], ast.While):
        # checking whether both classes are while loops, then checks whether the body,orelse and test are the same
        return check_type(expected_tree.body[0].body, actual_tree.body[0].body) and check_type(expected_tree.body[0].orelse, actual_tree.body[0].orelse) and check_type(expected_tree.body[0].test, actual_tree.body[0].test) 
    else:
        # print("Type not handled yet: "+ type(actual_tree.body[0]))
        raise UnsupportedSyntaxError
 
    return False

def check_type(expected, actual):
    """
    Function determines whether two classes are equivalent and determines the correct funcitons to determine this
    Returns a boolean stating whether the two classes passed in are equivalent
    """
    if type(actual) == type(expected):
        if isinstance(actual, ast.Constant) or isinstance(actual, ast.Expr):
            return (actual.value == expected.value)
        elif isinstance(actual, ast.Name):
            return (actual.id == expected.id)
        elif isinstance(actual, ast.UnaryOp):
            if expected.op == actual.op:
                return check_type(expected.operand, actual.operand)
        elif isinstance(actual, ast.BinOp):
            return check_bin_op(expected, actual)
        elif isinstance(actual, ast.Dict):
            return check_dict(expected, actual)
        elif isinstance(actual, ast.Call):
            return check_function_call(expected, actual)
        elif isinstance(actual, ast.List) or isinstance(actual, ast.Tuple) or isinstance(actual, ast.Set):
            return check_list(expected, actual)
        elif isinstance(actual, list):
            for i in range(len(actual)):
                if not check_type(expected[i], actual[i]):
                    return False
            return True
        elif isinstance(actual, ast.Subscript):
            if expected.ctx == actual.ctx:
                return check_type(expected.slice, actual.slice) and check_type(expected.value, actual.value)
        elif isinstance(actual, ast.Slice):
            return check_type(expected.lower, actual.lower) and check_type(expected.upper, actual.upper) and check_type(expected.step, actual.step)  
        elif isinstance(actual, ast.Attribute):
            if expected.attr == actual.attr:
                return check_type(expected.value, actual.value)
        elif isinstance(actual, ast.Compare):
            return check_compare(expected,actual)
        elif actual == None and expected == None:
            return True
        elif isinstance(actual, ast.Pass) or isinstance(actual, ast.Break) or isinstance(actual, ast.Continue):
            return True
        elif isinstance(actual, ast.If):
            return check_type(expected.body[0], actual.body[0]) and check_type(expected.orelse, actual.orelse) and check_type(expected.test, actual.test) 
        elif isinstance(actual, ast.BoolOp):
            return check_bool_op(expected, actual)
        else:
            # print("another type that is not handled yet")
            # return False
            raise UnsupportedSyntaxError
    return False

def check_bool_op(expected, actual):
    """
    Function determines whether two BoolOp statements are equivalent
    Returns a boolean stating whether the two BoolOp Statements passed in are equivalent
    """
    if expected.op == actual.op:
        if isinstance(actual.op, ast.Or):
            return check_type(expected.values[0], actual.values[0]) and check_type(expected.values[1], actual.values[1])
        elif isinstance(actual.op, ast.And):
            same = check_type(expected.values[0], actual.values[0]) and check_type(expected.values[1], actual.values[1])
            opposite = check_type(expected.values[0], actual.values[1]) and check_type(expected.values[1], actual.values[0])
            return same or opposite
        else:
            print("bool op not handled yet")
            return False
    else:
        return False

def check_compare(expected,actual):
    """
    Function determines whether two Compare statements are equivalent
    Returns a boolean stating whether the two Compare Statements passed in are equivalent
    """
    if len(actual.comparators) != len(expected.comparators) or len(actual.ops) != len(expected.ops):
        return False
    elif len(actual.comparators) == 1:
        opposites = {ast.Lt:ast.Gt, ast.Gt:ast.Lt, ast.GtE:ast.LtE, ast.LtE:ast.GtE}
        if expected.ops[0] == actual.ops[0]: # if both have the same operation
            return check_type(expected.left, actual.left) and check_type(expected.comparators[0], actual.comparators[0])
        else:
            if opposites.get(type(actual.ops[0])) == type(expected.ops[0]):
                return check_type(expected.left, actual.comparators[0]) and check_type(expected.left, actual.comparators[0])
            else:
                return False
    else:
        # print("case not handled yet")
        # return False
        raise UnsupportedSyntaxError
    
def check_dict(expected, actual):
    """
    Function determines whether two dictionaries are equivalent
    Returns a boolean stating whether the two dictionaries passed in are equivalent
    """
    if (len(expected.keys) != len(actual.keys)) or (len(expected.values) != len(actual.values)):
        return False
    elif (len(expected.keys) != len(expected.values)) or (len(actual.keys) != len(actual.values)):
        return False
    
    for a in range(len(actual.keys)):
        found = False
        for e in range(len(expected.keys)):
            if check_type(actual.keys[a], expected.keys[e]):
                found = True
                if not check_type(actual.values[a], expected.values[e]):
                    return False # return False if values don't match
        if not found:
            return False # return false if key is not in both dicts
    
    return True 

def check_list(expected, actual):
    """
    Function determines whether two lists calls are equivalent
    Returns a boolean stating whether the two lists passed in are equivalent
    """
    if len(actual.elts) != len(expected.elts): # ensuring same number of elements
        return False

    for i in range(len(actual.elts)):
        if not check_type(actual.elts[i],expected.elts[i]):
            return False
    return True

def check_function_call(expected_tree, actual_tree):
    """
    Function determines whether two function calls are equivalent
    Returns a boolean stating whether the two functions passed in are equivalent
    """
    if len(actual_tree.args) != len(expected_tree.args): # ensuring same number of arguments for each
        return False
    elif not check_type(expected_tree.func, actual_tree.func):
        return False

    for i in range(len(actual_tree.args)): # loop through and make sure arguments are the same
        if not check_type(actual_tree.args[i],expected_tree.args[i]):
            return False
    return True

def check_augassign_or_assign_equal(expected_tree, actual_tree):
    """
    Function determines whether an AugAssign and Assign are equivalent
    Returns a boolean stating whether the two trees passed in are equivalent
    """
    if isinstance(actual_tree, ast.AugAssign):
        aug_assign = actual_tree
        assign = expected_tree
    else:
        aug_assign = expected_tree
        assign = actual_tree

    if type(aug_assign.op) == type(assign.value.op): # check if operation is the same
        if isinstance(assign.value.right, ast.Name) or isinstance(assign.value.left, ast.Name): # one on right side of = must be a variable
            if check_type(assign.targets[0], aug_assign.target): # ensure setting equal to same variable
                if not isinstance(assign.value.left, ast.Name) and isinstance(assign.value.right, ast.Name): # right side is the variable
                    if isinstance(assign.value.op, ast.Sub) or isinstance(assign.value.op, ast.Div): # x=2-x != x-=2
                        return False
                    elif check_type(assign.value.right, assign.targets[0]) and check_type(assign.value.right, aug_assign.target):
                        return check_type(assign.value.left, aug_assign.value)
                elif not isinstance(assign.value.right, ast.Name) and isinstance(assign.value.left, ast.Name): # left side is variable
                    if check_type(assign.value.left, assign.targets[0]) and check_type(assign.value.left, aug_assign.target):
                        return check_type(assign.value.right, aug_assign.value)
                elif isinstance(assign.value.right, ast.Name) and isinstance(assign.value.left, ast.Name): # both sides are variables
                    var_left = assign.value.left
                    var_right = assign.value.right
                    if check_type(var_left, assign.targets[0]) and check_type(var_left, var_right): # all variables are the same
                        return check_type(var_right, aug_assign.value)
                    elif check_type(var_left, assign.targets[0]) and check_type(var_left, aug_assign.target): # left side is correct variable
                        return check_type(var_right, aug_assign.value)
                    elif check_type(var_right, assign.targets[0]) and check_type(var_right, aug_assign.target): # right side is correct variable
                        if isinstance(assign.value.op, ast.Add) or isinstance(assign.value.op, ast.Mult): # communtativity allowed
                            return check_type(var_left, aug_assign.value)
    return False

def check_bin_op(expected_tree, actual_tree):
    """
    Function determines whether two binop calls are equivalent
    Returns a boolean stating whether the two BinOps passed in are equivalent
    """
    if actual_tree.op == expected_tree.op: # check that the operation is the same
        if isinstance(actual_tree.op, ast.Sub) or isinstance(actual_tree.op, ast.Div): # not commutative
            return check_type(expected_tree.right, actual_tree.right) and check_type(expected_tree.left, actual_tree.left)
        else: # if add or mult
            same = check_type(expected_tree.right, actual_tree.right) and check_type(expected_tree.left, actual_tree.left)
            swapped = check_type(expected_tree.left, actual_tree.right) and check_type(expected_tree.right, actual_tree.left)
            return same or swapped

    return False
    
