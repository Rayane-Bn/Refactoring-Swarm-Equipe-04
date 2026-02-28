import pytest
from buggy_code import calculate_average, find_max, reverse_string, is_palindrome, bank_account

def test_calculate_average_normal_case():
    assert calculate_average([1, 2, 3, 4, 5]) == 3.0

def test_calculate_average_edge_case_empty_list():
    with pytest.raises(ValueError):
        calculate_average([])

def test_calculate_average_edge_case_single_element_list():
    assert calculate_average([5]) == 5.0

def test_calculate_average_edge_case_negative_numbers():
    assert calculate_average([-1, -2, -3, -4, -5]) == -3.0

def test_find_max_normal_case():
    assert find_max([1, 2, 3, 4, 5]) == 5

def test_find_max_edge_case_empty_list():
    with pytest.raises(ValueError):
        find_max([])

def test_find_max_edge_case_single_element_list():
    assert find_max([5]) == 5

def test_find_max_edge_case_negative_numbers():
    assert find_max([-1, -2, -3, -4, -5]) == -1

def test_reverse_string_normal_case():
    assert reverse_string("hello") == "olleh"

def test_reverse_string_edge_case_empty_string():
    assert reverse_string("") == ""

def test_reverse_string_edge_case_single_character():
    assert reverse_string("a") == "a"

def test_is_palindrome_normal_case_palindrome():
    assert is_palindrome("madam") == True

def test_is_palindrome_normal_case_not_palindrome():
    assert is_palindrome("hello") == False

def test_is_palindrome_edge_case_empty_string():
    assert is_palindrome("") == True

def test_is_palindrome_edge_case_single_character():
    assert is_palindrome("a") == True

def test_bank_account_init_normal_case():
    account = bank_account(100.0)
    assert account.balance == 100.0

def test_bank_account_init_edge_case_negative_balance():
    with pytest.raises(ValueError):
        bank_account(-100.0)

def test_bank_account_deposit_normal_case():
    account = bank_account(100.0)
    account.deposit(50.0)
    assert account.balance == 150.0

def test_bank_account_deposit_edge_case_negative_amount():
    account = bank_account(100.0)
    with pytest.raises(ValueError):
        account.deposit(-50.0)

def test_bank_account_withdraw_normal_case():
    account = bank_account(100.0)
    account.withdraw(50.0)
    assert account.balance == 50.0

def test_bank_account_withdraw_edge_case_negative_amount():
    account = bank_account(100.0)
    with pytest.raises(ValueError):
        account.withdraw(-50.0)

def test_bank_account_withdraw_edge_case_insufficient_funds():
    account = bank_account(100.0)
    with pytest.raises(ValueError):
        account.withdraw(150.0)