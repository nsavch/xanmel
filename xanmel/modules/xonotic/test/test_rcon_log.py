def test_feed(log_parser, mocker):
    log_parser.feed(b'test')
    assert log_parser.current == b'test'
    log_parser.feed(b'foobar')
    assert log_parser.current == b'testfoobar'
    log_parser.feed(b'a\nnewline')
    assert log_parser.current == b'newline'
