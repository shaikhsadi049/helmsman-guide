exec(open("eqcurve.py").read().split('row("dd*edge max5 (current)")')[0])
for mx in (1.5, 2, 2.5, 3, 4, 5):
    for fdd in (0.1, 0.15, 0.2):
        row(f"max{mx} fullDD{int(fdd*100)}", mx=mx, full_dd=fdd)
