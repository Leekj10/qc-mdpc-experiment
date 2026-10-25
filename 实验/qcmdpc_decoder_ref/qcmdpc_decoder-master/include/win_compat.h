/* Windows/mingw compat shim (2026-09-03), forced-include via -include.
 * zig's mingw-w64 header set does not declare C11 aligned_alloc.
 * We build WITHOUT AVX, so the 32-byte alignment is a pure performance
 * hint upstream; falling back to malloc keeps free() semantics correct
 * (_aligned_malloc would require _aligned_free and break upstream free()).
 * No algorithmic change. */
#pragma once
#ifdef _WIN32
#include <stdlib.h>
#ifndef QCMDPC_ALIGNED_ALLOC_SHIM
#define QCMDPC_ALIGNED_ALLOC_SHIM
static inline void *aligned_alloc(size_t alignment, size_t size) {
    (void)alignment;
    return malloc(size);
}
#endif
#endif
