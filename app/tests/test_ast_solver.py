
import unittest
from app.ast_solver import same_ast_tree
from sqlalchemy_utils import ScalarListType #need this to make the FITB question answers field a list.


class TestASTSolver(unittest.TestCase):
    def test_basics(self):
        self.assertEqual(True, same_ast_tree("7", "7"))
        self.assertEqual(False, same_ast_tree("8", "7"))

    def test_basic_assignments(self):
        self.assertEqual(True, same_ast_tree("x=7", "x=7"))
        self.assertEqual(False, same_ast_tree("x=8", "x=7"))
        self.assertEqual(False, same_ast_tree("7=x", "x=7"))
        self.assertEqual(True, same_ast_tree("x=y=7", "x=y=7"))
        self.assertEqual(False, same_ast_tree("x=y=7", "x=z=7"))

    def test_expressions(self):
        self.assertEqual(False, same_ast_tree("1+2", "1-2"))
        self.assertEqual(True, same_ast_tree("1-2", "1-2"))
        self.assertEqual(True, same_ast_tree("1+2", "1+2"))
        self.assertEqual(False, same_ast_tree("2+1+", "1+2"))
        self.assertEqual(True, same_ast_tree("2+1", "1+2"))
        

    def test_assignments_with_calculations(self):
        self.assertEqual(True, same_ast_tree("x=7+1", "x=7+1"))
        self.assertEqual(True, same_ast_tree("x=7+1", "x=1+7"))
        self.assertEqual(False, same_ast_tree("x=7+y", "x=7-y")) # different operation
        self.assertEqual(False,same_ast_tree("y=7-y", "x=7-y")) # different var_name on left side
        self.assertEqual(False, same_ast_tree("x=7-y", "y=7-x")) # swapping both variables
        self.assertEqual(False, same_ast_tree("x=7-y", "x=7-z")) # different var_name on right side
        self.assertEqual(False, same_ast_tree("x=7-y", "x=y-7")) # non commutable operation
        self.assertEqual(True, same_ast_tree("x-=2", "x-=2"))
        self.assertEqual(True, same_ast_tree("x-=2", "x=x-2")) # aug assign = assign
        self.assertEqual(True, same_ast_tree("x-=y", "x=x-y"))
        self.assertEqual(True, same_ast_tree("x-=x", "x=x-x"))
        self.assertEqual(False, same_ast_tree("x-=x", "x=y-x"))
        self.assertEqual(False, same_ast_tree("x=7+bar(7)", "x=7+foo(7)"))

    def test_functions(self):
        self.assertEqual(True, same_ast_tree("print(\"hello\")", "print(\"hello\")"))
        self.assertEqual(False, same_ast_tree("print(\"hi\")", "print(\"hello\")"))
        self.assertEqual(True, same_ast_tree("print(4+5)", "print(5+4)"))
        self.assertEqual(True, same_ast_tree("print(4+5, 4)", "print(5+4, 4)"))
        self.assertEqual(False, same_ast_tree("foo(4,5)", "foo(5,4)"))
        self.assertEqual(False, same_ast_tree("foo(4,bar(6))", "foo(5,bar(6))"))
        self.assertEqual(True, same_ast_tree("foo(5,bar(6))", "foo(5,bar(6))"))
        self.assertEqual(False, same_ast_tree("foo([1,2],1)", "foo(1,[1])"))
        self.assertEqual(True, same_ast_tree("x.insert(3,4)", "x.insert(3,4)"))

    def test_complex_expressions(self):
        self.assertEqual(True, same_ast_tree("1 + (4+5)", " (4+5) +1"))
        self.assertEqual(True, same_ast_tree("1 + (4*5)", " (4*5) +1"))
        self.assertEqual(True, same_ast_tree("1 + (4-5)", " (4-5) +1"))

    def test_lists(self):
        self.assertEqual(True, same_ast_tree("x=[]", "x=[]"))
        self.assertEqual(False, same_ast_tree("y=[]", "x=[]")) # assigned to different variables
        self.assertEqual(False, same_ast_tree("x=[]", "x=[1,2]")) # different lengths
        self.assertEqual(False, same_ast_tree("x=[1,2]", "x=[2,1]"))
        self.assertEqual(True, same_ast_tree("x=[1,2]", "x=[1,2]"))
        self.assertEqual(False, same_ast_tree("x=[1,foo(5)]", "x=[2,foo(5)]"))
        self.assertEqual(True, same_ast_tree("x=[2,foo(5)]", "x=[2,foo(5)]"))
        self.assertEqual(True, same_ast_tree("x=[2,1+1]", "x=[2,1+1]")) 
        self.assertEqual(False, same_ast_tree("x=[2,2]", "x=[2,1+1]"))
        self.assertEqual(True, same_ast_tree("foo([1,2],1)", "foo([1,2],1)"))
        self.assertEqual(True, same_ast_tree("x[1:2]", "x[1:2]"))
        self.assertEqual(True, same_ast_tree("x[1:2:3]", "x[1:2:3]"))
        self.assertEqual(False, same_ast_tree("x[1:3]", "x[1:2]"))
        self.assertEqual(False, same_ast_tree("x.append(2)", "x.append(1)"))
        self.assertEqual(True, same_ast_tree("x[1] = 2", "x[1] =2"))
        self.assertEqual(False, same_ast_tree("x[1] = 2", "x[1] =1"))
        self.assertEqual(False, same_ast_tree("x[2] = 2", "x[1] =2"))
        self.assertEqual(True, same_ast_tree("print(['apples', 'oranges','pineapple'])", "print(['apples', 'oranges','pineapple'])"))
        self.assertEqual(True, same_ast_tree("x= ['apples', 2,foo(5),-9]", "x= ['apples', 2,foo(5),-9]"))
        self.assertEqual(True, same_ast_tree("myList.extend([4, 5, 6])", "myList.extend([4, 5, 6])"))
    
    def test_tuples(self):
        self.assertEqual(True, same_ast_tree("x=()", "x=()"))
        self.assertEqual(False, same_ast_tree("y=()", "x=()")) # assigned to different variables
        self.assertEqual(False, same_ast_tree("x=()", "x=(1,2)")) # different lengths
        self.assertEqual(False, same_ast_tree("x=(1,2)", "x=(2,1)"))
        self.assertEqual(True, same_ast_tree("x=(1,2)", "x=(1,2)"))
        self.assertEqual(True, same_ast_tree("foo((1,2),1)", "foo((1,2),1)"))
        self.assertEqual(True, same_ast_tree("x,y=1,2", "x,y=1,2"))
        self.assertEqual(False, same_ast_tree("x,y=1,2", "x,y=1,2,3"))
        self.assertEqual(False, same_ast_tree("x,z=1,2", "x,y=1,2"))
        self.assertEqual(False, same_ast_tree("x,y=1,2", "x,y=1,3"))
    
    def test_unary_op(self):
        self.assertEqual(True, same_ast_tree("-1", "-1"))
        self.assertEqual(False, same_ast_tree("-1", "-2"))
        self.assertEqual(True, same_ast_tree("-2+1", "-2+1"))
        self.assertEqual(True, same_ast_tree("-2+1", "1+(-2)"))
        self.assertEqual(False, same_ast_tree("-2+1", "1-2")) 

    def test_dicts(self): 
        self.assertEqual(True, same_ast_tree("x={}", "x={}"))
        self.assertEqual(True, same_ast_tree("{}", "{}"))
        self.assertEqual(False, same_ast_tree("x={}", "x={'a':2}"))
        self.assertEqual(True, same_ast_tree("x={'a':2}", "x={'a':2}"))
        self.assertEqual(True, same_ast_tree("x={'a':1, 'b':2}", "x={'b':2, 'a':1}"))
        self.assertEqual(False, same_ast_tree("x={'a':1, 'c':2}", "x={'a':1,'b':2}")) 
        self.assertEqual(False, same_ast_tree("x={'a':1, 'b':2}", "x={'a':1,'b':3}")) 
        self.assertEqual(True, same_ast_tree("x={2:1, 'b':2}", "x={2:1,'b':2}")) 
        # add differing types


    def test_return(self):
        self.assertEqual(True, same_ast_tree("return 1", "return 1"))
        self.assertEqual(False, same_ast_tree("return 1", "return 2"))
        self.assertEqual(True, same_ast_tree("return x,y", "return x,y"))
        self.assertEqual(False, same_ast_tree("return x,y", "return x,z"))
    
    def test_del(self):
        self.assertEqual(True, same_ast_tree("del x", "del x"))
        self.assertEqual(False, same_ast_tree("del x", "del y"))
        self.assertEqual(True, same_ast_tree("del x,y", "del x,y"))
        self.assertEqual(False, same_ast_tree("del x,y", "del x,z"))

    def test_compare(self):
        self.assertEqual(True, same_ast_tree("x<y", "x<y"))
        self.assertEqual(False, same_ast_tree("x>y", "y>x"))
        self.assertEqual(True, same_ast_tree("x>y", "y<x"))
        self.assertEqual(False, same_ast_tree("x>y", "x<=y"))
        self.assertEqual(False, same_ast_tree("x<y", "x<y<z"))

    def test_if(self):
        self.assertEqual(True, same_ast_tree("if true:\n\tpass", "if true:\n\tpass"))
        self.assertEqual(True, same_ast_tree("if x in alist:\n\tpass", "if x in alist:\n\tpass"))
        self.assertEqual(False, same_ast_tree("if x in alist:\n\tpass", "if y in alist:\n\tpass"))
        self.assertEqual(True, same_ast_tree("if x> y:\n\tpass", "if x>y:\n\tpass")) 
    
    def test_for(self):
        self.assertEqual(True, same_ast_tree("for i in range(10):\n\tpass", " for i in  range(10):\n\tpass"))
        self.assertEqual(True, same_ast_tree("for i in fruits:\n\tpass", " for i in  fruits:\n\tpass"))
        self.assertEqual(True, same_ast_tree("for i in [1,2,3,4,5]:\n\tpass", " for i in  [1,2,3,4,5]:\n\tpass"))
        self.assertEqual(False, same_ast_tree("for i in [1,2,3,4,5]:\n\tpass", " for i in  [1,2,3,4,10]:\n\tpass"))
        self.assertEqual(False, same_ast_tree("for i in range(11):\n\tpass", " for i in  range(10):\n\tpass"))
        self.assertEqual(False, same_ast_tree("for x in range(10):\n\tpass", " for i in  range(10):\n\tpass"))
        self.assertEqual(True, same_ast_tree("for i in fruits.keys():\n\tpass", " for i in  fruits.keys():\n\tpass"))
        self.assertEqual(True, same_ast_tree("for k,v in fruits.values():\n\tpass", " for k,v in  fruits.values():\n\tpass"))
        self.assertEqual(False, same_ast_tree("for k,x in fruits.values():\n\tpass", " for k,v in  fruits.values():\n\tpass"))
        self.assertEqual(True, same_ast_tree("for _ in range(10):\n\tpass", " for _ in  range(10):\n\tpass"))

    def test_while(self):
        self.assertEqual(True, same_ast_tree("while true:\n\tpass", " while true:\n\tpass"))
        self.assertEqual(True, same_ast_tree("while x>y:\n\tpass", " while x >y:\n\tpass"))
        self.assertEqual(False, same_ast_tree("while not apples:\n\tpass", " while apples:\n\tpass"))
        self.assertEqual(False, same_ast_tree("while apples and oranges:\n\tpass", " while apples or oranges:\n\tpass"))
        self.assertEqual(True, same_ast_tree("while apples and oranges:\n\tpass", " while apples and oranges:\n\tpass"))
    
    def test_and_or(self):
        self.assertEqual(True, same_ast_tree("apples and oranges", " oranges and apples"))
        self.assertEqual(False, same_ast_tree("apples and oranges", " oranges or apples"))

    def test_super_complex(self):
        pass