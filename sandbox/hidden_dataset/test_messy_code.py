import pytest
from messy_code import is_positive_and_less_than_hundred

def test_is_positive_and_less_than_hundred_normal_case():
    assert is_positive_and_less_than_hundred(50) == True

def test_is_positive_and_less_than_hundred_zero():
    assert is_positive_and_less_than_hundred(0) == False

def test_is_positive_and_less_than_hundred_negative():
    assert is_positive_and_less_than_hundred(-10) == False

def test_is_positive_and_less_than_hundred_hundred():
    assert is_positive_and_less_than_hundred(100) == False

def test_is_positive_and_less_than_hundred_large_number():
    assert is_positive_and_less_than_hundred(1000) == False

def test_is_positive_and_less_than_hundred_positive_boundary():
    assert is_positive_and_less_than_hundred(1) == True

def test_is_positive_and_less_than_hundred_negative_boundary():
    assert is_positive_and_less_than_hundred(-1) == False

def test_is_positive_and_less_than_hundred_input_type():
    with pytest.raises(TypeError):
        is_positive_and_less_than_hundred("10")

def test_is_positive_and_less_than_hundred_input_none():
    with pytest.raises(TypeError):
        is_positive_and_less_than_hundred(None)