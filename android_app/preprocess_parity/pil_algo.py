"""Reimplementation of Pillow's ImagingResample for 8-bit RGB, BILINEAR.

Mirrors Pillow's resample.c exactly, including its fixed-point integer
arithmetic, so that a JVM port can be checked against it rather than against
a floating-point approximation that was never what Pillow actually computed.

  PRECISION_BITS = 32 - 8 - 2 = 22
  coefficients are rounded to int32 at that scale
  accumulation starts at 1 << (PRECISION_BITS - 1)  (round-to-nearest)
  output is (acc >> PRECISION_BITS) clamped to 0..255
  horizontal pass runs first, producing an 8-bit intermediate, then vertical
"""
import numpy as np

PRECISION_BITS = 32 - 8 - 2          # 22
SUPPORT = 1.0                        # bilinear filter support


def bilinear_filter(x: float) -> float:
    x = abs(x)
    return 1.0 - x if x < 1.0 else 0.0


def precompute_coeffs(in_size, in0, in1, out_size):
    """Pillow ImagingPrecomputeCoeffs."""
    scale = (in1 - in0) / out_size
    filterscale = scale if scale >= 1.0 else 1.0
    support = SUPPORT * filterscale
    ksize = int(np.ceil(support)) * 2 + 1

    bounds = np.zeros((out_size, 2), dtype=np.int64)
    kk = np.zeros(out_size * ksize, dtype=np.float64)

    for xx in range(out_size):
        center = in0 + (xx + 0.5) * scale
        ww = 0.0
        ss = 1.0 / filterscale
        xmin = int(center - support + 0.5)
        if xmin < 0:
            xmin = 0
        xmax = int(center + support + 0.5)
        if xmax > in_size:
            xmax = in_size
        xmax -= xmin
        k = kk[xx * ksize: xx * ksize + ksize]
        for x in range(xmax):
            w = bilinear_filter((x + xmin - center + 0.5) * ss)
            k[x] = w
            ww += w
        if ww != 0.0:
            k[:xmax] /= ww
        k[xmax:] = 0.0
        bounds[xx] = (xmin, xmax)
    return bounds, kk, ksize


def normalize_coeffs_8bpc(prekk):
    """Pillow normalize_coeffs_8bpc: round to int32 at PRECISION_BITS."""
    out = np.empty(prekk.shape, dtype=np.int64)
    scale = 1 << PRECISION_BITS
    for i, v in enumerate(prekk):
        out[i] = int(v * scale - 0.5) if v < 0 else int(v * scale + 0.5)
    return out


def clip8(v):
    v = v >> PRECISION_BITS
    return 0 if v < 0 else (255 if v > 255 else v)


def resample_horizontal(src, out_w):
    h, w, c = src.shape
    bounds, prekk, ksize = precompute_coeffs(w, 0.0, float(w), out_w)
    kk = normalize_coeffs_8bpc(prekk)
    dst = np.empty((h, out_w, c), dtype=np.uint8)
    init = 1 << (PRECISION_BITS - 1)
    for yy in range(h):
        row = src[yy].astype(np.int64)
        for xx in range(out_w):
            xmin, xmax = bounds[xx]
            k = kk[xx * ksize: xx * ksize + xmax]
            acc = init + (row[xmin:xmin + xmax] * k[:, None]).sum(axis=0)
            dst[yy, xx] = [clip8(int(a)) for a in acc]
    return dst


def resample_vertical(src, out_h):
    h, w, c = src.shape
    bounds, prekk, ksize = precompute_coeffs(h, 0.0, float(h), out_h)
    kk = normalize_coeffs_8bpc(prekk)
    dst = np.empty((out_h, w, c), dtype=np.uint8)
    init = 1 << (PRECISION_BITS - 1)
    for yy in range(out_h):
        ymin, ymax = bounds[yy]
        k = kk[yy * ksize: yy * ksize + ymax]
        block = src[ymin:ymin + ymax].astype(np.int64)
        acc = init + (block * k[:, None, None]).sum(axis=0)
        dst[yy] = np.vectorize(clip8)(acc).astype(np.uint8)
    return dst


def pil_equivalent_resize(src, out_w, out_h):
    """Full Pillow resize: horizontal pass, then vertical, 8-bit intermediate."""
    cur = src
    if out_w != src.shape[1]:
        cur = resample_horizontal(cur, out_w)
    if out_h != cur.shape[0]:
        cur = resample_vertical(cur, out_h)
    return cur
