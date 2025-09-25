from app.services.diff import unified_diff


def test_unified_diff_added():
    old = "<html>\n<body></body>\n</html>\n"
    new = "<html>\n<body>Hi</body>\n</html>\n"
    d = unified_diff(old, new)
    assert "+<body>Hi</body>" in d


def test_unified_diff_removed():
    old = "<html>\n<body>Hi</body>\n</html>\n"
    new = "<html>\n<body></body>\n</html>\n"
    d = unified_diff(old, new)
    assert "-<body>Hi</body>" in d
