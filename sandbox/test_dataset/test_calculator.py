from calculator import add, subtract, multiply, divide, Calculator

def test_add():
    assert add(2, 3) == 5
    assert add(0, 0) == 0
    assert add(-1, 1) == 0

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(10, 5) == 5

def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(0, 5) == 0

def test_divide():
    assert divide(10, 2) == 5
    assert divide(9, 3) == 3

def test_calculator_power():
    calc = Calculator()
    assert calc.Power(2, 3) == 8
    assert calc.Power(5, 2) == 25