
from cart import calculate_total


def test_multiple_products():

    prices = [100, 100]

    assert calculate_total(prices) == 200


def test_empty_cart():

    prices = []

    assert calculate_total(prices) == 0


def test_single_product():

    prices = [150]

    assert calculate_total(prices) == 150
