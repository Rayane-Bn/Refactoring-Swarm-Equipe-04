from data_processor import filterPositive, calculateAverage, removeDuplicates, FindMax

def test_filter_positive():
    assert filterPositive([1, -2, 3, -4, 5]) == [1, 3, 5]
    assert filterPositive([-1, -2, -3]) == []
    assert filterPositive([1, 2, 3]) == [1, 2, 3]

def test_calculate_average():
    assert calculateAverage([1, 2, 3, 4, 5]) == 3.0
    assert calculateAverage([10, 20]) == 15.0
    assert calculateAverage([]) == 0

def test_remove_duplicates():
    assert removeDuplicates([1, 2, 2, 3, 3, 3]) == [1, 2, 3]
    assert removeDuplicates([1, 1, 1]) == [1]
    assert removeDuplicates([]) == []

def test_find_max():
    assert FindMax([1, 5, 3, 9, 2]) == 9
    assert FindMax([10]) == 10
    assert FindMax([]) == None