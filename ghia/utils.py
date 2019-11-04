def parse_rules(cfg):
    """
    Parse labels to dict where label is key and list
    of patterns is corresponding value
    cfg: ConfigParser with loaded configuration of labels
    """
    patterns = {
        username: list(filter(None, cfg['patterns'][username].splitlines()))
        for username in cfg['patterns']
    }
    fallback = cfg.get('fallback', 'label', fallback=None)
    for user_patterns in patterns.values():
        for pattern in user_patterns:
            t, p = pattern.split(':', 1)
            assert t in GHIA.MATCHERS.keys()
    return patterns, fallback
