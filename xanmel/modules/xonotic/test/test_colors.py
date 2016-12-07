from xanmel.modules.xonotic.colors import Color


def test_colors():
    test_xonotic_string = b'^xE20Tri^xF40flu^xFB0ope^xCB0raz^xAF1ine^7\xee\x83\x81\xee\x83\x82\xee\x83\x83\xee\x83\x84\xe2\x97\x86\xf0\x9f\x8c\x8f\xf0\x9f\x8c\x8e'
    assert Color.dp_to_irc(test_xonotic_string).decode('utf8') == '\x0304Tri\x0304flu\x0307ope\x0307raz\x0307ine\x0fABCD◆🌏🌎\x0f'
    assert Color.dp_to_none(test_xonotic_string).decode('utf8') == 'TrifluoperazineABCD◆🌏🌎'
    test_irc_string = b'\x0304Tri\x0304flu\x0307ope\x0307raz\x0307ine\x0fABCD\xe2\x97\x86\xf0\x9f\x8c\x8f\xf0\x9f\x8c\x8e\x0f'
    assert Color.irc_to_dp(test_irc_string).decode('utf8') == '^1Tri^1flu^x5a0ope^x5a0raz^x5a0ine^7ABCD◆🌏🌎^7'
    assert Color.irc_to_none(test_irc_string).decode('utf8') == 'TrifluoperazineABCD◆🌏🌎'
