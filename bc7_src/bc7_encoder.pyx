import numpy as np
cimport numpy as cnp
from libc.stdint cimport uint8_t, uint32_t
from libc.stdlib cimport malloc, free
from libc.string cimport memcpy

cdef extern from "bc7enc.h":
    ctypedef struct bc7enc_compress_block_params:
        uint32_t m_max_partitions_mode[8]
        uint32_t m_weights[4]
        bint m_uber_level
        bint m_refinement_passes
        bint m_mode4_rotation_mask
        bint m_mode4_index_mask
        uint32_t m_max_partitions
        bint m_try_least_squares
        bint m_mode17_partition_estimation_filterbank
        bint m_uber1_mask
        bint m_perceptual

    void bc7enc_compress_block_init()
    void bc7enc_compress_block_params_init(bc7enc_compress_block_params *p)
    bint bc7enc_compress_block(void *pDst, const void *pSrc,
                               const bc7enc_compress_block_params *p)

def compress_bc7(cnp.uint8_t[:, :, :] rgba_array):
    cdef int height = rgba_array.shape[0]
    cdef int width = rgba_array.shape[1]

    if rgba_array.shape[2] != 4:
        raise ValueError("Input must be RGBA (4 channels)")

    if width % 4 != 0 or height % 4 != 0:
        raise ValueError("Dimensions must be multiples of 4")

    bc7enc_compress_block_init()

    cdef bc7enc_compress_block_params params
    bc7enc_compress_block_params_init(&params)

    cdef int num_blocks_x = width // 4
    cdef int num_blocks_y = height // 4
    cdef int total_blocks = num_blocks_x * num_blocks_y
    cdef int output_size = total_blocks * 16

    cdef cnp.ndarray[cnp.uint8_t, ndim=1] output = np.empty(
        output_size, dtype=np.uint8
    )

    cdef uint8_t* block_pixels = <uint8_t*>malloc(64)
    cdef int block_x, block_y, y
    cdef int block_idx = 0

    try:
        for block_y in range(num_blocks_y):
            for block_x in range(num_blocks_x):
                for y in range(4):
                    py = block_y * 4 + y
                    px = block_x * 4
                    memcpy(
                        &block_pixels[y * 16],
                        &rgba_array[py, px, 0],
                        16
                    )

                bc7enc_compress_block(
                    &output[block_idx * 16],
                    block_pixels,
                    &params
                )
                block_idx += 1
    finally:
        free(block_pixels)

    return output
