def calculate_average(numbers):
    """
    Calculate the average of a list of numbers.

    Args:
        numbers (list): A list of numbers.

    Returns:
        float: The average of the numbers.

    Raises:
        ValueError: If the list is empty.
    """
    if not numbers:
        raise ValueError("Cannot calculate average of an empty list")
    total = 0
    for num in numbers:
        total += num
    average = total / len(numbers)
    return average

def find_max(lst):
    """
    Find the maximum value in a list.

    Args:
        lst (list): A list of numbers.

    Returns:
        The maximum value in the list.

    Raises:
        ValueError: If the list is empty.
    """
    if not lst:
        raise ValueError("Cannot find max of an empty list")
    max_val = lst[0]
    for i in range(1, len(lst)):
        if lst[i] > max_val:
            max_val = lst[i]
    return max_val

def reverse_string(s):
    """
    Reverse a string.

    Args:
        s (str): The string to reverse.

    Returns:
        str: The reversed string.
    """
    result = ""
    for i in range(len(s) - 1, -1, -1):
        result += s[i]
    return result

def is_palindrome(word):
    """
    Check if a word is a palindrome.

    Args:
        word (str): The word to check.

    Returns:
        bool: True if the word is a palindrome, False otherwise.
    """
    return word == word[::-1]

class bank_account:
    """
    A class representing a bank account.

    Attributes:
        balance (float): The current balance of the account.
    """

    def __init__(self, balance):
        """
        Initialize a bank account with a given balance.

        Args:
            balance (float): The initial balance of the account.

        Raises:
            ValueError: If the balance is negative.
        """
        if balance < 0:
            raise ValueError("Initial balance cannot be negative")
        self.balance = balance

    def deposit(self, amount):
        """
        Deposit a given amount into the account.

        Args:
            amount (float): The amount to deposit.

        Raises:
            ValueError: If the deposit amount is negative.
        """
        if amount < 0:
            raise ValueError("Deposit amount cannot be negative")
        self.balance += amount

    def withdraw(self, amount):
        """
        Withdraw a given amount from the account.

        Args:
            amount (float): The amount to withdraw.

        Raises:
            ValueError: If the withdrawal amount is negative or exceeds the balance.
        """
        if amount < 0:
            raise ValueError("Withdrawal amount cannot be negative")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount