'''
Comparison of input param between derts at range=rng, summing derivatives from shorter + current range comps per pixel
Input is gradient g in dert[0] or angle a in dert[1], in ga_dert only, if fa: compute angle from dy, dx, in 2nd intra_comp
'''

import operator as op
import numpy as np
import numpy.ma as ma

# -----------------------------------------------------------------------------
# Constants

PI_TO_BYTE_SCALE = 162.33804195373324

# Declare comparison flags:
F_ANGLE = 0b01
F_DERIVE = 0b10

# Declare slicing for vectorized rng comparisons:
TRANSLATING_SLICES = {
    1:[
        (Ellipsis, slice(None, -2, None), slice(None, -2, None)),
        (Ellipsis, slice(None, -2, None), slice(1, -1, None)),
        (Ellipsis, slice(None, -2, None), slice(2, None, None)),
        (Ellipsis, slice(1, -1, None), slice(2, None, None)),
        (Ellipsis, slice(2, None, None), slice(2, None, None)),
        (Ellipsis, slice(2, None, None), slice(1, -1, None)),
        (Ellipsis, slice(2, None, None), slice(None, -2, None)),
        (Ellipsis, slice(1, -1, None), slice(None, -2, None)),
    ],
    2:[
        (Ellipsis, slice(None, -4, None), slice(None, -4, None)),
        (Ellipsis, slice(None, -4, None), slice(1, -3, None)),
        (Ellipsis, slice(None, -4, None), slice(2, -2, None)),
        (Ellipsis, slice(None, -4, None), slice(3, -1, None)),
        (Ellipsis, slice(None, -4, None), slice(4, None, None)),
        (Ellipsis, slice(1, -3, None), slice(4, None, None)),
        (Ellipsis, slice(2, -2, None), slice(4, None, None)),
        (Ellipsis, slice(3, -1, None), slice(4, None, None)),
        (Ellipsis, slice(4, None, None), slice(4, None, None)),
        (Ellipsis, slice(4, None, None), slice(3, -1, None)),
        (Ellipsis, slice(4, None, None), slice(2, -2, None)),
        (Ellipsis, slice(4, None, None), slice(1, -3, None)),
        (Ellipsis, slice(4, None, None), slice(None, -4, None)),
        (Ellipsis, slice(3, -1, None), slice(None, -4, None)),
        (Ellipsis, slice(2, -2, None), slice(None, -4, None)),
        (Ellipsis, slice(1, -3, None), slice(None, -4, None)),
    ],
    3:[
        (Ellipsis, slice(None, -6, None), slice(None, -6, None)),
        (Ellipsis, slice(None, -6, None), slice(1, -5, None)),
        (Ellipsis, slice(None, -6, None), slice(2, -4, None)),
        (Ellipsis, slice(None, -6, None), slice(3, -3, None)),
        (Ellipsis, slice(None, -6, None), slice(4, -2, None)),
        (Ellipsis, slice(None, -6, None), slice(5, -1, None)),
        (Ellipsis, slice(None, -6, None), slice(6, None, None)),
        (Ellipsis, slice(1, -5, None), slice(6, None, None)),
        (Ellipsis, slice(2, -4, None), slice(6, None, None)),
        (Ellipsis, slice(3, -3, None), slice(6, None, None)),
        (Ellipsis, slice(4, -2, None), slice(6, None, None)),
        (Ellipsis, slice(5, -1, None), slice(6, None, None)),
        (Ellipsis, slice(6, None, None), slice(6, None, None)),
        (Ellipsis, slice(6, None, None), slice(5, -1, None)),
        (Ellipsis, slice(6, None, None), slice(4, -2, None)),
        (Ellipsis, slice(6, None, None), slice(3, -3, None)),
        (Ellipsis, slice(6, None, None), slice(2, -4, None)),
        (Ellipsis, slice(6, None, None), slice(1, -5, None)),
        (Ellipsis, slice(6, None, None), slice(None, -6, None)),
        (Ellipsis, slice(5, -1, None), slice(None, -6, None)),
        (Ellipsis, slice(4, -2, None), slice(None, -6, None)),
        (Ellipsis, slice(3, -3, None), slice(None, -6, None)),
        (Ellipsis, slice(2, -4, None), slice(None, -6, None)),
        (Ellipsis, slice(1, -5, None), slice(None, -6, None)),
    ],
}

# Declare coefficients for decomposing d into dy and dx:
Y_COEFFS = {
    3:np.array([0.70710678, 0.83205029, 0.9486833 , 1.        , 0.9486833 ,
                0.83205029, 0.70710678, 0.5547002 , 0.31622777, 0.        ,
                0.31622777, 0.5547002 , 0.70710678, 0.83205029, 0.9486833 ,
                1.        , 0.9486833 , 0.83205029, 0.70710678, 0.5547002 ,
                0.31622777, 0.        , 0.31622777, 0.5547002 ]),
    2:np.array([0.70710678, 0.89442719, 1.        , 0.89442719, 0.70710678,
                0.4472136 , 0.        , 0.4472136 , 0.70710678, 0.89442719,
                1.        , 0.89442719, 0.70710678, 0.4472136 , 0.        ,
                0.4472136 ]),
    1:np.array([0.70710678, 1.        , 0.70710678, 0.        , 0.70710678,
                1.        , 0.70710678, 0.        ]),
}

