def parse_rules(cfg):
    return {
        rule: list(filter(None, cfg['patterns'][rule].splitlines()))
        for rule in cfg['patterns']
    }

def parse_fallback(cfg):
    return {
        label: list(filter(None, cfg['fallback'][label].splitlines()))
        for label in cfg['fallback']
    }
