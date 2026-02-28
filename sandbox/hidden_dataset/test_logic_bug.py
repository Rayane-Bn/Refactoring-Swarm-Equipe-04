import pytest
from logic_bug import count_down
import io
import sys

def test_count_down_normal_case(capsys):
    count_down(5)
    captured = capsys.readouterr()
    assert captured.out == "5\n4\n3\n2\n1\n"

def test_count_down_edge_case_zero(capsys):
    count_down(0)
    captured = capsys.readouterr()
    assert captured.out == ""

def test_count_down_edge_case_negative(capsys):
    count_down(-5)
    captured = capsys.readouterr()
    assert captured.out == ""

def test_count_down_edge_case_one(capsys):
    count_down(1)
    captured = capsys.readouterr()
    assert captured.out == "1\n"

def test_count_down_large_input(capsys):
    count_down(10)
    captured = capsys.readouterr()
    assert captured.out == "10\n9\n8\n7\n6\n5\n4\n3\n2\n1\n"