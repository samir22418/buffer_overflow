/*
 * Local-only reference source for the training notes.
 *
 * This file is intentionally vulnerable and is included for discussion. The
 * Python lab is the supported runnable implementation in this workspace because
 * no C compiler is available in the current environment.
 */

#include <stdio.h>
#include <string.h>

void vulnerable_copy(const char *input) {
    char buffer[64];
    strcpy(buffer, input);
    printf("copied: %.64s\n", buffer);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <input>\n", argv[0]);
        return 1;
    }

    vulnerable_copy(argv[1]);
    return 0;
}
