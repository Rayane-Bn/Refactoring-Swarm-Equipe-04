# Buggy Data Processor

def filterPositive(numbers):
    result = []
    for n in numbers:
        if n > 0:
            result.append(n)
    return result

def calculateAverage(Numbers):
    if len(Numbers) == 0:
        return 0
    Total = sum(Numbers)
    return Total / len(Numbers)

def removeDuplicates(lst):
    seen = []
    for item in lst:
        if item not in seen:
            seen.append(item)
    return seen

def FindMax(data_list):
    if not data_list:
        return None
    Maximum = data_list[0]
    for num in data_list:
        if num > Maximum:
            Maximum = num
    return Maximum

temp_var = "temporary"