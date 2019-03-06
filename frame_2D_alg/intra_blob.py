from time import time
import numpy as np
import numpy.ma as ma
import generic_functions
from angle_blobs import blob_to_ablobs
# from comp_inc_deriv import inc_deriv
# from comp_inc_range import inc_range
# from comp_P_ import comp_P_
'''
    - intra_blob() evaluates for recursive frame_blobs() and comp_P() within each blob
      combined with frame_blobs(), it forms a 2D version of first-level algorithm
      
    - inter_subb() will compare sub_blobs of same range and derivation within higher-level blob, bottom-up ) top-down:
    - inter_level() will compare between blob levels, where lower composition level is integrated by inter_subb
      match between levels'edges may form composite blob, axis comp if sub_blobs within blob margin?
    - inter_blob() comparison will be second-level 2D algorithm, and a prototype for recursive meta-level algorithm
'''

def eval_blob(blob):  # evaluate blob for comp_angle, comp_inc_range, comp_inc_deriv, comp_P_

    global rdn  # redundant representation counter, or branch-specific cost ratio?
    Ly, L, Y, X, I, Dy, Dx, G = blob.params
    Ave = ave * L  # whole-blob reprocessing filter
    val_deriv, val_range = 0, 0

    if blob.sign:  # positive gblob: area of noisy or directional (edge) gradient
        if G > ave_blob:  # ave, ave_blob: variable, fixed cost of hypot_g() per blob
            rdn += 1
            hypot_gradient(blob)  # max g is more precisely estimated as hypot(dx, dy), replaces dert_ with sub_blob_:
            # sub_blobs are defined by reduced g and increased ave, ave_blob: var, fixed costs of angle_blobs() and eval:
            blob_to_ablobs(blob)
            if blob.Ga > Ave:
                blob = intra_blob(blob)  # eval for angle comp recursion within ablobs: additional ref arg in intra_blob?

            val_deriv = ((G + Ave) / Ave) * -blob.Ga  # relative G * -Ga: angle match, likely edge
            val_range = G - val_deriv  # non-directional G: likely d reversal, distant-pixels match

    # val_PP_ = (L + I + G) * (L / Ly / Ly) * (Dy / Dx)
    # 1st term: proj P match Pm; Dx, Dy, abs_Dx, abs_Dy for scan-invariant hyp_g_P calc, comp, no indiv comp: rdn
    # 2nd term: elongation: >ave Pm? ~ box elong: (x_max - x_min) / (y_max - y_min)?
    # 3rd term: dimensional variation bias

    return [(val_deriv, 0, blob), (val_range, 1, blob)]  # + (val_PP_, 2, blob), estimated values per branch
    # ---------- eval_blob() end ----------------------------------------------------------------------------------------

def hypot_gradient(blob):  # compute and compare angle, define ablobs, accumulate a, da, sda in all reps within gblob
    ''' same functionality as image_to_blobs() in frame_blobs.py'''

    height, width = blob.map.shape

    for i in range(4):
        blob.params.append(0)

    seg_ = deque()

    recalc_g(blob)

    for y in range(1, height - 1):
        P_ = generic_functions.form_P_(y, blob)  # horizontal clustering
        P_ = generic_functions.scan_P_(P_, seg_, blob)
        seg_ = generic_functions.form_seg_(P_, blob)

    while seg_: generic_functions.form_blob(seg_.popleft(), blob)
    # ---------- hypot_gradient() end -----------------------------------------------------------------------------------

def recalc_g(blob):

    blob.new_dert__ = ma.array(blob.dert__, mask=~blob.map)
    blob.new_dert__[:, :, 3] = np.hypot(blob.new_dert__[:, :, 1], blob.new_dert__[:, :, 2]) - ave
    # ---------- recalc_g() end -----------------------------------------------------------------------------------------

def eval_layer(val_):  # val_: estimated values of active branches in current layer across recursion tree per blob

    global rdn
    val_ = sorted(val_, key=lambda val: val[0])
    sub_val_ = []  # estimated branch values of deeper layer of recursion tree per blob
    map_ = []  # blob maps of stronger branches in val_, appended for next val evaluation

    while val_:
        val, typ, blob = val_.pop()
        for map in map_:
            olp = olp(blob, map)  # if box overlap?
            rdn += 1 * (olp / blob.L())   # redundancy to previously formed representations

        if val > ave * blob.params(1) * rdn:
            if typ==0: blob = inc_range(blob)  # recursive comp over p_ of incremental distance
            else:      blob = inc_deriv(blob)  # recursive comp over g_ of incremental derivation
                       # dderived, blob selected for min_g
            # else: blob_sub_blobs = comp_P_(val, 0, blob, rdn)  # -> comp_P
            # val-= sub_blob and branch switch cost: added map?  only after g,a calc: no rough g comp?

            map_.append(blob.box, blob.map)
            for sub_blob in blob.sub_blob_:
                sub_val_ += eval_blob(sub_blob)  # returns estimated recursion values of the next layer:
                # [(val_deriv, 0, blob), (val_range, 1, blob), (val_PP_, 2, blob)] per sub_blob, may include deep angle_blobs
        else:
            break

    if sub_val_:
        rdn += 1
        eval_layer(sub_val_)  # evaluation of sub_val_ for recursion
    # ---------- eval_layer() end ---------------------------------------------------------------------------------------

def intra_blob(frame, redundancy=0.0):  # evaluate blobs for comp_angle, inc_range comp, inc_deriv comp, comp_P_

    global rdn
    for blob in frame.blob_:
        rdn = redundancy
        # eval_layer(eval_blob(blob))  # eval_blob returns val_

        # for debugging:
        if blob.sign:
            blob_to_ablobs(blob)
        #     inc_range(blob)
        #     inc_deriv(blob)
    return frame  # frame of 2D patterns, to be outputted to level 2
    # ---------- intra_blob() end ---------------------------------------------------------------------------------------

# ************ PROGRAM BODY *********************************************************************************************

from frame_2D_alg.misc import get_filters
get_filters(globals())  # imports all filters at once

# Main ---------------------------------------------------------------------------
import frame_blobs

start_time = time()
frame = intra_blob(frame_blobs.frame_of_blobs)
end_time = time() - start_time
print(end_time)

# Rebuild blob -------------------------------------------------------------------
# from DEBUG import draw_blob