from string_utils import reverseString, isPalindrome, countVowels, toTitleCase

def test_reverse_string():
    assert reverseString("hello") == "olleh"
    assert reverseString("Python") == "nohtyP"
    assert reverseString("") == ""

def test_is_palindrome():
    assert isPalindrome("racecar") == True
    assert isPalindrome("A man a plan a canal Panama") == True
    assert isPalindrome("hello") == False

def test_count_vowels():
    assert countVowels("hello") == 2
    assert countVowels("AEIOU") == 5
    assert countVowels("xyz") == 0

def test_to_title_case():
    assert toTitleCase("hello world") == "Hello World"
    assert toTitleCase("python programming") == "Python Programming"