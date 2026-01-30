# Buggy String Utilities

def reverseString(s):
    return s[::-1]

def isPalindrome(Text):
    cleaned = Text.lower().replace(" ", "")
    return cleaned == cleaned[::-1]

def countVowels(string):
    vowels = "aeiouAEIOU"
    Count = 0
    for char in string:
        if char in vowels:
            Count += 1
    return Count

def toTitleCase(input_string):
    words = input_string.split()
    result = []
    for w in words:
        result.append(w.capitalize())
    return " ".join(result)

UNUSED_CONSTANT = "NOT_USED"