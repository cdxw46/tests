"""
CTF Challenge: Validation (50pts)
URL: https://ictf-validation.iciaran.workers.dev/

The challenge uses frontend-only validation via HTML pattern attributes and CSS
selectors to validate each character of the flag. By analyzing the HTML source
and CSS stylesheet, we can extract every character.

Sources of validation:
1. HTML `pattern` attributes on <input> elements constrain certain positions
   to character ranges (e.g. [i], [e-g], [3-5], etc.)
2. CSS selectors in style.css use :nth-child() and [value="..."] attribute
   selectors with CSS unicode escapes (\XX) to turn inputs green only when
   the correct character is entered.

Flag: ictf{c55_0nly_v4l1d4t10n_7668ee90}
Leet-decoded: css_only_validation
"""

import re

flag = [None] * 35  # 1-indexed, 34 characters total

# --- HTML pattern attributes (1-indexed position → regex) ---
# pos 1:  pattern="[i]"
flag[1] = 'i'
# pos 4:  pattern="[e-g]" → 'f' (ictf format)
flag[4] = 'f'
# pos 9:  pattern="[^a-zA-Z0-9\x7b\x7d]" → '_'
flag[9] = '_'
# pos 12: pattern="[j-n]" → 'l'
flag[12] = 'l'
# pos 14: pattern="\x5f" → '_'
flag[14] = '_'
# pos 16: pattern="[3-5]" → '4'
flag[16] = '4'
# pos 21: pattern="[r-v]" → 't'
flag[21] = 't'
# pos 26: pattern="[7]" → '7'
flag[26] = '7'
# pos 32: pattern="\x39" → '9'
flag[32] = '9'

# --- CSS selector values (using CSS unicode escapes like \74 = 't') ---
flag[2]  = chr(0x63)  # \63 = 'c'
flag[3]  = chr(0x74)  # \74 = 't'
flag[5]  = '{'
flag[6]  = 'c'
flag[7]  = chr(0x35)  # \35 = '5'
flag[8]  = '5'
flag[10] = '0'
flag[11] = chr(0x6e)  # \6e = 'n'
flag[13] = chr(0x79)  # \79 = 'y'
flag[15] = 'v'
flag[17] = 'l'
flag[18] = '1'
flag[19] = chr(0x64)  # \64 = 'd'
flag[20] = '4'
flag[22] = '1'
flag[23] = '0'
flag[24] = chr(0x6e)  # \6e = 'n'
flag[25] = chr(0x5f)  # \5f = '_'
flag[27] = chr(0x36)  # \36 = '6'
flag[28] = '6'
flag[29] = '8'
flag[30] = chr(0x65)  # \65 = 'e'
flag[31] = 'e'
flag[33] = '0'
flag[34] = '}'

result = ''.join(flag[1:])
print(f"Flag: {result}")

# Verify HTML patterns
html_patterns = {
    1: r'[i]', 4: r'[e-g]', 9: r'[^a-zA-Z0-9\x7b\x7d]',
    12: r'[j-n]', 16: r'[3-5]', 21: r'[r-v]', 26: r'[7]', 32: r'\x39',
}
for pos, pat in html_patterns.items():
    assert re.fullmatch(pat, result[pos - 1]), f"pos {pos} failed"

print("All validations passed.")
