# Stolen dishonestly from Melanobot: https:#github.com/mbasaglia/Melanobot
import re


class Color:
    NOCOLOR = 0
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7

    BRIGHT = True
    DARK = False

    irc_regex = re.compile(b'(\3([0-9][0-9]?)?(,[0-9][0-9]?)?)|\x0f|\1|\2|\x16|\x1f')
    dp_regex = re.compile(b'(\^\^)|(\^[0-9])|(\^x[0-9a-fA-F]{3})')

    def __init__(self, code, bright=False):
        self.code = int(code)
        self.bright = bright

    @classmethod
    def irc_to_none(cls, text):
        return cls.irc_regex.sub(b'', text)

    @classmethod
    def irc_to_dp(cls, text):
        return b''

    @classmethod
    def dp_to_irc(cls, text):
        def __repl(matchobj):
            if matchobj.group(0) == b'^^':
                return b'^'
            else:
                return cls.from_dp(matchobj.group(0)).irc()

        return cls.dp_regex.sub(__repl, cls.dp_char_convert(text) + b'\x0f')

    def irc(self):
        if self.bright:
            out = {
                0: b'14',
                1: b'04',
                2: b'09',
                3: b'07',
                4: b'12',
                5: b'13',
                6: b'11',
                7: None
            }[self.code]
        else:
            out = {
                0: b'01',
                1: b'05',
                2: b'03',
                3: b'07',
                4: b'02',
                5: b'06',
                6: b'10',
                7: b'15'
            }[self.code]
        if not out:
            return b'\x0f'
        return b'\3' + out

    @classmethod
    def from_dp(cls, color):
        if isinstance(color, bytes):
            color = color.decode('ascii')
        if len(color) == 2 and int(color[1]) < 8:
            code = int(color[1])
            if code == 5:
                return cls(6, cls.BRIGHT)
            elif code == 6:
                return cls(5, cls.BRIGHT)
            else:
                return cls(code, cls.BRIGHT)
        elif len(color) == 5:
            return cls.from_12hex(color[2:])
        else:
            return cls(cls.NOCOLOR)

    @classmethod
    def from_12hex(cls, color):
        if isinstance(color, bytes):
            color = color.decode('ascii')
        if len(color) < 3:
            return cls(cls.NOCOLOR)
        r = int(color[0], 16)
        g = int(color[1], 16)
        b = int(color[2], 16)
        v = max(r, g, b)
        cmin = min(r, g, b)
        d = v - cmin
        if d == 0:
            c = 0
        else:
            if r == v:
                h = (g - b) / d
            elif g == v:
                h = (b - r) / d + 2
            else:
                h = (r - g) / d + 4
            s = d / v
            if s > 0.3:
                if h < 0:
                    h += 6
                if h < 0.5:
                    c = cls.RED
                elif h < 1.5:
                    c = cls.YELLOW
                elif h < 2.5:
                    c = cls.GREEN
                elif h < 3.5:
                    c = cls.CYAN
                elif h < 4.5:
                    c = cls.BLUE
                elif h < 5.5:
                    c = cls.MAGENTA
                else:
                    c = cls.RED
            elif v > 7:
                c = 7
            else:
                c = 0
        return cls(c, v > 9)

    @staticmethod
    def dp_char_convert(text):
        out = b''
        bytes_l = []
        length = 0
        unicode_char = b''
        for char_byte in text:
            c = bytes([char_byte])
            if char_byte < 128:
                # Ascii
                out += c
            else:
                if len(bytes_l) == 0:
                    unicode_char = b''
                    length = 0
                    while char_byte & 0x80:
                        length += 1
                        char_byte <<= 1
                    if length < 2:
                        continue
                    char_byte >>= length
                bytes_l.append(char_byte)
                unicode_char += c
                if len(bytes_l) == length:
                    unicode_l = 0
                    for byte in bytes_l:
                        unicode_l <<= 6
                        unicode_l |= byte & 63
                    if (unicode_l & 0xFF00) == 0xE000:
                        out += qfont_table[unicode_l & 0xFF].encode('utf8')
                    else:
                        out += unicode_char
                    bytes_l = []
        return out



qfont_table = [
    '', ' ', '-', ' ', '_', '#', '+', '·', 'F', 'T', ' ', '#', '·', '<', '#', '#',               # 0
    '[', ']', ':)', ':)', ':(', ':P', ':/', ':D', '«', '»', '·', '-', '#', '-', '-', '-',        # 1
    '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?',              # 2
    '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?',              # 3
    '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?',              # 4
    '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?',              # 5
    '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?',              # 6
    '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?',              # 7
    '=', '=', '=', '#', '¡', '[o]', '[u]', '[i]', '[c]', '[c]', '[r]', '#', '¿', '>', '#', '#',  # 8
    '[', ']', ':)', ':)', ':(', ':P', ':/', ':D', '«', '»', '#', 'X', '#', '-', '-', '-',        # 9
    ' ', '!', '"', '#', '$', '%', '&', '\'', '(', ')', '*', '+', ',', '-', '.', '/',             # 10
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?',              # 11
    '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',              # 12
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_',             # 13
    '.', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',              # 14
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '{', '|', '}', '~', '<'               # 15
]
