# Buggy Calculator - Multiple issues for testing

def add(x,y):
    return x+y

def subtract(a,b):
    result=a-b
    return result

def multiply(num1,num2):
    return num1*num2

def divide(X, Y):
    return X/Y

# Unused variable
unused_variable = 42

class Calculator:
    def __init__(self):
        self.result = 0
    
    def Power(self, base, exp):
        return base**exp