#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "param.h"
#include "types.h"
#include "code.h"
#include "decoder.h"

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s instances.bin\n", argv[0]);
        return 2;
    }
    FILE *fh = fopen(argv[1], "rb");
    if (!fh) {
        perror("fopen");
        return 2;
    }
    char magic[4];
    uint32_t hdr[5];
    if (fread(magic, 1, 4, fh) != 4 || fread(hdr, sizeof(uint32_t), 5, fh) != 5) {
        fprintf(stderr, "short header\n");
        return 2;
    }
    if (memcmp(magic, "QMD1", 4) != 0) {
        fprintf(stderr, "bad magic\n");
        return 2;
    }
    uint32_t r = hdr[0], d = hdr[1], t = hdr[2], nk = hdr[3], ne = hdr[4];
    if (r != BLOCK_LENGTH || d != BLOCK_WEIGHT || t != ERROR_WEIGHT) {
        fprintf(stderr, "parameter mismatch: file %u/%u/%u, build %u/%u/%u\n",
                r, d, t, (unsigned)BLOCK_LENGTH, (unsigned)BLOCK_WEIGHT,
                (unsigned)ERROR_WEIGHT);
        return 2;
    }

    uint16_t *supp = malloc((size_t)nk * 2 * d * sizeof(uint16_t));
    if (!supp || fread(supp, sizeof(uint16_t), (size_t)nk * 2 * d, fh)
                    != (size_t)nk * 2 * d) {
        fprintf(stderr, "short key section\n");
        return 2;
    }
    uint16_t *pos = malloc((size_t)t * sizeof(uint16_t));
    long *fails = calloc(nk, sizeof(long));
    if (!pos || !fails) {
        fprintf(stderr, "oom\n");
        return 2;
    }

    code_t H;
    e_t e __attribute__((aligned(32)));
    syndrome_t syn __attribute__((aligned(32)));
    decoder_t dec = aligned_alloc(32, sizeof(struct decoder));
    if (!dec) {
        fprintf(stderr, "oom dec\n");
        return 2;
    }
    init_decoder(dec, &H, &e, &syn);

    for (uint32_t ki = 0; ki < nk; ++ki) {
        memset(&H, 0, sizeof(H));
        for (uint32_t b = 0; b < INDEX; ++b)
            for (uint32_t l = 0; l < d; ++l)
                H.columns[b][l] = supp[(size_t)(ki * INDEX + b) * d + l];
        transpose_columns(&H);

        for (uint32_t eid = 0; eid < ne; ++eid) {
            if (fread(pos, sizeof(uint16_t), t, fh) != t) {
                fprintf(stderr, "short error section at key %u error %u\n", ki, eid);
                return 2;
            }
            memset(&e, 0, sizeof(e));
            for (uint32_t j = 0; j < t; ++j) {
                uint32_t p = pos[j];
                if (p < r)
                    e.vec[0][p] ^= 1;
                else
                    e.vec[1][p - r] ^= 1;
            }
            e.weight = t;
            reset_decoder(dec);
            compute_syndrome(&syn, &H, &e);
            if (!qcmdpc_decode(dec, 20)) {
                fails[ki]++;
                if (getenv("DUMP"))
                    printf("F %u %u\n", ki, eid);
            }
        }
        printf("%u %ld\n", ki, fails[ki]);
    }

    fclose(fh);
    free(supp);
    free(pos);
    free(fails);
    free(dec);
    return 0;
}