X_COEFFS = {
    3:np.array([0.70710678, 0.5547002 , 0.31622777, 0.        , 0.31622777,
                0.5547002 , 0.70710678, 0.83205029, 0.9486833 , 1.        ,
                0.9486833 , 0.83205029, 0.70710678, 0.5547002 , 0.31622777,
                0.        , 0.31622777, 0.5547002 , 0.70710678, 0.83205029,
                0.9486833 , 1.        , 0.9486833 , 0.83205029]),
    2:np.array([0.70710678, 0.4472136 , 0.        , 0.4472136 , 0.70710678,
                0.89442719, 1.        , 0.89442719, 0.70710678, 0.4472136 ,
                0.        , 0.4472136 , 0.70710678, 0.89442719, 1.        ,
                0.89442719]),
    1:np.array([0.70710678, 0.        , 0.70710678, 1.        , 0.70710678,
                0.        , 0.70710678, 1.        ]),
}

# -----------------------------------------------------------------------------
# Functions

def comp_i(dert___, rng, flags): # Need to be coded from scratch
    """
    Determine which parameter from dert__ is the input,
    then compare the input over predetermined range
    Parameters
    ----------
    dert__ : MaskedArray
        Contains input array.
    rng : int
        Determine translation between comparands.
    flags : int
        Indicate which params in dert__ being used as input.
    Return
    ------
    i__ : MaskedArray
        Input array for summing in form_P_().
    new_dert__ : MaskedArray
        Array contain new parameters derived from the comparisons.
    """
    # Compare angle flow control:
    if flags & F_ANGLE:
        return comp_a(dert___, rng, new_mask)

    # Assign input array:
    if flags & F_DERIVE:
        i__ = dert___[-1][0] # Assign g__ of previous layer to i__
        shape = tuple(np.subtract(i__.shape, rng * 2))

        # Accumulate dx__, dy__ starting from 0:
        dy__ = ma.zeros(shape)
        dx__ = ma.zeros(shape)
    else:
        i__ = dert___[-2][0] # Assign one layer away g__ to i__
        # Accumulated dx__, dy__ of previous layer:
        dy__, dx__ = dert___[-1][-2:]

    # Compare inputs:
    d__ = translated_operation(i__, rng, op.sub)

    # Decompose and add to corresponding dy and dx:
    dy__ += (d__ * Y_COEFFS[rng]).sum(axis=-1)
    dx__ += (d__ * X_COEFFS[rng]).sum(axis=-1)

    # Compute gs:
    g__ = ma.hypot(dy__, dx__)

    return i__, ma.stack((g__, dy__, dx__), axis=0)


def comp_a(dert___, rng):
    """
    as comp_i, but comparands are 2D vectors vs. scalars, and difference is in angle
    """
    # Assign array of comparands:
    if rng > 1:
        a__ = dert___[-1][1:3]  # Assign a__ of previous layer
        # Accumulated dax__, day__ of previous layer:
        day__ = dert___[-1][-4:-2]
        dax__ = dert___[-1][-2:]
    else:
        # Compute angle from g__, dy__, dx__ of previous layer:
        g__ = dert___[-1][0]
        dy__, dx__ =  dert___[-1][-2:]
        a__ = np.stack((dy, dx), axis=0) / g__

        shape = tuple(np.subtract(dy__.shape, rng * 2))
        # Accumulate dax__, day__ starting from 0:
        day__ = ma.zeros((2,)+shape)
        dax__ = ma.zeros((2,)+shape)

    # Compute angle differences:
    da__ = translated_operation(a__, rng, angle_diff)

    # Decompose and add to corresponding day and dax:
    day__ += (da__ * Y_COEFFS[rng]).sum(axis=-1)
    dax__ += (da__ * X_COEFFS[rng]).sum(axis=-1)

    # Compute ga:
    ga__ = ma.arctan2(*ma.hypot(day__, dax__)) * PI_TO_BYTE_SCALE

    return a__, ma.stack((ga__, a__, day__, dax__), axis=0)

# -----------------------------------------------------------------------------
# Utility functions

def central_slice(i):
    """Return central slice objects (last 2 dimensions)."""
    if i < 1:
        return ..., slice(None), slice(None)
    return ..., slice(i, -i), slice(i, -i)

def translated_operation(a, rng, operator):
    """
    Return an array of corresponding results from operations between
    translated slices and central slice of an array.
    Parameters
    ----------
    a : ndarray
        Input array.
    rng : int
        Range of translations.
    operator : function
        Binary operator of which the result between central
        and translated slices are returned.
    Return
    ------
    out : ndarray
        Array of results where additional dimension correspondent
        to each translated slice.
    """
    out = ma.masked_array([*map(lambda slices:
                                    operator(a[slices],
                                             a[central_slice(rng)]),
                                TRANSLATING_SLICES[rng])])

    # Rearrange axes:
    for dim in range(out.ndim - 1):
        out = out.swapaxes(dim, dim+1)

    return out
# ----------------------------------------------------------------------
def angle_diff(a2, a1):
    """
    Return the vector, of which angle is the angle between a2 and a1.
    Can be applied to arrays.
    Note: This only works for 2D vectors.
    """
    # Extend a1 vector(s) into basis/bases:
    y, x = a1
    bases = [(x, -y), (y, x)]
    transform_mat = ma.array(bases)

    # Apply transformation:
    da = (transform_mat * a2).sum(axis=1)

    return da