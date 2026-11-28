
def calculate_total(prices):

    # BUG: Only returns the first product price
    if not prices:
        return 0

    return sum(prices)


if __name__ == "__main__":

    products = [100, 100]

    total = calculate_total(products)

    print("Product prices:", products)
    print("Cart total:", total)
