#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

unsigned char flash[16777216];

uint32_t random_generator(uint32_t *state) {
    *state = (*state) * 0x41c64e6d + 0x0008042a;
    uint32_t s = *state;
    return s % 16777215;
}

int main() {
    FILE *f = fopen("flash_memory_dump.bin", "rb");
    if (!f) { perror("fopen"); return 1; }
    fread(flash, 1, 16777216, f);
    fclose(f);

    for (uint32_t seed = 0; seed <= 99999999; seed++) {
        uint32_t state = seed;
        
        uint32_t r1, r2, r3;
        r1 = random_generator(&state);
        uint32_t addr = (r1 & 0xFF0000);
        r2 = random_generator(&state);
        addr += (r2 & 0xFF00);
        r3 = random_generator(&state);
        addr += (r3 & 0xFF);
        
        if (flash[addr] != 'H') continue;
        
        r1 = random_generator(&state);
        addr = (r1 & 0xFF0000);
        r2 = random_generator(&state);
        addr += (r2 & 0xFF00);
        r3 = random_generator(&state);
        addr += (r3 & 0xFF);
        
        if (flash[addr] != 'T') continue;
        
        r1 = random_generator(&state);
        addr = (r1 & 0xFF0000);
        r2 = random_generator(&state);
        addr += (r2 & 0xFF00);
        r3 = random_generator(&state);
        addr += (r3 & 0xFF);
        
        if (flash[addr] != 'B') continue;
        
        r1 = random_generator(&state);
        addr = (r1 & 0xFF0000);
        r2 = random_generator(&state);
        addr += (r2 & 0xFF00);
        r3 = random_generator(&state);
        addr += (r3 & 0xFF);
        
        if (flash[addr] != '{') continue;

        printf("FOUND SEED: %u\n", seed);

        state = seed;
        for (int i = 0; i < 49; i++) {
            r1 = random_generator(&state);
            addr = (r1 & 0xFF0000);
            r2 = random_generator(&state);
            addr += (r2 & 0xFF00);
            r3 = random_generator(&state);
            addr += (r3 & 0xFF);
            printf("%c", flash[addr]);
        }
        printf("\n");
    }

    printf("Done.\n");
    return 0;
}
