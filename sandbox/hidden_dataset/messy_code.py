variable_name = 10

def is_positive_and_less_than_hundred(input_value: int) -> bool:
    """
    Checks if the input value is positive and less than 100.

    Args:
        input_value (int): The value to be checked.

    Returns:
        bool: True if the input value is positive and less than 100, False otherwise.
    """
    if input_value > 0 and input_value < 100:
        return True
    return False