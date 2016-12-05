# def expand_3D(v):
#     b = v &                0x00000000003FFFFF   # b = ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- --54 3210 fedc ba98 7654 3210
#     b = (b ^ (b <<  32)) & 0x003F00000000FFFF   # b = ---- ---- --54 3210 ---- ---- ---- ---- ---- ---- ---- ---- fedc ba98 7654 3210
#     b = (b ^ (b <<  16)) & 0x003F0000FF0000FF   # b = ---- ---- --54 3210 ---- ---- ---- ---- fedc ba98 ---- ---- ---- ---- 7654 3210
#     b = (b ^ (b <<  8))  & 0x300F00F00F00F00F   # b = --54 ---- ---- 3210 ---- ---- fedc ---- ---- ba98 ---- ---- 7654 ---- ---- 3210
#     b = (b ^ (b <<  4))  & 0x30c30c30c30c30c3   # b = --54 ---- 32-- --10 ---- fe-- --dc ---- ba-- --98 ---- 76-- --54 ---- 32-- --10
#     b = (b ^ (b <<  2))  & 0x1249249249249249   # b = 5--4 --3- -2-- 1--0 --f- -e-- d--c --b- -a-- 9--8 --7- -6-- 5--4 --3- -2-- 1--0
#     return b
#
# def encode_morton_3D(x, y, z):
#     return expand_3D(x) + (expand_3D(y) << 1) + (expand_3D(z) << 2)


def Expand3D(x):
    """
    Encodes the 93 bit morton code for a 31 bit number in the 3D space using
    a divide and conquer approach for separating the bits.

    Args:
        x (int): the requested 3D dimension

    Returns:
        int: 93 bit morton code in 3D

    Raises:
        Exception: ERROR: Morton code is valid only for positive numbers

    """

    if x < 0:
        raise Exception(
            """ERROR: Morton code is valid only for positive numbers""")
    x &= 0x7fffffffL
    x = (x ^ x << 32) & 0x7fff00000000ffffL
    x = (x ^ x << 16) & 0x7f0000ff0000ff0000ffL
    x = (x ^ x << 8) & 0x700f00f00f00f00f00f00fL
    x = (x ^ x << 4) & 0x430c30c30c30c30c30c30c3L
    x = (x ^ x << 2) & 0x49249249249249249249249L
    return x


def EncodeMorton3D(x, y, z):
    """
    Calculates the 3D morton code from the x, y, z dimensions

    Args:
        x (int): the x dimension of 31 bits
        y (int): the y dimension of 31 bits
        z (int): the z dimension of 31 bits

    Returns:
        int: 93 bit morton code in 3D
    """
    return Expand3D(x) + (Expand3D(y) << 1) + (Expand3D(z) << 2)
