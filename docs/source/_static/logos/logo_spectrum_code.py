import matplotlib.pyplot as plt
from skycalc_ipy import SkyCalc
skycalc = SkyCalc()
skycalc["wmin"] = 500
skycalc["wmax"] = 30000
skycalc["wdelta"] = 2
tbl = skycalc.get_sky_spectrum()
plt.figure(figsize=(15,5))
plt.plot(tbl["lam"], tbl["flux"], c="maroon", lw=2)
plt.xlabel("Wavelength " + str(tbl["lam"].unit))
plt.ylabel("Flux " + str(tbl["flux"].unit))
plt.loglog()
