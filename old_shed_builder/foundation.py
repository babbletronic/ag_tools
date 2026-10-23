from .geometry import box


def build(ctx, s):
    c = ctx.collections["Foundation"]
    for ix, x in enumerate((-s.width / 2 + 0.2, s.width / 2 - 0.2)):
        for iy, y in enumerate((-s.length / 2 + 0.2, 0, s.length / 2 - 0.2)):
            box(
                ctx,
                f"foundation.pier.{ix}.{iy}",
                (x, y, s.foundation_height / 2),
                (0.3, 0.3, s.foundation_height),
                c,
                "Concrete",
            )
