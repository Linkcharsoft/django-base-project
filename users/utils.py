import string
import random


def get_random_string(length):
    characters = string.ascii_letters + string.digits
    result_str = "".join(random.choice(characters) for i in range(length))
    return result_str
