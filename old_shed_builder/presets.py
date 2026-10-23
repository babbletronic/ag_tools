from .model import Settings


def dilapidated():
    s = Settings()
    s.leakage = 0.7
    s.missing = 0.065
    s.leak_loose = 0.16
    s.leak_gap = 0.009
    s.leak_separation = 0.035
    s.broken = 0.065
    s.aging = 0.8
    s.dirt = 0.42
    s.walls["Rear"].override = True
    s.walls["Rear"].amount = 0.85
    s.walls["Rear"].gap = 0.012
    s.walls["Rear"].missing = 0.07
    s.walls["Rear"].loose = 0.14
    return s
